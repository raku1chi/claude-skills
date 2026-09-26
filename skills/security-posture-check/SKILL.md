---
name: security-posture-check
description: Assess a repository's security posture against authoritative standards (OWASP ASVS 5.0, OWASP Top 10:2025, API Security Top 10, LLM/Agentic Top 10, CWE Top 25, NIST SSDF, OpenSSF Scorecard). Judges each control as implemented / partial / missing / needs-verification with file:line evidence, explains for every finding why it failed and what happens if it is left unfixed (with links to the sources), and produces a prioritized remediation plan that the user can save as a Markdown report or turn into GitHub Issues. Also checks AI-assisted development risks (coding-agent permissions, MCP servers, hallucinated dependencies, LLM features). Use whenever the user asks for a security check, audit, assessment or gap analysis of a codebase, or asks what security measures are missing, including Japanese requests like セキュリティ診断, セキュリティチェック, 脆弱性チェック, 対策状況の確認, 対応方針, Issue化. For reviewing only the diff of a single PR, a diff-focused review fits better.
---

# セキュリティ対策状況チェック

リポジトリのセキュリティ対策を、信頼できる基準に対応づけたチェック項目で**証拠にもとづいて**判定し、「何ができていて、何ができていないか」と「対応方針」を示す。結果はユーザーの選択で、ローカルの Markdown レポートか GitHub Issues にする。

レポート・チャットの言語はユーザーに合わせる（既定は日本語）。

## 原則（客観性を保つために）

この診断の価値は「誰がやっても同じ結論になる」ことにある。次のルールはそのためのもの。

1. **証拠のない判定をしない。** 判定ごとに `path:line`・設定値・コマンド出力のどれかを付ける。「見つからない」ことを根拠にする場合は、何をどこで探したかを書く（例: `src/` で `helmet|Content-Security-Policy` を検索 → 0 件）。
2. **リポジトリから分からないことは「要確認」にする。** ブランチ保護、クラウド・CDN・WAF の設定、組織の運用ルールなどを推測で「未対応」にしない。何をどこで確認すれば判定できるかを添える。
3. **既定値と代替策を確かめてから「未対応」にする。** フレームワークが既定で守っているもの（web-application.md 冒頭の表）、ミドルウェアやゲートウェイでの対策、明示的な無効化の有無を確認する。
4. **パターン一致はヒントにすぎない。** 周辺のコードを読み、外部からの入力が届くか、信頼境界をまたぐか、本番で通る経路かを確かめる。テスト・サンプルのコードは区別する。
5. **基準の ID はチェック項目のファイルから引用する。** ASVS の要件番号などを記憶から作らない。ファイルにない ID を使うのは、原典で確認できた場合だけ。1 つの項目に複数の ID が並んでいるときは、括弧内の説明（例: `1.5.1 (L1: XML 外部実体（XXE）)`）が指摘の内容に合うものだけを引用する。
6. **重大度はルーブリックで決める。** 盛りも甘くもしない。既定値から調整したら理由を書く。
7. **秘密情報の値を出力しない。** レポート・Issue・チャットのどこにも書かない。マスク表記（`AKIA...(20 chars)` のような先頭数文字と長さ）と位置だけを書く。
8. **診断中は何も変更しない。** レポートの書き出しを除き、ファイルを編集しない。外部に通信するツールは実行前にユーザーに伝える。

## 進め方

### 1. 範囲と前提を決める

- **対象**: 既定はカレントのリポジトリ全体。ディレクトリやモノレポの一部が指定されたらそこだけ。
- **深さ**: 既定は該当する全領域。「ざっと」「クイックに」と言われたら GOV・SEC・SCA・CICD だけにする。
- **前提**（重大度に効く）: 公開/非公開リポジトリか、インターネットに公開するサービスか、個人情報・決済情報を扱うか。README やデプロイ設定から推定し、分からなければ仮定としてレポートに明記する。ここでは質問せずに進める（作業を止めてユーザーに聞くのは、最後の出力先の確認だけ）。

### 2. 事実を集める

```bash
python3 <このスキルのディレクトリ>/scripts/collect_signals.py <対象ディレクトリ> --scan-history 300 --output <リポジトリ外の一時ディレクトリ>/signals.md
```

出力（以下 signals）を最初から最後まで読む。出力先はリポジトリの外にする（診断でリポジトリを汚さないため）。これはローカルだけで動き、ファイルを変更せず、秘密情報をマスクして出力する。マニフェスト・ロックファイル、フレームワーク、CI の設定、秘密情報の候補（Git 履歴を含む）、Dockerfile・IaC、AI エージェントの設定、危険なコードパターンと対策の存在を示すコードの位置、ルートの一覧などが得られる。

