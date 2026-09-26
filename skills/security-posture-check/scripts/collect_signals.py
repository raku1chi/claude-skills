#!/usr/bin/env python3
"""Collect security-relevant facts ("signals") from a source repository.

Part of the security-posture-check skill. Everything reported here is a
signal for a reviewer to verify by reading the code -- never a verdict.

Guarantees:
  * Read-only and local-only: no network access; writes only to --output.
  * Python 3.8+ standard library only.
  * Secret-like values are masked everywhere in the output.

Usage:
  python3 collect_signals.py [ROOT] [--format md|json] [--output FILE]
                             [--scan-history N] [--max-hits N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict

try:  # Python 3.11+
    import tomllib  # type: ignore
except ImportError:  # pragma: no cover - older Pythons fall back to regex parsing
    tomllib = None

VERSION = "1.0.0"
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 25_000
SNIPPET_CHARS = 160
EXAMPLES_PER_CATEGORY = 5

# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

SKIP_DIR_NAMES = {
    ".git", ".hg", ".svn", "node_modules", "bower_components", "jspm_packages",
    "vendor", "third_party", "third-party", ".venv", "venv", "site-packages",
    "__pycache__", ".tox", ".nox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", "out", ".next", ".nuxt", ".svelte-kit", ".output", ".vercel",
    "target", ".gradle", ".terraform", "coverage", ".nyc_output", ".cache",
    ".parcel-cache", ".turbo", "Pods", "DerivedData", ".idea",
}

LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lock", "bun.lockb", "poetry.lock", "Pipfile.lock", "uv.lock", "pdm.lock",
    "Cargo.lock", "go.sum", "composer.lock", "Gemfile.lock", "packages.lock.json",
    "pubspec.lock", "Package.resolved", "mix.lock", "gradle.lockfile", "flake.lock",
}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff", ".svg",
    ".pdf", ".zip", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".jar", ".war",
    ".ear", ".class", ".so", ".dll", ".dylib", ".exe", ".bin", ".wasm", ".woff",
    ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".mov", ".avi", ".webm",
    ".ogg", ".wav", ".flac", ".psd", ".sketch", ".fig", ".pyc", ".pyo", ".o",
    ".a", ".lib", ".map", ".db", ".sqlite", ".sqlite3", ".parquet", ".pkl",
    ".npy", ".npz", ".onnx", ".pt", ".pth", ".safetensors", ".h5", ".dmg",
    ".iso", ".apk", ".aab", ".ipa", ".msi", ".deb", ".rpm", ".whl", ".gem",
    ".nupkg", ".lockb",
}

ARTIFACT_EXTS = {
    ".exe", ".dll", ".so", ".dylib", ".jar", ".war", ".ear", ".class", ".pyc",
    ".o", ".a", ".lib", ".bin", ".apk", ".aab", ".ipa", ".msi", ".deb", ".rpm",
    ".dmg", ".whl", ".gem", ".nupkg",
}

LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    ".cts": "TypeScript", ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".go": "Go", ".rb": "Ruby", ".erb": "Ruby", ".php": "PHP", ".java": "Java",
    ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala", ".groovy": "Groovy",
    ".cs": "C#", ".rs": "Rust", ".swift": "Swift", ".m": "Objective-C", ".c": "C",
    ".h": "C/C++", ".cc": "C++", ".cpp": "C++", ".hpp": "C++", ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir", ".sh": "Shell", ".bash": "Shell",
    ".ps1": "PowerShell", ".tf": "Terraform", ".sql": "SQL", ".html": "HTML",
}

JS = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".vue", ".svelte", ".astro"}
PY = {".py"}
GO = {".go"}
RB = {".rb", ".erb", ".rake"}
PHP = {".php", ".phtml"}
JVM = {".java", ".kt", ".kts", ".scala", ".groovy"}
CS = {".cs", ".cshtml", ".razor"}
TEMPLATES = {".html", ".htm", ".jinja", ".jinja2", ".j2", ".njk", ".hbs",
             ".handlebars", ".ejs", ".pug", ".twig", ".liquid", ".mustache"}
SHELLISH = {".sh", ".bash", ".zsh", ".dockerfile", ".yml", ".yaml", ".mk", ".makefile"}
CONFIG = {".env", ".properties", ".yml", ".yaml", ".ini", ".cfg", ".conf", ".toml",
          ".json", ".xml", ".tf", ".tfvars", ".hcl", ".dockerfile"}
CODE = JS | PY | GO | RB | PHP | JVM | CS | {".rs", ".swift", ".dart", ".ex", ".exs", ".c", ".cc", ".cpp"}

TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|fixtures?|testdata|test-data|mocks?|__mocks__|"
    r"examples?|samples?|e2e|cypress|playwright)(/|$)|[._-](test|spec)\.[A-Za-z]+$|_test\.go$|"
    r"(^|/)test_[^/]*\.py$|(^|/)conftest\.py$",
    re.I,
)

SENSITIVE_NAME_RULES = [
    # (glob-ish predicate name, description)
    ("dotenv", "dotenv file"),
    ("private-key-file", "private key / keystore"),
    ("terraform-state", "Terraform state (contains secrets in plain text)"),
    ("terraform-vars", "Terraform variables file (may contain secrets)"),
    ("credential-file", "credential file"),
]
EXAMPLE_SUFFIXES = (".example", ".sample", ".template", ".dist", ".defaults",
                    ".tmpl", ".tpl", ".schema", ".test")


def classify_sensitive_name(rel):
    """Return a sensitive-file category for a path, or None."""
    name = rel.rsplit("/", 1)[-1]
    low = name.lower()
    if low.endswith(EXAMPLE_SUFFIXES) or ".example." in low or ".sample." in low:
        return None
    if low == ".env" or low.startswith(".env.") or low.endswith(".env"):
        return "dotenv"
    if low.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".ppk", ".kdbx")) \
            or low in {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}:
        return "private-key-file"
    if low.endswith((".tfstate", ".tfstate.backup")):
        return "terraform-state"
    if low.endswith(".tfvars") or low.endswith(".tfvars.json"):
        return "terraform-vars"
    if low in {".npmrc", ".pypirc", ".netrc", ".htpasswd", ".git-credentials", ".dockercfg",
               "credentials.json", "credentials", "master.key"} \
            or re.match(r"(client_secret|service[-_]?account)[^/]*\.json$", low) \
            or low.endswith(".ovpn"):
        return "credential-file"
    return None


def pseudo_ext(rel):
    name = rel.rsplit("/", 1)[-1]
    low = name.lower()
    if low in {"dockerfile", "containerfile"} or low.startswith("dockerfile.") or low.endswith(".dockerfile"):
        return ".dockerfile"
    if low == ".env" or low.startswith(".env.") or low.endswith(".env"):
        return ".env"
    if low in {"makefile", "gnumakefile"}:
        return ".makefile"
    if low in {"jenkinsfile"}:
        return ".groovy"
    if low.endswith(".blade.php"):
        return ".php"
    _, ext = os.path.splitext(low)
    return ext


def is_test_path(rel):
    return bool(TEST_PATH_RE.search(rel))


def is_vendored(rel):
    parts = rel.split("/")[:-1]
    return any(p in SKIP_DIR_NAMES for p in parts)


# ---------------------------------------------------------------------------
# Secret detection
# ---------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(
    r"(?i)^(?:x{3,}|\*{3,}|\.{3,}|-{3,}|_{3,}|0{3,}|(?:1234|abcd|qwerty)\w*|change[_-]?me\w*|"
    r"<[^>]*>|\$\{[^}]*\}|\$\([^)]*\)|\{\{[^}]*\}\}|%\([^)]*\)s|"
    r"password|secret|token|none|null|nil|undefined|true|false|todo|tbd|string|required|optional|default)$"
)
# Words that mark a value as a placeholder when they appear as a separate token
# ("your-api-key-here", "dummy_secret"), but not inside random-looking strings.
PLACEHOLDER_TOKEN_RE = re.compile(
    r"(?i)(?:^|[^a-z])(?:example|sample|dummy|placeholder|fake|redacted|replace|insert|here|test|testing|mock|"
    r"your|my|changeme|xxx+|foo|bar|lorem)(?:[^a-z]|$)"
)
ENV_LOOKUP_RE = re.compile(r"(?i)(process\.env|os\.environ|os\.getenv|getenv\(|env\(|ENV\[|System\.getenv|\$\{|\$[A-Z_]{3,}|%[A-Z_]+%|secrets\.)")


def is_placeholder(value):
    v = value.strip().strip("'\"")
    if len(v) < 6:
        return True
    if PLACEHOLDER_RE.match(v) or PLACEHOLDER_TOKEN_RE.search(v) or ENV_LOOKUP_RE.search(v):
        return True
    if len(set(v)) <= 3:  # e.g. "aaaaaaaa", "********"
        return True
    return False


def mask(value):
    v = value.strip()
    if not v:
        return "(empty)"
    keep = 4 if len(v) > 12 else 2
    return "%s...(%d chars)" % (v[:keep], len(v))


# (id, description, regex, confidence, value_group)
SECRET_RULES = [
    ("private-key", "Private key block", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----(?=(?:\\[rn]|\s)+[A-Za-z0-9+/=]{40,})", "high", 0),
    ("aws-access-key-id", "AWS access key ID", r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b", "high", 1),
    ("aws-secret-access-key", "AWS secret access key", r"(?i)aws_?secret_?access_?key[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])", "high", 1),
    ("github-token", "GitHub token", r"\b((?:gh[pousr]_[A-Za-z0-9]{36,255})|(?:github_pat_[A-Za-z0-9_]{22,255}))\b", "high", 1),
    ("gitlab-token", "GitLab token", r"\b(glpat-[A-Za-z0-9_\-]{20,})\b", "high", 1),
    ("slack-token", "Slack token", r"\b(xox[abposr]-[A-Za-z0-9-]{10,})\b", "high", 1),
    ("slack-webhook", "Slack incoming webhook", r"(https://hooks\.slack\.com/services/T[A-Za-z0-9_]+/B[A-Za-z0-9_]+/[A-Za-z0-9_]+)", "high", 1),
    ("discord-webhook", "Discord webhook", r"(https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_\-]+)", "high", 1),
    ("stripe-live-key", "Stripe live secret key", r"\b((?:sk|rk)_live_[A-Za-z0-9]{16,})\b", "high", 1),
    ("stripe-test-key", "Stripe test secret key", r"\b((?:sk|rk)_test_[A-Za-z0-9]{16,})\b", "medium", 1),
    ("google-api-key", "Google API key", r"\b(AIza[0-9A-Za-z_\-]{35})\b", "high", 1),
    ("gcp-service-account", "GCP service account key JSON", r"\"type\"\s*:\s*\"service_account\"", "medium", 0),
    ("anthropic-api-key", "Anthropic API key", r"\b(sk-ant-(?:api|admin)\d{2}-[A-Za-z0-9_\-]{20,})", "high", 1),
    ("openai-api-key", "OpenAI API key", r"\b(sk-(?!ant-)(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{20,})", "medium", 1),
    ("npm-token", "npm access token", r"\b(npm_[A-Za-z0-9]{36})\b", "high", 1),
    ("pypi-token", "PyPI API token", r"\b(pypi-AgEIcHlwaS5vcmc[A-Za-z0-9_\-]{50,})", "high", 1),
    ("sendgrid-key", "SendGrid API key", r"\b(SG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43})\b", "high", 1),
    ("azure-storage-key", "Azure storage account key", r"AccountKey=([A-Za-z0-9+/=]{80,})", "high", 1),
    ("jwt", "JSON Web Token literal", r"\b(eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})", "low", 1),
    ("db-url-credentials", "Connection string with inline password",
     r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|rediss|amqps?|mssql|sqlserver)://[^\s:/@'\"]+:([^\s@'\"/]{3,})@", "medium", 1),
    ("generic-secret-assignment", "Hard-coded secret-like value",
     r"(?i)(?:password|passwd|pwd|secret|api[_\-]?key|apikey|access[_\-]?token|auth[_\-]?token|client[_\-]?secret|private[_\-]?key|secret[_\-]?key|access[_\-]?key)[\"']?\s*(?::|=|:=|=>)\s*[\"']([^\"'\s]{8,})[\"']",
     "low", 1),
]
CONFIG_ASSIGNMENT_RE = re.compile(
    r"(?im)^[ \t]*(?:export[ \t]+|-[ \t]*)?([A-Za-z0-9_.\-]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|APIKEY|PRIVATE_?KEY|ACCESS_?KEY|CLIENT_?SECRET|CREDENTIALS?)[A-Za-z0-9_.\-]*)"
    r"[ \t]*[:=][ \t]*(\"[^\"\n]{6,}\"|'[^'\n]{6,}'|[^\s#'\"{$][^\s#]{5,})[ \t]*(?:#.*)?$"
)
SECRET_RULES_C = [(i, d, re.compile(p), c, g) for (i, d, p, c, g) in SECRET_RULES]
# Cheap substring pre-checks: a rule's regex only runs if one needle is present.
# (needles, case_insensitive)
SECRET_NEEDLES = {
    "private-key": (("PRIVATE KEY",), False), "aws-access-key-id": (("AKIA", "ASIA"), False),
    "aws-secret-access-key": (("aws",), True), "github-token": (("ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_"), False),
    "gitlab-token": (("glpat-",), False), "slack-token": (("xox",), False), "slack-webhook": (("hooks.slack.com",), False),
    "discord-webhook": (("discord",), False), "stripe-live-key": (("_live_",), False), "stripe-test-key": (("_test_",), False),
    "google-api-key": (("AIza",), False), "gcp-service-account": (("service_account",), False),
    "anthropic-api-key": (("sk-ant-",), False), "openai-api-key": (("sk-",), False), "npm-token": (("npm_",), False),
    "pypi-token": (("pypi-",), False), "sendgrid-key": (("SG.",), False), "azure-storage-key": (("AccountKey=",), False),
    "jwt": (("eyJ",), False), "db-url-credentials": (("://",), False),
    "generic-secret-assignment": (("pass", "pwd", "secret", "key", "token"), True),
}
CONFIG_ASSIGNMENT_NEEDLES = ("pass", "secret", "token", "key", "credential")
HISTORY_RULE_IDS = {r[0] for r in SECRET_RULES if r[3] == "high"}


def mask_secrets_in(text):
    """Mask anything that looks like a secret inside an output snippet."""
    for rid, _, rx, _, group in SECRET_RULES_C:
        def _sub(m, group=group):
            if group and m.lastindex and m.group(group):
                s, e = m.span(group)
                return m.string[m.start():s] + mask(m.group(group)) + m.string[e:m.end()]
            return m.group(0)
        text = rx.sub(_sub, text)
    text = CONFIG_ASSIGNMENT_RE.sub(lambda m: m.group(0).replace(m.group(2), mask(m.group(2))), text)
    return text


# ---------------------------------------------------------------------------
# Risky code patterns (hints only)
# ---------------------------------------------------------------------------

def R(rid, title, cwe, exts, pattern, needles=None, context=None, flags=0, file_requires=None,
      absent_after=None, mask_group=None):
    """A risky-pattern rule.

    context      -- regex that must also match the same line
    file_requires-- regex (or compiled pattern) that must match somewhere in the file
    absent_after -- (regex, window): skip the hit if regex appears within `window`
                    chars after the match (stopping at the next ';')
    mask_group   -- regex group whose text is masked in the reported snippet
    """
    if isinstance(file_requires, str):
        file_requires = re.compile(file_requires)
    return {
        "id": rid, "title": title, "cwe": cwe, "exts": exts,
        "re": re.compile(pattern, flags), "needles": needles,
        "ci": bool(flags & re.I),
        "context": re.compile(context, re.I) if context else None,
        "file_requires": file_requires,
        "absent_after": (re.compile(absent_after[0]), absent_after[1]) if absent_after else None,
        "mask_group": mask_group,
    }


SEC_WORDS = r"token|secret|password|passwd|nonce|salt|otp|csrf|session|api[_-]?key|reset|verif|invite"
REQ_JS = r"req\.(?:query|body|params|headers)|request\.(?:query|body|params)|ctx\.(?:query|params|request\.body)|searchParams\.get\s*\("
REQ_PY = r"request\.(?:args|form|values|json|GET|POST|data|files|query_params|path_params|cookies|headers)"
REQ_PHP = r"\$_(?:GET|POST|REQUEST|COOKIE)"

LLM_IMPORT_RE = re.compile(
    r"(?:from\s+['\"]|require\(\s*['\"]|import\s+['\"])(?:openai|@anthropic-ai/[\w-]+|@google/generative-ai|@google/genai|ai|@ai-sdk/[\w-]+|"
    r"langchain|@langchain/[\w-]+|llamaindex|cohere-ai|@mistralai/mistralai|ollama|groq-sdk|@modelcontextprotocol/sdk[\w/.-]*|@openai/agents)['\"]"
    r"|^\s*(?:from|import)\s+(?:openai|anthropic|langchain\w*|langgraph|llama_index|google\.generativeai|google\.genai|vertexai|cohere|mistralai|"
    r"ollama|litellm|transformers|crewai|autogen\w*|mcp|fastmcp|semantic_kernel|dspy|haystack|pydantic_ai|smolagents|agents|claude_agent_sdk|instructor)\b"
    r"|\"github\.com/(?:sashabaranov/go-openai|openai/openai-go|anthropics/anthropic-sdk-go|tmc/langchaingo|google/generative-ai-go)",
    re.M,
)

RISK_RULES = [
    # --- code execution / injection
    R("dynamic-code-eval", "eval / dynamic code execution", "CWE-95", JS,
      r"(?<![\w$.])(?:eval|Function)\s*\(|new\s+Function\s*\(", needles=("eval", "Function")),
    R("dynamic-code-eval", "eval / dynamic code execution", "CWE-95", PY,
      r"(?<![\w.])(?:eval|exec)\s*\(", needles=("eval", "exec")),
    R("dynamic-code-eval", "eval / dynamic code execution", "CWE-95", RB,
      r"(?<![\w.])eval\s*[\(\s]", needles=("eval",)),
    R("dynamic-code-eval", "eval / dynamic code execution", "CWE-95", PHP,
      r"(?<![\w>$])(?:eval|create_function)\s*\(|\bassert\s*\(\s*\$", needles=("eval", "create_function", "assert")),
    R("os-command-shell", "OS command execution through a shell", "CWE-78", JS,
      r"(?:\b(?:child_process|childProcess|cp)\.|(?<!async )(?<![\w$.]))(?:exec|execSync)\s*\((?![^)\n]*\)\s*\{)|\bshell\s*:\s*true",
      needles=("exec", "shell:"), file_requires=r"child_process"),
    R("os-command-shell", "OS command execution through a shell", "CWE-78", PY,
      r"\bshell\s*=\s*True|\bos\.(?:system|popen)\s*\(|\bcommands\.getoutput\s*\(",
      needles=("shell", "os.system", "os.popen", "commands.")),
    R("os-command-shell", "OS command execution through a shell", "CWE-78", GO,
      r"exec\.Command(?:Context)?\s*\((?:\s*ctx\s*,)?\s*\"(?:/bin/)?(?:ba)?sh\"\s*,\s*\"-c\"", needles=("exec.Command",)),
    R("os-command-shell", "OS command execution through a shell", "CWE-78", RB,
      r"(?<![\w.])(?:system|exec|spawn)\s*\(?\s*\"[^\"\n]*#\{|`[^`\n]*#\{|%x[\(\{\[]", needles=("system", "exec", "spawn", "`", "%x")),
    R("os-command-shell", "OS command execution through a shell", "CWE-78", PHP,
      r"(?<![\w>$])(?:shell_exec|exec|system|passthru|popen|proc_open)\s*\([^)\n]*\$", needles=("exec", "system", "passthru", "popen")),
    R("os-command-shell", "OS command execution", "CWE-78", JVM,
      r"Runtime\.getRuntime\(\)\.exec\s*\(|new\s+ProcessBuilder\s*\(", needles=("exec", "ProcessBuilder")),
    R("os-command-shell", "OS command execution", "CWE-78", CS,
      r"Process\.Start\s*\(|new\s+ProcessStartInfo\s*\(", needles=("Process",)),
    R("sql-string-building", "SQL built by string interpolation/concatenation", "CWE-89", JS,
      r"(?<![\w$])(?:query|execute|raw|run|all|get|prepare|exec|unsafe)\s*\(\s*`[^`]*\b(?:SELECT|INSERT|UPDATE|DELETE)\b[^`]*\$\{"
      r"|(?<![\w$])(?:query|execute|raw)\s*\(\s*['\"][^'\"\n]*\b(?:SELECT|INSERT|UPDATE|DELETE)\b[^'\"\n]*['\"]\s*\+"
      r"|\$(?:queryRawUnsafe|executeRawUnsafe)\s*\(",
      needles=("select", "insert", "update", "delete", "unsafe"), flags=re.I),
    R("sql-string-building", "SQL built by string formatting", "CWE-89", PY,
      r"\.(?:execute|executemany|executescript|raw|extra|exec_driver_sql)\s*\(\s*(?:f['\"]|['\"][^'\"\n]*['\"]\s*(?:%|\.format\s*\(|\+))"
      r"|\btext\s*\(\s*f['\"]",
      needles=("execute", "raw", "extra", "text(")),
    R("sql-string-building", "SQL built by string formatting", "CWE-89", GO,
      r"\.(?:Query|QueryRow|Exec|QueryContext|QueryRowContext|ExecContext|Raw|Where)\s*\((?:\s*ctx\s*,)?\s*(?:fmt\.Sprintf\s*\(|\"[^\"\n]*\"\s*\+)",
      needles=("Query", "Exec", "Raw", "Where")),
    R("sql-string-building", "SQL built by string interpolation", "CWE-89", RB,
      r"\b(?:where|find_by_sql|execute|exec_query|select|order|group|having|joins|pluck|from)\s*\(?\s*\"[^\"\n]*#\{",
      needles=("#{",)),
    R("sql-string-building", "SQL built by string concatenation", "CWE-89", PHP,
      r"(?:mysql_query|mysqli_query|->query|->exec|pg_query)\s*\(\s*(?:\$\w+\s*,\s*)?(?:\"[^\"\n]*\$\w+|'[^'\n]*'\s*\.\s*\$|\"[^\"\n]*\"\s*\.\s*\$)",
      needles=("query", "exec")),
    R("sql-string-building", "SQL built by string concatenation", "CWE-89", JVM,
      r"(?:executeQuery|executeUpdate|execute|prepareStatement|createQuery|createNativeQuery)\s*\(\s*\"[^\"\n]*\"\s*\+",
      needles=("execute", "prepare", "Query")),
    R("sql-string-building", "SQL built by string interpolation/concatenation", "CWE-89", CS,
      r"(?:SqlCommand|ExecuteSqlRaw|FromSqlRaw|ExecuteSqlCommand)\s*\(\s*(?:\$\"[^\"\n]*\{|\"[^\"\n]*\"\s*\+)|CommandText\s*=\s*(?:\$\"[^\"\n]*\{|\"[^\"\n]*\"\s*\+)",
      needles=("Sql", "CommandText")),
    R("nosql-operator-injection", "MongoDB $where / operator injection risk", "CWE-943", JS,
      r"\$where\b|\.find(?:One)?\s*\(\s*req\.(?:body|query)\s*\)", needles=("$where", "find")),
    # --- XSS / templating
    R("unsafe-html-sink", "Unescaped HTML output / dangerous DOM sink", "CWE-79", JS,
      r"dangerouslySetInnerHTML|\.(?:inner|outer)HTML\s*=|document\.write(?:ln)?\s*\(|insertAdjacentHTML\s*\(|\bv-html\s*=|\{@html\s",
      needles=("dangerouslySetInnerHTML", "HTML", "document.write", "v-html", "@html")),
    R("unsafe-html-sink", "Autoescape bypass", "CWE-79", PY,
      r"\bmark_safe\s*\(|\bMarkup\s*\(|render_template_string\s*\(|autoescape\s*=\s*False",
      needles=("mark_safe", "Markup", "render_template_string", "autoescape")),
    R("unsafe-html-sink", "Unescaped template output", "CWE-79", TEMPLATES,
      r"\|\s*safe\b|\{%-?\s*autoescape\s+(?:off|false)|<%-|\{\{\{|\{!!",
      needles=("safe", "autoescape", "<%-", "{{{", "{!!")),
    R("unsafe-html-sink", "Unescaped output", "CWE-79", RB,
      r"\.html_safe\b|(?<![\w.])raw\s*\(|<%==", needles=("html_safe", "raw", "<%==")),
    R("unsafe-html-sink", "Unescaped output", "CWE-79", PHP,
      r"\{!!|(?:echo|print)\s+" + REQ_PHP, needles=("{!!", "$_")),
    R("unsafe-html-sink", "html/template escaping bypass", "CWE-79", GO,
      r"template\.(?:HTML|JS|JSStr|URL)\s*\(", needles=("template.",)),
    # --- deserialization
    R("unsafe-deserialization", "Deserialization of potentially untrusted data", "CWE-502", PY,
      r"\b(?:pickle|cPickle|dill)\.loads?\s*\(|\bjoblib\.load\s*\(|\byaml\.(?:unsafe_load|load_all|full_load)\s*\("
      r"|\byaml\.load\s*\((?![^)\n]*Loader\s*=\s*(?:yaml\.)?C?SafeLoader)|\btorch\.load\s*\((?![^)\n]*weights_only\s*=\s*True)",
      needles=("pickle", "dill", "joblib", "yaml", "torch.load")),
    R("remote-model-code", "Model loading that executes code from the model repository", "CWE-94", PY,
      r"trust_remote_code\s*=\s*True", needles=("trust_remote_code",)),
    R("unsafe-deserialization", "Deserialization of potentially untrusted data", "CWE-502", RB,
      r"\bMarshal\.load\s*\(|\bYAML\.(?:unsafe_load|load)\s*\(|\bOj\.load\s*\(", needles=("Marshal", "YAML", "Oj.")),
    R("unsafe-deserialization", "Deserialization of potentially untrusted data", "CWE-502", PHP,
      r"\bunserialize\s*\(", needles=("unserialize",)),
    R("unsafe-deserialization", "Deserialization of potentially untrusted data", "CWE-502", JVM,
      r"new\s+ObjectInputStream\s*\(|\bXMLDecoder\s*\(|enableDefaultTyping\s*\(|activateDefaultTyping\s*\(|new\s+Yaml\s*\(\s*\)",
      needles=("ObjectInputStream", "XMLDecoder", "DefaultTyping", "Yaml")),
    R("unsafe-deserialization", "Deserialization of potentially untrusted data", "CWE-502", CS,
      r"\bBinaryFormatter\b|TypeNameHandling\s*=\s*TypeNameHandling\.(?:All|Auto|Objects|Arrays)|\bLosFormatter\b|\bNetDataContractSerializer\b",
      needles=("BinaryFormatter", "TypeNameHandling", "LosFormatter", "NetDataContract")),
    R("unsafe-deserialization", "Deserialization of potentially untrusted data", "CWE-502", JS,
      r"['\"]node-serialize['\"]|\bunserialize\s*\(", needles=("serialize",)),
    # --- TLS / crypto / randomness
    R("tls-verification-disabled", "TLS certificate verification disabled", "CWE-295", JS,
      r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED|strictSSL\s*:\s*false",
      needles=("rejectUnauthorized", "NODE_TLS_REJECT_UNAUTHORIZED", "strictSSL")),
    R("tls-verification-disabled", "TLS certificate verification disabled", "CWE-295", PY,
      r"\bverify\s*=\s*False|_create_unverified_context|\bCERT_NONE\b|check_hostname\s*=\s*False",
      needles=("verify", "unverified", "CERT_NONE", "check_hostname")),
    R("tls-verification-disabled", "TLS certificate verification disabled", "CWE-295", GO,
      r"InsecureSkipVerify\s*:\s*true", needles=("InsecureSkipVerify",)),
    R("tls-verification-disabled", "TLS certificate verification disabled", "CWE-295", RB,
      r"VERIFY_NONE|ssl_verify\w*\s*(?::|=>|=)\s*false", needles=("VERIFY_NONE", "ssl_verify")),
    R("tls-verification-disabled", "TLS certificate verification disabled", "CWE-295", PHP,
      r"CURLOPT_SSL_VERIFY(?:PEER|HOST)\s*,\s*(?:false|0)|['\"]verify['\"]\s*=>\s*false", needles=("CURLOPT_SSL_VERIFY", "verify")),
    R("tls-verification-disabled", "TLS certificate verification disabled", "CWE-295", JVM,
      r"TrustAllCerts|trustAllCerts|NoopHostnameVerifier|ALLOW_ALL_HOSTNAME_VERIFIER|checkServerTrusted\s*\([^)]*\)\s*(?:throws\s+\w+\s*)?\{\s*\}",
      needles=("rustAll", "HostnameVerifier", "checkServerTrusted")),
    R("tls-verification-disabled", "TLS certificate verification disabled", "CWE-295", CS,
      r"ServerCertificateCustomValidationCallback\s*=|ServerCertificateValidationCallback\s*\+?=|DangerousAcceptAnyServerCertificateValidator",
      needles=("CertificateCustomValidationCallback", "CertificateValidationCallback", "DangerousAcceptAny")),
    R("tls-verification-disabled", "Insecure download (TLS verification disabled)", "CWE-295", SHELLISH,
      r"\bcurl\b[^\n|;]*(?:\s-k\b|\s--insecure\b)|\bwget\b[^\n|;]*--no-check-certificate", needles=("curl", "wget")),
    R("download-without-integrity-check", "Remote script piped straight into a shell", "CWE-494", SHELLISH,
      r"\b(?:curl|wget)\b[^\n|;]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b", needles=("curl", "wget")),
    R("weak-crypto", "Weak hash/cipher (check whether used for security)", "CWE-327", JS,
      r"createHash\s*\(\s*['\"](?:md5|sha1)['\"]|createCipheriv?\s*\(\s*['\"](?:des|rc4|[^'\"]*-ecb)[^'\"]*['\"]|\bcreateCipher\s*\(",
      needles=("createHash", "createCipher")),
    R("weak-crypto", "Weak hash/cipher (check whether used for security)", "CWE-327", PY,
      r"hashlib\.(?:md5|sha1)\s*\((?![^)\n]*usedforsecurity\s*=\s*False)|hashlib\.new\s*\(\s*['\"](?:md5|sha1)['\"](?![^)\n]*usedforsecurity\s*=\s*False)|\bDES\.new\s*\(|\bARC4\.new\s*\(|MODE_ECB",
      needles=("md5", "sha1", "DES", "ARC4", "MODE_ECB")),
    R("weak-crypto", "Weak hash/cipher (check whether used for security)", "CWE-327", GO,
      r"\b(?:md5|sha1)\.(?:New|Sum)\s*\(|\bdes\.NewCipher\s*\(|\brc4\.NewCipher\s*\(", needles=("md5.", "sha1.", "des.", "rc4.")),
    R("weak-crypto", "Weak hash/cipher (check whether used for security)", "CWE-327", JVM,
      r"MessageDigest\.getInstance\s*\(\s*\"(?:MD5|SHA-?1)\"|Cipher\.getInstance\s*\(\s*\"(?:DES|DESede|RC4|[^\"]*ECB)[^\"]*\"",
      needles=("MessageDigest", "Cipher")),
    R("weak-crypto", "Weak hash (check whether used for passwords/tokens)", "CWE-327", PHP,
      r"(?<![\w>$])(?:md5|sha1)\s*\(\s*\$", needles=("md5", "sha1")),
    R("weak-crypto", "Weak hash (check whether used for security)", "CWE-327", RB,
      r"Digest::(?:MD5|SHA1)\b", needles=("Digest::",)),
    R("weak-crypto", "Weak hash/cipher (check whether used for security)", "CWE-327", CS,
      r"\b(?:MD5|SHA1)\.Create\s*\(|new\s+(?:MD5|SHA1)CryptoServiceProvider|\bDESCryptoServiceProvider\b|CipherMode\.ECB",
      needles=("MD5", "SHA1", "DES", "ECB")),
    R("insecure-randomness", "Non-cryptographic RNG used near security-sensitive value", "CWE-338", JS,
      r"Math\.random\s*\(", needles=("Math.random",), context=SEC_WORDS),
    R("insecure-randomness", "Non-cryptographic RNG used near security-sensitive value", "CWE-338", PY,
      r"\brandom\.(?:random|randint|randrange|choice|choices|getrandbits|sample)\s*\(", needles=("random.",), context=SEC_WORDS),
    R("insecure-randomness", "Non-cryptographic RNG used near security-sensitive value", "CWE-338", JVM,
      r"new\s+(?:java\.util\.)?Random\s*\(|Math\.random\s*\(", needles=("Random", "random"), context=SEC_WORDS),
    R("insecure-randomness", "Non-cryptographic RNG used near security-sensitive value", "CWE-338", GO,
      r"\brand\.(?:Int|Intn|Int63|Int31|Read|Float64)\s*\(", needles=("rand.",), context=SEC_WORDS, file_requires=r"\"math/rand"),
    R("insecure-randomness", "Non-cryptographic RNG used near security-sensitive value", "CWE-338", PHP,
      r"(?<![\w>$])(?:rand|mt_rand|uniqid|lcg_value)\s*\(", needles=("rand", "uniqid", "lcg_value"), context=SEC_WORDS),
    # --- auth / session / cors / csrf
    R("jwt-verification-weakness", "JWT decoded without verification / weak verification options", "CWE-347", JS,
      r"\bjwt\.decode\s*\(|algorithms\s*:\s*\[[^\]]*['\"]none['\"]|ignoreExpiration\s*:\s*true",
      needles=("jwt.decode", "none", "ignoreExpiration")),
    R("jwt-verification-weakness", "JWT signature/expiry verification disabled", "CWE-347", PY,
      r"verify_signature['\"]?\s*:\s*False|jwt\.decode\s*\([^)\n]*verify\s*=\s*False|algorithms\s*=\s*\[[^\]]*['\"]none['\"]|verify_exp['\"]?\s*:\s*False",
      needles=("verify", "none")),
    R("cors-permissive", "Permissive CORS (wildcard or reflected origin)", "CWE-942", JS,
      r"\borigin\s*:\s*(?:['\"]\*['\"]|true)\b|\bcors\s*\(\s*\)|Access-Control-Allow-Origin['\"]?\s*,\s*['\"]\*",
      needles=("origin", "cors(", "Access-Control-Allow-Origin")),
    R("cors-permissive", "Permissive CORS (wildcard)", "CWE-942", PY,
      r"CORS_(?:ORIGIN_)?ALLOW_ALL(?:_ORIGINS)?\s*=\s*True|allow_origins\s*=\s*\[\s*['\"]\*['\"]|\bCORS\s*\(\s*app\s*\)|origins\s*=\s*['\"]\*['\"]",
      needles=("CORS", "allow_origins", "origins")),
    R("cors-permissive", "Permissive CORS (wildcard)", "CWE-942", CONFIG | GO | RB | PHP | JVM | CS,
      r"Access-Control-Allow-Origin['\"]?\s*[:=,]\s*['\"]?\*|AllowAllOrigins\s*:\s*true|AllowOrigins\s*:\s*\[\]string\{\s*\"\*\"|origins\s+['\"]\*['\"]",
      needles=("Access-Control-Allow-Origin", "AllowAllOrigins", "AllowOrigins", "origins")),
    R("csrf-protection-disabled", "CSRF protection disabled/exempted", "CWE-352", PY,
      r"@csrf_exempt|WTF_CSRF_ENABLED\s*=\s*False|CSRF_ENABLED\s*=\s*False", needles=("csrf_exempt", "CSRF_ENABLED")),
    R("csrf-protection-disabled", "CSRF protection disabled/exempted", "CWE-352", RB,
      r"skip_before_action\s+:verify_authenticity_token|skip_forgery_protection|protect_from_forgery\s+with:\s*:null_session",
      needles=("verify_authenticity_token", "skip_forgery_protection", "null_session")),
    R("csrf-protection-disabled", "CSRF protection disabled", "CWE-352", JVM,
      r"csrf\s*\(\s*\)\s*\.\s*disable\s*\(\s*\)|csrf\s*\(\s*(?:AbstractHttpConfigurer::disable|\w+\s*->\s*\w+\.disable\s*\(\s*\))|csrf\s*\{\s*(?:it\.)?disable\s*\(\s*\)",
      needles=("csrf",)),
    R("cookie-flags-weak", "Cookie security attribute disabled", "CWE-614", JS,
      r"\b(?:httpOnly|secure)\s*:\s*false|sameSite\s*:\s*['\"]?none", flags=re.I, needles=("httponly", "secure", "samesite")),
    R("cookie-flags-weak", "Cookie security attribute disabled", "CWE-614", PY,
      r"(?:SESSION|CSRF)_COOKIE_(?:SECURE|HTTPONLY)\s*=\s*False|\b(?:secure|httponly)\s*=\s*False|samesite\s*=\s*['\"]?None",
      flags=re.I, needles=("cookie", "secure", "httponly", "samesite")),
    R("debug-mode-enabled", "Debug mode / verbose errors enabled", "CWE-489", PY,
      r"^\s*DEBUG\s*=\s*True\b|\.run\s*\([^)\n]*debug\s*=\s*True|DEBUG_PROPAGATE_EXCEPTIONS\s*=\s*True",
      flags=re.M, needles=("DEBUG", "debug")),
    R("debug-mode-enabled", "Debug mode / verbose errors enabled", "CWE-489", CONFIG | PHP,
      r"APP_DEBUG\s*=\s*true|display_errors\s*=\s*On|include-stacktrace\s*[:=]\s*always|^\s*DEBUG\s*[:=]\s*(?:True|true|1)\b",
      flags=re.M, needles=("APP_DEBUG", "display_errors", "include-stacktrace", "DEBUG")),
    # --- redirects / SSRF / paths / mass assignment (single-line taint hints)
    R("open-redirect", "Redirect target taken from request", "CWE-601", JS,
      r"\.redirect\s*\(\s*(?:\d{3}\s*,\s*)?(?:" + REQ_JS + ")", needles=("redirect",)),
    R("open-redirect", "Redirect target taken from request", "CWE-601", PY,
      r"\bredirect\s*\(\s*(?:" + REQ_PY + ")", needles=("redirect",)),
    R("open-redirect", "Redirect target taken from request", "CWE-601", RB,
      r"redirect_to\s*\(?\s*params\[", needles=("redirect_to",)),
    R("open-redirect", "Redirect target taken from request", "CWE-601", PHP,
      r"header\s*\(\s*['\"]Location:\s*['\"]?\s*\.\s*" + REQ_PHP, needles=("Location",)),
    R("ssrf", "Server-side request to a URL taken from request", "CWE-918", JS,
      r"(?<![\w$.])(?:fetch|axios(?:\.(?:get|post|put|delete|request))?|got|needle|http\.get|https\.get)\s*\(\s*(?:" + REQ_JS + ")",
      needles=("fetch", "axios", "got", "needle", "http")),
    R("ssrf", "Server-side request to a URL taken from request", "CWE-918", PY,
      r"(?:requests|httpx|aiohttp|urllib\.request)\.\w+\s*\(\s*(?:" + REQ_PY + ")|urlopen\s*\(\s*(?:" + REQ_PY + ")",
      needles=("requests", "httpx", "aiohttp", "urllib", "urlopen")),
    R("ssrf", "Server-side request / file read from request input", "CWE-918", PHP,
      r"(?:file_get_contents|fopen|curl_init)\s*\(\s*" + REQ_PHP, needles=("file_get_contents", "fopen", "curl_init")),
    R("path-traversal", "File path built from request input", "CWE-22", JS,
      r"(?:readFile(?:Sync)?|createReadStream|writeFile(?:Sync)?|sendFile|download|unlink(?:Sync)?|readdir(?:Sync)?|path\.join|path\.resolve)\s*\([^)\n]*(?:" + REQ_JS + ")",
      needles=("File", "Stream", "download", "unlink", "readdir", "path.")),
    R("path-traversal", "File path built from request input", "CWE-22", PY,
      r"(?<![\w.])(?:open|send_file|send_from_directory|FileResponse|os\.path\.join|Path)\s*\([^)\n]*(?:" + REQ_PY + ")",
      needles=("open", "send_", "FileResponse", "os.path", "Path")),
    R("path-traversal", "File inclusion/path from request input", "CWE-98", PHP,
      r"(?:include|require)(?:_once)?\s*\(?\s*[^;\n]*" + REQ_PHP, needles=("include", "require")),
    R("path-traversal", "File path from request params", "CWE-22", RB,
      r"(?:File\.(?:read|open|write)|send_file|IO\.read)\s*\(?\s*[^\n]*params\[", needles=("File.", "send_file", "IO.read")),
    R("mass-assignment", "Request body passed straight into a model/update", "CWE-915", JS,
      r"\.(?:create|update|insert|save|findOneAndUpdate|findByIdAndUpdate|updateOne|updateMany|upsert)\s*\(\s*(?:[^()\n]*,\s*)?(?:\{\s*\.\.\.\s*)?req\.body\s*[,)}]"
      r"|Object\.assign\s*\(\s*[\w.]+\s*,\s*req\.body\s*\)|data\s*:\s*req\.body\b"
      r"|SET\s+\?[^'\"`\n]*['\"`]\s*,\s*\[\s*req\.body\b",
      needles=("req.body",)),
    R("mass-assignment", "Request data unpacked straight into a model", "CWE-915", PY,
      r"\(\s*\*\*\s*(?:request\.(?:json|data|form|POST|get_json\s*\(\s*\))|await\s+request\.json\s*\(\s*\))",
      needles=("**",)),
    R("mass-assignment", "Unrestricted strong parameters", "CWE-915", RB,
      r"\.permit!|params\.permit\s*\(\s*!", needles=("permit",)),
    R("sensitive-data-logging", "Possible secret/credential written to logs", "CWE-532", JS,
      r"console\.(?:log|info|debug|warn|error)\s*\([^)\n]*(?:,\s*|\$\{\s*|\+\s*)(?:[\w$]+\.)*(?:password|passwd|secret|token|accessToken|refreshToken|apiKey|api_key|authorization|cardNumber)\b",
      flags=re.I, needles=("console.",)),
    R("sensitive-data-logging", "Possible secret/credential written to logs", "CWE-532", PY,
      r"(?:print|logging\.\w+|logger\.\w+|log\.\w+)\s*\([^)\n]*(?:,\s*|\{\s*|%\s*\(?\s*|\+\s*)(?:\w+\.)*(?:password|passwd|secret|token|api_key|authorization)\b",
      flags=re.I, needles=("print", "log")),
    R("insecure-default-secret", "Secret falls back to a hard-coded default when the env var is missing", "CWE-798", JS,
      r"(?i)\b[\w.]*(?:secret|password|passwd|token|api_?key|private_?key)\w*\s*[:=]\s*process\.env\.\w+\s*(?:\|\||\?\?)\s*['\"`]([^'\"`\n]+)['\"`]",
      needles=("process.env",), mask_group=1),
    R("insecure-default-secret", "Secret falls back to a hard-coded default when the env var is missing", "CWE-798", PY,
      r"(?i)os\.(?:environ\.get|getenv)\s*\(\s*['\"]\w*(?:secret|password|passwd|token|api_?key|private_?key)\w*['\"]\s*,\s*['\"]([^'\"\n]+)['\"]",
      needles=("environ.get", "getenv"), mask_group=1),
    R("error-details-exposed", "Stack trace / exception details returned to the client", "CWE-209", JS,
      r"\.(?:json|send|end)\s*\([^)\n]*\b\w+\.stack\b", needles=(".stack",)),
    R("error-details-exposed", "Stack trace returned to the client", "CWE-209", PY,
      r"(?:return|jsonify\s*\(|Response\s*\()[^\n]*traceback\.format_exc\s*\(", needles=("traceback",)),
    R("jwt-without-expiry", "JWT issued without an expiry (check options/payload)", "CWE-613", JS,
      r"\bjwt\.sign\s*\(", needles=("jwt.sign",), absent_after=(r"expiresIn|\bexp\b", 400)),
    R("llm-tool-definitions", "LLM tools/function calling defined (review agency & permissions)", "", CODE,
      r"[\"']input_schema[\"']\s*:|\btool_choice\b|\bfunction_call\b|@tool\b|\btools\s*=\s*\[|\btools\s*:\s*\[",
      needles=("input_schema", "tool_choice", "function_call", "@tool", "tools"), file_requires=LLM_IMPORT_RE),
    R("llm-dangerous-sink", "Dangerous sink in a file that calls an LLM (check if model output reaches it)", "", PY,
      r"\.execute\s*\(\s*text\s*\(|\bsubprocess\.\w+\s*\(|\bos\.system\s*\(|(?<![\w.])(?:eval|exec)\s*\(",
      needles=("execute", "subprocess", "os.system", "eval", "exec"), file_requires=LLM_IMPORT_RE),
    R("llm-dangerous-sink", "Dangerous sink in a file that calls an LLM (check if model output reaches it)", "", JS,
      r"child_process|(?<![\w$.])eval\s*\(|new\s+Function\s*\(|\.(?:query|execute|raw)\s*\(\s*[\w.]*(?:input|args|arguments)\b|\bfs\.(?:writeFile|rm|unlink)\w*\s*\(",
      needles=("child_process", "eval", "Function", "query", "execute", "raw", "fs."), file_requires=LLM_IMPORT_RE),
    R("security-todo", "Security-related TODO/FIXME left in code", "", CODE | TEMPLATES | CONFIG,
      r"(?:TODO|FIXME|XXX|HACK)\b[^\n]{0,60}?(?i:\b(?:security|auth\w*|csrf|xss|inject\w*|saniti[sz]\w*|validat\w*|password|secret|token|vuln\w*|permission|rate.?limit\w*|encrypt\w*|escap\w*))",
      needles=("TODO", "FIXME", "XXX", "HACK")),
]

# Positive evidence: code that suggests a control *is* implemented.
POSITIVE_RULES = [
    ("security-headers", r"\bhelmet\s*\(|Content-Security-Policy|Strict-Transport-Security|SECURE_HSTS_SECONDS|\bTalisman\s*\(|X-Frame-Options|X-Content-Type-Options|frame-ancestors|contentSecurityPolicy|SecureHeaders|secure_headers|add_header\s+(?:Content-Security|Strict-Transport|X-Frame|X-Content-Type)", 0),
    ("rate-limiting", r"\brateLimit\s*\(|RateLimit|rate_limit|ratelimit|\bLimiter\s*\(|@limiter\.limit|\bThrottle\b|ThrottlerModule|Rack::Attack|limit_req_zone|slowDown\s*\(", 0),
    ("csrf-protection", r"csrf|xsrf|antiforgery|verify_authenticity_token|protect_from_forgery|CsrfViewMiddleware", re.I),
    ("password-hashing", r"bcrypt\.(?:hash|compare|hashpw|checkpw|genSalt)|argon2\.(?:hash|verify)|PasswordHasher\s*\(|make_password\s*\(|check_password\s*\(|password_hash\s*\(|password_verify\s*\(|BCryptPasswordEncoder|Argon2PasswordEncoder|generate_password_hash|check_password_hash|has_secure_password|scrypt(?:Sync)?\s*\(|pbkdf2(?:Sync|_hmac)?\s*\(|CryptContext\s*\(", 0),
    ("input-validation", r"\bz\.(?:object|string|number|array|enum)\s*\(|\bJoi\.\w+\s*\(|\byup\.\w+\s*\(|\(\s*BaseModel\s*\)|ValidationPipe|@Is(?:String|Int|Email|NotEmpty|UUID)\b|validationResult\s*\(|ajv\.compile|\bforms\.(?:Model)?Form\b|serializers\.\w*Serializer\b|@Valid\b|validates\s+:|\bFormRequest\b|safeParse\s*\(", 0),
    ("authn-authz-checks", r"@login_required|login_required\s*\(|permission_required|IsAuthenticated|@PreAuthorize|@Secured|@RolesAllowed|before_action\s+:authenticate|authenticate_user!|requireAuth|isAuthenticated|ensureAuthenticated|passport\.authenticate|jwt\.verify|getServerSession|auth\(\)\.protect|withAuth|Depends\(\s*get_current_user|OAuth2PasswordBearer|HTTPBearer|@UseGuards|authorize!|\bauthorize\s*\(|can\?\s*\(|Gate::|->can\(|policy\s*\(", 0),
    ("security-logging", r"\b(?:logger|log|logging|winston|pino|bunyan|structlog|zap|logrus|slog)\.(?:warn|warning|error|info|critical|audit)\s*\([^)\n]*(?:login|logon|sign.?in|auth|unauthori[sz]ed|forbidden|denied|failed|invalid (?:password|token|credentials))", re.I),
    ("cookie-security-flags", r"httpOnly\s*:\s*true|secure\s*:\s*true|sameSite\s*:|SESSION_COOKIE_SECURE\s*=\s*True|SESSION_COOKIE_HTTPONLY\s*=\s*True|CSRF_COOKIE_SECURE\s*=\s*True|SESSION_COOKIE_SAMESITE|cookie_secure|HttpOnly;|SameSite=", 0),
    ("output-sanitization", r"DOMPurify\.sanitize|sanitizeHtml\s*\(|bleach\.clean|nh3\.clean|htmlspecialchars\s*\(|html\.escape\s*\(|markupsafe\.escape|escapeHtml\s*\(", 0),
    ("request-limits", r"(?:json|urlencoded|raw|text)\s*\(\s*\{[^}\n]*limit\s*:|bodyLimit|MAX_CONTENT_LENGTH|DATA_UPLOAD_MAX_MEMORY_SIZE|client_max_body_size|maxFileSize|fileSize\s*:|max_request_size|MaxBytesReader|max_tokens|maxTokens|max_output_tokens", 0),
]
POSITIVE_NEEDLES = {
    "security-headers": ("helmet", "content-security-policy", "strict-transport-security", "hsts", "talisman",
                         "x-frame-options", "x-content-type-options", "frame-ancestors", "contentsecuritypolicy",
                         "secureheaders", "secure_headers", "add_header"),
    "rate-limiting": ("ratelimit", "rate_limit", "limiter", "throttle", "rack::attack", "limit_req_zone", "slowdown"),
    "csrf-protection": ("csrf", "xsrf", "antiforgery", "verify_authenticity_token", "protect_from_forgery"),
    "password-hashing": ("bcrypt", "argon2", "passwordhasher", "make_password", "check_password", "password_hash",
                         "password_verify", "passwordencoder", "generate_password_hash", "has_secure_password",
                         "scrypt", "pbkdf2", "cryptcontext"),
    "input-validation": ("z.", "joi.", "yup.", "basemodel", "validationpipe", "@is", "validationresult", "ajv",
                         "forms.", "serializers.", "@valid", "validates", "formrequest", "safeparse"),
    "authn-authz-checks": ("login_required", "permission_required", "isauthenticated", "preauthorize", "@secured",
                           "rolesallowed", "authenticate", "requireauth", "ensureauthenticated", "jwt.verify",
                           "getserversession", "protect", "withauth", "get_current_user", "oauth2passwordbearer",
                           "httpbearer", "useguards", "authorize", "can?", "gate::", "->can(", "policy("),
    "security-logging": ("logger", "logging", "log.", "winston", "pino", "bunyan", "structlog", "zap.", "logrus", "slog."),
    "cookie-security-flags": ("httponly", "secure", "samesite", "session_cookie", "csrf_cookie", "cookie_secure"),
    "output-sanitization": ("dompurify", "sanitizehtml", "bleach", "nh3", "htmlspecialchars", "html.escape",
                            "markupsafe", "escapehtml"),
    "request-limits": ("limit", "max_content_length", "data_upload_max_memory_size", "client_max_body_size",
                       "maxfilesize", "filesize", "max_request_size", "maxbytesreader", "max_tokens", "maxtokens",
                       "max_output_tokens"),
}
POSITIVE_RULES_C = [(cat, re.compile(p, f)) for cat, p, f in POSITIVE_RULES]

ROUTE_RULES = [
    (JS, re.compile(r"\b(?:app|router|server|fastify|api|route|routes|hono)\s*\.\s*(?:get|post|put|patch|delete|all|route)\s*\(\s*['\"`/]")),
    (JS, re.compile(r"@(?:Get|Post|Put|Patch|Delete|All)\s*\(")),
    (JS, re.compile(r"export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|PATCH|DELETE)\b|export\s+const\s+(?:GET|POST|PUT|PATCH|DELETE)\s*=")),
    (PY, re.compile(r"@\w+\.(?:route|get|post|put|patch|delete|api_route|websocket)\s*\(")),
    (PY, re.compile(r"\b(?:path|re_path|url)\s*\(\s*r?['\"]")),
    (RB, re.compile(r"^\s*(?:get|post|put|patch|delete|resources?|namespace|match)\s+['\":]", re.M)),
    (JVM, re.compile(r"@(?:Get|Post|Put|Patch|Delete|Request)Mapping\b")),
    (GO, re.compile(r"\.(?:HandleFunc|Handle|GET|POST|PUT|PATCH|DELETE|Get|Post|Put|Patch|Delete)\s*\(\s*\"")),
    (PHP, re.compile(r"Route::(?:get|post|put|patch|delete|any|match|resource|apiResource)\s*\(")),
    (CS, re.compile(r"\[(?:HttpGet|HttpPost|HttpPut|HttpPatch|HttpDelete|Route)\b|\.Map(?:Get|Post|Put|Patch|Delete)\s*\(")),
]

AUTH_PATH_RE = re.compile(
    r"(?i)(^|/|_|-)(auth\w*|login|logout|signin|signup|register|session\w*|passport|jwt|token\w*|middleware\w*|guard\w*|"
    r"polic(?:y|ies)|permission\w*|rbac|acl|roles?|oauth\w*|oidc|password\w*|csrf|security)(\.|/|_|-|$)"
)

# ---------------------------------------------------------------------------
# Dependency knowledge
# ---------------------------------------------------------------------------

FRAMEWORKS = {
    "express": "Express", "fastify": "Fastify", "koa": "Koa", "@hapi/hapi": "hapi", "@nestjs/core": "NestJS",
    "next": "Next.js", "nuxt": "Nuxt", "@remix-run/node": "Remix", "@sveltejs/kit": "SvelteKit", "hono": "Hono",
    "astro": "Astro", "@angular/core": "Angular", "react": "React", "vue": "Vue", "svelte": "Svelte",
    "electron": "Electron", "react-native": "React Native", "expo": "Expo",
    "django": "Django", "djangorestframework": "Django REST framework", "flask": "Flask", "fastapi": "FastAPI",
    "starlette": "Starlette", "tornado": "Tornado", "aiohttp": "aiohttp", "sanic": "Sanic", "bottle": "Bottle",
    "pyramid": "Pyramid", "streamlit": "Streamlit", "gradio": "Gradio",
    "rails": "Rails", "sinatra": "Sinatra", "hanami": "Hanami",
    "laravel/framework": "Laravel", "symfony/framework-bundle": "Symfony", "slim/slim": "Slim",
    "spring-boot-starter-web": "Spring Boot (web)", "spring-boot-starter-webflux": "Spring WebFlux",
    "actix-web": "Actix Web", "axum": "Axum", "rocket": "Rocket", "warp": "warp",
}
GO_FRAMEWORKS = {
    "github.com/gin-gonic/gin": "Gin", "github.com/labstack/echo": "Echo", "github.com/gofiber/fiber": "Fiber",
    "github.com/go-chi/chi": "chi", "github.com/gorilla/mux": "gorilla/mux",
}
SECURITY_LIBS = {
    "helmet": "security headers", "@fastify/helmet": "security headers", "koa-helmet": "security headers",
    "csurf": "CSRF (deprecated package)", "csrf-csrf": "CSRF", "csrf-sync": "CSRF", "lusca": "security middleware",
    "@fastify/csrf-protection": "CSRF", "tiny-csrf": "CSRF",
    "express-rate-limit": "rate limiting", "rate-limiter-flexible": "rate limiting", "@fastify/rate-limit": "rate limiting",
    "express-slow-down": "rate limiting", "@upstash/ratelimit": "rate limiting", "@nestjs/throttler": "rate limiting",
    "cors": "CORS", "@fastify/cors": "CORS",
    "bcrypt": "password hashing", "bcryptjs": "password hashing", "argon2": "password hashing",
    "@node-rs/argon2": "password hashing", "@node-rs/bcrypt": "password hashing",
    "jsonwebtoken": "JWT", "jose": "JWT/JOSE", "express-jwt": "JWT", "passport": "authentication", "passport-jwt": "JWT",
    "next-auth": "authentication", "@auth/core": "authentication", "better-auth": "authentication", "lucia": "authentication",
    "@clerk/nextjs": "authentication (Clerk)", "@supabase/supabase-js": "BaaS (Supabase)", "firebase": "BaaS (Firebase)",
    "firebase-admin": "BaaS (Firebase admin)",
    "express-session": "sessions", "cookie-session": "sessions", "iron-session": "sessions", "@fastify/session": "sessions",
    "@fastify/secure-session": "sessions",
    "dompurify": "HTML sanitization", "isomorphic-dompurify": "HTML sanitization", "sanitize-html": "HTML sanitization",
    "xss": "HTML sanitization",
    "zod": "input validation", "joi": "input validation", "yup": "input validation", "ajv": "input validation",
    "class-validator": "input validation", "express-validator": "input validation", "valibot": "input validation",
    "@sinclair/typebox": "input validation", "express-mongo-sanitize": "NoSQL injection filter", "hpp": "HTTP parameter pollution",
    "@casl/ability": "authorization", "casbin": "authorization", "accesscontrol": "authorization",
    "django-cors-headers": "CORS", "flask-cors": "CORS", "flask-talisman": "security headers", "django-csp": "CSP",
    "secure": "security headers", "flask-wtf": "CSRF/forms", "flask-seasurf": "CSRF",
    "flask-limiter": "rate limiting", "slowapi": "rate limiting", "django-ratelimit": "rate limiting",
    "django-axes": "brute-force protection", "fastapi-limiter": "rate limiting",
    "argon2-cffi": "password hashing", "passlib": "password hashing", "pwdlib": "password hashing",
    "pyjwt": "JWT", "python-jose": "JWT", "authlib": "OAuth/OIDC", "django-allauth": "authentication",
    "flask-login": "authentication", "fastapi-users": "authentication", "djangorestframework-simplejwt": "JWT",
    "flask-jwt-extended": "JWT", "bleach": "HTML sanitization", "nh3": "HTML sanitization",
    "pydantic": "input validation", "marshmallow": "input validation", "cerberus": "input validation",
    "cryptography": "cryptography", "pynacl": "cryptography", "defusedxml": "safe XML parsing",
    "django-guardian": "authorization", "rules": "authorization",
    "rack-attack": "rate limiting", "devise": "authentication", "secure_headers": "security headers",
    "rack-cors": "CORS", "pundit": "authorization", "cancancan": "authorization",
    "brakeman": "SAST", "bundler-audit": "dependency audit",
    "laravel/sanctum": "authentication", "laravel/fortify": "authentication", "spatie/laravel-permission": "authorization",
    "spring-boot-starter-security": "Spring Security", "spring-security-core": "Spring Security",
    "golang.org/x/crypto": "cryptography (bcrypt/argon2)", "github.com/golang-jwt/jwt": "JWT",
    "github.com/gorilla/csrf": "CSRF", "github.com/unrolled/secure": "security headers", "github.com/ulule/limiter": "rate limiting",
    "tower-governor": "rate limiting", "governor": "rate limiting",
}
DATASTORES = {
    "@prisma/client": "Prisma", "prisma": "Prisma", "sequelize": "Sequelize", "typeorm": "TypeORM", "mongoose": "Mongoose",
    "mongodb": "MongoDB driver", "knex": "Knex", "drizzle-orm": "Drizzle", "kysely": "Kysely", "pg": "node-postgres",
    "mysql": "mysql", "mysql2": "mysql2", "sqlite3": "sqlite3", "better-sqlite3": "better-sqlite3", "redis": "Redis", "ioredis": "Redis",
    "sqlalchemy": "SQLAlchemy", "sqlmodel": "SQLModel", "psycopg2": "psycopg2", "psycopg2-binary": "psycopg2", "psycopg": "psycopg",
    "asyncpg": "asyncpg", "pymongo": "PyMongo", "motor": "Motor", "peewee": "peewee", "tortoise-orm": "Tortoise ORM",
    "mysqlclient": "mysqlclient", "pymysql": "PyMySQL", "sequel": "Sequel", "pg (gem)": "pg",
    "gorm.io/gorm": "GORM", "github.com/jmoiron/sqlx": "sqlx", "github.com/jackc/pgx": "pgx",
    "go.mongodb.org/mongo-driver": "MongoDB driver", "diesel": "Diesel", "sqlx": "sqlx", "sea-orm": "SeaORM",
    "doctrine/orm": "Doctrine", "illuminate/database": "Eloquent", "hibernate-core": "Hibernate",
    "spring-boot-starter-data-jpa": "Spring Data JPA", "mybatis": "MyBatis",
    "flask-sqlalchemy": "SQLAlchemy (Flask)", "django": "Django ORM", "activerecord": "ActiveRecord",
}
LLM_LIBS = {
    "openai", "@anthropic-ai/sdk", "anthropic", "@google/generative-ai", "@google/genai", "google-generativeai",
    "google-genai", "google-cloud-aiplatform", "vertexai", "cohere", "cohere-ai", "@mistralai/mistralai", "mistralai",
    "groq", "groq-sdk", "together", "ollama", "litellm", "langchain", "langchain-core", "langchain-openai",
    "langchain-anthropic", "langchain-community", "@langchain/core", "@langchain/openai", "@langchain/anthropic",
    "@langchain/langgraph", "langgraph", "llama-index", "llama-index-core", "llamaindex", "ai", "@ai-sdk/openai",
    "@ai-sdk/anthropic", "crewai", "autogen-agentchat", "pyautogen", "ag2", "semantic-kernel", "dspy", "dspy-ai",
    "haystack-ai", "transformers", "sentence-transformers", "@huggingface/inference", "huggingface-hub",
    "@modelcontextprotocol/sdk", "mcp", "fastmcp", "@openai/agents", "openai-agents", "claude-agent-sdk",
    "@anthropic-ai/claude-agent-sdk", "instructor", "pydantic-ai", "smolagents", "chromadb", "pinecone",
    "pinecone-client", "@pinecone-database/pinecone", "weaviate-client", "qdrant-client", "@qdrant/js-client-rest",
    "faiss-cpu", "pgvector", "lancedb", "pymilvus", "ruby-openai",
    "github.com/sashabaranov/go-openai", "github.com/openai/openai-go", "github.com/anthropics/anthropic-sdk-go",
    "github.com/tmc/langchaingo",
}

CI_SECURITY_TOOLS = [
    ("codeql", r"github/codeql-action"), ("semgrep", r"semgrep"), ("trivy", r"trivy"), ("grype", r"\bgrype\b|anchore/scan-action"),
    ("gitleaks", r"gitleaks"), ("trufflehog", r"trufflehog"), ("detect-secrets", r"detect-secrets"),
    ("snyk", r"\bsnyk\b"), ("osv-scanner", r"osv-scanner"), ("dependency-review", r"actions/dependency-review-action"),
    ("npm audit", r"\b(?:npm|pnpm|yarn)\s+audit\b"), ("pip-audit", r"pip-audit"), ("safety", r"\bsafety\s+check\b"),
    ("bandit", r"\bbandit\b"), ("gosec", r"\bgosec\b"), ("govulncheck", r"govulncheck"), ("brakeman", r"brakeman"),
    ("bundler-audit", r"bundler?-audit"), ("cargo-audit", r"cargo[- ]audit|cargo[- ]deny"), ("scorecard", r"ossf/scorecard-action"),
    ("zizmor", r"zizmor"), ("actionlint", r"actionlint"), ("hadolint", r"hadolint"), ("checkov", r"checkov"),
    ("tfsec/trivy-config", r"tfsec"), ("kics", r"\bkics\b"), ("sonar", r"sonar(?:cloud|qube|source)"),
    ("harden-runner", r"step-security/harden-runner"), ("zap", r"zaproxy|owasp-zap|zap-baseline"),
]
CI_TEST_RE = re.compile(
    r"\b(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?test\b|\bpytest\b|\btox\b|\bnox\b|\bgo\s+test\b|\bcargo\s+test\b|\brspec\b|\brake\s+test\b|"
    r"\bmvn\b[^\n]*\b(?:test|verify)\b|\bgradlew?\b[^\n]*\b(?:test|check)\b|\bdotnet\s+test\b|\bphpunit\b|\bjest\b|\bvitest\b|\bmocha\b|\bplaywright\s+test\b|"
    r"\bmake\s+(?:test|check)\b|python\s+-m\s+unittest"
)
UNTRUSTED_GHA_CTX = re.compile(
    r"\$\{\{[^}]*?(github\.event\.(?:issue\.(?:title|body)|pull_request\.(?:title|body|head\.ref|head\.label|head\.repo\.default_branch)"
    r"|comment\.body|review\.body|review_comment\.body|pages\.[^}]*?page_name|commits\.[^}]*?(?:message|author\.email|author\.name)"
    r"|head_commit\.(?:message|author\.email|author\.name)|workflow_run\.(?:head_branch|head_commit\.(?:message|author\.email|author\.name)|display_title)"
    r"|discussion\.(?:title|body)|discussion_comment\.body)|github\.head_ref)[^}]*\}\}"
)
LONG_LIVED_CLOUD_SECRET_RE = re.compile(
    r"secrets\.(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|GCP_SA_KEY|GCP_CREDENTIALS|GOOGLE_CREDENTIALS|GOOGLE_APPLICATION_CREDENTIALS|AZURE_CREDENTIALS|AZURE_CLIENT_SECRET)"
)

EXTERNAL_TOOLS = [
    "gitleaks", "trufflehog", "detect-secrets", "semgrep", "bandit", "trivy", "grype", "syft", "osv-scanner",
    "npm", "pnpm", "yarn", "pip-audit", "safety", "govulncheck", "gosec", "cargo-audit", "bundle-audit",
    "brakeman", "zizmor", "actionlint", "hadolint", "checkov", "tfsec", "scorecard", "gh",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, cwd=None, timeout=60):
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                             errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    return res.stdout


def git(root, *args, timeout=60):
    return run(["git", "-C", root, *args], timeout=timeout)


def read_text(path):
    try:
        size = os.path.getsize(path)
    except OSError:
        return None, "unreadable"
    if size > MAX_FILE_BYTES:
        return None, "large"
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None, "unreadable"
    if b"\x00" in data[:8192]:
        return None, "binary"
    return data.decode("utf-8", errors="replace"), None


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def line_text(text, pos):
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end]


def snippet(text, pos):
    s = line_text(text, pos).strip()
    s = mask_secrets_in(s)
    if len(s) > SNIPPET_CHARS:
        s = s[:SNIPPET_CHARS - 3] + "..."
    return s


def sanitize_remote(url):
    # Never print credentials embedded in a remote URL.
    return re.sub(r"(://)[^/@\s]+@", r"\1***@", url.strip())


def parse_github_slug(url):
    m = re.search(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
    if m:
        return "%s/%s" % (m.group(1), m.group(2))
    m = re.search(r"/git/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)  # some proxied remotes
    if m:
        return "%s/%s" % (m.group(1), m.group(2))
    return None


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

class Collector:
    def __init__(self, root, max_hits):
        self.root = os.path.abspath(root)
        self.max_hits = max_hits
        self.r = {
            "tool": {"name": "collect_signals.py", "version": VERSION},
            "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "root": self.root,
        }
        self.files = []          # tracked (or walked) relative paths
        self.texts = {}          # rel -> text for scanned files
        self.skipped = Counter()

    # -- inventory ---------------------------------------------------------
    def inventory(self):
        root = self.root
        is_git = (git(root, "rev-parse", "--is-inside-work-tree") or "").strip() == "true"
        info = {"is_git_repo": is_git}
        if is_git:
            remote = (git(root, "config", "--get", "remote.origin.url") or "").strip()
            info["remote"] = sanitize_remote(remote) if remote else None
            info["github_repo"] = parse_github_slug(remote) if remote else None
            info["branch"] = (git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip() or None
            info["head"] = (git(root, "rev-parse", "--short", "HEAD") or "").strip() or None
            count = (git(root, "rev-list", "--count", "HEAD") or "").strip()
            info["commit_count"] = int(count) if count.isdigit() else None
            info["last_commit_date"] = (git(root, "log", "-1", "--format=%cI") or "").strip() or None
            listing = git(root, "ls-files", "-z") or ""
            self.files = [p for p in listing.split("\0") if p]
        else:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES
                               and not os.path.exists(os.path.join(dirpath, d, "pyvenv.cfg"))]
                for fn in filenames:
                    rel = os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/")
                    self.files.append(rel)
                    if len(self.files) >= MAX_FILES:
                        break
        self.is_git = is_git
        self.fileset = set(self.files)
        self.r["git"] = info

        langs = Counter()
        vendored = Counter()
        artifacts = []
        for rel in self.files:
            ext = pseudo_ext(rel)
            if is_vendored(rel):
                top = next(p for p in rel.split("/")[:-1] if p in SKIP_DIR_NAMES)
                vendored[top] += 1
                continue
            if ext in LANG_BY_EXT:
                langs[LANG_BY_EXT[ext]] += 1
            if ext in ARTIFACT_EXTS:
                artifacts.append(rel)
        self.r["languages"] = dict(langs.most_common())
        self.r["vendored_tracked_dirs"] = dict(vendored)
        self.r["binary_artifacts_tracked"] = artifacts[:20]
        self.r["binary_artifacts_count"] = len(artifacts)

    def load_texts(self):
        n = 0
        for rel in self.files:
            if is_vendored(rel):
                self.skipped["vendored"] += 1
                continue
            name = rel.rsplit("/", 1)[-1]
            ext = pseudo_ext(rel)
            if name in LOCKFILES:
                self.skipped["lockfile"] += 1
                continue
            if ext in BINARY_EXTS:
                self.skipped["binary"] += 1
                continue
            if n >= MAX_FILES:
                self.skipped["over-limit"] += 1
                continue
            text, why = read_text(os.path.join(self.root, rel))
            if text is None:
                self.skipped[why] += 1
                continue
            if name.endswith((".min.js", ".min.css")) or (len(text) > 5000 and text.count("\n") < 3):
                self.skipped["minified"] += 1
                continue
            self.texts[rel] = text
            n += 1
        self.r["scan"] = {"text_files_scanned": len(self.texts), "skipped": dict(self.skipped)}

    # -- manifests & dependencies -----------------------------------------
    def manifests(self):
        results = []
        deps = defaultdict(set)  # name -> manifests

        def has_lock(rel_dir, names):
            d = rel_dir
            while True:
                for ln in names:
                    cand = (d + "/" + ln) if d else ln
                    if cand in self.fileset:
                        return cand
                if not d:
                    return None
                d = d.rsplit("/", 1)[0] if "/" in d else ""

        for rel in self.files:
            if is_vendored(rel):
                continue
            name = rel.rsplit("/", 1)[-1]
            rel_dir = rel.rsplit("/", 1)[0] if "/" in rel else ""
            text = self.texts.get(rel)
            entry = None
            names = set()
            if name == "package.json":
                entry = {"path": rel, "ecosystem": "npm",
                         "lockfile": has_lock(rel_dir, ["package-lock.json", "npm-shrinkwrap.json", "yarn.lock",
                                                        "pnpm-lock.yaml", "bun.lock", "bun.lockb"])}
                try:
                    data = json.loads(text or "{}")
                    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                        names |= set((data.get(key) or {}).keys())
                    entry["has_renovate_key"] = "renovate" in data
                    scripts = data.get("scripts") or {}
                    entry["install_scripts"] = sorted(k for k in scripts if k in ("preinstall", "install", "postinstall", "prepare"))
                except (ValueError, AttributeError):
                    entry["parse_error"] = True
            elif name == "pyproject.toml":
                entry = {"path": rel, "ecosystem": "python",
                         "lockfile": has_lock(rel_dir, ["poetry.lock", "uv.lock", "pdm.lock", "Pipfile.lock"])}
                names |= self._pyproject_deps(text or "")
            elif name == "Pipfile":
                entry = {"path": rel, "ecosystem": "python", "lockfile": has_lock(rel_dir, ["Pipfile.lock"])}
                names |= self._toml_table_keys(text or "", ("packages", "dev-packages"))
            elif re.match(r"requirements[^/]*\.txt$", name) or (rel_dir.endswith("requirements") and name.endswith(".txt")):
                reqs, pinned = self._requirements(text or "")
                entry = {"path": rel, "ecosystem": "python", "lockfile": "(pins in file)" if reqs and pinned == len(reqs) else None,
                         "requirements": len(reqs), "exactly_pinned": pinned}
                names |= set(reqs)
            elif name == "go.mod":
                entry = {"path": rel, "ecosystem": "go", "lockfile": has_lock(rel_dir, ["go.sum"])}
                names |= set(re.findall(r"^\s*(?:require\s+)?([a-z0-9.\-]+\.[a-z]{2,}/[^\s]+)\s+v[\d.]", text or "", re.M))
            elif name == "Cargo.toml":
                entry = {"path": rel, "ecosystem": "rust", "lockfile": has_lock(rel_dir, ["Cargo.lock"])}
                names |= self._toml_table_keys(text or "", ("dependencies", "dev-dependencies", "workspace.dependencies"))
            elif name == "Gemfile":
                entry = {"path": rel, "ecosystem": "ruby", "lockfile": has_lock(rel_dir, ["Gemfile.lock"])}
                names |= set(re.findall(r"^\s*gem\s+['\"]([^'\"]+)['\"]", text or "", re.M))
            elif name == "composer.json":
                entry = {"path": rel, "ecosystem": "php", "lockfile": has_lock(rel_dir, ["composer.lock"])}
                try:
                    data = json.loads(text or "{}")
                    names |= set((data.get("require") or {}).keys()) | set((data.get("require-dev") or {}).keys())
                except ValueError:
                    entry["parse_error"] = True
            elif name == "pom.xml":
                entry = {"path": rel, "ecosystem": "maven", "lockfile": "(n/a: versions declared in pom)"}
                names |= set(re.findall(r"<artifactId>\s*([^<\s]+)\s*</artifactId>", text or ""))
            elif name in ("build.gradle", "build.gradle.kts"):
                entry = {"path": rel, "ecosystem": "gradle", "lockfile": has_lock(rel_dir, ["gradle.lockfile"])}
                names |= set(m.group(2) for m in re.finditer(r"['\"]([\w.\-]+):([\w.\-]+)(?::[^'\"]*)?['\"]", text or ""))
            elif name.endswith(".csproj"):
                entry = {"path": rel, "ecosystem": "nuget", "lockfile": has_lock(rel_dir, ["packages.lock.json"])}
                names |= set(n.lower() for n in re.findall(r"<PackageReference\s+Include=\"([^\"]+)\"", text or ""))
                if re.search(r"Sdk=\"Microsoft\.NET\.Sdk\.Web\"", text or ""):
                    names.add("aspnetcore")
            elif name == "pubspec.yaml":
                entry = {"path": rel, "ecosystem": "dart", "lockfile": has_lock(rel_dir, ["pubspec.lock"])}
            elif name == "Package.swift":
                entry = {"path": rel, "ecosystem": "swift", "lockfile": has_lock(rel_dir, ["Package.resolved"])}
            elif name == "mix.exs":
                entry = {"path": rel, "ecosystem": "elixir", "lockfile": has_lock(rel_dir, ["mix.lock"])}
            if entry is not None:
                results.append(entry)
                for n in names:
                    deps[self._norm(n)].add(rel)

        self.deps = deps
        self.r["manifests"] = results

        def pick(table, prefix_table=None):
            found = {}
            for dep, where in deps.items():
                label = table.get(dep) if isinstance(table, dict) else (dep if dep in table else None)
                if label is None and prefix_table:
                    for pfx, lbl in prefix_table.items():
                        if dep.startswith(pfx):
                            label = lbl
                            break
                if label:
                    found.setdefault(label if isinstance(table, dict) else dep, set()).update(where)
            return {k: sorted(v)[:3] for k, v in sorted(found.items())}

        self.r["frameworks"] = pick(FRAMEWORKS, GO_FRAMEWORKS)
        sec = {}
        for dep, where in deps.items():
            purpose = SECURITY_LIBS.get(dep)
            if purpose is None:
                for pfx in ("github.com/golang-jwt/jwt", "golang.org/x/crypto"):
                    if dep.startswith(pfx):
                        purpose = SECURITY_LIBS[pfx]
            if purpose:
                sec.setdefault(purpose, []).append(dep)
        self.r["security_libraries"] = {k: sorted(v) for k, v in sorted(sec.items())}
        self.r["datastores"] = pick(DATASTORES)
        self.r["llm_libraries"] = sorted(d for d in deps if d in LLM_LIBS)

    @staticmethod
    def _norm(name):
        n = name.strip().lower()
        if not n.startswith("@") and "/" not in n:
            n = n.replace("_", "-")
        return n

    def _requirements(self, text):
        reqs, pinned = [], 0
        for raw in text.splitlines():
            line = raw.split(" #", 1)[0].strip()
            if not line or line.startswith(("#", "-r", "-c", "-e", "--", "git+", "http")):
                continue
            m = re.match(r"([A-Za-z0-9][A-Za-z0-9._\-]*)", line)
            if not m:
                continue
            reqs.append(m.group(1))
            if re.search(r"===?\s*[\w.*+!\-]+", line) or "--hash" in raw:
                pinned += 1
        return reqs, pinned

    def _pyproject_deps(self, text):
        names = set()
        spec_name = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._\-]*)")
        if tomllib is not None:
            try:
                data = tomllib.loads(text)
            except Exception:
                data = None
            if data:
                proj = data.get("project") or {}
                specs = list(proj.get("dependencies") or [])
                for group in (proj.get("optional-dependencies") or {}).values():
                    specs += list(group or [])
                for group in (data.get("dependency-groups") or {}).values():
                    specs += [g for g in (group or []) if isinstance(g, str)]
                for s in specs:
                    m = spec_name.match(str(s))
                    if m:
                        names.add(m.group(1))
                poetry = (data.get("tool") or {}).get("poetry") or {}
                names |= set((poetry.get("dependencies") or {}).keys())
                names |= set((poetry.get("dev-dependencies") or {}).keys())
                for grp in (poetry.get("group") or {}).values():
                    names |= set(((grp or {}).get("dependencies") or {}).keys())
                names.discard("python")
                return names
        # Fallback: quoted PEP 508 strings and poetry-style "name = ..." lines.
        for m in re.finditer(r"[\"']([A-Za-z0-9][A-Za-z0-9._\-]*)\s*(?:\[[^\]]*\])?\s*(?:[<>=!~;@ ][^\"']*)?[\"']", text):
            names.add(m.group(1))
        names.discard("python")
        return names

    def _toml_table_keys(self, text, tables):
        keys = set()
        if tomllib is not None:
            try:
                data = tomllib.loads(text)
                for t in tables:
                    node = data
                    for part in t.split("."):
                        node = (node or {}).get(part) if isinstance(node, dict) else None
                    if isinstance(node, dict):
                        keys |= set(node.keys())
                return keys
            except Exception:
                pass
        current = None
        for line in text.splitlines():
            h = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
            if h:
                current = h.group(1).strip()
                continue
            if current in tables:
                m = re.match(r"^\s*([A-Za-z0-9_\-]+)\s*=", line)
                if m:
                    keys.add(m.group(1))
        return keys

    # -- repository governance ---------------------------------------------
    def governance(self):
        fs = self.fileset

        def first(*cands):
            for c in cands:
                if c in fs:
                    return c
            return None

        gov = {
            "security_policy": first("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md", "SECURITY.rst", "SECURITY.txt"),
            "codeowners": first("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"),
            "license": next((f for f in self.files if re.match(r"(?i)^(LICEN[CS]E|COPYING)(\.\w+)?$", f)), None),
            "gitignore": ".gitignore" if ".gitignore" in fs else None,
            "pre_commit": first(".pre-commit-config.yaml", ".pre-commit-config.yml", "lefthook.yml", ".lefthook.yml")
                          or (".husky/" if any(f.startswith(".husky/") for f in self.files) else None),
            "secret_scanning_config": first(".gitleaks.toml", ".secrets.baseline", ".trufflehog.yml", ".gitguardian.yaml"),
        }
        dependabot = first(".github/dependabot.yml", ".github/dependabot.yaml")
        ecos = []
        if dependabot and dependabot in self.texts:
            ecos = sorted(set(re.findall(r"package-ecosystem:\s*['\"]?([\w\-]+)", self.texts[dependabot])))
        renovate = first("renovate.json", "renovate.json5", ".renovaterc", ".renovaterc.json", ".github/renovate.json",
                         ".github/renovate.json5", ".gitlab/renovate.json")
        if not renovate and any(m.get("has_renovate_key") for m in self.r.get("manifests", [])):
            renovate = "package.json#renovate"
        gov["dependency_updates"] = {"dependabot": dependabot, "dependabot_ecosystems": ecos, "renovate": renovate}
        self.r["governance"] = gov

    # -- CI/CD ------------------------------------------------------------
    def ci(self):
        workflows = [f for f in self.files if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", f)]
        actions = [f for f in self.files if re.match(r"^\.github/(?:actions/.+/)?action\.ya?ml$", f)]
        other_ci = [f for f in self.files if f in (".gitlab-ci.yml", ".circleci/config.yml", "azure-pipelines.yml",
                                                   "Jenkinsfile", "bitbucket-pipelines.yml", ".travis.yml",
                                                   "cloudbuild.yaml", "buildspec.yml", ".drone.yml", "appveyor.yml")]
        tools, tests = set(), set()
        wf_reports = []
        for wf in workflows + actions:
            text = self.texts.get(wf)
            if text is None:
                continue
            rep = self._analyze_workflow(wf, text)
            wf_reports.append(rep)
            tools |= set(rep.pop("_tools"))
            tests |= set(rep.pop("_tests"))
        for f in other_ci:
            text = self.texts.get(f, "")
            for name, rx in CI_SECURITY_TOOLS:
                if re.search(rx, text, re.I):
                    tools.add(name)
            for m in CI_TEST_RE.finditer(text):
                tests.add(m.group(0).strip())
        self.r["ci"] = {
            "github_actions_workflows": len(workflows),
            "other_ci_files": other_ci,
            "security_tools_in_ci": sorted(tools),
            "test_commands_in_ci": sorted(tests)[:10],
            "workflows": wf_reports,
        }

    def _analyze_workflow(self, path, text):
        lines = text.splitlines()
        rep = {"path": path}
        rep["triggers"] = self._triggers(lines)
        m = re.search(r"^permissions\s*:\s*(.*)$", text, re.M)
        if m:
            val = m.group(1).split("#")[0].strip()
            if not val:
                block = []
                start = text[:m.start()].count("\n") + 1
                for l in lines[start:]:
                    if l.strip() and not l.startswith((" ", "\t")):
                        break
                    if l.strip():
                        block.append(l.strip())
                val = ", ".join(block) or "(empty mapping)"
            rep["top_level_permissions"] = val
        else:
            rep["top_level_permissions"] = None
        rep["job_level_permissions_blocks"] = len(re.findall(r"^[ \t]+permissions\s*:", text, re.M))
        writes = sorted(set(re.findall(r"^\s*([\w-]+)\s*:\s*write\b", text, re.M)))
        if re.search(r"permissions\s*:\s*write-all", text):
            writes.append("write-all")
        rep["write_scopes"] = writes

        unpinned, pinned = [], 0
        for mm in re.finditer(r"^\s*-?\s*uses\s*:\s*['\"]?([^'\"\s#]+)", text, re.M):
            ref = mm.group(1)
            if ref.startswith("./"):
                continue
            if ref.startswith("docker://"):
                if "@sha256:" not in ref:
                    unpinned.append({"uses": ref, "owner": "docker", "line": line_of(text, mm.start())})
                else:
                    pinned += 1
                continue
            name, _, version = ref.partition("@")
            if re.fullmatch(r"[0-9a-f]{40}", version or ""):
                pinned += 1
                continue
            owner = name.split("/")[0].lower()
            unpinned.append({"uses": ref, "owner": "github-owned" if owner in ("actions", "github") else "third-party",
                             "line": line_of(text, mm.start())})
        rep["actions_pinned_by_sha"] = pinned
        rep["actions_not_pinned"] = unpinned[:20]

        injections = []
        in_block, block_indent = False, 0
        for i, l in enumerate(lines, 1):
            stripped = l.strip()
            indent = len(l) - len(l.lstrip())
            km = re.match(r"^(\s*)(?:-\s+)?(run|script)\s*:\s*(.*)$", l)
            if km:
                rest = km.group(3).strip()
                if rest[:1] in ("|", ">"):
                    in_block, block_indent = True, len(km.group(1))
                    continue
                in_block = False
                if UNTRUSTED_GHA_CTX.search(rest):
                    injections.append({"line": i, "expr": UNTRUSTED_GHA_CTX.search(rest).group(1)})
                continue
            if in_block:
                if stripped and indent <= block_indent:
                    in_block = False
                elif UNTRUSTED_GHA_CTX.search(l):
                    injections.append({"line": i, "expr": UNTRUSTED_GHA_CTX.search(l).group(1)})
        rep["untrusted_input_in_run"] = injections[:20]

        trig = set(rep["triggers"])
        rep["pull_request_target"] = "pull_request_target" in trig
        rep["prt_checks_out_pr_head"] = bool(
            "pull_request_target" in trig and re.search(
                r"ref\s*:\s*\$\{\{\s*github\.event\.pull_request\.head\.(?:sha|ref)|refs/pull/|github\.head_ref", text))
        rep["workflow_run_trigger"] = "workflow_run" in trig
        rep["self_hosted_runner"] = bool(re.search(r"runs-on\s*:.*self-hosted", text))
        rep["oidc_id_token_write"] = bool(re.search(r"id-token\s*:\s*write", text))
        rep["long_lived_cloud_secrets"] = sorted(set(LONG_LIVED_CLOUD_SECRET_RE.findall(text)))
        rep["secrets_referenced"] = len(set(re.findall(r"secrets\.([A-Za-z0-9_]+)", text)))
        rep["tools_fetched_at_latest"] = [line_of(text, m.start()) for m in re.finditer(r"@latest\b", text)][:10]
        rep["_tools"] = [n for n, rx in CI_SECURITY_TOOLS if re.search(rx, text, re.I)]
        rep["_tests"] = [m.group(0).strip() for m in CI_TEST_RE.finditer(text)]
        return rep

    @staticmethod
    def _triggers(lines):
        for i, line in enumerate(lines):
            m = re.match(r"^(?:on|\"on\"|'on'|true)\s*:\s*(.*)$", line)
            if not m:
                continue
            rest = m.group(1).split("#")[0].strip()
            if rest:
                if rest.startswith("["):
                    return [t.strip().strip("'\"") for t in rest.strip("[]").split(",") if t.strip()]
                return [rest.strip("'\"")]
            triggers, child = [], None
            for l in lines[i + 1:]:
                if not l.strip() or l.lstrip().startswith("#"):
                    continue
                ind = len(l) - len(l.lstrip())
                if ind == 0:
                    break
                if child is None:
                    child = ind
                if ind == child:
                    mm = re.match(r"^\s*-?\s*([A-Za-z_]+)", l)
                    if mm:
                        triggers.append(mm.group(1))
            return triggers
        return []

    # -- secrets ------------------------------------------------------------
    def secrets(self):
        hits = []
        per_rule = Counter()
        self._secret_hashes = set()
        for rel, text in self.texts.items():
            ext = pseudo_ext(rel)
            lower = text.lower()
            for rid, desc, rx, conf, group in SECRET_RULES_C:
                needles, ci = SECRET_NEEDLES.get(rid, ((), False))
                if needles and not any(n in (lower if ci else text) for n in needles):
                    continue
                for m in rx.finditer(text):
                    value = m.group(group) if group else m.group(0)
                    if rid in ("generic-secret-assignment", "db-url-credentials", "openai-api-key", "jwt") and is_placeholder(value):
                        continue
                    if rid == "gcp-service-account" and "private_key" not in text:
                        continue
                    per_rule[rid] += 1
                    self._secret_hashes.add(hashlib.sha256(value.encode()).hexdigest())
                    if per_rule[rid] <= self.max_hits:
                        c = conf
                        if rid == "openai-api-key" and "T3BlbkFJ" in value:
                            c = "high"
                        hits.append({"rule": rid, "description": desc, "confidence": c, "file": rel,
                                     "line": line_of(text, m.start()), "value": mask(value) if group else m.group(0)[:40],
                                     "test_path": is_test_path(rel)})
            if (ext in CONFIG or ext == ".env") and any(n in lower for n in CONFIG_ASSIGNMENT_NEEDLES):
                for m in CONFIG_ASSIGNMENT_RE.finditer(text):
                    value = m.group(2).strip("'\"")
                    if is_placeholder(value):
                        continue
                    per_rule["config-secret-assignment"] += 1
                    self._secret_hashes.add(hashlib.sha256(value.encode()).hexdigest())
                    if per_rule["config-secret-assignment"] <= self.max_hits:
                        hits.append({"rule": "config-secret-assignment", "description": "Secret-like key with literal value in config",
                                     "confidence": "medium" if ext == ".env" else "low", "file": rel,
                                     "line": line_of(text, m.start()), "key": m.group(1), "value": mask(value),
                                     "test_path": is_test_path(rel)})
        order = {"high": 0, "medium": 1, "low": 2}
        best = {}  # one entry per (file, line): keep the most specific/confident rule
        for h in hits:
            key = (h["file"], h["line"])
            if key not in best or order[h["confidence"]] < order[best[key]["confidence"]]:
                best[key] = h
        hits = sorted(best.values(), key=lambda h: (order[h["confidence"]], h["test_path"], h["file"], h["line"]))
        self.r["secrets"] = {"candidates": hits, "counts_by_rule": dict(per_rule)}

        # Sensitive files: tracked vs. present-but-not-ignored vs. ignored.
        tracked, exposed, ignored = [], [], []
        for rel in self.files:
            cat = classify_sensitive_name(rel)
            if cat and not is_vendored(rel):
                if cat == "credential-file" and rel.endswith(".npmrc"):
                    t = self.texts.get(rel, "")
                    if not re.search(r"_authToken\s*=\s*(?!\$\{)\S+", t):
                        continue
                if cat == "private-key-file" and rel.endswith((".pem", ".key")):
                    t = self.texts.get(rel)
                    if t is not None and "PRIVATE KEY" not in t:
                        continue
                tracked.append({"file": rel, "kind": cat})
        if self.is_git:
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
                for fn in filenames:
                    rel = os.path.relpath(os.path.join(dirpath, fn), self.root).replace(os.sep, "/")
                    if rel in self.fileset:
                        continue
                    cat = classify_sensitive_name(rel)
                    if not cat:
                        continue
                    ign = run(["git", "-C", self.root, "check-ignore", "-q", "--", rel]) is not None
                    (ignored if ign else exposed).append({"file": rel, "kind": cat})
            probe = run(["git", "-C", self.root, "check-ignore", "-q", "--no-index", "--", ".env"]) is not None
        else:
            probe = None
        examples = [f for f in self.files if re.search(r"(?i)(^|/)\.env[^/]*\.(example|sample|template|dist)$|(^|/)(example|sample)\.env$", f)]
        self.r["sensitive_files"] = {
            "tracked": tracked[:30],
            "untracked_not_ignored": exposed[:30],
            "ignored_present": [f["file"] for f in ignored][:30],
            "gitignore_covers_dotenv": probe,
            "env_example_files": examples[:10],
        }

    def history(self, n_commits):
        if not self.is_git or n_commits <= 0:
            self.r["history_scan"] = {"performed": False}
            return
        hist_rules = [r for r in SECRET_RULES_C if r[0] in HISTORY_RULE_IDS]
        cmd = ["git", "-C", self.root, "log", "--all", "-p", "--no-color", "-U0", "--no-ext-diff",
               "-n", str(n_commits), "--format=__COMMIT__ %H %cI"]
        found, seen = [], set()
        start = time.time()
        lines_read = 0
        truncated = False
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
        except OSError:
            self.r["history_scan"] = {"performed": False, "error": "git not available"}
            return
        commit, date, path = None, None, None
        for line in proc.stdout:
            lines_read += 1
            if lines_read > 3_000_000 or time.time() - start > 90:
                truncated = True
                break
            if line.startswith("__COMMIT__ "):
                parts = line.split()
                commit, date = parts[1][:12], (parts[2] if len(parts) > 2 else None)
            elif line.startswith("+++ "):
                path = line[6:].strip() if line.startswith("+++ b/") else None
            elif line.startswith("+") and path:
                for rid, desc, rx, conf, group in hist_rules:
                    for m in rx.finditer(line):
                        value = m.group(group) if group else m.group(0)
                        h = hashlib.sha256(value.encode()).hexdigest()
                        key = (rid, h)
                        if key in seen:
                            continue
                        seen.add(key)
                        found.append({"rule": rid, "commit": commit, "date": date, "file": path,
                                      "value": mask(value) if group else value[:40],
                                      "still_in_working_tree": h in self._secret_hashes})
        proc.kill()
        proc.wait()
        self.r["history_scan"] = {"performed": True, "commits_requested": n_commits, "truncated": truncated,
                                  "findings": found[: self.max_hits * 2]}

    # -- containers & infrastructure ------------------------------------------
    def containers(self):
        dockerfiles = [f for f in self.texts if pseudo_ext(f) == ".dockerfile"]
        reports = []
        for df in dockerfiles:
            text = re.sub(r"\\\r?\n", " ", self.texts[df])
            rep = {"path": df}
            stages, images, final_user = set(), [], None
            for line in text.splitlines():
                s = line.strip()
                m = re.match(r"(?i)^FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", s)
                if m:
                    img = m.group(1)
                    if m.group(2):
                        stages.add(m.group(2).lower())
                    final_user = None
                    if img.lower() in stages or img == "scratch":
                        continue
                    tag = img.split("@")[0].rsplit(":", 1)[1] if ":" in img.split("@")[0].split("/")[-1] else None
                    images.append({"image": img, "digest_pinned": "@sha256:" in img,
                                   "tag": tag, "latest_or_untagged": ("@sha256:" not in img) and tag in (None, "latest")})
                    continue
                m = re.match(r"(?i)^USER\s+(\S+)", s)
                if m:
                    final_user = m.group(1)
            rep["base_images"] = images
            rep["final_stage_user"] = final_user
            rep["runs_as_root"] = final_user is None or final_user.split(":")[0] in ("root", "0")
            rep["add_remote_url"] = bool(re.search(r"(?im)^\s*ADD\s+(?:--\S+\s+)*https?://", text))
            rep["curl_pipe_shell"] = bool(re.search(r"(?:curl|wget)[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b", text))
            rep["secret_like_env_or_arg"] = sorted(set(
                m.group(1) for m in re.finditer(r"(?im)^\s*(?:ENV|ARG)\s+([A-Za-z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|ACCESS_?KEY)[A-Za-z0-9_]*)\s*[= ]\s*\S", text)))
            rep["copies_whole_context"] = bool(re.search(r"(?im)^\s*(?:COPY|ADD)\s+(?:--\S+\s+)*\.\s+", text))
            d = df.rsplit("/", 1)[0] if "/" in df else ""
            rep["dockerignore"] = next((c for c in ((d + "/.dockerignore") if d else ".dockerignore", ".dockerignore")
                                        if c in self.fileset), None)
            rep["healthcheck"] = bool(re.search(r"(?im)^\s*HEALTHCHECK\s", text))
            reports.append(rep)

        compose = []
        for f, text in self.texts.items():
            if re.search(r"(^|/)(docker-)?compose[^/]*\.ya?ml$", f):
                compose.append({
                    "path": f,
                    "privileged": bool(re.search(r"privileged\s*:\s*true", text)),
                    "host_network": bool(re.search(r"network_mode\s*:\s*['\"]?host", text)),
                    "docker_socket_mount": "/var/run/docker.sock" in text,
                    "db_ports_published_all_interfaces": sorted(set(re.findall(
                        r"-\s*['\"]?(?:0\.0\.0\.0:)?(\d+):(?:5432|3306|27017|6379|9200|11211|5984|1433|9042)['\"]?\s*$", text, re.M))),
                })

        k8s = []
        for f, text in self.texts.items():
            if pseudo_ext(f) not in (".yml", ".yaml") or "apiVersion" not in text:
                continue
            kinds = set(re.findall(r"(?m)^kind\s*:\s*(\w+)", text))
            if kinds & {"Deployment", "Pod", "StatefulSet", "DaemonSet", "Job", "CronJob", "ReplicaSet"}:
                k8s.append({
                    "path": f, "kinds": sorted(kinds),
                    "privileged": bool(re.search(r"privileged\s*:\s*true", text)),
                    "run_as_non_root": bool(re.search(r"runAsNonRoot\s*:\s*true", text)),
                    "allow_privilege_escalation_false": bool(re.search(r"allowPrivilegeEscalation\s*:\s*false", text)),
                    "read_only_root_fs": bool(re.search(r"readOnlyRootFilesystem\s*:\s*true", text)),
                    "host_network_or_pid": bool(re.search(r"host(?:Network|PID|IPC)\s*:\s*true", text)),
                    "host_path": "hostPath" in text,
                    "resource_limits": bool(re.search(r"limits\s*:", text)),
                    "latest_images": sorted(set(re.findall(r"image\s*:\s*['\"]?([^\s'\"]+:latest)", text))),
                })
            if "Secret" in kinds and re.search(r"(?m)^(?:data|stringData)\s*:", text):
                k8s.append({"path": f, "kinds": ["Secret"], "committed_secret_manifest": True})

        tf = []
        tf_rules = [
            ("open-to-world-ingress", r"cidr_blocks\s*=\s*\[[^\]]*\"0\.0\.0\.0/0\"|ipv6_cidr_blocks\s*=\s*\[[^\]]*\"::/0\""),
            ("public-bucket-acl", r"acl\s*=\s*\"public-read(?:-write)?\""),
            ("public-access-block-disabled", r"block_public_(?:acls|policy)\s*=\s*false|restrict_public_buckets\s*=\s*false"),
            ("db-publicly-accessible", r"publicly_accessible\s*=\s*true"),
            ("encryption-disabled", r"(?:storage_)?encrypted\s*=\s*false"),
            ("imdsv1-allowed", r"http_tokens\s*=\s*\"optional\""),
            ("weak-tls", r"min(?:imum)?_tls_version\s*=\s*\"(?:TLS1_0|TLS1_1|1\.0|1\.1)\""),
        ]
        for f, text in self.texts.items():
            if pseudo_ext(f) != ".tf":
                continue
            flags = {}
            for rid, rx in tf_rules:
                ms = [line_of(text, m.start()) for m in re.finditer(rx, text)]
                if ms:
                    flags[rid] = ms[:5]
            if flags:
                tf.append({"path": f, "flags": flags})
        self.r["containers_iac"] = {"dockerfiles": reports, "compose": compose, "kubernetes": k8s[:20],
                                    "terraform_flags": tf[:20],
                                    "terraform_files": sum(1 for f in self.files if f.endswith(".tf"))}

    # -- AI agent configuration ------------------------------------------------
    def ai_config(self):
        out = {}
        instr = [f for f in self.files if f in ("CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules",
                                                ".windsurfrules", ".github/copilot-instructions.md")
                 or f.startswith(".cursor/rules/") or re.match(r"^[^/]+/(CLAUDE|AGENTS)\.md$", f)]
        out["instruction_files"] = instr[:20]
        out["claude_dirs"] = sorted(set(f.split("/")[1] for f in self.files if f.startswith(".claude/") and f.count("/") >= 2))
        settings = []
        for f in (".claude/settings.json", ".claude/settings.local.json"):
            if f not in self.fileset:
                continue
            rep = {"path": f, "tracked": True}
            if f.endswith("settings.local.json"):
                rep["note"] = "settings.local.json is meant to be personal and uncommitted"
            try:
                data = json.loads(self.texts.get(f, "") or "{}")
            except ValueError:
                rep["parse_error"] = True
                settings.append(rep)
                continue
            perms = data.get("permissions") or {}
            allow = [str(x) for x in (perms.get("allow") or [])]
            deny = [str(x) for x in (perms.get("deny") or [])]
            rep["allow"] = allow[:40]
            rep["deny"] = deny[:40]
            rep["ask"] = [str(x) for x in (perms.get("ask") or [])][:20]
            rep["default_mode"] = perms.get("defaultMode") or data.get("defaultMode")
            rep["disable_bypass_permissions_mode"] = perms.get("disableBypassPermissionsMode")
            rep["additional_directories"] = perms.get("additionalDirectories")
            broad = []
            for rule in allow:
                low = rule.strip().lower()
                if low in ("bash", "bash(*)", "bash(:*)", "bash(**)", "bash(* *)"):
                    broad.append(rule + "  <- any shell command")
                    continue
                m = re.match(r"bash\((.+)\)$", low)
                if m:
                    first_word = re.split(r"[\s:*]", m.group(1).strip(), 1)[0]
                    if first_word in ("rm", "curl", "wget", "sudo", "chmod", "chown", "ssh", "scp", "rsync", "sh", "bash",
                                      "zsh", "eval", "python", "python3", "node", "npx", "bunx", "deno", "ruby", "perl",
                                      "docker", "kubectl", "terraform", "aws", "gcloud", "az", "git", "gh", "nc", "dd"):
                        broad.append(rule + "  <- high-impact command family")
                if low in ("webfetch", "webfetch(*)"):
                    broad.append(rule + "  <- any URL")
                if low.startswith("mcp__") and low.endswith("*"):
                    broad.append(rule + "  <- all tools of an MCP server")
            rep["broad_allow_rules"] = broad
            rep["denies_secret_reads"] = any(re.search(r"\.env|secret|\.pem|\.key|id_rsa|credentials|\.ssh", d, re.I) for d in deny)
            rep["enable_all_project_mcp_servers"] = data.get("enableAllProjectMcpServers")
            rep["enabled_mcpjson_servers"] = data.get("enabledMcpjsonServers")
            hooks = data.get("hooks") or {}
            hook_cmds = []
            if isinstance(hooks, dict):
                for event, entries in hooks.items():
                    for entry in entries or []:
                        for h in (entry or {}).get("hooks", []) if isinstance(entry, dict) else []:
                            if isinstance(h, dict) and h.get("command"):
                                hook_cmds.append("%s: %s" % (event, mask_secrets_in(str(h["command"]))[:120]))
            rep["hooks"] = hook_cmds[:20]
            env = data.get("env") or {}
            rep["env_literal_secrets"] = sorted(k for k, v in env.items()
                                                if re.search(r"(?i)key|token|secret|password", k) and isinstance(v, str)
                                                and not is_placeholder(v))
            rep["api_key_helper"] = bool(data.get("apiKeyHelper"))
            rep["sandbox"] = data.get("sandbox") if isinstance(data.get("sandbox"), (dict, bool)) else None
            settings.append(rep)
        out["claude_settings"] = settings

        mcp = []
        for f in (".mcp.json", ".vscode/mcp.json", ".cursor/mcp.json", ".gemini/settings.json"):
            if f not in self.fileset:
                continue
            try:
                data = json.loads(self.texts.get(f, "") or "{}")
            except ValueError:
                mcp.append({"path": f, "parse_error": True})
                continue
            servers = data.get("mcpServers") or data.get("servers") or {}
            for name, cfg in (servers.items() if isinstance(servers, dict) else []):
                cfg = cfg or {}
                args = [str(a) for a in (cfg.get("args") or [])]
                cmd = str(cfg.get("command") or "")
                issues = []
                if cmd in ("npx", "bunx", "pnpx", "uvx", "pipx") or (cmd == "pnpm" and "dlx" in args):
                    pkgs = [a for a in args if not a.startswith("-") and a not in ("dlx", "run")]
                    pkg = pkgs[0] if pkgs else ""
                    if pkg and not re.search(r"(?<!^)@\d|==\d", pkg):
                        issues.append("package not version-pinned: %s" % pkg)
                for field in ("env", "headers"):
                    for k, v in (cfg.get(field) or {}).items():
                        if isinstance(v, str) and re.search(r"(?i)key|token|secret|password|authorization", k) and "${" not in v \
                                and not is_placeholder(v.replace("Bearer ", "")):
                            issues.append("literal credential in %s.%s (%s)" % (field, k, mask(v)))
                url = str(cfg.get("url") or "")
                if url.startswith("http://") and not re.match(r"http://(localhost|127\.0\.0\.1|\[::1\])", url):
                    issues.append("plain-HTTP remote server")
                if any(rx.search(a) for a in args for _, _, rx, _, _ in SECRET_RULES_C):
                    issues.append("credential embedded in command arguments")
                command = mask_secrets_in((cmd + " " + " ".join(args)).strip())
                mcp.append({"path": f, "server": name, "command": command[:160] or None,
                            "url": mask_secrets_in(url) or None, "type": cfg.get("type"), "issues": issues})
        out["mcp_servers"] = mcp
        self.r["ai_agent_config"] = out

    # -- code patterns ---------------------------------------------------------
    def code_patterns(self):
        hits, counts = [], Counter()
        positives = defaultdict(list)
        pos_counts = Counter()
        routes = Counter()
        llm_files, auth_files = [], []
        for rel, text in self.texts.items():
            ext = pseudo_ext(rel)
            lower = None
            for rule in RISK_RULES:
                if rule["exts"] is not None and ext not in rule["exts"]:
                    continue
                if rule["needles"]:
                    hay = text
                    if rule["ci"]:
                        if lower is None:
                            lower = text.lower()
                        hay = lower
                    if not any((n.lower() if rule["ci"] else n) in hay for n in rule["needles"]):
                        continue
                if rule["file_requires"] and not rule["file_requires"].search(text):
                    continue
                for m in rule["re"].finditer(text):
                    if rule["context"] and not rule["context"].search(line_text(text, m.start())):
                        continue
                    if rule["absent_after"]:
                        rx_after, window = rule["absent_after"]
                        tail = text[m.end():m.end() + window].split(";", 1)[0]
                        if rx_after.search(tail):
                            continue
                    counts[rule["id"]] += 1
                    if counts[rule["id"]] <= self.max_hits:
                        snip = snippet(text, m.start())
                        if rule["mask_group"] and m.group(rule["mask_group"]):
                            snip = snip.replace(m.group(rule["mask_group"]), mask(m.group(rule["mask_group"])))
                        hits.append({"rule": rule["id"], "title": rule["title"], "cwe": rule["cwe"], "file": rel,
                                     "line": line_of(text, m.start()), "snippet": snip,
                                     "test_path": is_test_path(rel)})
            if ext in CODE or ext in CONFIG or ext in TEMPLATES:
                if lower is None:
                    lower = text.lower()
                for cat, rx in POSITIVE_RULES_C:
                    if not any(n in lower for n in POSITIVE_NEEDLES[cat]):
                        continue
                    m = rx.search(text)
                    if m:
                        pos_counts[cat] += 1
                        if len(positives[cat]) < EXAMPLES_PER_CATEGORY and not is_test_path(rel):
                            positives[cat].append("%s:%d" % (rel, line_of(text, m.start())))
            for exts, rx in ROUTE_RULES:
                if ext in exts:
                    n = len(rx.findall(text))
                    if n:
                        routes[rel] += n
            if ext in CODE and LLM_IMPORT_RE.search(text):
                llm_files.append(rel)
            if ext in CODE and AUTH_PATH_RE.search(rel) and not is_test_path(rel):
                auth_files.append(rel)
        for rel in self.files:  # Next.js/Remix style file-based API routes
            if re.search(r"(^|/)(pages/api/|app/.*/route\.[jt]sx?$)", rel) and rel not in routes:
                routes[rel] += 1
        hits.sort(key=lambda h: (h["test_path"], h["rule"], h["file"], h["line"]))
        self.r["code_patterns"] = {"hits": hits, "counts": dict(counts)}
        self.r["positive_evidence"] = {cat: {"files": pos_counts[cat], "examples": positives[cat]}
                                       for cat, _ in POSITIVE_RULES_C}
        self.r["entrypoints"] = {"files_with_routes": len(routes), "top": routes.most_common(25)}
        self.r["llm_call_sites"] = sorted(llm_files)[:30]
        self.r["auth_related_files"] = sorted(auth_files)[:40]

    def tools(self):
        self.r["local_tools_available"] = {t: bool(shutil.which(t)) for t in EXTERNAL_TOOLS}

    def collect(self, history_commits):
        self.inventory()
        self.load_texts()
        self.manifests()
        self.governance()
        self.ci()
        self.secrets()
        self.history(history_commits)
        self.containers()
        self.ai_config()
        self.code_patterns()
        self.tools()
        return self.r


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def yn(v):
    return "yes" if v else "no"


def code_span(s):
    """Render text as a Markdown code span, even if it contains backticks."""
    if "`" not in s:
        return "`%s`" % s
    return "`` %s ``" % s


def render_md(r):
    out = []
    w = out.append
    g = r["git"]
    w("# Security signals: %s" % r["root"])
    w("")
    w("_collect_signals.py %s — generated %s. Signals are hints to verify, not verdicts._" % (r["tool"]["version"], r["generated_at"]))
    w("")
    w("## Repository")
    if g.get("is_git_repo"):
        w("- git: remote=%s, github_repo=%s, branch=%s, HEAD=%s, commits=%s, last commit=%s" % (
            g.get("remote"), g.get("github_repo"), g.get("branch"), g.get("head"), g.get("commit_count"), g.get("last_commit_date")))
    else:
        w("- git: not a git repository (walked the directory tree)")
    sc = r["scan"]
    w("- text files scanned: %d (skipped: %s)" % (sc["text_files_scanned"], ", ".join("%s=%d" % kv for kv in sc["skipped"].items()) or "none"))
    w("- languages (files): %s" % (", ".join("%s %d" % kv for kv in list(r["languages"].items())[:10]) or "none detected"))
    if r["vendored_tracked_dirs"]:
        w("- vendored/generated dirs tracked in git: %s" % ", ".join("%s (%d files)" % kv for kv in r["vendored_tracked_dirs"].items()))
    if r["binary_artifacts_count"]:
        w("- binary artifacts tracked: %d (e.g. %s)" % (r["binary_artifacts_count"], ", ".join(r["binary_artifacts_tracked"][:5])))
    w("")

    w("## Project profile")
    if r["manifests"]:
        for m in r["manifests"]:
            extra = ""
            if "requirements" in m:
                extra = " — %d/%d requirements exactly pinned" % (m["exactly_pinned"], m["requirements"])
            if m.get("install_scripts"):
                extra += " — install scripts: %s" % ", ".join(m["install_scripts"])
            w("- manifest `%s` (%s): lockfile=%s%s" % (m["path"], m["ecosystem"], m.get("lockfile") or "**none found**", extra))
    else:
        w("- no dependency manifests found")
    w("- frameworks: %s" % (", ".join("%s (%s)" % (k, ", ".join(v)) for k, v in r["frameworks"].items()) or "none detected"))
    w("- security libraries: %s" % (", ".join("%s: %s" % (k, ", ".join(v)) for k, v in r["security_libraries"].items()) or "none detected"))
    w("- datastores/ORMs: %s" % (", ".join(r["datastores"].keys()) or "none detected"))
    w("- LLM/AI libraries: %s" % (", ".join(r["llm_libraries"]) or "none detected"))
    ep = r["entrypoints"]
    w("- route/entrypoint files: %d%s" % (ep["files_with_routes"], (" — top: " + ", ".join("%s (%d)" % kv for kv in ep["top"][:12])) if ep["top"] else ""))
    if r["auth_related_files"]:
        w("- auth-related files: %s" % ", ".join(r["auth_related_files"][:20]))
    if r["llm_call_sites"]:
        w("- files importing LLM SDKs: %s" % ", ".join(r["llm_call_sites"][:15]))
    w("")

    w("## Governance & process")
    gv = r["governance"]
    w("- SECURITY.md: %s" % (gv["security_policy"] or "**missing**"))
    w("- CODEOWNERS: %s" % (gv["codeowners"] or "missing"))
    w("- LICENSE: %s" % (gv["license"] or "missing"))
    w("- .gitignore: %s" % (gv["gitignore"] or "**missing**"))
    w("- pre-commit hooks: %s" % (gv["pre_commit"] or "none"))
    w("- secret-scanning config in repo: %s" % (gv["secret_scanning_config"] or "none"))
    du = gv["dependency_updates"]
    w("- dependency update automation: dependabot=%s%s, renovate=%s" % (
        du["dependabot"] or "none", (" (" + ", ".join(du["dependabot_ecosystems"]) + ")") if du["dependabot_ecosystems"] else "",
        du["renovate"] or "none"))
    ci = r["ci"]
    w("- CI: GitHub Actions workflows=%d%s" % (ci["github_actions_workflows"], (", other: " + ", ".join(ci["other_ci_files"])) if ci["other_ci_files"] else ""))
    w("- security tools referenced in CI: %s" % (", ".join(ci["security_tools_in_ci"]) or "**none**"))
    w("- test commands in CI: %s" % (", ".join(ci["test_commands_in_ci"]) or "none found"))
    w("- NOT visible from the repository (check via GitHub settings/API): branch protection/rulesets, required reviews, "
      "secret scanning & push protection, Dependabot alerts, private vulnerability reporting, repo visibility")
    w("")

    if ci["workflows"]:
        w("## GitHub Actions details")
        for wf in ci["workflows"]:
            w("### %s" % wf["path"])
            w("- triggers: %s" % (", ".join(wf["triggers"]) or "(none/composite action)"))
            w("- top-level permissions: %s; job-level permission blocks: %d; write scopes: %s" % (
                wf["top_level_permissions"] or "**not set (repository default token permissions apply)**",
                wf["job_level_permissions_blocks"], ", ".join(wf["write_scopes"]) or "none"))
            np_ = wf["actions_not_pinned"]
            w("- actions pinned by full SHA: %d; not pinned: %d%s" % (
                wf["actions_pinned_by_sha"], len(np_),
                (" — " + ", ".join("%s [%s] L%d" % (a["uses"], a["owner"], a["line"]) for a in np_[:8])) if np_ else ""))
            if wf["untrusted_input_in_run"]:
                w("- **untrusted input interpolated in run/script**: %s" % ", ".join("L%d `%s`" % (x["line"], x["expr"]) for x in wf["untrusted_input_in_run"]))
            flags = []
            if wf["pull_request_target"]:
                flags.append("pull_request_target" + (" + checks out PR head (**dangerous**)" if wf["prt_checks_out_pr_head"] else ""))
            if wf["workflow_run_trigger"]:
                flags.append("workflow_run trigger")
            if wf["self_hosted_runner"]:
                flags.append("self-hosted runner")
            if wf["oidc_id_token_write"]:
                flags.append("OIDC (id-token: write)")
            if wf["long_lived_cloud_secrets"]:
                flags.append("long-lived cloud credentials: " + ", ".join(wf["long_lived_cloud_secrets"]))
            if wf["tools_fetched_at_latest"]:
                flags.append("tools fetched at @latest (unpinned) on L" + ",".join(map(str, wf["tools_fetched_at_latest"])))
            if flags:
                w("- notes: " + "; ".join(flags))
            w("- secrets referenced: %d" % wf["secrets_referenced"])
        w("")

    w("## Secrets")
    s = r["secrets"]
    if s["candidates"]:
        w("Secret-like values in scanned files (masked; confirm each by reading the line):")
        for h in s["candidates"]:
            w("- [%s] %s — `%s:%d` %s%s%s" % (h["confidence"], h["rule"], h["file"], h["line"],
                                             ("key=%s " % h["key"]) if h.get("key") else "", h["value"],
                                             " (test/example path)" if h["test_path"] else ""))
        over = {k: v for k, v in s["counts_by_rule"].items() if v > 0}
        w("- total by rule: %s" % ", ".join("%s=%d" % kv for kv in over.items()))
    else:
        w("- no secret-like values matched in scanned files")
    sf = r["sensitive_files"]
    w("- sensitive files tracked in git: %s" % (", ".join("%s (%s)" % (f["file"], f["kind"]) for f in sf["tracked"]) or "none"))
    if sf["untracked_not_ignored"]:
        w("- **sensitive files present but NOT gitignored**: %s" % ", ".join(f["file"] for f in sf["untracked_not_ignored"]))
    if sf["ignored_present"]:
        w("- sensitive files present and gitignored: %s" % ", ".join(sf["ignored_present"][:10]))
    uses_dotenv = bool(sf["tracked"] or sf["untracked_not_ignored"] or sf["ignored_present"] or sf["env_example_files"])
    covers = sf["gitignore_covers_dotenv"]
    w("- .gitignore covers `.env`: %s" % (
        "unknown" if covers is None else "yes" if covers else
        "**no**" if uses_dotenv else "no (no .env files seen; matters only if the project adopts them)"))
    w("- env example files: %s" % (", ".join(sf["env_example_files"]) or "none"))
    hs = r["history_scan"]
    if hs.get("performed"):
        w("- git history scan (last %d commits, high-confidence rules%s): %s" % (
            hs["commits_requested"], ", truncated" if hs["truncated"] else "",
            "; ".join("%s in %s @%s (%s)%s" % (f["rule"], f["file"], f["commit"], f["value"],
                                               " still present" if f["still_in_working_tree"] else " removed from tree but in history")
                      for f in hs["findings"]) or "no findings"))
    else:
        w("- git history scan: not performed (re-run with --scan-history N)")
    w("")

    ci_ = r["containers_iac"]
    if ci_["dockerfiles"] or ci_["compose"] or ci_["kubernetes"] or ci_["terraform_files"]:
        w("## Containers & IaC")
        for d in ci_["dockerfiles"]:
            imgs = ", ".join("%s%s" % (i["image"], " (unpinned/latest)" if i["latest_or_untagged"] else (" (digest)" if i["digest_pinned"] else ""))
                             for i in d["base_images"]) or "-"
            w("- `%s`: base=%s; final USER=%s%s; dockerignore=%s; ADD remote URL=%s; curl|sh=%s; secret-like ENV/ARG=%s; COPY whole context=%s" % (
                d["path"], imgs, d["final_stage_user"] or "(none)", " (**runs as root**)" if d["runs_as_root"] else "",
                d["dockerignore"] or "**none**", yn(d["add_remote_url"]), yn(d["curl_pipe_shell"]),
                ", ".join(d["secret_like_env_or_arg"]) or "none", yn(d["copies_whole_context"])))
        for c in ci_["compose"]:
            w("- `%s`: privileged=%s, host network=%s, docker.sock mount=%s, DB ports published on all interfaces=%s" % (
                c["path"], yn(c["privileged"]), yn(c["host_network"]), yn(c["docker_socket_mount"]),
                ", ".join(c["db_ports_published_all_interfaces"]) or "none"))
        for k in ci_["kubernetes"]:
            if k.get("committed_secret_manifest"):
                w("- `%s`: **Kubernetes Secret manifest with data committed**" % k["path"])
                continue
            w("- `%s` (%s): privileged=%s, runAsNonRoot=%s, allowPrivilegeEscalation:false=%s, readOnlyRootFS=%s, host ns=%s, hostPath=%s, limits=%s, latest images=%s" % (
                k["path"], ",".join(k["kinds"]), yn(k["privileged"]), yn(k["run_as_non_root"]), yn(k["allow_privilege_escalation_false"]),
                yn(k["read_only_root_fs"]), yn(k["host_network_or_pid"]), yn(k["host_path"]), yn(k["resource_limits"]),
                ", ".join(k["latest_images"]) or "none"))
        for t in ci_["terraform_flags"]:
            w("- `%s`: %s" % (t["path"], "; ".join("%s at L%s" % (k, ",".join(map(str, v))) for k, v in t["flags"].items())))
        w("")

    ai = r["ai_agent_config"]
    if ai["instruction_files"] or ai["claude_settings"] or ai["mcp_servers"] or ai["claude_dirs"]:
        w("## AI coding-agent configuration")
        if ai["instruction_files"]:
            w("- instruction files: %s" % ", ".join(ai["instruction_files"]))
        if ai["claude_dirs"]:
            w("- .claude/ subdirectories: %s" % ", ".join(ai["claude_dirs"]))
        for st in ai["claude_settings"]:
            if st.get("parse_error"):
                w("- `%s`: could not parse JSON" % st["path"])
                continue
            w("- `%s`%s: defaultMode=%s; allow=%d; deny=%d (denies secret reads: %s); enableAllProjectMcpServers=%s; hooks=%d; literal secrets in env=%s" % (
                st["path"], " (" + st["note"] + ")" if st.get("note") else "", st["default_mode"] or "(unset)",
                len(st["allow"]), len(st["deny"]), yn(st["denies_secret_reads"]), st["enable_all_project_mcp_servers"],
                len(st["hooks"]), ", ".join(st["env_literal_secrets"]) or "none"))
            if st["broad_allow_rules"]:
                w("  - broad allow rules: %s" % "; ".join(st["broad_allow_rules"]))
            if st["hooks"]:
                w("  - hooks: %s" % "; ".join(st["hooks"][:5]))
        for m in ai["mcp_servers"]:
            if m.get("parse_error"):
                w("- `%s`: could not parse JSON" % m["path"])
                continue
            w("- MCP server `%s` in `%s`: %s%s" % (m["server"], m["path"], m["command"] or m["url"] or "?",
                                                 (" — issues: " + "; ".join(m["issues"])) if m["issues"] else ""))
        w("")

    w("## Risky code patterns (hints — read the surrounding code before judging)")
    cp = r["code_patterns"]
    if cp["hits"]:
        w("Counts: " + ", ".join("%s=%d" % kv for kv in sorted(cp["counts"].items())))
        for h in cp["hits"]:
            w("- [%s%s] `%s:%d` %s%s" % (h["rule"], (" " + h["cwe"]) if h["cwe"] else "", h["file"], h["line"],
                                       code_span(h["snippet"]), " (test/example path)" if h["test_path"] else ""))
    else:
        w("- no risky patterns matched")
    w("")
    w("## Positive evidence (code suggesting a control exists — verify it is applied everywhere needed)")
    for cat, v in r["positive_evidence"].items():
        w("- %s: %d file(s)%s" % (cat, v["files"], (" — e.g. " + ", ".join(v["examples"])) if v["examples"] else ""))
    w("")
    w("## Local security tools available")
    avail = [t for t, ok in r["local_tools_available"].items() if ok]
    w("- available: %s" % (", ".join(avail) or "none"))
    w("- not installed: %s" % ", ".join(t for t, ok in r["local_tools_available"].items() if not ok))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Collect security signals from a repository (local, read-only).")
    ap.add_argument("root", nargs="?", default=".", help="repository root (default: .)")
    ap.add_argument("--format", choices=("md", "json"), default="md")
    ap.add_argument("--output", help="write to this file instead of stdout")
    ap.add_argument("--scan-history", type=int, default=0, metavar="N",
                    help="also scan the last N commits (all refs) for high-confidence secrets")
    ap.add_argument("--max-hits", type=int, default=25, help="max examples reported per rule (default 25)")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        ap.error("not a directory: %s" % args.root)
    report = Collector(args.root, args.max_hits).collect(args.scan_history)
    text = json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render_md(report)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s" % args.output)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
