# GitHub Issues にする手順

Issue の作成は外部に公開される操作なので、**作る前に一覧を見せて了承をもらう**。了承の範囲（どの Issue を、どのリポジトリに、ラベルを作るか）を超えて作らない。

## 1. リポジトリと公開範囲を確認する

- 対象リポジトリ: signals の `github_repo`。違うリポジトリに起票したい場合はユーザーが指定する。
- 公開範囲: `gh repo view <owner/repo> --json visibility`、または GitHub の MCP ツールでリポジトリ情報を取得。分からなければユーザーに聞く。

### 公開リポジトリでの注意（重要）

未修正の脆弱性の場所と悪用方法を公開 Issue に書くと、修正前に攻撃者に教えることになる。対応項目を次の 2 種類に分ける。

| 種類 | 例 | 起票の方法 |
|---|---|---|
| 悪用できる脆弱性 | 秘密情報の露出、インジェクション、認可・認証の欠落（INJ、AUTHZ、AUTH-03、SESS-03、CICD-03 など） | 公開 Issue にしない。次のどれかをユーザーに選んでもらう: ① リポジトリのセキュリティアドバイザリ（下書き・非公開）を作る（`POST /repos/{owner}/{repo}/security-advisories`。管理者かセキュリティマネージャーの権限が必要）② ローカルのレポートだけで管理する ③ 場所と再現手順を省いた概要だけの Issue にする |
| 堅牢化・プロセスの改善 | SECURITY.md の追加、Dependabot、ワークフローの権限、セキュリティヘッダ | 通常の Issue でよい |

秘密情報の露出は、Issue を作る前にローテーションを済ませるよう促す。

非公開リポジトリでも、Issue を見られる人の範囲を意識する（外部の協力者など）。

## 2. 使える手段を選ぶ

1. **gh CLI**（`gh auth status` で認証済みなら）
2. **GitHub の MCP ツール**（issue の検索・作成ツールがあれば）
3. **どちらもない場合**: Issue の下書きを `security-reports/issues/R-01.md` のように書き出し、作成方法（Web の New issue に貼り付ける、`gh issue create --body-file` を使う）を伝える

## 3. 重複を防ぐ

各 Issue の本文末尾に、次の目印を入れる（関連するチェック ID を昇順に並べる）。

```
<!-- security-posture-check controls=SEC-01,SEC-02 -->
```

作成前に、開いている Issue からこの目印を探す。

```bash
gh issue list --repo <owner/repo> --state open --search "security-posture-check in:body" --json number,title,body --limit 100
```

同じチェック ID を含む Issue が既にあれば新しく作らず、状況の更新をコメントするかをユーザーに聞く。以前の Issue が閉じられているのに今回も未対応なら、再発として新しい Issue を作り、古い Issue の番号を本文で参照する。

## 4. ラベル

`security` と `priority: P1` / `priority: P2` / `priority: P3` を使う。存在しないラベルは、ユーザーの了承を得たうえで作る（`gh label create "security" --color B60205` など）。作れない場合はラベルなしで作成し、本文の見出しで優先度が分かるようにする。

## 5. 作成前の確認

次のような一覧を見せて、了承をもらう。

```
作成予定の Issue（owner/repo, 非公開リポジトリ）:
1. [Security][P1] AWS の鍵をローテーションし、設定から除去する  (security, priority: P1)
2. [Security][P1] 注文 API に所有者チェックを追加する  (security, priority: P1)
3. [Security][P2] GitHub Actions のトークン権限を最小化する  (security, priority: P2)
まとめの Issue: 作る / 作らない
新しく作るラベル: priority: P1, priority: P2
```

## 6. 作成する

```bash
gh issue create --repo <owner/repo> --title "<タイトル>" --body-file <本文ファイル> --label "security" --label "priority: P1"
```

本文は一時ファイルに書いてから `--body-file` で渡す（改行や記号の崩れを防ぐ）。作成したら番号と URL を控え、最後に一覧で報告する。レポートも書き出す場合は、対応項目に Issue の URL を追記する。

**まとめの Issue**（ユーザーが望んだ場合だけ）: 作成した Issue をチェックリストで並べた Issue を 1 件作る（例: `[Security] セキュリティ診断 YYYY-MM-DD の対応状況`）。望まれていなければ、まとめはチャットの返答に書けば足りる。下書きモードでも、頼まれていないまとめ用ファイルは作らない。

## Issue のタイトルと本文

タイトル: `[Security][P1] <対応項目のタイトル>`（動詞で終わる具体的な作業にする。例:「注文 API に所有者チェックを追加する」）

````markdown
## 概要
<何を、なぜ直すのか。1〜2 文>

## 該当するチェック項目
- ❌ AUTHZ-02 オブジェクト単位の認可がある（IDOR / BOLA 対策） — High
- ❌ AUTHZ-03 更新できる項目が制限されている（Mass Assignment） — High

## 引っかかった理由
- `src/routes/orders.js:14` `GET /api/orders/:id` が注文 ID だけで検索しており、ログイン中のユーザーの注文かどうかを確認していない
- `src/routes/orders.js:21` `PUT /api/orders/:id` がリクエスト本文をそのまま `UPDATE orders SET ?` に渡している

## 放置した場合のリスク
<このプロジェクトに即して。何が、誰に、どうなるか>

## 対応手順
- [ ] <具体的な手順 1>
- [ ] <具体的な手順 2>

## 完了条件
- [ ] <確認方法。例: 他ユーザーの注文 ID で 404 が返るテストが通る>

## 根拠・参考
- ASVS v5.0.0-8.2.2 (L1): https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md
- OWASP API1:2023: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/
- CWE-639: https://cwe.mitre.org/data/definitions/639.html

---
<sub>security-posture-check による診断（YYYY-MM-DD、コミット abc1234）。対応項目 R-02</sub>
<!-- security-posture-check controls=AUTHZ-02,AUTHZ-03 -->
````

公開リポジトリで「場所と再現手順を省いた概要だけ」にする場合は、「引っかかった理由」を「詳細は非公開で管理（担当者に確認）」とし、ファイル位置と攻撃方法を書かない。
