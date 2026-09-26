# 使用している基準と情報源

チェック項目の根拠にしている資料の一覧。版・公開日・URL は 2026-09 に原典で確認した。レポートの「適用した基準」には、実際に使ったものだけを載せる。

## アプリケーション

| 基準 | 版・公開日 | URL | 使い方 |
|---|---|---|---|
| OWASP ASVS（Application Security Verification Standard） | 5.0.0（2025-05-30） | https://owasp.org/projects/asvs / 原文 https://github.com/OWASP/ASVS/tree/v5.0.0 | 要件単位の根拠。表記は `v5.0.0-<章>.<節>.<番号>`（例: v5.0.0-1.2.5）。17 章 345 要件、L1 70・L2 183・L3 92。レベルは累積（L2 は L1 を含む） |
| OWASP Top 10:2025 | 正式版（2025-11-06 に RC として公開され、その後正式版に移行） | https://owasp.org/Top10/2025/ （日本語: https://owasp.org/Top10/2025/ja/ ） | 指摘の分類。各カテゴリのページが CWE の対応表を持つ |
| OWASP API Security Top 10 | 2023（2023-06-05） | https://owasp.org/API-Security/editions/2023/en/0x11-t10/ | API の認可・リソース消費など |
| CWE / CWE Top 25 | Top 25 は 2025 年版（2025-12-11） | https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html / 個別: https://cwe.mitre.org/data/definitions/<番号>.html | 個別の弱点の分類 |
| OWASP Cheat Sheet Series | 随時更新 | https://cheatsheetseries.owasp.org/ | 対応方針の参考 |
| IPA「安全なウェブサイトの作り方」 | 改訂第 7 版（第 4 刷 2021-03-31） | https://www.ipa.go.jp/security/vuln/websecurity/about.html | 日本語での補足。1.1 SQL インジェクション 〜 1.11 アクセス制御や認可制御の欠落 |

OWASP Top 10:2025 の一覧（日本語名は公式訳）: A01 アクセス制御の不備 / A02 セキュリティ設定の不備 / A03 ソフトウェアサプライチェーンの不備 / A04 暗号化の不備 / A05 インジェクション / A06 安全性を欠いた設計 / A07 認証の不備 / A08 ソフトウェアまたはデータの完全性の不備 / A09 セキュリティログとアラートの不備 / A10 例外的な状況への不適切な対応。各カテゴリの URL は `https://owasp.org/Top10/2025/A0N_2025-<英語名をアンダースコアでつないだもの>/`（例: A10 は https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/ ）。

## 開発プロセス・サプライチェーン・CI/CD

| 基準 | 版・公開日 | URL | 使い方 |
|---|---|---|---|
| NIST SP 800-218 SSDF | v1.1（2022-02）。v1.2（Rev. 1）は 2025-12 公開の草案で未確定 | https://csrc.nist.gov/pubs/sp/800/218/final | 開発プロセスの根拠（PO / PS / PW / RV の各プラクティス。PW.3 は v1.1 で廃止） |
| NIST SP 800-218A | 2024-07（生成 AI・基盤モデル向けの SSDF プロファイル） | https://csrc.nist.gov/pubs/sp/800/218/a/final | AI モデルを開発する場合の補足 |
| OpenSSF Scorecard | checks.md（main） | https://github.com/ossf/scorecard/blob/main/docs/checks.md | リポジトリの衛生状態（20 チェック。Dangerous-Workflow と Webhooks が Critical） |
| SLSA | v1.2（2025-11） | https://slsa.dev/spec/v1.2/build-track-basics | 配布物のビルド来歴（Build L0〜L3） |
| OWASP Top 10 CI/CD Security Risks | CICD-SEC-1〜10 | https://owasp.org/projects/top-10-cicd-security-risks | CI/CD の分類 |
| GitHub Docs「Secure use reference」ほか | 随時更新 | https://docs.github.com/en/actions/reference/security/secure-use | Actions の権限・SHA 固定・スクリプトインジェクション・pull_request_target・OIDC |
| CIS Docker Benchmark | v1.8.0 | https://www.cisecurity.org/benchmark/docker | コンテナの設定 |
| Docker Docs「Building best practices」 | 随時更新 | https://docs.docker.com/build/building/best-practices/ | 非 root の USER など |

## AI / LLM

| 基準 | 版・公開日 | URL | 使い方 |
|---|---|---|---|
| OWASP Top 10 for LLM Applications | 2026 年版（2026-08 公開）。項目別の解説ページは 2025 年版（2024-11） | 2026: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/ / 2025: https://genai.owasp.org/llm-top-10/ | LLM 機能のリスク。2026 と 2025 で番号が違うため両方を併記（ai-and-llm.md の対応表） |
| OWASP Top 10 for Agentic Applications | 2026 年版（2025-12） | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | エージェントのリスク（ASI01〜ASI10） |
| OWASP Secure Coding with AI Cheat Sheet | 随時更新 | https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html | AI 支援開発のリスク（架空の依存、間接プロンプトインジェクション、ルールファイル、テストの削除など 14 節） |
| OWASP MCP Security / AI Agent Security / LLM Prompt Injection Prevention / RAG Security Cheat Sheet | 随時更新 | https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html ほか | 対応方針の参考 |
| Claude Code ドキュメント | 随時更新 | https://code.claude.com/docs/en/security / permissions / settings / mcp | AI コーディングエージェントの権限設定 |
| AI事業者ガイドライン（経済産業省・総務省） | 第 1.2 版（2026-03-31） | https://www.meti.go.jp/shingikai/mono_info_service/ai_shakai_jisso/20260331_report.html | 組織としての AI ガバナンス（コードの診断対象外。背景として紹介する場合のみ） |

## 基準を更新するときの手順

新しい版が出たら（例: ASVS 5.0.x、OWASP Top 10 の次版、SSDF v1.2 の確定）:

1. 原典（リポジトリや公式ページ）から ID と名称を取得し、`references/controls/*.md` の該当箇所を置き換える。記憶や二次情報からは書かない。
2. リンクがすべて 200 を返すか確認する（例: `curl -s -o /dev/null -w "%{http_code}" <URL>`）。
3. この表の版・公開日を更新する。
