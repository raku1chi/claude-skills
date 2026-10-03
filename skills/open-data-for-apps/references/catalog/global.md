# 海外・グローバル

調査時点：2026年10月。列の意味と「商用」の区分は SKILL.md の「表の読み方」、出典と更新手順は [sources.md](../sources.md) を参照。

日本のアプリでもよく使うのは、OpenStreetMap（地図・施設）、Wikidata（多言語の百科データ、CC0）、Open-Meteo（天気。無料版は非商用のみ）です。2025〜2026年は、無料でキー不要だったAPIのキー必須化・有料化・制限強化が相次いでいます。

## 地図・地理

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright)（OSM財団・貢献者） | 世界の道路・建物・施設・行政界（日本分は約2.4GB） | 一括ダウンロード（PBFなど） | 不要 | 可（ODbL：表示と派生DBの継承） | 自前タイル・経路探索・施設検索 |
| [Nominatim](https://operations.osmfoundation.org/policies/nominatim/)（OSM財団） | 住所と座標の相互変換 | REST（JSON） | 不要（User-Agent必須） | 条件付き（1秒1件まで、入力補完・一括取得は禁止） | 単発の住所→座標変換 |
| [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)（公開インスタンス） | 条件を指定したOSMデータの抽出 | REST（JSON/XML） | 不要 | 条件付き（公開インスタンスは軽い利用のみ、商用は自前運用） | 半径1km内のカフェを抽出 |
| [Overture Maps](https://docs.overturemaps.org/getting-data/)（Overture Maps Foundation） | 世界の建物・道路・施設・住所・行政界 | GeoParquet（月次） | 不要 | 可（テーマごとにODbL/CDLA-Permissive-2.0など） | 施設検索、建物単位の分析 |
| [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/)（Natural Earth） | 小縮尺の世界地図用データ（国境・海岸線など） | 一括ダウンロード | 不要 | 可（パブリックドメイン） | 世界地図の国別塗り分け |
| [GeoNames](https://www.geonames.org/export/)（GeoNames） | 2,500万超の地名（座標・人口・別名） | REST（JSON/XML）、日次ダンプ | APIは要（無料ユーザー名） | 可（CC BY 4.0） | 地名サジェスト、都市名→座標 |

## 百科・知識

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [Wikidata](https://www.wikidata.org/wiki/Wikidata:Data_access)（ウィキメディア財団） | 人物・地名・作品・組織などの構造化データ（多言語ラベル） | SPARQL、REST API、ダンプ | 不要（User-Agent必須） | 可（CC0） | 日本語ラベル付きの人物・地名辞書 |
| [Wikipedia API](https://www.mediawiki.org/wiki/API:Etiquette)（ウィキメディア財団） | 百科事典の本文・要約 | REST API、ダンプ | 不要（User-Agent必須） | 可（CC BY-SA：表示と継承） | 用語の概要表示 |
| [Wikimedia Enterprise](https://enterprise.wikimedia.com/pricing/)（ウィキメディア財団） | 記事のスナップショットと更新配信 | API | 要（無料アカウント） | 可（無料枠を超えると有償） | 大量・商用での記事取得 |

## 経済・社会指標

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [World Bank Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)（世界銀行） | 約1.6万の国別時系列指標 | REST（JSON/XML） | 不要 | 可（多くはCC BY 4.0、データセットごとに確認） | 国別のGDP・人口比較 |
| [IMF Data API](https://data.imf.org/en/Resource-Pages/IMF-API)（国際通貨基金） | 世界経済見通し（WEO）などのマクロ統計 | SDMX REST | 多くは不要 | 可（出典表示） | 各国の成長率・インフレ予測 |
| [OECD Data API](https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.STES/DSD_STES@DF_CLI/latest)（OECD） | 加盟国などの経済・社会統計 | SDMX REST | 不要 | 可（CC BY 4.0） | 日本と他国の指標比較 |
| [Our World in Data](https://docs.owid.io/projects/etl/api/chart-api/)（Our World in Data） | CO2・寿命などグラフ単位の整形済み時系列 | Chart API（CSV/JSON） | 不要 | 可（自作分はCC BY 4.0） | 記事・アプリへのグラフ取り込み |
| [WHO GHO OData API](https://www.who.int/data/gho/info/gho-odata-api)（世界保健機関） | 平均寿命などの国別保健指標 | OData（JSON） | 不要 | 条件付き（商用は事前許可） | 健康指標の国際比較 |
| [UN Comtrade](https://uncomtrade.org/docs/subscriptions/)（国連統計部） | 国別・品目別の貿易統計 | REST（JSON） | 要（無料キーで1日500回） | 条件付き（原則内部利用、再配布は許諾・有償） | 社内の輸出入分析 |

## 気象・地球

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [Open-Meteo](https://open-meteo.com/en/terms)（Open-Meteo） | 天気予報と過去の天気（気象庁のGSM/MSMモデルを含む） | REST（JSON） | 無料版は不要、商用はキー | 条件付き（無料版は非商用のみ） | 個人アプリの天気表示 |
| [USGS 地震フィード](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)（米国地質調査所） | 世界の地震（毎分更新） | GeoJSON | 不要 | 可（パブリックドメイン） | 世界の地震マップ・通知 |
| [Copernicus Data Space Ecosystem](https://documentation.dataspace.copernicus.eu/Quotas.html)（欧州委員会・ESA） | Sentinel衛星の画像（全球） | OData/S3/STACなど | 要（無料アカウント） | 可（出典表記） | 災害前後の衛星画像比較 |
| [Landsat](https://www.usgs.gov/landsat-missions/landsat-data-access)（米国地質調査所） | Landsat 1〜9の衛星画像（全球） | API、AWS S3 | 要（アカウント） | 可 | 長期の土地被覆の変化 |
| [NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)（NASA） | 全球の日射量・気温など300超の項目（1981年〜） | REST（JSON/CSV） | 記載なし | 要確認（無料と表示） | 太陽光発電量の試算 |
| [NASA Open APIs](https://api.nasa.gov/)（NASA） | 天文写真（APOD）などNASA系のAPI | REST（JSON） | 要（無料キー） | APIごと | 今日の天文写真 |

## 学術

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [OpenAlex](https://help.openalex.org/api/llm-quick-reference/)（OpenAlex） | 論文・著者・機関・引用 | REST（JSON）、四半期ごとの無料スナップショット | 推奨（無料キーで1日1ドル分まで） | 可（CC0。超過分は従量課金） | 研究者・機関の論文一覧 |
| [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)（Crossref） | DOI付き文献の書誌 | REST（JSON） | 不要（mailto指定で優遇枠） | 可（書誌は自由、抄録は権利者による） | DOIから引用情報を補完 |
| [arXiv API](https://info.arxiv.org/help/api/tou.html)（arXiv） | プレプリントの書誌・抄録 | REST（Atom）、OAI-PMH | 不要 | 可（メタデータはCC0、本文は著者の権利） | 分野別の新着論文通知 |
| [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/)（NCBI） | 医学・生命科学文献の書誌・抄録 | REST（XML/JSON） | 任意（キーで毎秒10件） | 条件付き（抄録に著作権の可能性） | 医学文献検索 |
| [Semantic Scholar API](https://www.semanticscholar.org/product/api)（Ai2） | 約2.1億件の論文・引用・推薦 | REST（JSON） | 任意 | 条件付き（API再販禁止、データのライセンスは混在） | 関連論文のレコメンド |

## 金融・企業

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [GLEIF LEI API](https://www.gleif.org/en/lei-data/gleif-api)（GLEIF） | 法人識別子LEIと法人情報・親子関係（日本は約1.9万件） | REST（JSON）、一括 | 不要 | 可（CC0） | 取引先の名寄せ |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)（米国証券取引委員会） | 米国企業の開示書類とXBRL財務データ | REST（JSON）、一括ZIP | 不要（User-Agentに連絡先） | 可（毎秒10件まで） | 米国株の財務チャート |
| [FRED API](https://fred.stlouisfed.org/docs/api/terms_of_use.html)（セントルイス連邦準備銀行） | 米国中心の経済時系列（金利・雇用・物価） | REST（JSON/XML） | 要（無料キー） | 条件付き（免責表示、第三者の権利がある系列は許諾） | 米金利・失業率ダッシュボード |
| [ECB Data Portal API](https://data.ecb.europa.eu/help/api/data)（欧州中央銀行） | ユーロ参照為替（円を含む）・金利 | SDMX REST（CSV/JSON） | 不要 | 可（出典表示） | ユーロ円レートの推移 |
| [Frankfurter](https://frankfurter.dev/)（オープンソース） | 中央銀行の参照為替レート（1948年〜） | REST（JSON） | 不要 | 規約の記載なし（MITで自前運用可） | 旅行アプリの通貨換算 |

## 生活・文化・交通

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [Open Food Facts](https://openfoodfacts.github.io/openfoodfacts-server/api/)（Open Food Facts） | 食品のバーコード・原材料・栄養（日本は約4.5万件） | REST（JSON）、一括 | 読み取りは不要 | 可（ODbL、画像はCC BY-SA） | バーコードで栄養表示 |
| [MusicBrainz](https://musicbrainz.org/doc/About/Data_License)（MetaBrainz） | アーティスト・作品・曲のメタデータ | REST（JSON/XML）、ダンプ | 不要（User-Agent必須） | 可（コアはCC0、補足データは非商用） | 楽曲メタデータの補完 |
| [Open Library](https://openlibrary.org/developers/api)（Internet Archive） | 書誌と表紙画像 | REST（JSON）、ダンプ | 不要 | 要確認（明示のライセンスなし） | ISBNから書誌・表紙 |
| [Project Gutenberg](https://www.gutenberg.org/policy/robot_access.html)（Project Gutenberg） | パブリックドメインの英語書籍 | ミラー、カタログ（RDF/CSV） | 不要 | 可（商標を外せば自由） | 英語名作リーダー |
| [GBIF API](https://techdocs.gbif.org/en/openapi/)（GBIF） | 生き物の出現記録（日本は約1,776万件） | REST（JSON） | 検索は不要 | レコードごと（CC0/CC BY/CC BY-NC） | 近所の生き物マップ |
| [iNaturalist API](https://www.inaturalist.org/pages/api+recommended+practices)（iNaturalist） | 市民の生き物観察記録と写真 | REST（JSON） | 読み取りは不要 | 条件付き（多くはCC BY-NC） | 観察記録の地図 |
| [Mobility Database](https://mobilitydatabase.org/)（MobilityData） | 世界6,000超のGTFS/GTFS-RT/GBFSフィードの目録 | REST API、CSV | APIは要（無料アカウント） | 目録はCC0、各フィードは事業者の規約 | 都市ごとのGTFS入手先の探索 |
| [OpenSky Network API](https://openskynetwork.github.io/opensky-api/rest.html)（OpenSky Network） | 航空機の現在位置と飛行履歴 | REST（JSON） | 匿名可（OAuth2で増枠） | 不可（研究・非商用のみ） | 個人用の上空の飛行機表示 |

## データを探す場所

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [Google Dataset Search](https://datasetsearch.research.google.com/help)（Google） | 公開データセットの横断検索 | Web | 不要 | データごと | データ探しの最初の一歩 |
| [Registry of Open Data on AWS](https://registry.opendata.aws/)（AWS） | S3上の公開データ（衛星・気象・ゲノムなど） | S3 | 不要 | データごと | クラウド上で大容量データを処理 |
| [Hugging Face Datasets](https://huggingface.co/docs/hub/datasets-overview)（Hugging Face） | 機械学習向けのデータセット | Git/HTTP、ライブラリ | 公開分は任意 | データごと | 学習・評価データの調達 |
| [Kaggle Datasets](https://www.kaggle.com/docs/datasets)（Kaggle） | 投稿型のデータセット | API/CLI | 要 | データごと | 分析用のサンプルデータ |
| [public-apis](https://github.com/public-apis/public-apis)（コミュニティ） | 無料APIのカテゴリ別リスト | GitHub | 不要 | リストはMIT | 使えるAPI探し |
| [data.gov](https://catalog.data.gov/dataset)・[data.europa.eu](https://data.europa.eu/en)・[data.gov.uk](https://www.data.gov.uk/)（米国・EU・英国） | 各国政府の公開データの目録 | カタログ／API | 不要 | データごと | 海外の公的データ探し |

- 無料APIの有料化・制限強化が続いています。REST Countries は2026年4月のv5でAPIキー必須になり、無料プランは非商用のみ（v1〜v4は停止）。OpenAlex は2026年2月に従量課金を導入し、Crossref は2025年12月にレート制限を改定しました。
- OSMの公式タイル・Nominatim・Overpassの公開インスタンスは、重い利用や商用アプリの本番には使えません。自前で立てるか、商用の提供者を使います。
- データのライセンスとAPIの利用規約は別物です。ODbL（OSM、Open Food Facts、Overtureの一部テーマ）は、混ぜて配るデータベースにも同じライセンスが及びます。
- Overture は公開リリースを最大60日で削除し、OpenAlex の無料スナップショットは四半期ごとです。使った版は自前で保存し、取得日を記録します。
- IMF は旧データポータルを廃止して新APIに移りました。WHO もGHO OData APIの置き換えを予告しています（2026年10月時点で旧APIは応答）。
