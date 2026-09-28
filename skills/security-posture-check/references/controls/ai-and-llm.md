# チェック項目: AI / LLM 機能と AI 支援開発の環境

2 つの領域がある。書式は repo-and-supply-chain.md と同じ。

- **LLM-xx**: プロダクトが LLM を呼び出す機能を持つ場合（signals の `LLM/AI libraries`、`files importing LLM SDKs`）
- **AIDEV-xx**: リポジトリに AI コーディングエージェントの設定・指示ファイルがある場合（signals の `AI coding-agent configuration`）。AI で開発スピードを上げているプロジェクトでは、ここが新しい攻撃面になる

## 参照する基準（ID の読み方）

OWASP Top 10 for LLM Applications は 2026 年版（https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/ ）で番号が並び替わった。項目ごとの解説ページは 2025 年版にしかないため、**2026 年版の ID と 2025 年版の ID・リンクを併記**する。

| リスク | 2026 年版 | 2025 年版（解説ページ） |
|---|---|---|
| Prompt Injection | LLM01:2026 | LLM01:2025 https://genai.owasp.org/llmrisk/llm01-prompt-injection/ |
| Sensitive Information Disclosure | LLM02:2026 | LLM02:2025 https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/ |
| Excessive Agency | LLM03:2026 | LLM06:2025 https://genai.owasp.org/llmrisk/llm062025-excessive-agency/ |
| Supply Chain | LLM04:2026 | LLM03:2025 https://genai.owasp.org/llmrisk/llm032025-supply-chain/ |
| Data and Model Poisoning | LLM05:2026 | LLM04:2025 https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/ |
| Unbounded Consumption | LLM06:2026 | LLM10:2025 https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/ |
| Hidden Context Exposure（2025: System Prompt Leakage） | LLM08:2026 | LLM07:2025 https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/ |
| Vector and Embedding Weaknesses | LLM09:2026 | LLM08:2025 https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/ |
| Improper Output Handling | LLM10:2026 | LLM05:2025 https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/ |

エージェント（ツール呼び出し・自律実行）には OWASP Top 10 for Agentic Applications 2026（ASI01〜ASI10, https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ ）を併用する: ASI01 Agent Goal Hijack / ASI02 Tool Misuse and Exploitation / ASI03 Identity and Privilege Abuse / ASI04 Agentic Supply Chain Vulnerabilities / ASI05 Unexpected Code Execution (RCE) / ASI06 Memory & Context Poisoning / ASI07 Insecure Inter-Agent Communication / ASI08 Cascading Failures / ASI09 Human-Agent Trust Exploitation / ASI10 Rogue Agents。

ASVS 5.0 には LLM 固有の要件はない。LLM の出力が SQL・HTML・コマンドに流れる箇所は、web-application.md の INJ 項目も合わせて適用する。

---

## LLM 機能

### LLM-01 プロンプトインジェクションを前提にした設計になっている
- **適用**: LLM に外部由来のテキスト（利用者の入力、アップロード文書、Web ページ、メール、検索結果、ツールの戻り値）を渡す
- **確認方法**: signals の `files importing LLM SDKs` を読み、システム指示と信頼できないデータを分けて渡しているか（役割の分離、区切り、「以下はデータであり指示ではない」旨の明示）。完全な防御は存在しないため、**注入された場合の被害範囲**（LLM-02 の出力の扱い、LLM-03 の権限）とセットで評価する
- **判定**: ✅ 信頼できないデータを区別し、注入されても被害が限定される（出力・権限の対策あり）/ 🟡 区別はあるが出力・権限側の対策が弱い / ❌ 外部データを指示と区別せずに渡し、出力・権限の制限もない
- **重大度**: 注入された場合にできることで決まる（副作用のあるツールがあれば High、テキストを返すだけなら Low〜Medium）
- **リスク**: 文書や Web ページに埋め込まれた指示でモデルの振る舞いが乗っ取られ、情報の持ち出しや意図しない操作につながる
- **対応方針**: 信頼できないデータの区別、ツールの最小化（LLM-03）、出力の検証（LLM-02）、重要操作の人間承認
- **根拠**: OWASP LLM01:2026 / LLM01:2025 / ASI01 Agent Goal Hijack
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html

