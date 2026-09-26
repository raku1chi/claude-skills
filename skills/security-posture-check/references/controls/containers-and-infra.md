# チェック項目: コンテナ・インフラ定義（IaC）

Dockerfile、docker-compose、Kubernetes マニフェスト、Terraform 等がリポジトリにある場合に適用する。書式は repo-and-supply-chain.md と同じ。

### CTR-01 コンテナを root 以外のユーザーで実行している
- **適用**: Dockerfile / Kubernetes マニフェストがある
- **確認方法**: signals の `final USER` / `runs as root`、Kubernetes の `runAsNonRoot`、compose の `user:`
- **判定**: ✅ 最終ステージで非 root の USER を指定（k8s は `runAsNonRoot: true`）/ 🟡 一部のイメージのみ / ❌ USER 指定なし（root で実行）
- **重大度**: Medium
- **リスク**: アプリの脆弱性を突かれたとき、攻撃者がコンテナ内で root 権限を得る。コンテナ脱出やマウントしたボリュームの改ざんにつながりやすい
- **対応方針**: 専用ユーザーを作成して `USER app`（UID/GID を明示）。書き込みが必要なディレクトリだけ所有権を付与
- **根拠**: Docker Docs「Building best practices – USER」（https://docs.docker.com/build/building/best-practices/#user ）/ CIS Docker Benchmark v1.8.0（https://www.cisecurity.org/benchmark/docker ）/ CWE-250（https://cwe.mitre.org/data/definitions/250.html ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html

### CTR-02 ベースイメージが固定され、脆弱性が確認されている
- **適用**: Dockerfile がある
- **確認方法**: signals の `base` 画像（`latest`・タグなし・ダイジェスト固定）、Dependabot の `docker` エコシステム、CI のイメージスキャン（trivy、grype 等）
- **判定**: ✅ バージョン（できればダイジェスト）固定＋自動更新かスキャン / 🟡 タグ固定のみ / ❌ `latest` またはタグなし
- **重大度**: Medium
- **リスク**: ビルドのたびに中身が変わり再現できない。脆弱な OS パッケージや、改ざんされたイメージを気づかず取り込む
- **対応方針**: `node:22.x-slim@sha256:...` のように固定し、Dependabot（docker）で更新。CI でイメージをスキャン。可能なら最小イメージ（slim、distroless）
- **根拠**: CIS Docker Benchmark v1.8.0 / OWASP Top 10:2025 A03（https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html

### CTR-03 イメージに秘密情報や不要なファイルが入らない
- **適用**: Dockerfile がある
- **確認方法**: signals の `dockerignore`、`COPY whole context`、`secret-like ENV/ARG`、`ADD remote URL`、`curl|sh`。`.dockerignore` が `.env`・`.git`・資格情報ファイルを除外しているか
- **判定**: ✅ `.dockerignore` で除外し、秘密情報は実行時に注入（BuildKit の secret mount 等）/ 🟡 除外はあるが不完全 / ❌ `.dockerignore` なしで `COPY . .`、または ENV/ARG に秘密情報
- **重大度**: High（秘密情報がイメージに入る）/ Medium（`.git` 等のみ）
- **リスク**: イメージを取得できる人（レジストリ権限の保有者、公開イメージなら誰でも）に秘密情報やソースの履歴が渡る。ENV・ARG の値はイメージの履歴に残る
- **対応方針**: `.dockerignore` を追加、マルチステージビルドで成果物だけをコピー、秘密情報は `--mount=type=secret` か実行時の環境変数で渡す
- **根拠**: ASVS v5.0.0-13.3.1 (L2: 秘密情報の管理の仕組み・ソースや成果物に秘密を含めない), 13.4.1 (L1: .git など管理用メタデータの非公開)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x22-V13-Configuration.md ）/ CWE-540（https://cwe.mitre.org/data/definitions/540.html ）→ A01:2025
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html

### CTR-04 コンテナの実行権限が絞られている
- **適用**: docker-compose / Kubernetes マニフェストがある
- **確認方法**: signals の compose（`privileged`、`host network`、`docker.sock mount`）、Kubernetes（`privileged`、`allowPrivilegeEscalation`、`readOnlyRootFilesystem`、host namespace、`hostPath`、`limits`）
- **判定**: ✅ privileged・ホスト名前空間・docker.sock のマウントなし、k8s は securityContext とリソース上限を設定 / 🟡 一部 / ❌ privileged や docker.sock マウントがある
- **重大度**: High（privileged / docker.sock はホストの乗っ取りと同等）/ Medium（リソース上限なし等）
- **リスク**: コンテナ内の侵害がそのままホスト全体の侵害になる。リソース上限がないと 1 つのコンテナがノード全体を止める
- **根拠**: CIS Docker Benchmark v1.8.0 / CWE-250 / OWASP Top 10:2025 A02（https://owasp.org/Top10/2025/A02_2025-Security_Misconfiguration/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Kubernetes_Security_Cheat_Sheet.html

### IAC-01 インフラ定義に危険な公開・無効化設定がない
- **適用**: Terraform / CloudFormation / Kubernetes / compose でネットワークやストレージを定義している
- **確認方法**: signals の `terraform_flags`（`0.0.0.0/0` の受信許可、公開 ACL のバケット、パブリックアクセスブロック無効、DB の公開、暗号化無効、IMDSv1、古い TLS）、compose の `DB ports published on all interfaces`。コミットされた Kubernetes Secret や `*.tfstate` は SEC-01 / SEC-03 で扱う
- **判定**: ✅ 該当なし、または意図と緩和策がコメント等で明示 / 🟡 開発用の定義のみで該当 / ❌ 本番の定義で該当
- **重大度**: High（データストアや管理ポート（SSH・DB）のインターネット公開）/ Medium
- **リスク**: データベースやストレージがインターネットから直接読める、管理ポートが総当たり攻撃にさらされる
- **対応方針**: 受信元を限定、パブリックアクセスブロックを有効化、暗号化を有効化、IMDSv2 を必須化。CI に IaC スキャナ（checkov、trivy config 等）を追加
- **根拠**: OWASP Top 10:2025 A02 / OWASP Infrastructure as Code Security Cheat Sheet（https://cheatsheetseries.owasp.org/cheatsheets/Infrastructure_as_Code_Security_Cheat_Sheet.html ）
