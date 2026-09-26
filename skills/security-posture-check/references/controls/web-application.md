# チェック項目: Web アプリケーション・API

HTTP でリクエストを受けるサーバー（Web アプリ、REST/GraphQL API、BFF、SSR フレームワーク）がある場合に適用する。書式は repo-and-supply-chain.md と同じ（適用 / 確認方法 / 判定 / 重大度 / リスク / 対応方針 / 根拠・参考）。ASVS の要件 ID は OWASP ASVS 5.0.0 の公式表記 `v5.0.0-<章>.<節>.<番号>`、括弧内はレベル（L1 が最低限）。

目次: [フレームワークの既定値](#defaults) / [AUTH 認証](#auth) / [SESS セッション・トークン](#sess) / [AUTHZ 認可](#authz) / [INJ 入力処理・インジェクション](#inj) / [WEB ブラウザ保護・通信](#web) / [CRY 暗号](#cry) / [DATA・CFG・API](#data)

<a id="defaults"></a>
## 判定の前に: フレームワークの既定値

「コードに対策が見当たらない」＝未対応とは限らない。既定で有効な対策と、明示的に無効化しているかを確認する。既定値はバージョンで変わるため、判定の根拠には実際のバージョン（ロックファイル）と設定箇所を引用すること。

| フレームワーク | 既定で有効 | 既定では無い・明示設定が必要 |
|---|---|---|
| Django | CSRF ミドルウェア（startproject の既定）、テンプレートの自動エスケープ、ORM のパラメータ化、`X-Frame-Options: DENY`、`nosniff`、セッション Cookie の HttpOnly | HSTS（`SECURE_HSTS_SECONDS` は 0）、`SESSION_COOKIE_SECURE`・`CSRF_COOKIE_SECURE`（False）。生成直後の settings は `DEBUG = True`。`python manage.py check --deploy` が参考になる |
| Flask | Jinja2 の自動エスケープ（`.html` 等のテンプレート）、セッション Cookie の HttpOnly | CSRF（Flask-WTF 等）、セキュリティヘッダ、`SESSION_COOKIE_SECURE`。**Flask-Talisman** を使うと既定で HTTPS 強制・HSTS・`frame-options: SAMEORIGIN`・`nosniff`・Referrer-Policy・セッション Cookie の Secure / HttpOnly / SameSite=Lax が設定される |
| FastAPI / Starlette | Pydantic による入力の型検証 | CORS（`CORSMiddleware` を明示追加）、Cookie 認証時の CSRF、セキュリティヘッダ、レート制限 |
| Express | `express.json()` の本文サイズ上限（既定 100kb） | セキュリティヘッダ（helmet）、CSRF、レート制限。`X-Powered-By` は既定で送信。引数なしの `cors()` は全オリジン許可 |
| Next.js | JSX の自動エスケープ。Server Actions は POST のみで Origin と Host を比較する（CSRF の緩和） | CSP 等のヘッダ、Route Handler / API Routes の CSRF・認可・レート制限。`dangerouslySetInnerHTML` はエスケープされない |
| Rails | CSRF 保護、ERB の自動エスケープ、Strong Parameters | `skip_forgery_protection`・`permit!`・`html_safe`・`raw` で無効化される。production の `config.force_ssl` を確認 |
| Laravel | web ルートの CSRF ミドルウェア、Blade `{{ }}` のエスケープ、Eloquent のパラメータ化、`$fillable` / `$guarded` | `{!! !!}` はエスケープされない。API ルートの認可・レート制限は明示が必要 |
| Spring Boot + Spring Security | CSRF（セッション利用時）、既定のセキュリティヘッダ（nosniff、X-Frame-Options DENY、HTTPS 時の HSTS 等） | Spring Security を導入していなければいずれも無い |
| Go (net/http) | `html/template` の文脈に応じた自動エスケープ | `text/template` はエスケープしない。ヘッダ・CSRF・レート制限は自前で実装 |

IPA「安全なウェブサイトの作り方」（改訂第7版, https://www.ipa.go.jp/security/vuln/websecurity/about.html ）の該当節も各項目に併記した。日本語で背景を説明したいときの参考にする。

---

<a id="auth"></a>
## AUTH 認証

### AUTH-01 パスワードが安全な方式で保存されている
- **適用**: アプリ自身がパスワードを保存する（外部 IdP のみなら ➖）
- **確認方法**: signals の `password-hashing` と `weak-crypto`。登録・パスワード変更処理でハッシュ関数を特定する
- **判定**: ✅ argon2id / scrypt / bcrypt / PBKDF2 等のパスワード用関数 / 🟡 適切な関数だがパラメータが弱い / ❌ 平文・MD5・SHA-1・SHA-256 単体（ソルトの有無に関わらず）
- **重大度**: High（平文保存は Critical）
- **リスク**: DB が漏れたとき、高速ハッシュは総当たりで短時間に元のパスワードに戻され、他サービスでの使い回しも含めて被害が広がる
- **対応方針**: argon2id か bcrypt に移行。次回ログイン時に再ハッシュして段階的に置き換える
- **根拠**: ASVS v5.0.0-11.4.2 (L2)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x20-V11-Cryptography.md ）/ CWE-916（https://cwe.mitre.org/data/definitions/916.html ）→ OWASP Top 10:2025 A04（https://owasp.org/Top10/2025/A04_2025-Cryptographic_Failures/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

### AUTH-02 ログイン試行が制限されている（ブルートフォース・パスワードリスト攻撃対策）
- **適用**: パスワード・OTP 等の認証エンドポイントがある
- **確認方法**: signals の `rate-limiting`。ログイン・パスワードリセット・OTP 検証のルートにレート制限、ロックアウト、CAPTCHA 等があるか。ゲートウェイや WAF で制限している可能性があり、リポジトリに証拠がなければ要確認と併記。ロードバランサやリバースプロキシの配下で IP 単位に制限する場合は、クライアント IP の取得設定（signals の `proxy-aware-client-ip`。Express の `trust proxy`、Flask の `ProxyFix` 等）があるか。ないと全員が同じ IP として数えられて制限がすぐ埋まるか、逆に `X-Forwarded-For` の偽装で回避される
- **判定**: ✅ 認証系エンドポイントすべてに制限 / 🟡 一部のみ、またはアプリ全体の緩い制限だけ / ❌ なし
- **重大度**: Medium（インターネット公開で個人情報を扱う場合は High）
- **リスク**: 流出したパスワードリストや総当たりでアカウントが乗っ取られる
- **対応方針**: 認証系エンドポイントに IP・アカウント単位のレート制限（例: express-rate-limit、Flask-Limiter、django-axes）。ロックアウトは嫌がらせに悪用されない設計にする
- **根拠**: ASVS v5.0.0-6.3.1 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x15-V6-Authentication.md ）/ CWE-307（https://cwe.mitre.org/data/definitions/307.html ）→ A07:2025（https://owasp.org/Top10/2025/A07_2025-Authentication_Failures/ ）/ OWASP API2:2023（https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

### AUTH-03 保護が必要な機能すべてに認証がかかっている
- **適用**: 認証を持つアプリ
- **確認方法**: signals の `entrypoints` と `auth-related files` からルート一覧を作り、各ルートに認証ミドルウェア・デコレータ（`login_required`、`requireAuth`、`Depends(get_current_user)` 等）が適用されているかを確認。ルーター単位のマウント（例: `app.use('/api/admin', adminRoutes)`）でまとめて漏れていないか特に注意
- **判定**: ✅ 公開意図のあるもの以外すべて認証必須 / 🟡 重要度の低い一部ルートに漏れ / ❌ 管理機能・個人データ・状態変更のルートに認証がない
- **重大度**: Critical（管理機能・全ユーザーデータ）/ High（その他）
- **リスク**: URL を知っていれば誰でも管理機能の実行やデータ取得ができる
- **対応方針**: 既定で認証必須にし、公開ルートを明示的に許可する構成（deny by default）へ
- **根拠**: CWE-306（https://cwe.mitre.org/data/definitions/306.html ）→ A07:2025 / ASVS v5.0.0-8.2.1 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md ）/ IPA 1.11 アクセス制御や認可制御の欠落

### AUTH-04 既定アカウント・初期パスワードがない
- **適用**: アプリ・シード・設定にユーザー作成処理や管理者アカウントがある
- **確認方法**: シードスクリプト、マイグレーション、docker-compose の環境変数、README の「初期ログイン」記載を確認（admin/admin 等）
- **判定**: ✅ 既定アカウントなし、または初回起動時に強制変更 / ❌ 固定の既定資格情報で本番に入れる
- **重大度**: High
- **リスク**: 公開ドキュメントやソースに書かれた既定の資格情報で管理者としてログインされる
- **対応方針**: 既定アカウントを削除し、初期管理者は環境ごとに生成したランダムな資格情報か招待フローで作成
- **根拠**: ASVS v5.0.0-6.3.2 (L1), 13.2.3 (L2) / CWE-1392（https://cwe.mitre.org/data/definitions/1392.html ）→ A07:2025

### AUTH-05 多要素認証（MFA）を利用できる
- **適用**: アプリ自身が認証を実装し、管理者や重要データを扱う（外部 IdP 利用なら IdP 側設定として要確認）
- **確認方法**: TOTP・WebAuthn・パスキー関連の実装やライブラリ
- **判定**: ✅ MFA を提供（管理者は必須）/ 🟡 提供するが管理者も任意 / ❌ なし
- **重大度**: Medium（管理画面がある場合）/ Low（一般ユーザー向けのみ）
- **リスク**: パスワードが漏れた時点でアカウントが乗っ取られる
- **対応方針**: 管理者から MFA を必須化。認証をマネージド IdP に委ねるのも有効
- **根拠**: ASVS v5.0.0-6.3.3 (L2), 6.4.3 (L2)
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html

### AUTH-06 外部 IdP・OAuth/OIDC 連携が安全に実装されている
- **適用**: OAuth / OIDC / SAML でログインする（ライブラリ任せの標準的な実装なら確認は軽くてよい）
- **確認方法**: 認可コードフロー＋PKCE か、`state` / `nonce` の検証、ID トークンの署名・`iss`・`aud` の検証、ユーザーの識別に `sub` を使っているか（メールアドレスで照合していないか）
- **判定**: ✅ 実績あるライブラリで標準的に実装 / 🟡 一部の検証が欠ける / ❌ 署名・state を検証していない、Implicit フロー
- **重大度**: High
- **リスク**: 他人のアカウントへのログイン（アカウント乗っ取り）、ログイン CSRF
- **根拠**: ASVS v5.0.0-10.1.2 (L2), 10.2.1 (L2), 10.5.1 (L2), 10.5.2 (L2), 6.8.2 (L2)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x19-V10-OAuth-and-OIDC.md ）

---

<a id="sess"></a>
## SESS セッション・トークン

### SESS-01 Cookie にセキュリティ属性が付いている
- **適用**: Cookie でセッション・認証情報を扱う
- **確認方法**: signals の `cookie-security-flags` / `cookie-flags-weak`。セッション設定（express-session の `cookie`、Django/Flask の `SESSION_COOKIE_*`、Talisman 等の既定値）
- **判定**: ✅ Secure・HttpOnly・SameSite が適切 / 🟡 一部欠落（例: Secure なし）/ ❌ 明示的に無効化、または認証 Cookie に HttpOnly がない
- **重大度**: Medium
- **リスク**: HTTP 通信での盗聴や XSS でセッション Cookie を盗まれ、なりすまされる
- **対応方針**: `Secure`・`HttpOnly`・`SameSite=Lax` 以上。可能なら `__Host-` プレフィックス
- **根拠**: ASVS v5.0.0-3.3.1 (L1), 3.3.2 (L2), 3.3.4 (L2)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x12-V3-Web-Frontend-Security.md ）/ CWE-614（https://cwe.mitre.org/data/definitions/614.html ）, CWE-1004 → A02:2025（https://owasp.org/Top10/2025/A02_2025-Security_Misconfiguration/ ）/ IPA 1.4 セッション管理の不備
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

### SESS-02 ログイン時にセッションを再生成し、ログアウト・期限切れで確実に無効化する
- **適用**: セッション（Cookie・参照トークン）を使う
- **確認方法**: ログイン処理での再生成（`req.session.regenerate`、`session.clear()` 後の再設定、Django の `login()` 等）、ログアウトでサーバー側のセッションを破棄しているか、アイドル・絶対タイムアウト。署名付き Cookie セッション（Flask の既定など）はサーバー側で失効できない点に注意
- **判定**: ✅ 再生成・サーバー側失効・タイムアウトあり / 🟡 一部欠落（例: Cookie セッションでログアウト後も再利用可能）/ ❌ いずれもない
- **重大度**: Medium
- **リスク**: セッション固定攻撃、盗まれたセッションがログアウト後も使い続けられる
- **根拠**: ASVS v5.0.0-7.2.4 (L1), 7.4.1 (L1), 7.3.1 (L2)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md ）/ CWE-384（https://cwe.mitre.org/data/definitions/384.html ）, CWE-613 → A07:2025

### SESS-03 トークン（JWT 等）が正しく検証されている
- **適用**: JWT などの自己完結型トークンを発行・検証する
- **確認方法**: signals の `jwt-verification-weakness` / `jwt-without-expiry`。検証で署名を確認しているか（`jwt.decode` だけで信頼していないか）、許可アルゴリズムの固定、`exp`・`nbf`・`aud` の検証、有効期限の設定、失効手段
- **判定**: ✅ 署名・アルゴリズム・期限を検証し、発行時に有効期限あり / 🟡 期限なしの発行や `aud` 未検証など一部欠落 / ❌ 署名を検証しない、`none` を許可
- **重大度**: Critical（署名未検証）/ Medium（期限なし）
- **リスク**: トークンを改ざん・偽造して他人や管理者になりすませる。期限のないトークンは漏えい後も永久に使える
- **対応方針**: `verify` 系 API で署名検証、`algorithms` を固定、短い `expiresIn` とリフレッシュトークン運用
- **根拠**: ASVS v5.0.0-9.1.1 (L1), 9.1.2 (L1), 9.2.1 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x18-V9-Self-contained-Tokens.md ）/ CWE-347（https://cwe.mitre.org/data/definitions/347.html ）→ A04:2025 / CWE-613 → A07:2025
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html

---

<a id="authz"></a>
## AUTHZ 認可

### AUTHZ-01 機能レベルの認可がサーバー側で強制されている
- **適用**: 役割（管理者・一般など）や権限の区別がある
- **確認方法**: 管理機能・権限が必要な操作のルートで、ロール・権限チェックがサーバー側（ミドルウェア・ポリシー）にあるか。フロントエンドでボタンを隠しているだけではないか
- **判定**: ✅ すべての特権操作でサーバー側チェック / 🟡 一部漏れ / ❌ チェックなし、またはクライアント側のみ
- **重大度**: High（管理機能なら Critical）
- **リスク**: 一般ユーザー（または未認証者）が管理機能を直接呼び出して実行できる
- **対応方針**: 権限チェックを共通のミドルウェア・ポリシー層に集約し、既定拒否にする
- **根拠**: ASVS v5.0.0-8.2.1 (L1), 8.3.1 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md ）/ CWE-862（https://cwe.mitre.org/data/definitions/862.html ）→ A01:2025（https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/ ）/ OWASP API5:2023（https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/ ）/ IPA 1.11
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

### AUTHZ-02 オブジェクト単位の認可がある（IDOR / BOLA 対策）
- **適用**: ユーザーごとのデータ（注文・文書・プロフィール等）を ID で取得・更新する
- **確認方法**: ID をパラメータに取るルート（`/:id`、`<int:id>`、`{id}`）を列挙し、クエリに所有者条件（`user_id = 現在のユーザー`）かポリシーチェックがあるかを読む。共有リンク・公開用ルートは推測可能な ID で他人のデータが見えないか確認
- **判定**: ✅ すべての取得・更新・削除で所有者・権限を検証 / 🟡 一部のルートで欠落 / ❌ 検証がないルートが主要機能にある
- **重大度**: High（他人の個人情報・決済情報に届く場合は Critical）
- **リスク**: URL の ID を変えるだけで他人のデータを閲覧・改ざん・削除できる
- **対応方針**: クエリに所有者条件を必ず含める、または共通の認可ヘルパーを通す。推測しにくい ID は補助策にすぎず認可の代わりにならない。他人の ID でアクセスして拒否されることをテストする
- **根拠**: ASVS v5.0.0-8.2.2 (L1) / CWE-639（https://cwe.mitre.org/data/definitions/639.html ）→ A01:2025 / OWASP API1:2023（https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html

### AUTHZ-03 更新できる項目が制限されている（Mass Assignment・プロパティ単位の認可）
- **適用**: リクエストの内容でレコードを作成・更新する
- **確認方法**: signals の `mass-assignment`。`req.body` や `**request.json` をそのまま ORM・`UPDATE ... SET ?` に渡していないか。レスポンスに不要な項目（パスワードハッシュ、内部フラグ）を返していないか
- **判定**: ✅ 許可リスト（DTO・スキーマ・Strong Parameters）で項目を限定 / 🟡 一部のみ / ❌ 入力をそのまま保存
- **重大度**: High（`role` や `is_admin` を書き換えられる場合）/ Medium
- **リスク**: 利用者が `role: "admin"` や価格・所有者などを勝手に書き換えられる。不要な項目がレスポンスから漏れる
- **対応方針**: 更新可能な項目を明示した許可リストで受け取り、レスポンスも出力用スキーマで絞る
- **根拠**: ASVS v5.0.0-8.2.3 (L2), 15.3.3 (L2) / CWE-915（https://cwe.mitre.org/data/definitions/915.html ）→ A08:2025（https://owasp.org/Top10/2025/A08_2025-Software_or_Data_Integrity_Failures/ ）/ OWASP API3:2023（https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html

---

<a id="inj"></a>
## INJ 入力処理・インジェクション

### INJ-01 SQL / NoSQL インジェクション対策（パラメータ化）
- **適用**: データベースを使う
- **確認方法**: signals の `sql-string-building` / `nosql-operator-injection`。文字列連結・テンプレート文字列・f-string で組み立てたクエリに、ユーザー入力が届くかを読む
- **判定**: ✅ すべてプレースホルダ・ORM / 🟡 連結はあるが入力は届かない（定数・許可リスト済み）/ ❌ ユーザー入力が連結される
- **重大度**: Critical（認証前に到達できる場合）/ High
- **リスク**: DB の全データの窃取・改ざん・削除、認証回避。条件によってはサーバー上でのコマンド実行
- **対応方針**: プレースホルダ（`?`、`$1`、`%s` をパラメータとして渡す）か ORM のクエリビルダーに置き換え。識別子（列名・並び順）は許可リストで選ぶ
- **根拠**: ASVS v5.0.0-1.2.4 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x10-V1-Encoding-and-Sanitization.md ）/ CWE-89（https://cwe.mitre.org/data/definitions/89.html ）→ A05:2025（https://owasp.org/Top10/2025/A05_2025-Injection/ ）/ IPA 1.1 SQLインジェクション
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html / https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html

### INJ-02 OS コマンドインジェクション対策
- **適用**: 外部コマンドを実行する
- **確認方法**: signals の `os-command-shell`。シェル経由の実行（`exec`、`shell=True`、`sh -c`）にユーザー入力が届くか。信頼境界に注意（CLI の利用者自身が書いた設定ファイルの実行は、同じ権限の中の操作なので通常は脆弱性ではない）
- **判定**: ✅ シェルを使わず引数配列で実行、または入力が届かない / 🟡 入力は届くが厳格な許可リスト検証あり / ❌ 外部からの入力がシェルに渡る
- **重大度**: Critical
- **リスク**: サーバー上で任意のコマンドが実行され、サーバーごと乗っ取られる
- **対応方針**: `execFile` / `spawn`（shell なし）、`subprocess.run([...])` のように引数を配列で渡す。値は許可リストで検証。可能ならコマンド実行自体をライブラリ呼び出しに置き換える
- **根拠**: ASVS v5.0.0-1.2.5 (L1) / CWE-78（https://cwe.mitre.org/data/definitions/78.html ）→ A05:2025 / IPA 1.2 OSコマンド・インジェクション
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html

### INJ-03 XSS 対策（出力エスケープ・HTML のサニタイズ）
- **適用**: HTML を返す、またはフロントエンドで DOM を組み立てる
- **確認方法**: signals の `unsafe-html-sink`（`dangerouslySetInnerHTML`、`innerHTML`、`v-html`、`|safe`、`mark_safe`、`html_safe`、`{!! !!}` 等）。そこにユーザー入力・外部データ・LLM の出力が届くか、サニタイズ（DOMPurify 等）があるか
- **判定**: ✅ 自動エスケープに任せ、例外箇所はサニタイズ済み / 🟡 エスケープ回避はあるが信頼できるデータのみ / ❌ 信頼できないデータがエスケープなしで出力される
- **重大度**: High（保存型・他ユーザーに届く）/ Medium（反射型・自分にのみ影響）
- **リスク**: 閲覧者のブラウザで攻撃者のスクリプトが動き、セッション乗っ取り・画面の改ざん・操作の代行が起きる
- **対応方針**: テンプレートの自動エスケープを使い、HTML を許す必要がある箇所だけ実績あるサニタイザで処理。CSP（WEB-01）を併用
- **根拠**: ASVS v5.0.0-1.2.1 (L1), 1.3.1 (L1), 3.2.2 (L1) / CWE-79（https://cwe.mitre.org/data/definitions/79.html ）→ A05:2025 / IPA 1.5 クロスサイト・スクリプティング
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html / https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html

### INJ-04 動的コード実行・テンプレートインジェクション・安全でないデシリアライズがない
- **適用**: 常に（該当コードがなければ ✅）
- **確認方法**: signals の `dynamic-code-eval`、`unsafe-deserialization`（pickle、`yaml.load` + `Loader=yaml.Loader`、`unserialize`、`BinaryFormatter` 等）。`render_template_string` 等にユーザー入力が入らないか。XML パーサの外部エンティティ設定
- **判定**: ✅ 使用なし、または信頼できる入力のみ / ❌ 外部からの入力が届く
- **重大度**: Critical（外部入力が届く場合）
- **リスク**: サーバー上での任意コード実行
- **対応方針**: `eval` を使わない設計へ。`yaml.safe_load`、JSON 等データ専用の形式、型を許可リストで制限したデシリアライズ。XML は外部エンティティを無効化
- **根拠**: ASVS v5.0.0-1.3.2 (L1), 1.3.7 (L2), 1.5.1 (L1), 1.5.2 (L2) / CWE-94（https://cwe.mitre.org/data/definitions/94.html ）→ A05:2025 / CWE-502（https://cwe.mitre.org/data/definitions/502.html ）→ A08:2025
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html

### INJ-05 パストラバーサル・ファイルアップロード対策
- **適用**: ファイルの読み書き・ダウンロード・アップロードに外部入力が関わる
- **確認方法**: signals の `path-traversal`。ファイル名・パスを入力から組み立てていないか、アップロードのサイズ・拡張子・内容（マジックバイト）の検証、保存場所で実行されないか。同じ値を URL とファイルパスの両方に使う箇所に注意（`name#/../../x` のように、URL としては無害でもパスとしては外に出る）。CLI の引数や設定ファイルからの値も、そのツールを使う人以外が値を決められる経路（プラグイン名、ダウンロード元の応答など）がないか確認する
- **判定**: ✅ 内部生成の名前で保存・読み込み、サイズと種類を検証 / 🟡 一部の検証が欠ける / ❌ 入力をそのままパスに使う
- **重大度**: High
- **リスク**: `../` で任意のファイル（設定・秘密鍵）を読まれる・上書きされる。アップロードしたスクリプトが実行される
- **対応方針**: ファイル名はサーバー側で生成、ベースディレクトリ外を拒否（正規化して比較）、サイズ・種類を検証
- **根拠**: ASVS v5.0.0-5.2.1 (L1), 5.2.2 (L1), 5.3.1 (L1), 5.3.2 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x14-V5-File-Handling.md ）/ CWE-22（https://cwe.mitre.org/data/definitions/22.html ）→ A01:2025 / CWE-434 → A06:2025 / IPA 1.3 ディレクトリ・トラバーサル
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

### INJ-06 SSRF 対策
- **適用**: サーバーが外部の URL にアクセスする（Webhook、URL プレビュー、画像取得、LLM ツールの Web 取得など）
- **確認方法**: signals の `ssrf`。URL・ホストが入力で決まるか、許可リスト、内部アドレス（169.254.169.254、localhost、プライベート IP）の拒否、リダイレクト追従の制御
- **判定**: ✅ 許可リストで宛先を限定 / 🟡 部分的な検証のみ / ❌ 入力の URL にそのままアクセス
- **重大度**: High（クラウド環境ではメタデータ経由で資格情報が取られるため Critical になりうる）
- **リスク**: 内部ネットワークやクラウドのメタデータサービスにアクセスされ、資格情報や内部データが盗まれる
- **根拠**: ASVS v5.0.0-1.3.6 (L2), 13.2.4 (L2), 15.3.2 (L2) / CWE-918（https://cwe.mitre.org/data/definitions/918.html ）→ A01:2025 / OWASP API7:2023（https://owasp.org/API-Security/editions/2023/en/0xa7-server-side-request-forgery/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

### INJ-07 入力が信頼境界で検証されている
- **適用**: 外部からの入力を受け取る
- **確認方法**: signals の `input-validation`。API の入口でスキーマ検証（zod、Joi、Pydantic、Bean Validation 等）をしているか。クライアント側の検証だけに頼っていないか。ヘッダ・メールヘッダに改行を含む値を入れていないか
- **判定**: ✅ 主要な入口でスキーマ・許可リスト検証 / 🟡 一部のみ / ❌ ほぼなし
- **重大度**: Medium
- **リスク**: 想定外の型・長さ・値が処理に入り、インジェクションやロジックの抜け穴につながる
- **根拠**: ASVS v5.0.0-2.2.1 (L1), 2.2.2 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x11-V2-Validation-and-Business-Logic.md ）/ CWE-20（https://cwe.mitre.org/data/definitions/20.html ）→ A05:2025 / IPA 1.7 HTTPヘッダ・インジェクション, 1.8 メールヘッダ・インジェクション
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html

### INJ-08 オープンリダイレクトがない
- **適用**: 入力でリダイレクト先を決める（`next=`、`returnTo=` 等）
- **確認方法**: signals の `open-redirect`。リダイレクト先が相対パスか許可リストのドメインに限定されているか
- **判定**: ✅ 限定済み / ❌ 任意の URL にリダイレクト
- **重大度**: Medium
- **リスク**: 正規ドメインのリンクを踏み台にしたフィッシング、OAuth のトークン漏えい
- **根拠**: ASVS v5.0.0-3.7.2 (L2) / CWE-601（https://cwe.mitre.org/data/definitions/601.html ）→ A01:2025
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html

---

<a id="web"></a>
## WEB ブラウザ保護・通信

### WEB-01 セキュリティヘッダが設定されている（CSP・HSTS・nosniff・frame-ancestors・Referrer-Policy）
- **適用**: ブラウザ向けに HTML を返す（JSON のみの API は nosniff 以外は影響が小さい → 重大度を下げる）
- **確認方法**: signals の `security-headers`（helmet、Talisman、SecurityMiddleware、nginx の `add_header`、`next.config.js` の headers）。リバースプロキシや CDN で付けている可能性があれば要確認と併記
- **判定**: ✅ 主要ヘッダが揃う / 🟡 一部のみ（例: HSTS のみ）/ ❌ なし
- **重大度**: Medium（API のみなら Low）
- **リスク**: XSS の被害拡大（CSP がない）、HTTPS から HTTP への格下げ（HSTS がない）、クリックジャッキング（frame-ancestors がない）
- **対応方針**: helmet / Talisman / フレームワーク設定で CSP・HSTS・`X-Content-Type-Options: nosniff`・`frame-ancestors`・Referrer-Policy を付与
- **根拠**: ASVS v5.0.0-3.4.1 (L1), 3.4.3 (L2), 3.4.4 (L2), 3.4.5 (L2), 3.4.6 (L2) / CWE-1021（https://cwe.mitre.org/data/definitions/1021.html ）→ A06:2025（https://owasp.org/Top10/2025/A06_2025-Insecure_Design/ ）/ IPA 1.9 クリックジャッキング
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html / https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html

### WEB-02 CORS が必要なオリジンに限定されている
- **適用**: CORS を設定している、またはブラウザから別オリジンで呼ばれる API
- **確認方法**: signals の `cors-permissive`。`*`、リクエストの Origin をそのまま返す実装、`credentials: true` との組み合わせ
- **判定**: ✅ 許可リストで限定 / 🟡 `*` だが認証情報を使わない公開 API / ❌ 認証付き API で `*` やオリジン反射
- **重大度**: High（認証情報付きでオリジン反射）/ Medium
- **リスク**: 悪意あるサイトが、ログイン中の利用者の権限で API を呼び出してデータを読み取る
- **根拠**: ASVS v5.0.0-3.4.2 (L1) / CWE-942（https://cwe.mitre.org/data/definitions/942.html ）→ A02:2025

### WEB-03 CSRF 対策がある
- **適用**: Cookie など自動送信される資格情報で認証する（`Authorization` ヘッダのトークンのみなら ➖）
- **確認方法**: signals の `csrf-protection` / `csrf-protection-disabled`、フレームワーク既定値（上の表）、SameSite 属性、状態変更に GET を使っていないか
- **判定**: ✅ トークン・Origin 検証・SameSite 等で保護 / 🟡 SameSite のみ、または一部で除外（`csrf_exempt` 等）/ ❌ 保護なし
- **重大度**: Medium（送金・権限変更など重要操作がある場合は High）
- **リスク**: 利用者が罠サイトを開いただけで、ログイン中のアカウントで意図しない操作（設定変更・購入・投稿）が行われる
- **根拠**: ASVS v5.0.0-3.5.1 (L1), 3.5.2 (L1), 3.5.3 (L1), 3.3.2 (L2) / CWE-352（https://cwe.mitre.org/data/definitions/352.html ）→ A01:2025 / IPA 1.6 CSRF
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

### WEB-04 TLS を強制し、外部接続で証明書を検証している
- **適用**: 常に（公開サービスと外部 API 呼び出し）
- **確認方法**: signals の `tls-verification-disabled`（`verify=False`、`rejectUnauthorized: false`、`InsecureSkipVerify` 等）。本番コードかテスト・開発専用かを確認。HTTPS 強制・HTTP リダイレクトの設定（プラットフォーム側なら要確認）
- **判定**: ✅ 検証無効化なし＋HTTPS 強制 / 🟡 開発用途に限定された無効化 / ❌ 本番の通信で検証を無効化
- **重大度**: High
- **リスク**: 経路上の攻撃者が通信を盗聴・改ざんし、送信した資格情報やデータを奪う
- **対応方針**: 検証の無効化を削除し、社内 CA なら CA バンドルを指定する
- **根拠**: ASVS v5.0.0-12.2.1 (L1), 12.3.2 (L2)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x21-V12-Secure-Communication.md ）/ CWE-295（https://cwe.mitre.org/data/definitions/295.html ）→ A07:2025 / CWE-319 → A04:2025
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html

---

<a id="cry"></a>
## CRY 暗号

### CRY-01 弱い暗号アルゴリズムを使っていない
- **適用**: 暗号化・ハッシュ・署名を使う
- **確認方法**: signals の `weak-crypto`。MD5・SHA-1 がセキュリティ目的（パスワード、署名、トークン、改ざん検知）か、キャッシュキー・ETag 等の非セキュリティ用途かを文脈で判断。ECB モード、DES/RC4
- **判定**: ✅ セキュリティ用途は承認済みアルゴリズムのみ / 🟡 非セキュリティ用途の MD5 等のみ（明記を推奨）/ ❌ セキュリティ用途で弱いアルゴリズム
- **重大度**: High（パスワード・署名用途）/ Low（非セキュリティ用途）
- **リスク**: 衝突・総当たりで改ざん検知や秘匿が破られる
- **根拠**: ASVS v5.0.0-11.3.1 (L1), 11.4.1 (L1) / CWE-327（https://cwe.mitre.org/data/definitions/327.html ）→ A04:2025
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html

### CRY-02 推測されてはいけない値に暗号論的乱数を使っている
- **適用**: セッション ID・リセットトークン・API キー・招待コード等を生成する
- **確認方法**: signals の `insecure-randomness`（`Math.random`、`random.random`、`math/rand` 等）。生成箇所を読み、用途を確認
- **判定**: ✅ `crypto.randomBytes` / `crypto.randomUUID` / `secrets` / `crypto/rand` 等 / ❌ 非暗号論的乱数
- **重大度**: High（認証・パスワードリセットに使われる場合）
- **リスク**: トークンを推測され、パスワードリセットの乗っ取りやセッションの奪取が起きる
- **根拠**: ASVS v5.0.0-7.2.3 (L1), 11.5.1 (L2) / CWE-338（https://cwe.mitre.org/data/definitions/338.html ）→ A04:2025

---

<a id="data"></a>
## DATA・CFG・API データ保護・設定・可用性

### DATA-01 機密情報がログ・URL・レスポンスに出ていない
- **適用**: 常に
- **確認方法**: signals の `sensitive-data-logging`。パスワード・トークン・カード番号をログに出していないか、URL のクエリにトークンを載せていないか、レスポンスにパスワードハッシュ等の不要な項目がないか
- **判定**: ✅ 該当なし / 🟡 開発用ログのみ / ❌ 本番経路で出力
- **重大度**: Medium（資格情報が平文でログに残る場合は High）
- **リスク**: ログ基盤・監視 SaaS・ブラウザ履歴・Referer 経由で資格情報や個人情報が漏れる
- **根拠**: ASVS v5.0.0-16.2.5 (L2), 14.2.1 (L1)（https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md ）/ CWE-532（https://cwe.mitre.org/data/definitions/532.html ）→ A09:2025（https://owasp.org/Top10/2025/A09_2025-Security_Logging_and_Alerting_Failures/ ）/ CWE-598 → A06:2025
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

### DATA-02 エラー時に内部情報を返さず、安全側に倒れる
- **適用**: 常に
- **確認方法**: signals の `error-details-exposed`。共通エラーハンドラがスタックトレース・SQL・例外メッセージを返していないか。例外時に認可や検証を飛ばして処理が続かないか（fail-open）
- **判定**: ✅ 汎用メッセージ＋サーバー側ログ、例外時は拒否 / 🟡 一部で詳細を返す / ❌ スタックトレースを返す、または例外時に処理を継続
- **重大度**: Medium（fail-open で認可を迂回できる場合は High）
- **リスク**: 内部構造・ライブラリのバージョン・クエリが攻撃者に伝わり、次の攻撃の手がかりになる。例外時に検証が素通りする
- **根拠**: ASVS v5.0.0-16.5.1 (L2), 16.5.3 (L2) / CWE-209（https://cwe.mitre.org/data/definitions/209.html ）, CWE-636 → OWASP Top 10:2025 A10（https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html

### DATA-03 セキュリティ上の出来事を記録している
- **適用**: 認証・認可を持つアプリ
- **確認方法**: signals の `security-logging`。ログイン成功・失敗、認可の拒否、パスワード変更などをログに残しているか。ログ注入（改行を含む入力）への対策
- **判定**: ✅ 主要なイベントを記録 / 🟡 一部のみ / ❌ なし
- **重大度**: Low（管理機能や金銭を扱う場合は Medium）
- **リスク**: 攻撃や不正アクセスに気づけず、事後に被害範囲を調べられない
- **根拠**: ASVS v5.0.0-16.3.1 (L2), 16.3.2 (L2), 16.4.1 (L2) / CWE-778（https://cwe.mitre.org/data/definitions/778.html ）→ A09:2025

### CFG-01 本番でデバッグ機能・開発用機能が無効になっている
- **適用**: 常に
- **確認方法**: signals の `debug-mode-enabled`。本番の起動経路（Dockerfile の CMD、Procfile、gunicorn 等）で有効になるのか、`if __name__ == "__main__"` のような開発専用経路だけかを区別する。デバッグ用ルート、サンプル、管理用エンドポイントの露出
- **判定**: ✅ 本番経路では無効 / 🟡 開発専用経路のみで有効（本番設定の分離を推奨）/ ❌ 本番で有効
- **重大度**: High（Werkzeug のデバッガ等、対話コンソールが公開される場合は Critical）
- **リスク**: スタックトレースや設定値の露出。対話型デバッガが公開されるとサーバー上で任意コードを実行される
- **根拠**: ASVS v5.0.0-13.4.2 (L2), 15.2.3 (L2), 13.4.1 (L1) / CWE-489（https://cwe.mitre.org/data/definitions/489.html ）→ A02:2025 / CWE-215 → A10:2025
- **参考**: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/ / https://flask.palletsprojects.com/en/stable/web-security/ / https://expressjs.com/en/advanced/best-practice-security.html

### API-01 レート制限とリソース消費の上限がある
- **適用**: 公開 API・Web アプリ（特にコストの高い処理: 検索、エクスポート、ファイル処理、LLM 呼び出し、メール送信）
- **確認方法**: signals の `rate-limiting` / `request-limits`。本文サイズ上限、ページングの上限、タイムアウト、GraphQL の深さ・コスト制限。ゲートウェイ側の制限は要確認と併記。プロキシ配下でのクライアント IP の扱いは AUTH-02 と同じ観点で確認
- **参考（プロキシ配下の設定）**: https://expressjs.com/en/guide/behind-proxies.html / https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/
- **判定**: ✅ コストの高い処理に制限 / 🟡 全体の緩い制限のみ / ❌ なし
- **重大度**: Medium（従量課金の外部 API を呼ぶ処理は High になりうる）
- **リスク**: サービス停止、クラウドや外部 API の高額請求、データの大量取得
- **根拠**: ASVS v5.0.0-2.4.1 (L2), 15.2.2 (L2), 4.3.1 (L2) / CWE-770（https://cwe.mitre.org/data/definitions/770.html ）/ OWASP API4:2023（https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/ ）
- **参考**: https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html
