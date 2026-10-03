# 統計・人口・経済指標

調査時点：2026年10月。列の意味と「商用」の区分は SKILL.md の「表の読み方」、出典と更新手順は [sources.md](../sources.md) を参照。

本命は e-Stat API です。政府統計をほぼ網羅し、appId を登録すれば無料で使えます。ブラウザから直接呼ぶなら、登録不要で CORS に対応した統計ダッシュボードAPIが手軽です。

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [e-Stat API](https://www.e-stat.go.jp/api/)（総務省） | 政府統計の統計表・メタ情報・データ（小地域・メッシュを含む） | REST（XML/JSON/CSV） | 要（ユーザ登録→appId） | 可（クレジット表示必須） | 市区町村別の人口・物価の推移 |
| [統計ダッシュボードAPI](https://dashboard.e-stat.go.jp/static/api)（総務省統計局） | 主要指標 約6,000系列（全国・都道府県・市区町村） | REST（JSON/CSVなど。JSON系はCORS対応） | 不要 | 可（クレジット表示必須） | ブラウザだけで動く指標グラフ |
| [統計GIS（地図で見る統計）](https://www.e-stat.go.jp/gis)（総務省統計局） | 町丁・字などの小地域とメッシュの境界・統計 | Shapefile/GML/KML、CSV | 不要 | 可 | 町丁目別の人口塗り分け地図 |
| [SSDSE（教育用標準データセット）](https://www.nstac.go.jp/use/literacy/ssdse/)（統計センター） | 市区町村×125項目などの整形済みの表（2026年版） | CSV/Excel | 不要 | 可（出典必須） | 地域比較アプリの試作 |
| [日本銀行 時系列統計データ検索サイト API](https://www.stat-search.boj.or.jp/)（日本銀行） | 金利・為替・マネー・物価・短観などの時系列 | REST（JSON/CSV） | 不要 | 条件付き（商用は事前相談、改変不可） | 金利・為替の推移表示 |
| [住民基本台帳に基づく人口・人口動態及び世帯数](https://www.soumu.go.jp/main_sosiki/jichi_gyousei/daityo/jinkou_jinkoudoutai-setaisuu.html)（総務省） | 1月1日時点の市区町村別の人口・世帯数・年齢階級 | Excel（過去分はe-Stat） | 不要 | 可 | 人口増減ランキング |
| [国勢調査（令和7年）](https://www.stat.go.jp/data/kokusei/2025/index.html)（総務省統計局） | 人口・世帯の基本集計 | e-Stat（API／ファイル） | API利用時はappId | 可 | 地域の人口構成の表示 |
| [消費者物価指数](https://www.stat.go.jp/data/cpi/index.html)（総務省統計局） | 全国・東京都区部の月次物価指数（2025年基準） | e-Stat（API／ファイル） | API利用時はappId | 可 | 品目別の物価推移 |
| [家計調査](https://www.stat.go.jp/data/kakei/index.html)（総務省統計局） | 家計収支、都市別の品目別支出・平均価格 | e-Stat（API／ファイル） | API利用時はappId | 可 | 平均的な世帯との支出比較 |
| [人口推計](https://www.stat.go.jp/data/jinsui/index.html)（総務省統計局） | 毎月1日現在の全国・都道府県の人口 | e-Stat（API／ファイル） | API利用時はappId | 可 | 最新人口の表示 |
| [国民経済計算（GDP）](https://www.esri.cao.go.jp/jp/sna/menu.html)・[景気動向指数](https://www.esri.cao.go.jp/jp/stat/di/menu_di.html)（内閣府） | 四半期GDP速報、月次の景気指数 | CSV/Excel | 不要 | 可（規約の明示は要確認） | 景気ダッシュボード |
| [宿泊旅行統計調査](https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html)（観光庁） | 月次の延べ宿泊者数・客室稼働率 | Excel／e-Stat | 不要 | 可（e-Stat経由） | 観光地の季節需要の可視化 |
| [法人企業統計調査](https://www.mof.go.jp/pri/reference/ssc/index.htm)（財務省） | 業種別の売上高・経常利益・設備投資 | e-Stat／PDF | 不要 | 可（e-Stat経由） | 業種別の業績トレンド |
| [統計LOD](https://data.e-stat.go.jp/lodw/)（総務省統計局） | 統計の Linked Open Data | SPARQL | 記載なし | 可（CC BY 4.0） | 統計データの結合・研究 |
| [全国の人流オープンデータ](https://www.geospatial.jp/ckan/dataset/mlit-1km-fromto)（国土交通省） | 1kmメッシュ別の滞在人口（2019〜2021年の月別） | CSV | 要（G空間情報センターにログイン） | 可 | コロナ前後の人出比較 |

- RESAS-API は2025年3月24日に終了しました（新規申込は2024年10月末で停止）。RESAS 自体は画面で見るだけのWebツールとして続いています。アプリに組み込むなら元の統計（e-Statなど）を使います。V-RESAS は2024年3月に公開を終えました。
- 日本銀行のAPIは2026年2月18日に始まりました。APIの留意事項では、クレジット表示、サービスを公開したときの連絡、高頻度アクセスの禁止を求めています。日銀サイトの著作権ルールでは、商用目的の転載・複製は事前相談、無断の改変は不可です。
- e-Stat API、統計ダッシュボードAPI、日銀APIは、アプリ内にクレジット表示が必要です。文言は各公式ページのものを使います。
- 統計表IDは基準改定で変わります。消費者物価指数は2026年8月から2025年基準に移り、2020年基準は2026年12月分で終わります。IDは直書きせず、検索APIで引くか設定ファイルで管理します。
- 人流オープンデータは2019〜2021年で更新が止まっています。令和7年国勢調査の小地域・メッシュ集計は2027年5月までに公表予定で、それまでは令和2年版を使います。