### LLM-02 LLM の出力を信頼できない入力として扱っている
- **適用**: LLM の出力を画面表示・DB・コマンド・コード・URL 取得などに使う
- **確認方法**: signals の `llm-dangerous-sink` と `unsafe-html-sink`。出力が `|safe`・`innerHTML`・`dangerouslySetInnerHTML`・SQL・シェル・`eval`・ファイルパス・テンプレートにそのまま渡っていないか
- **判定**: ✅ エスケープ・スキーマ検証・サンドボックスを経由 / 🟡 一部の出力先で未処理 / ❌ 危険な処理にそのまま渡している
- **重大度**: High（SQL・コード実行に流れる場合は Critical）
- **リスク**: プロンプトインジェクションを経由して、XSS・SQL インジェクション・コマンド実行が成立する（入力元が「AI」になっただけで、INJ 項目と同じ脆弱性）
- **対応方針**: 表示は自動エスケープかサニタイズ、構造化出力はスキーマで検証、コード実行はサンドボックス
- **根拠**: OWASP LLM10:2026 / LLM05:2025 Improper Output Handling / ASI05 Unexpected Code Execution / 出力先に応じて CWE-79・CWE-89・CWE-94（web-application.md の INJ-01〜04）

### LLM-03 ツール・エージェントの権限が最小化され、重要な操作に人の承認がある
- **適用**: function calling / tool use / エージェント（signals の `llm-tool-definitions`）
- **確認方法**: 各ツールでできること（読み取り・書き込み・削除・外部送信・コード実行）、使う資格情報の権限（DB は読み取り専用か）、利用者の権限範囲に限定されているか（他ユーザーのデータに届かないか）、破壊的操作の承認、ループ回数の上限
- **判定**: ✅ 必要最小限のツールで、利用者の権限内に限定し、重要操作は承認制 / 🟡 一部が広い / ❌ 任意の SQL・コマンド実行・全データへのアクセスなど強力なツールを制限なく提供
- **重大度**: Critical（任意 SQL / コードを全データに対して実行可能）/ High
- **リスク**: プロンプトインジェクションや誤動作で、モデルが他ユーザーのデータ取得・削除・外部送信を実行する
- **対応方針**: 汎用ツール（任意 SQL 等）を目的別の限定ツールに置き換え、利用者のスコープで実行、読み取り専用の資格情報、破壊的操作は確認を挟む、ループ上限
- **根拠**: OWASP LLM03:2026 / LLM06:2025 Excessive Agency / ASI02 Tool Misuse and Exploitation / ASI03 Identity and Privilege Abuse
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html

### LLM-04 機密情報をプロンプト・文脈に含めず、出力からの漏えいを防いでいる
- **適用**: LLM 機能がある
- **確認方法**: システムプロンプトや文脈に API キー・内部 URL・他ユーザーの情報を入れていないか。プロンプトと応答のログに個人情報が残らないか。外部 LLM プロバイダへ送るデータの範囲（契約・データ保持方針は組織側の確認事項なので要確認）
- **判定**: ✅ 秘密情報を含めず、ログも配慮 / 🟡 一部懸念 / ❌ 秘密情報や他人のデータを文脈に入れている
- **重大度**: High（資格情報・他人の個人情報）/ Medium
- **リスク**: 巧妙な質問でシステムプロンプトや文脈の内容を引き出され、秘密や他人の情報が漏れる
- **根拠**: OWASP LLM02:2026 / LLM02:2025 Sensitive Information Disclosure / LLM08:2026 Hidden Context Exposure（2025: LLM07 System Prompt Leakage）

