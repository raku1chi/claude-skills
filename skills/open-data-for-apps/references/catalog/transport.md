# 交通・移動

調査時点：2026年10月。列の意味と「商用」の区分は SKILL.md の「表の読み方」、出典と更新手順は [sources.md](../sources.md) を参照。

鉄道・バスのリアルタイム情報は公共交通オープンデータセンター（ODPT、無料登録）、地方のバスはGTFSデータリポジトリ（380超の事業者・市町村）が入口です。2026年3月にGTFS-JP第4.0版が出て、鉄道・旅客船・デマンド交通・シェアサイクルまで同じ仕様で扱えるようになりました。

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [公共交通オープンデータセンター（ODPT）](https://www.odpt.org/overview/)（公共交通オープンデータ協議会） | 鉄道・バス・航空・フェリー・シェアサイクルの時刻表、運行情報、車両位置、フライト発着 | REST（JSON-LD）、GTFS/GTFS-RT、GBFS | 要（無料のユーザ登録） | データごと（CC BY 4.0は可、ほかは規約確認） | 乗換案内、遅延のプッシュ通知 |
| [ODPT 登録不要API](https://api-public.odpt.org/api/v4/odpt:TrainInformation?odpt:operator=odpt.Operator:Toei)（公共交通オープンデータ協議会） | 都営の運行情報、シェアサイクルのGBFSなど一部 | REST（JSON-LD）、GBFS | 不要 | データごと | ログイン不要の運行情報ウィジェット |
| [東京都交通局のデータ（ODPT経由）](https://ckan.odpt.org/dataset?organization=toei)（東京都交通局） | 都営地下鉄・都営バスの時刻表、車両位置、運行情報、運賃、乗降人員 | JSON、GTFS、GTFS-RT | 要（ODPT登録） | 可（CC BY 4.0） | 都営線の接近表示、到着予測 |
| [JAL・ANAのフライト情報（ODPT経由）](https://ckan.odpt.org/dataset?q=%E3%83%95%E3%83%A9%E3%82%A4%E3%83%88)（日本航空・全日本空輸） | フライト時刻表、出発・到着のリアルタイム情報 | JSON | 要（ODPT登録） | 規約確認 | 遅延に合わせた空港アクセス案内 |
| [GTFSデータリポジトリ](https://gtfs-data.jp/)（日本バス情報協会） | 380超のバス事業者・市町村のGTFS、フィード一覧API | GTFS/GTFS-RT、REST（JSON） | 不要 | フィードごと（CC BY 4.0が中心） | 地方バスの時刻表・経路検索 |
| [ドコモ・バイクシェア GBFS](https://ckan.odpt.org/dataset?res_format=GBFS)（ドコモ・バイクシェア） | ポートの位置と貸出可能台数 | GBFS（JSON） | 不要 | 可（CC BY 4.0） | 空きポートの地図表示 |
| [HELLO CYCLING GBFS](https://api-public.odpt.org/api/v4/gbfs/hellocycling/gbfs.json)（OpenStreet） | ステーションの位置・空き状況・車種 | GBFS（JSON） | 不要 | 可（CC BY 4.0・ODbLなどを列記） | シェアサイクルの横断検索 |
| [国土数値情報 鉄道・駅別乗降客数・バス停](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2024.html)（国土交通省） | 路線形状と駅位置、駅ごとの1日乗降客数（2024年度まで）、バス停・バス路線 | GML/Shapefile/GeoJSON | 不要 | 可（CC BY 4.0。旧版の一部は非商用） | 路線図の描画、駅の賑わい比較 |
| [交通量API](https://www.jartic-open-traffic.org/)（国土交通省） | 直轄国道 約2,600地点の方向別・車種別交通量（5分・1時間） | WFS（GeoJSON/CSV） | 規約への同意が必要 | 条件付き（参考値である旨の表示義務） | 国道の混雑推移ダッシュボード |
| [JARTIC オープンデータ](https://www.jartic.or.jp/service/opendata/)（日本道路交通情報センター） | 交通規制（一方通行・一時停止など）、断面交通量 | CSV（毎月更新） | 記載なし | 可（出典記載） | 徒歩・自転車ナビへの交通規制の反映 |
| [道路交通センサス](https://www.mlit.go.jp/road/census/r3/index.html)（国土交通省） | 区間別・時間帯別の交通量、旅行速度（2021年度調査） | CSV/Excel | 不要 | 可（PDL1.0） | 出店・物流ルートの需要推計 |
| [交通事故統計オープンデータ](https://www.npa.go.jp/publications/statistics/koutsuu/opendata/index_opendata.html)（警察庁） | 2019〜2025年の人身事故1件ごとの日時・緯度経度・天候・道路形状など | CSV | 不要 | 可（PDL1.0） | 通学路・自転車ルートの危険地点マップ |

- ODPTのライセンスはデータごとに違います。都営などCC BY 4.0のものは商用可ですが、JR東日本や羽田国際線などは公共交通オープンデータチャレンジ（応募は2026年10月1日〜2027年1月11日）限定で、通年で使えるとは限りません。「基本ライセンス」の条件は開発者サイトの規約で確かめてください（本調査では本文を確認できていません）。
- 交通量APIと道路データプラットフォーム（xROAD）は2025年5月12日に公開されたばかりのサービスです。
- 京都・大津のシェアサイクル kotobike は2026年3月末で終了し、GBFSも止まっています。
- 民間の駅データ.jp は無料APIを2020年に止め、今はCSVの配布です。駅の位置だけなら国土数値情報で足ります。
- フェリー・旅客船にも標準フォーマット（Ver.5、2025年4月）があり、ODPTで航路データの公開が増えています。
