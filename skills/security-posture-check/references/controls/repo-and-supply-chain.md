# チェック項目: リポジトリ運用・シークレット・依存関係・CI/CD

どのプロジェクトにも適用する基本領域。各項目の書式:

- **適用**: この項目を評価する条件（満たさなければ ➖対象外）
- **確認方法**: 証拠の集め方（`signals` = `collect_signals.py` の出力）
- **判定**: ✅対応済み / 🟡一部対応 / ❌未対応 の基準（証拠がなければ ❓要確認）
- **重大度**: 未対応・一部対応だった場合の既定の重大度（文脈による調整は SKILL.md のルーブリック参照）
- **リスク**: 対応しない場合に起きること（レポートの「放置した場合のリスク」に使う）
- **対応方針**: 標準的な直し方（プロジェクトに合わせて具体化する）
- **根拠 / 参考**: 基準の該当箇所とリンク。レポートにはリンクを完全な URL のまま載せる

目次: [GOV 開発プロセス](#gov) / [SEC シークレット](#sec) / [SCA 依存関係・サプライチェーン](#sca) / [CICD](#cicd)

---

## GOV

### GOV-01 脆弱性の報告窓口がある
- **適用**: 常に（公開リポジトリ・配布物では特に重要）
- **確認方法**: signals の `SECURITY.md`。内容に非公開の連絡手段（メール、GitHub の Private vulnerability reporting）があるか読む。PVR の有効化は `GET /repos/{owner}/{repo}/private-vulnerability-reporting`（取得できなければ要確認）
- **判定**: ✅ 非公開の報告手段が明記されている / 🟡 ファイルはあるが公開 Issue での報告しか案内していない / ❌ なし
- **重大度**: Low（公開リポジトリ・配布物は Medium）
- **リスク**: 脆弱性を見つけた人が公開 Issue に詳細を書き、修正前に攻撃者にも知られる。そもそも報告が届かない
- **対応方針**: SECURITY.md を追加（報告方法・対象バージョン・返信の目安）。公開リポジトリなら Private vulnerability reporting を有効化
- **根拠**: NIST SSDF RV.1（https://csrc.nist.gov/pubs/sp/800/218/final ）/ OpenSSF Scorecard Security-Policy（https://github.com/ossf/scorecard/blob/main/docs/checks.md#security-policy ）
- **参考**: https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/add-security-policy / https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository

### GOV-02 デフォルトブランチが保護され、変更はレビューを経る
- **適用**: 常に（1人開発でも「AI が生成した変更を検査なしで main に入れない」仕組みとして有効）
- **確認方法**: リポジトリ外の設定。`gh` か GitHub の MCP ツールが使えれば `GET /repos/{owner}/{repo}/rules/branches/{branch}` または `GET /repos/{owner}/{repo}/branches/{branch}/protection`（管理者権限が必要）。取得できなければ ❓要確認 とし、確認手順を書く。CODEOWNERS は補助的な証拠
- **判定**: ✅ PR 必須＋必須ステータスチェック＋force push 禁止 / 🟡 一部のみ / ❌ 保護なし
- **重大度**: Medium（main への push が本番デプロイに直結する場合は High）
- **リスク**: 未レビューの変更（AI 生成コード、誤操作、乗っ取られたアカウントからの push）がそのまま本番に入る
- **対応方針**: ルールセットで「PR 必須」「ステータスチェック必須」「force push・削除の禁止」を設定。1人開発ならセルフレビュー＋CI 必須でも効果がある
- **根拠**: NIST SSDF PS.1, PW.7 / Scorecard Branch-Protection, Code-Review（https://github.com/ossf/scorecard/blob/main/docs/checks.md#branch-protection ）/ OWASP Top 10 CI/CD CICD-SEC-1 Insufficient Flow Control Mechanisms（https://owasp.org/projects/top-10-cicd-security-risks ）
- **参考**: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

### GOV-03 テストが CI で自動実行される
- **適用**: 常に
- **確認方法**: signals の `test commands in CI` とテストファイルの有無。セキュリティ上重要な処理（認証・認可・入力検証）にテストがあるか。**CI が実際に通る状態か**も読む（未定義のフィクスチャ、足りないロックファイル等で必ず失敗する、`continue-on-error: true` で失敗が無視される）。失敗したステップの後ろにあるセキュリティ検査は実行されていない
- **判定**: ✅ PR/push ごとにテストが走り、通る状態 / 🟡 テストはあるが CI で走らない、CI が必ず失敗する状態、または CI はあるがテストがほぼない / ❌ なし
- **重大度**: Low（認証・認可を持つアプリは Medium）
- **リスク**: セキュリティ修正の退行に気づけない。AI による変更でテストが削除・骨抜きにされても検出できない
- **対応方針**: 既存テストを CI で実行し、認可（他人のデータにアクセスできないこと）などの否定系テストを追加
- **根拠**: NIST SSDF PW.8 / Scorecard CI-Tests / OWASP Secure Coding with AI Cheat Sheet「Test Fabrication and Test Deletion」（https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html ）

### GOV-04 静的解析（SAST）が自動実行される
- **適用**: 常に
- **確認方法**: signals の `security tools referenced in CI`（codeql, semgrep, bandit, gosec, brakeman 等）。GitHub code scanning の default setup はリポジトリ設定なので、ワークフローが無くても有効な場合がある（取得できなければ要確認）
- **判定**: ✅ PR ごとに実行 / 🟡 手動のみ・一部言語のみ / ❌ なし
- **重大度**: Medium
- **リスク**: インジェクション等の典型的な脆弱性が混入しても自動で気づけない。AI 生成コードの量が増えるほど人手レビューだけでは追いつかない
- **対応方針**: GitHub code scanning（CodeQL の default setup）を有効化するか、言語に合う SAST を CI に追加
- **根拠**: NIST SSDF PW.7 / Scorecard SAST
- **参考**: https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configure-code-scanning / https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html

---

## SEC

### SEC-01 現在のファイルに秘密情報が含まれていない
- **適用**: 常に
- **確認方法**: signals の Secrets（値はマスク済み）。各行を実際に読み、本物の資格情報か／テスト用ダミーか／公開前提の値（Firebase の Web API キー等）かを判断する。**値はレポートに一切書かない**（先頭数文字＋長さのマスク表記のみ）
- **判定**: ✅ 検出なし / 🟡 テスト用・失効済みの値のみ / ❌ 実際の資格情報が追跡ファイルにある
- **重大度**: Critical（クラウド・決済・本番 DB の資格情報）/ High（その他の実資格情報）
- **リスク**: リポジトリを見られる人（公開なら誰でも。フォーク・クローン・CI ログも含む）がその資格情報を使える。クラウドの不正利用と高額請求、データ漏えい、なりすまし
- **対応方針**: ①最初に失効・ローテーション（ファイルから消すだけでは不十分）②プロバイダのログで悪用の有無を確認 ③環境変数・シークレットマネージャへ移行 ④SEC-04 で再発防止
- **根拠**: CWE-798（https://cwe.mitre.org/data/definitions/798.html ）→ OWASP Top 10:2025 A07（https://owasp.org/Top10/2025/A07_2025-Authentication_Failures/ ）/ ASVS v5.0.0-13.3.1 (L2)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x22-V13-Configuration.md ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

### SEC-02 Git 履歴に秘密情報が残っていない
- **適用**: Git リポジトリ
- **確認方法**: `collect_signals.py --scan-history N` の結果。gitleaks があれば `gitleaks git --redact`（古い版は `gitleaks detect --redact`）。現行ファイルから消えていても履歴に残っていれば検出扱い
- **判定**: ✅ 検出なし / ❌ 過去のコミットに残っている / ❓ 履歴を走査できない
- **重大度**: SEC-01 と同じ基準（公開リポジトリでは削除済みでも同等に扱う）
- **リスク**: ファイルから削除しても、履歴・フォーク・キャッシュから取り出せる
- **対応方針**: ローテーションが本質的な対策。`git filter-repo` 等での履歴書き換えは補助策で、既に取得された写しには効かない
- **根拠**: CWE-798 / CWE-540（https://cwe.mitre.org/data/definitions/540.html ）/ GitHub secret scanning は全履歴を走査対象にしている（https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning ）

### SEC-03 秘密情報ファイルが Git 管理から除外されている
- **適用**: 常に
- **確認方法**: signals の `sensitive files tracked` / `present but NOT gitignored` / `.gitignore covers .env` / `env example files`。Dockerfile の `COPY . .` で秘密ファイルがイメージに入らないか（CTR-03）
- **判定**: ✅ 追跡なし＋.gitignore で除外＋`.env.example` 等のひな形あり / 🟡 追跡はないが除外設定がない、またはひな形がない / ❌ 秘密ファイルを追跡している
- **重大度**: High（実値入りファイルの追跡）/ Low（除外設定の欠如のみ）
- **リスク**: `git add .` 一回で秘密情報がコミットされる。AI エージェントがまとめてステージングする運用では特に起きやすい
- **対応方針**: `.env*` 等を .gitignore に追加し、追跡済みなら `git rm --cached` と SEC-01 の手順（ローテーション）を実施。キーを空にした `.env.example` を用意
- **根拠**: CWE-540 → OWASP Top 10:2025 A01（https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/ ）/ ASVS v5.0.0-13.3.1 (L2)

### SEC-04 秘密情報の混入を検出・防止する仕組みがある
- **適用**: 常に
- **確認方法**: リポジトリ内: gitleaks・trufflehog・detect-secrets の pre-commit / CI 設定。リポジトリ外: GitHub の secret scanning と push protection（`GET /repos/{owner}/{repo}` の `security_and_analysis`。管理者権限が必要）→ 取得できなければ要確認
- **判定**: ✅ push 前（pre-commit か push protection）と CI の両方で検出 / 🟡 どちらか一方 / ❌ なし
- **重大度**: Medium
- **リスク**: 人も AI も秘密情報を貼り付けるミスをする。仕組みがないと漏えいに気づくのが遅れる
- **対応方針**: GitHub の push protection を有効化（プランにより利用条件あり）、CI か pre-commit に gitleaks を追加
- **根拠**: NIST SSDF PO.3, PS.1 / OWASP Secrets Management Cheat Sheet
- **参考**: https://docs.github.com/en/code-security/concepts/secret-security/push-protection

### SEC-05 秘密情報は実行環境から供給され、弱い既定値にフォールバックしない
- **適用**: 秘密情報（署名鍵・API キー・DB パスワード等）を使うアプリ
- **確認方法**: 設定の読み込み箇所。signals の `insecure-default-secret`（例: `process.env.JWT_SECRET || 'dev-secret'`、`os.getenv("SECRET_KEY", "dev")`）。本番と開発で同じ鍵を使っていないか。未設定時に起動を止めるか
- **判定**: ✅ 環境変数・シークレットマネージャから供給し、未設定なら起動失敗 / 🟡 環境変数だが弱い既定値にフォールバックする / ❌ コードに固定値
- **重大度**: High（署名・暗号化の鍵がフォールバック可能なら Critical: トークン偽造につながる）
- **リスク**: 環境変数の設定漏れに気づかず、ソースに書かれた既定値（誰でも読める）で署名・暗号化され、トークンやセッションを偽造される
- **対応方針**: 必須の設定値は未設定なら起動時にエラーにする。シークレットマネージャ・最小権限・定期ローテーション
- **根拠**: ASVS v5.0.0-13.3.1 (L2), 13.3.2 (L2), 13.3.4 (L3) / CWE-1188（https://cwe.mitre.org/data/definitions/1188.html ）/ CWE-798

---

## SCA

### SCA-01 依存関係がロックファイルで固定されている
- **適用**: 依存関係マニフェストがある（ライブラリとして配布するだけのパッケージはロックファイル任意）
- **確認方法**: signals の manifests の `lockfile`。CI のインストールが固定モード（`npm ci`、`pip install --require-hashes`、`uv sync --locked`、`go mod verify` 等）か
- **判定**: ✅ すべてのアプリ用マニフェストにロックファイル＋CI で固定インストール / 🟡 ロックファイルはあるが CI が固定モードでない、または一部欠落 / ❌ ロックファイルなし
- **重大度**: Medium
- **リスク**: ビルドのたびに異なるバージョンが入り、乗っ取られた新バージョンも気づかず本番に入る。どのバージョンを使っているか特定できず、脆弱性の影響を判断できない
- **対応方針**: ロックファイルをコミットし、CI では固定インストールを使う
- **根拠**: OWASP Top 10:2025 A03（https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/ ）/ Scorecard Pinned-Dependencies / NIST SSDF PW.4
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html / https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html

### SCA-02 依存関係の更新が自動化されている
- **適用**: 依存関係がある
- **確認方法**: signals の `dependency update automation`。Dependabot の対象エコシステムが全マニフェストと `github-actions` を網羅しているか
- **判定**: ✅ 全エコシステムを対象に設定 / 🟡 一部のみ / ❌ なし
- **重大度**: Medium
- **リスク**: 修正済みの脆弱性を含む古い依存関係を使い続ける
- **対応方針**: `.github/dependabot.yml`（または Renovate）で全エコシステムと github-actions を対象にし、Dependabot security updates も有効化
- **根拠**: ASVS v5.0.0-15.1.1 (L1), 15.2.1 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x24-V15-Secure-Coding-and-Architecture.md ）/ Scorecard Dependency-Update-Tool / CWE-1104 → A03:2025
- **参考**: https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-version-updates

### SCA-03 既知の脆弱性を持つ依存関係を検出している
- **適用**: 依存関係がある
- **確認方法**: CI の監査ステップ（npm audit、pip-audit、osv-scanner、govulncheck、dependency-review-action 等）と、そのステップが実際に実行されるか（前のステップが必ず失敗する、`continue-on-error: true`、常に偽になる `if:` がないか）。ユーザーの了承があればローカルで実行してよい（依存関係の情報が外部サービスへ送られることを先に伝える）。Dependabot alerts はリポジトリ設定（要確認）
- **判定**: ✅ CI で継続的に検査し、重大な既知脆弱性が残っていない / 🟡 検査はあるが結果が放置されている、または手動のみ / ❌ 検査がない、または実行して重大な脆弱性が見つかった
- **重大度**: 見つかった脆弱性の深刻度に従う。検査の仕組みがないだけなら Medium
- **リスク**: 既に公開されている攻撃手法がそのまま使える状態になる
- **対応方針**: CI に監査ステップを追加し、PR では dependency-review-action で新規の脆弱な依存を止める
- **根拠**: ASVS v5.0.0-15.2.1 (L1) / Scorecard Vulnerabilities / CWE-1395（https://cwe.mitre.org/data/definitions/1395.html ）→ A03:2025 / NIST SSDF RV.1
- **参考**: https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-dependency-review-action / https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html

### SCA-04 依存パッケージが正当なものである（タイポスクワット・AI の架空パッケージ対策）
- **適用**: 依存関係がある（AI にパッケージ追加を任せている場合は特に）
- **確認方法**: 直接依存の名前を一覧し、有名パッケージに酷似した名前・見慣れない名前・最近追加されたもの（`git log -p -- <manifest>`）を抽出。インストールスクリプト（signals の `install scripts` 等）の有無。レジストリでの実在・公開時期・リポジトリの確認はネットワークが必要なので、できない場合は候補を一覧化して要確認にする
- **判定**: ✅ 疑わしい依存なし＋PR で依存の差分を確認する仕組みあり / 🟡 疑わしい依存はないが確認の仕組みがない / ❌ 疑わしい依存がある
- **重大度**: High（疑わしい依存が見つかった場合）/ Low（仕組みの欠如のみ）
- **リスク**: AI が提案した実在しないパッケージ名を攻撃者が先に登録しておく手口（slopsquatting）やタイポスクワットで、マルウェアを取り込む。インストール時のスクリプトで開発機や CI の秘密情報が盗まれる
- **対応方針**: 追加前にレジストリで実在・メンテナ・ソースリポジトリを確認。dependency-review-action で差分をレビュー。npm では `ignore-scripts` を検討
- **根拠**: OWASP Top 10:2025 A03 / ASVS v5.0.0-15.1.2 (L2), 15.2.4 (L3) / OWASP CICD-SEC-3 Dependency Chain Abuse / OWASP Secure Coding with AI Cheat Sheet「Hallucinated Dependencies」（https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html ）

### SCA-05 配布物の完全性を検証できる（署名・来歴・SBOM）
- **適用**: パッケージ・バイナリ・コンテナイメージを配布・公開している（Web サービスのみなら ➖対象外）
- **確認方法**: goreleaser・cosign・sigstore、`npm publish --provenance`、SLSA のビルド来歴生成、チェックサム公開、SBOM 生成の設定
- **判定**: ✅ 署名またはビルド来歴（provenance）を公開 / 🟡 チェックサムのみ / ❌ なし
- **重大度**: Medium
- **リスク**: 配布物が差し替えられても、利用者が改ざんを検知できない
- **対応方針**: 成果物に署名（cosign 等）し、CI 上でビルド来歴を生成。SBOM を添付
- **根拠**: NIST SSDF PS.2, PS.3 / SLSA v1.2 Build Track（https://slsa.dev/spec/v1.2/build-track-basics ）/ Scorecard Signed-Releases, SBOM / OWASP Top 10:2025 A08（https://owasp.org/Top10/2025/A08_2025-Software_or_Data_Integrity_Failures/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Dependency_Graph_SBOM_Cheat_Sheet.html

### SCA-06 実行時に取得するコード・スクリプトを検証している
- **適用**: アプリ・CLI・インストーラがプラグインや更新をダウンロードして実行する、または手順・Makefile に `curl | sh` がある
- **確認方法**: signals の `download-without-integrity-check`。HTTP でファイルを取得して実行権限を付けるコード、自動アップデート処理
- **判定**: ✅ 署名かチェックサムを検証してから実行 / 🟡 HTTPS 取得のみ（改ざんは検知できない）/ ❌ 検証なしで実行
- **重大度**: High（製品コードが検証なしで実行する）/ Low（開発者向けの Makefile 等）
- **リスク**: 配布サーバーの侵害や経路上の改ざんで、利用者の環境で任意のコードが実行される
- **対応方針**: チェックサム・署名の検証、取得元とバージョンの固定
- **根拠**: CWE-494（https://cwe.mitre.org/data/definitions/494.html ）→ A08:2025 / OWASP CICD-SEC-9 Improper Artifact Integrity Validation / NIST SSDF PS.2

### SCA-07 言語ランタイム・ツールチェーン・ベースイメージがサポート期間内である
- **適用**: 常に
- **確認方法**: signals の `declared runtimes/toolchains`（go.mod の `go`、`engines.node`、`.nvmrc`、`requires-python`、CI の `*-version`）と Dockerfile のベースイメージ。各バージョンのサポート終了日を公式のリリースポリシーで確認する。確認できない（ネットワークが使えない等）場合は、バージョンと確認先を示して ❓要確認 にする。記憶だけで終了済みと断定しない
- **判定**: ✅ すべてサポート期間内 / 🟡 まもなく終了、または宣言が曖昧（`>=` だけ等）/ ❌ サポート終了済みのバージョンでビルド・実行している
- **重大度**: Medium（配布するバイナリやインターネット公開のサービスで使う場合は High）
- **リスク**: ランタイム自体の脆弱性修正（TLS・HTTP・暗号の実装など）が提供されなくなる。Go のように標準ライブラリを静的に組み込む言語では、配布したバイナリに修正が入らない
- **対応方針**: サポート中のバージョンに上げ、CI・Dockerfile・go.mod 等の宣言をそろえる。Dependabot 等で更新を追う
- **根拠**: ASVS v5.0.0-15.2.1 (L1) / CWE-1104（https://cwe.mitre.org/data/definitions/1104.html ）→ A03:2025
- **参考**: https://endoflife.date/ / Go https://go.dev/doc/devel/release / Node.js https://nodejs.org/en/about/previous-releases / Python https://devguide.python.org/versions/

---

## CICD

### CICD-01 ワークフローのトークン権限が最小化されている
- **適用**: GitHub Actions を使用（他の CI も同等の観点で評価）
- **確認方法**: signals の `top-level permissions` / `write scopes` / `job-level permission blocks`
- **判定**: ✅ トップレベルが read（または `{}`）で、必要なジョブだけ write / 🟡 明示はあるが広い（`write-all` 等）/ ❌ 未指定（リポジトリ既定値に依存。既定が read-only かは設定なので要確認と併記）
- **重大度**: Medium（信頼できないトリガー（CICD-03）と組み合わさる場合は High）
- **リスク**: ワークフローや利用中のアクションが侵害されたとき、リポジトリへの書き込み・リリースの改ざんに悪用される
- **対応方針**: トップに `permissions: contents: read` を置き、必要なジョブにだけ権限を追加
- **根拠**: GitHub Docs「Secure use reference」（https://docs.github.com/en/actions/reference/security/secure-use ）/ Scorecard Token-Permissions / OWASP CICD-SEC-5 Insufficient PBAC
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/GitHub_Actions_Security_Cheat_Sheet.html

### CICD-02 サードパーティのアクションがコミット SHA で固定されている
- **適用**: GitHub Actions を使用
- **確認方法**: signals の `actions not pinned`（[third-party] と [github-owned] を区別）
- **判定**: ✅ すべて 40 桁 SHA で固定（コメントでバージョン併記）/ 🟡 サードパーティは SHA、GitHub 公式はタグ / ❌ サードパーティをタグ・ブランチで参照
- **重大度**: Medium（secrets を渡すサードパーティアクションが未固定なら High）
- **リスク**: タグは後から別のコミットに付け替えられるため、アクションの提供元が侵害されると CI の秘密情報が盗まれる
- **対応方針**: 完全な SHA で固定し、Dependabot（github-actions）で更新を追う
- **根拠**: GitHub Docs「Using third-party actions」（https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions ）/ Scorecard Pinned-Dependencies / OWASP CICD-SEC-3 / A03:2025

### CICD-03 危険なトリガーや信頼できない入力の展開がない
- **適用**: GitHub Actions を使用
- **確認方法**: signals の `pull_request_target + checks out PR head`、`untrusted input interpolated in run/script`、`workflow_run`。該当ワークフローを読み、PR 由来のコードや値が secrets・書き込みトークンのある文脈で実行されるか確認
- **判定**: ✅ 該当なし / 🟡 `pull_request_target` を使うが PR のコードは実行しない等の緩和あり / ❌ PR のコードを特権文脈で実行、または信頼できない値を `run:` に直接展開
- **重大度**: Critical（公開リポジトリで secrets か書き込みトークンに到達できる）/ High（それ以外）
- **リスク**: 外部の誰かが PR を出す（タイトルを細工する）だけで、CI の秘密情報窃取・リポジトリ改ざん・リリース汚染ができる（Poisoned Pipeline Execution）
- **対応方針**: `pull_request_target` をやめて `pull_request` を使う（必要なら PR のコードをチェックアウト・実行しない）。信頼できない値は `env:` で渡してシェル内で `"$VAR"` として参照
- **根拠**: GitHub Docs「Script injections」（https://docs.github.com/en/actions/concepts/security/script-injections ）/「Securely using pull_request_target」（https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target ）/ Scorecard Dangerous-Workflow / OWASP CICD-SEC-4 Poisoned Pipeline Execution / CWE-78 → A05:2025

### CICD-04 CI の資格情報と実行環境が適切に管理されている
- **適用**: CI を使用
- **確認方法**: signals の `long-lived cloud credentials`、`OIDC (id-token: write)`、`self-hosted runner`、`tools fetched at @latest`。デプロイ用の資格情報の渡し方
- **判定**: ✅ クラウド認証は OIDC、公開リポジトリの PR で self-hosted runner を使わない、ツールはバージョン固定 / 🟡 長期クレデンシャルを secrets に保存（スコープは最小）、または一部ツールが未固定 / ❌ 公開リポジトリの PR で self-hosted runner を使う、または過剰な権限の長期鍵
- **重大度**: Medium（公開リポジトリでの self-hosted runner は High）
- **リスク**: 長期鍵は漏えいしたときの被害期間が長い。公開リポジトリの self-hosted runner では外部の PR から runner のマシン上で任意コードを実行されうる
- **対応方針**: OIDC による短期クレデンシャルへ移行、self-hosted runner は信頼できるワークフローに限定、CI で使うツールのバージョンを固定
- **根拠**: GitHub Docs「OpenID Connect」（https://docs.github.com/en/actions/concepts/security/openid-connect ）/ OWASP CICD-SEC-6 Insufficient Credential Hygiene, CICD-SEC-7 Insecure System Configuration
