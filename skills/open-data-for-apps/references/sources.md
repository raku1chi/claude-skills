# 出典と更新の手順

## 出典

このスキルのカタログ（`catalog/*.md`、`licenses-and-legal.md`、`idea-patterns.md` の「組み合わせの例」）は、調査資料「アプリ開発に使えるオープンデータ総覧」（2026-10-03 作成、確認時点 2026 年 10 月）の本文を、分野ごとのファイルに分けたもの。文章と表は資料のまま。各データのリンク先が一次情報（公式ページ）。

- **対象**: 公的機関のオープンデータ、オープンライセンスで公開された共同編集データ（OpenStreetMap、Wikidata など）、無料で使える公的 API。有料の商用データは含まない
- **件数**: 13 分野・190 件（自治体標準オープンデータセットは 2 つの分野に載っている）
- **「商用」の列**: 規約の要約。提供終了や仕様変更が多い分野なので、本番で使う前に公式ページの最新の規約を確かめる

SKILL.md の「データの地図」「よくある落とし穴」と `idea-patterns.md` の「共通キー」「発想の型」「アイデアを広げる問い」は、このカタログの要点に、データをつなぐための一般的な知識（コードの桁など）を足してまとめたもの。

## 元の資料から直したところ

| 日付 | 箇所 | 内容 |
|---|---|---|
| 2026-10-03 | catalog/weather-disaster.md の指定緊急避難場所データ | リンクが国土地理院のトップへ転送されていた（`bosaichiri`）ので、`https://www.gsi.go.jp/bousaichiri/hinanbasho.html` に直した |

## 更新するとき

1. 元の調査資料を更新したら、Markdown で書き出す。
2. `## ` の見出しごとに、本文を次の表のファイルへそのまま移す。`### ` は `## ` に 1 段上げる。各ファイルは 1 行目を `# 見出し`、次の段落を調査時点の注記にする。

| 調査資料の見出し | 移す先 |
|---|---|
| この資料の見方 | SKILL.md の「表の読み方」（列の定義が変わったときだけ） |
| データを探す入口（横断カタログ） | catalog/portals.md |
| 統計・人口・経済指標 | catalog/statistics.md |
| 地図・住所・地理空間 | catalog/maps-addresses.md |
| 不動産・土地・まちづくり | catalog/real-estate.md |
| 交通・移動 | catalog/transport.md |
| 気象・防災 | catalog/weather-disaster.md |
| 環境・農林水産・宇宙 | catalog/environment-agri-space.md |
| 法令・行政・政治 | catalog/law-government.md |
| 企業・金融・雇用 | catalog/business-finance-jobs.md |
| 医療・福祉・食品 | catalog/health-welfare-food.md |
| 暮らし・教育・自治体データ | catalog/life-education-local.md |
| 文化・学術・図書・言語 | catalog/culture-research-language.md |
| 海外・グローバル | catalog/global.md |
| ライセンスと利用上の注意 | licenses-and-legal.md |
| 組み合わせアイデア | idea-patterns.md の「組み合わせの例」 |

3. 上の「元の資料から直したところ」が、新しい資料にも入っているか確かめる。入っていなければ同じように直す。
4. 分野が増えたらファイルを足し、SKILL.md の「データの地図」とこの表に行を足す。
5. 注記で終了・移行・規約の変更が増えたら、SKILL.md の「よくある落とし穴」を直す。
6. 調査時点を書いている箇所を新しい時点にそろえる: 各ファイルの注記、SKILL.md（frontmatter の description、冒頭、原則、公式ページで確かめるとき、出力の形）、この節の件数、リポジトリの README.md と marketplace.json の説明。
7. リンクが開けるか確かめる（例: `curl -s -o /dev/null -w "%{http_code}" <URL>`）。サイトによってはボット対策や古い TLS の設定で curl が通らないので、開けなかったものはブラウザで確かめる。
