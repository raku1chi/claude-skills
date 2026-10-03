# 文化・学術・図書・言語

調査時点：2026年10月。列の意味と「商用」の区分は SKILL.md の「表の読み方」、出典と更新手順は [sources.md](../sources.md) を参照。

本や論文のメタデータは NDLサーチAPI と CiNii Research API、文化財の画像はジャパンサーチ（メタデータは原則CC0）が入口です。商用アプリでは、NDLサーチ・CiNii・J-STAGE の営利利用に申請や相談が要る点に注意します。

| データ（提供元） | 中身 | 形式 | 登録 | 商用 | 使いどころ |
| --- | --- | --- | --- | --- | --- |
| [ジャパンサーチ](https://jpsearch.go.jp/api)（国立国会図書館） | 美術・文化財・図書・公文書など約2,860万件のメタデータ | JSON API、SPARQL | 記載なし | 条件付き（メタデータは原則CC0、画像は作品ごと） | 商用可の画像だけを集めたギャラリー |
| [NDLサーチ API](https://ndlsearch.ndl.go.jp/help/api)（国立国会図書館） | 全国の図書館・機関の書誌と所蔵 | SRU/OpenSearch/OAI-PMH | 営利・収益のある利用は申請 | 条件付き（申請＋提供元ごとの条件） | ISBNから書誌を引く読書記録 |
| [NDLの書誌データ（全国書誌など）](https://www.ndl.go.jp/data/data_service/quickguide)（国立国会図書館） | 国内出版物の書誌（週次更新）と典拠 | API（SRU/SPARQLなど）＋ファイル | 不要（JAPAN/MARC全件のみ申込み） | 可（出典記載） | 新刊通知・蔵書管理のマスタ |
| [次世代デジタルライブラリー](https://lab.ndl.go.jp/service/tsugidigi/)（国立国会図書館） | 著作権の切れた図書約28万点・古典籍約8万点のOCR全文と図版 | REST（JSON/XML）、IIIF | 不要（営利で継続的に使うなら相談） | 条件付き | 明治〜戦前の本の全文・挿絵検索 |
| [NDLデジタルコレクション](https://www.ndl.go.jp/jp/use/reproduction/index.html)（国立国会図書館） | 保護期間が切れたインターネット公開資料の画像 | IIIF | 不要 | 自由利用（商用の明記なし） | 古地図・錦絵の拡大ビューア |
| [NDLOCR-Lite](https://lab.ndl.go.jp/news/2025/2026-02-24/)（国立国会図書館） | GPUなしで動く日本語OCR | OSS（GitHub） | 不要 | 可（CC BY 4.0） | 手持ち資料の端末内テキスト化 |
| [CiNii Research API](https://support.nii.ac.jp/ja/cir/r_opensearch)（国立情報学研究所） | 論文・図書・博士論文・研究データ・研究者 | OpenSearch（JSON-LDなど） | 要（appid） | 条件付き（商用サイトは事前に問い合わせ） | 論文の新着アラート |
| [J-STAGE WebAPI](https://www.jstage.jst.go.jp/static/pages/JstageServices/TAB3/-char/ja)（科学技術振興機構） | 学会誌の巻号・記事の検索 | REST（XML/Atom） | 非営利は不要、営利は申請・承認 | 条件付き（クレジット表示、大量ダウンロード禁止） | 学会誌の新着フィード |
| [KAKEN API](https://support.nii.ac.jp/ja/kaken/api/api_outline)（国立情報学研究所） | 科研費の研究課題と研究者 | OpenSearch（XML） | 要（appid） | 要確認 | 研究テーマから研究者を探す |
| [国立公文書館デジタルアーカイブ](https://www.digital.archives.go.jp/secondary-use)（国立公文書館） | 公文書の目録と画像・動画・音声 | JSON/RDF、SPARQL、IIIF | 不要 | 可（目録はCC0） | 歴史学習アプリで公文書を見せる |
| [日本古典籍データセット](https://codh.rois.ac.jp/pmjt/)（人文学オープンデータ共同利用センター） | 古典籍3,126点の画像・書誌・本文テキスト | ZIP/CSV、IIIF | 不要 | 可（CC BY-SA 4.0） | 古典籍・挿絵のビューア |
| [KMNIST・くずし字データセット](https://codh.rois.ac.jp/kmnist/)（人文学オープンデータ共同利用センター） | くずし字の字形画像（約108万文字）とMNIST形式の学習用データ | ZIP/NumPy | 不要 | 可（CC BY-SA 4.0） | くずし字認識・機械学習の教材 |
| [江戸料理レシピデータセット](https://codh.rois.ac.jp/edo-cooking/)（人文学オープンデータ共同利用センター） | 江戸の料理本の翻刻・現代語訳・現代版レシピ | Web | 不要 | 可（CC BY-SA 4.0） | 江戸料理のレシピアプリ |
| [青空文庫](https://www.aozora.gr.jp/guide/kijyunn.html)（青空文庫） | 著作権が切れた作品などのテキスト、作家別作品一覧CSV | 作品ファイル、CSV | 不要 | 作品ごと（保護期間満了の作品は可） | 縦書きリーダー・朗読アプリ |
| [JMdict/EDICT・KANJIDIC2](https://www.edrdg.org/jmdict/j_jmdict.html)（EDRDG） | 日本語の多言語辞書、漢字情報（毎日更新） | XML | 不要 | 可（CC BY-SA 4.0、アプリ内に帰属表示） | 単語帳・漢字学習アプリ |
| [日本語WordNet](https://github.com/bond-lab/wnja)（NICT・Bond研究室） | 日本語の概念辞書（類義語） | ファイル | 不要 | 可（独自の寛容なライセンス） | 類義語の提案、連想ゲーム |
| [SudachiDict](https://github.com/WorksApplications/SudachiDict)（ワークスアプリケーションズ） | 形態素解析辞書と同義語辞書 | ファイル（GitHub/PyPI） | 不要 | 可（Apache 2.0） | 検索・テキスト解析の前処理 |
| [UniDic](https://clrd.ninjal.ac.jp/unidic/)（国立国語研究所） | 形態素解析辞書（現代語・話し言葉・古文・方言） | ファイル | 不要 | GPL/LGPL/BSDから選択 | 読み仮名の付与、古文学習 |
| [MJ文字情報一覧表](https://moji.or.jp/mojikiban/mjlist/)（文字情報技術促進協議会） | 漢字の字形と各種コード・辞書の対応 | XLSX/XML | 不要 | 可（CC BY-SA 2.1 JP） | 人名・地名の異体字の照合 |
| [Wikipedia日本語版ダンプ](https://ja.wikipedia.org/wiki/Wikipedia:データベースダウンロード)（ウィキメディア財団） | 全記事のXML・抄録・タイトル一覧 | 一括ダウンロード | 不要 | 可（CC BY-SA 4.0） | 用語集・クイズ生成、検索用コーパス |

- 文化遺産オンライン（文化庁）はデータの転用が禁止で、APIもありません。文化財の画像を使うなら、ジャパンサーチで作品ごとのライセンス（CC BYなど）を確かめます。
- CC BY-SA のデータ（CODH、JMdict、Wikipedia、MJ文字情報）は、加工して配るときに同じライセンスを引き継ぎます。アプリのコードと配布するデータは分けて考えます。
- 青空文庫の公式GitHubリポジトリは、2026年10月時点で公開されていません（404）。作品ファイルと一覧CSVは公式サイトから取得します。
- CiNiiは日経BP（2024年12月）とNielsen（2025年2月）の提供データを削除しました。書影や内容紹介に頼らない設計にします。
- 2026年9月、NDLデジタルコレクションの全文検索に古典籍約7.5万点が加わり、計約423万点になりました。
