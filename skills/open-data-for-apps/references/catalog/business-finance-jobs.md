# 企業・金融・雇用

調査時点：2026年10月。列の意味と「商用」の区分は SKILL.md の「表の読み方」、出典と更新手順は [sources.md](../sources.md) を参照。

企業データの土台は法人番号（国税庁）で、全件CSVなら登録なしで使えます。そこに gBizINFO（補助金・調達・職場情報）と EDINET API（有価証券報告書のXBRL・CSV）をつなぐと、企業プロフィールが作れます。株価の J-Quants は規約で第三者への提供が禁じられており、公開するアプリには使えません。

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [法人番号 基本3情報ダウンロード](https://www.houjin-bangou.nta.go.jp/download/)（国税庁） | 全法人の法人番号・商号・所在地（全件は月次、差分は日次） | CSV/XML | 不要 | 可（PDL1.0） | 全法人マスタの自前DB |
| [法人番号公表サイト Web-API](https://www.houjin-bangou.nta.go.jp/webapi/)（国税庁） | 法人番号・商号・所在地の検索と変更の差分 | REST（CSV/XML） | 要（アプリケーションID、2週間〜1か月） | 可（クレジット表示必須） | 社名・住所の自動補完、名寄せ |
| [インボイス公表サイト 公表情報ダウンロード](https://www.invoice-kohyo.nta.go.jp/download/index.html)（国税庁） | 適格請求書発行事業者の全件と差分 | CSV/XML/JSON | 不要 | 条件付き（個人の情報の扱いに注意） | 会計ソフトでの一括照合 |
| [インボイス公表サイト Web-API](https://www.invoice-kohyo.nta.go.jp/web-api/index.html)（国税庁） | 登録番号の有効性・登録日・取消日・名称 | REST（CSV/XML/JSON） | 要（アプリケーションID） | 条件付き（運営方針の目的の範囲内） | 受け取った請求書の登録番号チェック |
| [gBizINFO API](https://content.info.gbiz.go.jp/api/index.html)（経済産業省） | 法人の届出・認定、表彰、補助金、調達、財務、特許、職場情報 | REST（JSON）、一括ダウンロード | 要（利用申請→トークン） | 可（申告した目的の範囲内） | 補助金・受注実績つきの企業プロフィール |
| [EDINET API v2](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0110.html)（金融庁） | 有価証券報告書などの書類一覧と本体（過去10年） | REST（JSON）＋XBRL/CSV/PDF | 要（アカウント＋多要素認証→APIキー） | 可（PDL1.0） | 有報から財務・従業員データを抽出 |
| [J-Quants API](https://jpx-jquants.com/ja)（JPX総研） | 株価・財務サマリー・銘柄一覧（無料プランは12週遅延・2年分） | REST（JSON） | 要（無料登録→APIキー） | 不可（第三者への提供は規約で禁止） | 自分専用の銘柄分析・バックテスト |
| [しょくばらぼ](https://shokuba.mhlw.go.jp/)（厚生労働省） | 約15万社の職場情報（残業・有休など） | CSV（Web APIは一時停止中） | 要確認 | 要確認 | 働きやすさで企業を比較 |
| [女性の活躍推進企業データベース オープンデータ](https://positive-ryouritsu.mhlw.go.jp/positivedb/opendata/index.html)（厚生労働省） | 女性管理職比率・男女の賃金差異など（法人番号付き） | CSV | 不要 | 要確認 | 男女の賃金差異の比較 |
| [job tag 職業情報ダウンロード](https://shigoto.mhlw.go.jp/User/download)（厚生労働省） | 職業ごとの仕事内容・必要スキル・数値データ | CSV/Excel | 不要 | 二次利用可（出典必須、商用の明記なし） | 職種レコメンド、キャリア診断 |
| [ハローワーク求人・求職情報提供サービス](https://www.hellowork.mhlw.go.jp/provide/provide_top.html)（厚生労働省） | ハローワークの求人（420項目超） | REST（XML） | 要（職業紹介事業者・自治体などに限定） | 対象者のみ | 職業紹介事業者の求人掲載 |
| [地域別最低賃金](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/roudoukijun/minimumichiran/)（厚生労働省） | 都道府県別の最低賃金と改定履歴 | PDF/Excel | 不要 | 要確認 | 給与計算時の最低賃金チェック |
| [賃金構造基本統計調査](https://www.e-stat.go.jp/statistics/00450091)（厚生労働省） | 職種・産業・企業規模・年齢別の賃金 | e-Stat（API/ファイル） | API利用時はappId | 可（e-Stat経由） | 職種別の年収相場 |

- インボイスWeb-APIの規約は、運営方針の目的以外での第三者提供を禁じています（2026年9月21日の改正では、申請書のメール提出が不要になりました）。個人事業者の情報を名簿や検索サービスにするのは避けます。
- 法人番号とインボイスのWeb-APIは、アプリケーションIDの発行に2週間〜1か月かかり、アプリ内に所定のクレジット表示が要ります。
- J-Quants（2026年6月1日にV1が終了し、V2はAPIキー方式）とJPXサイトのデータは、アプリで配信するには別の許諾・契約が要ります。適時開示（TDnet）にも無料のAPIはありません。
- EDINET API v1は2024年3月で終わり、v2（APIキー必須）だけになりました。gBizINFOは事業所情報の期間指定APIを2026年7月31日に止めています。
- しょくばらぼのWeb APIは一時停止中で、再開時期は未定です。女性活躍DBのオープンデータは、最終更新が2025年7月と古めです。
