# ライセンスと利用上の注意

調査時点：2026年10月。列の意味と「商用」の区分は SKILL.md の「表の読み方」、出典と更新手順は [sources.md](sources.md) を参照。

国の新しいデータの多くは公共データ利用規約（PDL1.0、2024年7月5日制定）で、出典を書けば商用でも自由に使えます。注意が要るのは、APIごとのクレジット表示、ODbL・CC BY-SAの継承、気象業務法・測量法、個人に関する公表情報の扱いの4点です。以下は一般的な情報の整理で、法的な助言ではありません。

| 規約・ライセンス | 主な採用先 | 商用 | 出典表記 | 同じ条件での再配布 | 注意点 |
| --- | --- | --- | --- | --- | --- |
| [公共データ利用規約（PDL1.0）](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0) | デジタル庁、気象庁、総務省・統計局、国税庁（法人番号・インボイス）、EDINET、国土数値情報 | 可 | 必須（加工した場合はその旨も） | 不要 | CC BY 4.0と互換。ロゴ・キャラクターは対象外。加工物を国が作ったように見せない |
| 政府標準利用規約（第2.0版） | e-Stat、gBizINFO | 可 | 必須 | 不要 | CC BY 4.0と互換。各サイトはPDL1.0へ移行中 |
| [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) | 東京都、OECD、GeoNamesなど | 可 | 必須（ライセンスへのリンク、改変の有無） | 不要 | 推奨されているように見せない |
| [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.ja) | Wikipedia、JMdict、CODHのデータ | 可 | 必須 | 必要（改変物は同じライセンス） | 加工したデータを配るとライセンスが引き継がれる |
| [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.ja) | Wikidata、GLEIF、OpenAlex | 可 | 不要 | 不要 | 商標や肖像などの権利は別 |
| [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) | OpenStreetMap、Open Food Facts | 可 | 必須 | 必要（派生データベースを公開する場合） | 地図画像などの生成物は自由。ジオコーディング結果の保存は継承の対象外 |
| [CDLA-Permissive-2.0](https://cdla.dev/permissive-2-0/) | Overture Mapsの一部テーマ | 可 | 規定なし（再配布時に規約文を同梱） | 不要 | 解析結果や学習済みモデルには制約なし |

## クレジット表示が必須のAPI

| API | アプリ内に表示する内容（要約） |
| --- | --- |
| [e-Stat API](https://www.e-stat.go.jp/api/api-info/credit)・[統計ダッシュボードAPI](https://dashboard.e-stat.go.jp/static/api) | APIを使っていること、内容を国が保証するものではないこと |
| [法人番号システムWeb-API](https://www.houjin-bangou.nta.go.jp/webapi/riyokiyaku.html)・[インボイス公表システムWeb-API](https://www.invoice-kohyo.nta.go.jp/web-api/riyou_kiyaku.html) | 各APIで取得した情報をもとに作っていること、国税庁が保証するものではないこと（両方使うなら両方を表示） |
| [不動産情報ライブラリAPI](https://www.reinfolib.mlit.go.jp/help/termsOfUse/) | 規約が指定するクレジット |
| [日本銀行 時系列統計API](https://www.stat-search.boj.or.jp/info/api_notice.pdf) | 規約が指定するクレジット（サービス公開時は連絡も） |
| [海しるAPI](https://portal.msil.go.jp/) | 海上保安庁が保証するものではないこと |
| [交通量API](https://www.jartic-open-traffic.org/) | 数値が参考値であること |
| [J-STAGE WebAPI](https://www.jstage.jst.go.jp/static/pages/JstageServices/TAB3/-char/ja) | 「Powered by J-STAGE」とリンク |
| [OpenStreetMap](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines) | 「OpenStreetMap」と表記し、著作権ページへリンク |

文言は各公式ページのものをそのまま使い、APIのクレジットとは別に、取得したデータそのものの出典（PDLなど）も書きます。

## 法令と運用の注意

- **気象業務法**：気象庁の予報をそのまま表示したり解説したりするだけなら許可は不要です。独自の予報は、機械学習を含め方法を問わず予報業務許可が要ります。警報は気象庁しか出せないので、自前の通知を「警報」と名付けません。2023年11月30日施行の改正で、洪水・土砂崩れなど防災に関わる予報は、事前に説明を受けた利用者にしか提供できなくなりました。
- **測量法**：地理院タイルをリアルタイムで読み込むなら、出典の明示だけで足ります。タイルを一括ダウンロードして自前で配信したり、オフライン用に同梱したりする「複製」は承認が要る可能性があるので、国土地理院に確認します。
- **個人に関する公表情報**：インボイスの公表情報を本人の同意なく公表すると、個人情報保護法に触れるおそれがあります。Web-APIで得た情報を目的外で第三者に提供することも規約で禁じられています。官報などの公開情報を集めて地図で公開した「破産者マップ」には、個人情報保護委員会が停止命令と刑事告発を行いました（2022〜2023年）。
- **法令と判決**：法令・告示・判決は著作権法13条で権利の対象外です。ただし民間が作った判例要旨やデータベースは保護されることがあり、提供サイトの利用条件も別に守ります。
- **APIキーの置き場所**：アプリケーションIDやAPIキーはブラウザやスマホアプリに埋め込まず、サーバ側で持ちます。国税庁の両APIはIDの開示を、e-Stat APIはIDの譲渡・貸与を禁じています。
- **スクレイピング**：EDINETとインボイス公表サイトは規約でスクレイピングを禁じています。公式APIや配布データを使い、非公式のエンドポイントは止まる前提でキャッシュと監視を用意します。
- **規約の改正**：2026年9月に法人番号Web-API（9月24日）とインボイスWeb-API（9月21日）の規約が改正されました。インボイスWeb-APIは申請書のメール提出が不要になるなど手続きが変わっており、それより前の解説記事の手順は古い可能性があります。