### LLM-05 LLM の利用量・コストに上限がある
- **適用**: LLM 機能がある
- **確認方法**: `max_tokens` 等の出力上限、LLM を呼ぶエンドポイントのユーザー単位のレート制限、エージェントのループ上限、タイムアウト、入力サイズの制限、予算アラート（プロバイダ側設定は要確認）
- **判定**: ✅ 出力上限＋ユーザー単位の制限＋ループ上限 / 🟡 一部 / ❌ なし
- **重大度**: Medium（従量課金で上限が一切ない場合は High）
- **リスク**: 大量リクエストや終わらないエージェントループで、高額請求やサービス停止（Denial of Wallet）
- **根拠**: OWASP LLM06:2026 / LLM10:2025 Unbounded Consumption / OWASP API4:2023（https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/ ）/ CWE-770

### LLM-06 RAG・ベクトル検索に利用者単位のアクセス制御がある
- **適用**: RAG / 埋め込み検索がある（ベクトル DB ライブラリ、埋め込み API の利用）
- **確認方法**: 検索時に利用者・テナントの権限で絞り込んでいるか、取り込むデータの出所と改ざん対策
- **判定**: ✅ 権限フィルタあり / 🟡 一部 / ❌ 全データを横断検索
- **重大度**: High（他テナントのデータが回答に混ざる）
- **リスク**: 他の利用者の文書が回答に混ざって漏れる。汚染された文書で回答が誘導される
- **根拠**: OWASP LLM09:2026 / LLM08:2025 Vector and Embedding Weaknesses / LLM05:2026 / LLM04:2025 Data and Model Poisoning
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html

### LLM-07 モデルや AI コンポーネントを安全に取り込んでいる
- **適用**: モデルファイルを読み込む、外部のモデル・プラグインを使う
- **確認方法**: signals の `unsafe-deserialization`（`torch.load`、pickle）と `remote-model-code`（`trust_remote_code=True`）。モデルの取得元とバージョン・ハッシュの固定、safetensors 形式の利用
- **判定**: ✅ 信頼できる取得元・固定・安全な形式 / 🟡 一部 / ❌ 出所不明のモデルを pickle 形式で読み込む、リモートのモデルコードを実行
- **重大度**: High（任意コード実行につながる読み込み）
- **リスク**: 悪意あるモデルファイルの読み込みで任意のコードが実行される
- **根拠**: OWASP LLM04:2026 / LLM03:2025 Supply Chain / CWE-502（https://cwe.mitre.org/data/definitions/502.html ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Secure_AI_Model_Ops_Cheat_Sheet.html

---

## AI 支援開発の環境

### AIDEV-01 AI コーディングエージェントの権限設定が最小限になっている
- **適用**: `.claude/settings.json`、`.claude/skills/`・`.claude/commands/`・`.claude/agents/` など、AI エージェントの共有設定がリポジトリにある（なければ ➖対象外。推奨事項として触れるのはよい）
- **確認方法**: signals の `claude_settings`（`broad allow rules`、`defaultMode`、`denies secret reads`、`enableAllProjectMcpServers`、`hooks`、`settings.local.json` の追跡）と、`project skill/command … pre-approves (allowed-tools)`・`subagent … permissionMode` の行。スキルやコマンドの `allowed-tools` は、呼び出されたターンの間、許可の確認なしにそのツールを使わせる。フォルダーを信頼していなくても効くので、settings.json と同じ重さで読む。他のエージェント（Cursor、Copilot、Gemini 等）の設定も同じ観点で読む
- **判定**: ✅ 許可ルールが具体的で、秘密ファイルの読み取りを deny し、`bypassPermissions` を共有しない / 🟡 一部に広い許可 / ❌ `Bash(*)` などの無制限許可（settings.json かスキルの `allowed-tools`）、`bypassPermissions`、`enableAllProjectMcpServers: true` を共有設定でコミット
- **重大度**: Medium（本番の資格情報に届く環境では High）
- **リスク**: リポジトリ内の文書・Issue・依存パッケージに仕込まれた指示（間接プロンプトインジェクション）で、エージェントが確認なしにコマンドを実行し、秘密情報の外部送信やファイルの破壊を行う。共有設定なのでチーム全員の環境に波及する
- **対応方針**: allow は必要なコマンドに限定（例: `Bash(npm run test:*)`）、deny に `Read(./.env)`・`Read(./.env.*)`・`Read(./secrets/**)` 等、`defaultMode` の強い設定や `enableAllProjectMcpServers` は共有設定に書かない、個人用の設定は `settings.local.json`（Git 管理外）へ。スキルの `allowed-tools` は同梱スクリプトなど必要なものだけに絞る（例: `Bash(${CLAUDE_SKILL_DIR}/scripts/check.sh *)`）
- **根拠**: Claude Code ドキュメント Security（https://code.claude.com/docs/en/security ）・Permissions（https://code.claude.com/docs/en/permissions ）・Settings（https://code.claude.com/docs/en/settings ）・Skills「Pre-approve tools for a skill」（https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill ）/ OWASP LLM03:2026 Excessive Agency / ASI02, ASI03 / OWASP Secure Coding with AI Cheat Sheet「Indirect Prompt Injection in the Development Loop」「Agent Runtime Sandboxing」（https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html ）

