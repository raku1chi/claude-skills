# claude-skills

自作の [Claude Skills](https://code.claude.com/docs/en/skills) 置き場。

## スキル一覧

| スキル | できること |
|---|---|
| [security-posture-check](skills/security-posture-check/) | リポジトリのセキュリティ対策を OWASP ASVS 5.0・OWASP Top 10:2025・NIST SSDF などの基準に照らして証拠ベースで診断し、「できていること／できていないこと」と優先度付きの対応方針を出す。結果は Markdown レポートか GitHub Issues にできる |

## インストール

### Claude Code（すべてのプロジェクトで使う）

```bash
git clone https://github.com/raku1chi/claude-skills.git ~/src/claude-skills
mkdir -p ~/.claude/skills
ln -s ~/src/claude-skills/skills/security-posture-check ~/.claude/skills/security-posture-check
```

シンボリックリンクにしておくと、`git pull` するだけで更新が反映される。

### Claude Code（特定のプロジェクトだけで使う）

```bash
mkdir -p .claude/skills
cp -r ~/src/claude-skills/skills/security-posture-check .claude/skills/
```

## 使い方

Claude Code で次のように頼むと、スキルが使われる（`/security-posture-check` で明示的に呼び出してもよい）。

- 「このリポジトリのセキュリティ診断をして、対応方針を出して」
- 「公開前にセキュリティで足りないところを洗い出して。結果は security-reports/ に保存して」
- 「AI 機能と Claude Code の設定も含めてセキュリティチェックして。対応が必要なものは Issue にしたい」

診断結果をチャットで示したあと、出力先（ローカルの Markdown レポート / GitHub Issues / 両方）を確認してから書き出す。Issue を作る前には、作成予定の一覧を見せて了承を取る。

### 必要なもの

- Python 3.8 以上（事実収集スクリプト用。標準ライブラリのみ。無い場合は Claude が手作業で同じ観点を確認する）
- Issue を作る場合: 認証済みの `gh` CLI、または GitHub の MCP ツール（どちらもなければ Issue の下書きをファイルに書き出す）
- 任意: gitleaks、semgrep、trivy などのセキュリティツール（入っていれば使う。インストールはしない）

## ディレクトリ構成

```
skills/
└── <skill-name>/
    ├── SKILL.md        # スキル本体（frontmatter の name / description と手順）
    ├── scripts/        # スキルが実行するスクリプト
    └── references/     # 必要なときだけ読み込む参考資料
```