- Python が使えない場合は、同じ観点を Glob / Grep で確認する（マニフェストとロックファイル、`.github/workflows/`、SECURITY.md、Dockerfile、秘密情報らしき文字列、`.claude/settings.json`・`.mcp.json`）。
- **リポジトリ外の設定**: `gh` が認証済みか、GitHub の MCP ツールがあれば、読み取り系の API で確かめる。公開/非公開（`gh repo view --json visibility`）、ブランチ保護（`gh api repos/{owner}/{repo}/rules/branches/{branch}`）、secret scanning と push protection（`gh api repos/{owner}/{repo} --jq .security_and_analysis`）、private vulnerability reporting（`gh api repos/{owner}/{repo}/private-vulnerability-reporting`）。権限が足りなければ要確認にする。
- **追加のツール**（任意）: signals の「Local security tools available」にあるものだけを使い、インストールはしない。gitleaks・actionlint・hadolint のようにローカルで完結するものは実行してよい。依存関係の脆弱性照会（npm audit、pip-audit、osv-scanner、govulncheck）やルール・DB のダウンロード（semgrep のレジストリルール、trivy）は外部に通信するので、実行前にユーザーに一言確認する。

### 3. 適用する領域を決める

| 条件 | 読むファイル | 領域 |
|---|---|---|
| 常に | [references/controls/repo-and-supply-chain.md](references/controls/repo-and-supply-chain.md) | GOV 開発プロセス / SEC シークレット / SCA 依存関係 / CICD |
| HTTP サーバー・API・SSR がある | [references/controls/web-application.md](references/controls/web-application.md) | AUTH / SESS / AUTHZ / INJ / WEB / CRY / DATA・CFG・API |
| Dockerfile・compose・Kubernetes・IaC がある | [references/controls/containers-and-infra.md](references/controls/containers-and-infra.md) | CTR / IAC |
| LLM を呼ぶ機能、または AI エージェントの設定・指示ファイルがある | [references/controls/ai-and-llm.md](references/controls/ai-and-llm.md) | LLM / AIDEV |

HTTP サーバーのない CLI やライブラリでは、web-application.md のうち INJ（入力処理）・CRY（暗号）・WEB-04（TLS 検証）だけを、「誰が入力を与えるか」という信頼境界を考えたうえで適用する。

領域ごと当てはまらない場合（例: LLM 機能がない、コンテナの定義がない）は、項目を 1 つずつ ➖ にせず、**領域単位で 1 行**に理由を書く（例: 「LLM: 対象外 — LLM を呼ぶコードなし」）。スコアカードや件数には、適用した項目だけを数える。領域の中で一部の項目だけ当てはまらない場合は、その項目を ➖ にして理由を書く。

### 4. 項目ごとに判定する

チェック項目ファイルの各項目について、「確認方法」に従って証拠を集め、「判定」の基準で状態を決める。

| 状態 | 意味 | 必要な証拠 |
|---|---|---|
| ✅ 対応済み | 判定基準を満たす | 実装箇所・設定 |
| 🟡 一部対応 | 一部の箇所・条件でだけ満たす | 満たしている箇所と欠けている箇所 |
| ❌ 未対応 | 必要なのに満たしていない | 問題の箇所、または探索の範囲と結果 |
| ❓ 要確認 | リポジトリからは判断できない | 何を確認すれば判定できるか |
| ➖ 対象外 | 前提となる機能がない | その理由 |

確信度も付ける: **高**（コード・設定を直接読んで確認）/ **中**（強い間接証拠）/ **低**（パターン一致や推定のみ）。確信度が低いまま ❌ にしない。コードを読んで確かめるか、❓ にする。

**チェック項目の外も探す。** チェックリストは見落としを防ぐためのもので、上限ではない。signals の entrypoints・auth-related files・LLM を呼ぶファイルから、主要な処理を入口から最後まで読む。特に、外部から来る値がファイルパス・URL・コマンド・SQL・テンプレート・デシリアライズ・リダイレクト先に届く経路、エラー時の分岐（例外で検証が飛ばされないか）、ダウンロードや更新の処理を追う。チェック項目にない問題を見つけたら、最も近い項目に「個別の指摘」として紐づけ、CWE を付ける。

**安全に確かめられるなら小さく再現してよい。** 判定の確信度を上げるため、次の条件を満たす範囲でローカルに再現してよい: 外部と通信しない、リポジトリの外の一時ディレクトリで行う、無害な入力を使う、秘密情報を使わない、リポジトリのファイルを変更しない。何をどう確かめたかをレポートに書く。条件を満たせないなら、コードを読んだ根拠で判定し、確信度にその旨を反映する。

### 5. 重大度と優先度を付ける

チェック項目ファイルの「重大度」を出発点にして、次の目安で確定する。

| 重大度 | 目安 |
|---|---|
| Critical | 認証なし、または簡単な操作で重大な被害が出る（任意コード実行、全データの漏えい・改ざん、有効な本番資格情報の露出） |
| High | 条件付き（ログイン済みの利用者など）で重大な被害が出る。または重大な被害を防ぐ主要な対策が欠けている |
| Medium | 被害が限定的、または多層防御のうち一層が欠けている |
| Low | ベストプラクティスからの逸脱で、直接悪用するのは難しい |