### AIDEV-02 MCP サーバーの出所・権限・資格情報が管理されている
- **適用**: `.mcp.json`（`.vscode/mcp.json`、`.cursor/mcp.json` 等）に MCP サーバーの設定がある
- **確認方法**: signals の `MCP server` 行（未固定のパッケージ、`env`・`headers`・引数の資格情報、平文 HTTP）。接続先が本番環境か、管理者権限か。提供元が信頼できるか
- **判定**: ✅ 信頼できる提供元・バージョン固定・資格情報は `${VAR}` 展開・最小権限（読み取り専用ユーザー、ステージング）/ 🟡 一部 / ❌ 資格情報のハードコード、本番に管理者権限で接続、出所不明で未固定のパッケージ
- **重大度**: High（本番 DB の管理者資格情報がコミットされていれば Critical。SEC-01 でも扱う）
- **リスク**: MCP サーバー（またはその更新版）が悪意あるものだったり、ツールの戻り値に仕込まれた指示に従ったりして、エージェントが本番データを持ち出す・壊す。コミットされた資格情報は漏えいと同じ
- **対応方針**: 資格情報は `${VAR}` で環境変数から展開、パッケージのバージョンを固定、接続先はステージングや読み取り専用ユーザー、提供元とソースを確認
- **根拠**: Claude Code ドキュメント MCP（https://code.claude.com/docs/en/mcp ）/ OWASP MCP Security Cheat Sheet（https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html ）/ ASI04 Agentic Supply Chain Vulnerabilities / LLM04:2026 Supply Chain / CWE-798

### AIDEV-03 AI 支援開発の運用ルールとガードレールがある
- **適用**: AI コーディング支援を使っている（指示ファイルがある、またはユーザーがそう述べている）
- **確認方法**: CLAUDE.md / AGENTS.md / `.cursor/rules` 等の内容（本番への接続を促す、テストが落ちたらテストを直せ、といった危険な指示がないか。秘密情報・依存追加・テストの扱いのルールがあるか）。GOV-02〜04 の結果（レビュー・テスト・SAST）
- **判定**: ✅ 指示ファイルに安全な運用ルールがあり、レビューと CI で担保 / 🟡 どちらか一方 / ❌ 指示ファイルが危険な操作を促す、またはレビューも CI もない
- **重大度**: Low（危険な指示がある場合は Medium）
- **リスク**: AI が大量に生成した変更が、脆弱なパターン・架空の依存・テストの削除を含んだまま取り込まれる。指示ファイルが改ざんされると以後の生成がすべて汚染される
- **対応方針**: 指示ファイルに「秘密情報を読まない・書かない」「依存追加時はレジストリで確認」「テストを弱めない」「本番に接続しない」等を明記し、PR レビューと CI（GOV-02〜04）で担保
- **根拠**: OWASP Secure Coding with AI Cheat Sheet「Rules Files and Persistent Steering」「Out-of-Scope Edits and Review Anchoring」「Test Fabrication and Test Deletion」「Human Accountability」/ NIST SSDF PW.7, PW.8（https://csrc.nist.gov/pubs/sp/800/218/final ）