文脈による調整（理由を必ず書く）: 上げる要因は、公開リポジトリ、インターネット公開、個人情報・決済、本番で使われている経路。下げる要因は、内部専用、試作段階、確認できた代替策。

同じ原因が複数の項目に当たることは多い（例: 1 行の SQL 組み立てが INJ-01 と LLM-02 の両方に当たる）。項目ごとの判定はそのまま残しつつ、**総評と重大度の内訳は原因（＝対応項目）単位で数える**。項目単位で数えると深刻さが水増しされて見えるため。

優先度と工数:

| 優先度 | 基準 |
|---|---|
| P1 今すぐ（数日以内） | Critical と、悪用が容易な High。漏えいした秘密情報のローテーションは常に P1 |
| P2 次の開発サイクル | 残りの High と、効果の大きい Medium |
| P3 計画的に | 残りの Medium と Low、プロセスの改善 |

工数は S（設定変更・数行。1 時間程度）/ M（1 日程度）/ L（設計変更・複数日）。優先度が高く工数 S のものは「すぐできる改善」として目立たせる。

### 6. 対応方針をまとめる

指摘を**対応項目**（R-01, R-02, …）にまとめる。1 つの対応で複数のチェック項目が解決することが多い（例: helmet の導入で WEB-01 の大部分が解決）。各対応項目には次を書く:

- タイトル、優先度、重大度、工数、関連するチェック ID
- 目的（何のリスクを消すのか）
- 手順: **このコードベースに即して**書く（ファイル名・関数名・設定例）。一般論だけにしない
- 完了条件: どう確かめれば完了か（テスト、設定の確認コマンドなど）
- 参考リンク

### 7. 結果を伝える

チャットでは要点を簡潔に伝える。詳細はレポートや Issue に書く。

1. 総評（3〜5 行。最大のリスクと、できている点の両方）
2. スコアカード（領域ごとの ✅🟡❌❓➖ の件数）
3. P1 の対応項目
4. 重要な指摘の説明。**指摘ごとに必ず次の 4 点をそろえる**:
   - どのチェック項目か（ID と名前）
   - なぜ引っかかったか（理由と証拠の `path:line`）
   - 放置すると何が起きるか（チェック項目の「リスク」を、このプロジェクトの状況に合わせて具体的に）
   - 根拠と参考のリンク（完全な URL）
5. 要確認事項の一覧

### レポートの長さ

レポートは最後まで読まれてこそ役に立つ。詳しさは保ちつつ、同じことを二度書かない。

- 指摘の詳細（チェック項目ごと）は ❌ と 🟡 のうち Medium 以上だけ。1 項目は「理由・リスク・根拠・対応先」の 4 行程度にし、根拠のリンクは最も具体的なもの 3 つまで。
- Low の項目、✅、❓、➖ は表の 1 行にまとめる（Low の行にも理由とリンクを 1 つ入れる）。
- 対応項目（R-xx）には手順と完了条件を書き、証拠やリスクの説明は繰り返さない（関連するチェック ID を示せば足りる）。

### 8. 出力先を確認して書き出す

依頼の時点で出力先が指定されていなければ、結果を伝えたあとでユーザーに選んでもらう（AskUserQuestion ツールがあれば使う）。

- **ローカルの Markdown レポート**: 既定のパスは `security-reports/YYYY-MM-DD-security-posture.md`。書式は [references/report-template.md](references/report-template.md)。公開リポジトリなら、未修正の脆弱性を書いたレポートをコミットすると公表と同じになることを伝え、`.gitignore` への追加かリポジトリ外への保存を提案する。
- **GitHub Issues**: 対応項目ごとに 1 件（まとめの Issue はユーザーが望んだ場合だけ）。手順・重複の防止・公開リポジトリでの注意は [references/github-issues.md](references/github-issues.md) に従う。**作成前に、作る Issue の一覧を見せて了承をもらう。**
- **両方** / **今回はチャットだけ**

### 再診断（前回との比較）

`security-reports/` に前回のレポートがあれば、付録 A の判定一覧どうしを比べ、「改善した項目」「悪化した項目」「新しく見つかった項目」をレポートの冒頭に載せる。以前作った Issue の状態も分かる範囲で添える。

## 診断の限界（レポートに必ず書く）

- リポジトリの静的な調査であり、ペネトレーションテストや本番環境の検査ではない。
- 見つからなかったことは、脆弱性がないことの証明ではない。
- ASVS の全要件（5.0.0 で 345 件）ではなく主要な項目を抜粋して評価しており、ASVS への準拠を示すものではない。
- 診断日、対象のコミット、使ったツールとそのバージョンを明記する。

## ファイル

- `scripts/collect_signals.py` — 事実収集（ローカル専用・読み取り専用・秘密情報はマスク）。`--help` で使い方
- `references/controls/*.md` — チェック項目（判定基準・重大度・リスク・対応方針・根拠リンク）
- `references/report-template.md` — レポートと付録の書式
- `references/github-issues.md` — Issue 化の手順と Issue 本文の書式
- `references/sources.md` — 使っている基準の版・公開日・URL と、基準を更新するときの手順
