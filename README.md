# claude-skills

自作の [Claude Skills](https://code.claude.com/docs/en/skills) 置き場。

## スキル一覧

| スキル | できること |
|---|---|
| [security-posture-check](skills/security-posture-check/) | リポジトリのセキュリティ対策を OWASP ASVS 5.0・OWASP Top 10:2025・NIST SSDF などの基準に照らして証拠ベースで診断し、「できていること／できていないこと」と優先度付きの対応方針を出す。結果は Markdown レポートか GitHub Issues にできる |
| [open-data-for-apps](skills/open-data-for-apps/) | アプリのアイデア出しと、作りたいアプリに使えるデータ探しを手伝う。日本の公的機関を中心に海外も含むオープンデータ・公開 API 約 190 件の調査（2026 年 10 月時点）をもとに、登録の要否・商用利用の可否と、提供終了やライセンス・法令の注意点まで示す |

## インストール

### プラグインとして入れる（おすすめ）

このリポジトリは Claude Code のプラグインマーケットプレイスになっている。Claude Code のセッションで次を実行する。

```
/plugin marketplace add raku1chi/claude-skills
/plugin install security-posture-check@raku1chi-skills
/plugin install open-data-for-apps@raku1chi-skills
```

スキルごとに別のプラグインになっているので、使うものだけを入れればよい。この節の以降の例は security-posture-check なので、ほかのスキルは名前を置き換える。

`/plugin install` を実行するとプラグインの詳細が開くので、使う範囲（スコープ）を選んでインストールする。

- **user**: 自分の、すべてのプロジェクトで使う
- **project**: そのリポジトリで作業する全員で使う（下の「チームで使う」を参照）
- **local**: 自分だけが、そのリポジトリでだけ使う

シェルからも入れられる（既定は user。`--scope project` か `--scope local` を付けると変えられる）。

```bash
claude plugin marketplace add raku1chi/claude-skills
claude plugin install security-posture-check@raku1chi-skills
```

#### チームで使う

対象のリポジトリで次を実行し、書き換わった `.claude/settings.json` をコミットする。マーケットプレイスの登録とプラグインの有効化がどちらもこのファイルに入る。

```bash
claude plugin marketplace add raku1chi/claude-skills --scope project
claude plugin install security-posture-check@raku1chi-skills --scope project
```

ほかのメンバーは、そのリポジトリで Claude Code を開き、フォルダーを信頼すれば使える。使えない場合は、上の `claude plugin install` を一度実行する。

#### 更新

自分で追加したマーケットプレイスは、既定では自動更新されない。`/plugin` の **Marketplaces** タブで `raku1chi-skills` を選び、**Enable auto-update** を選ぶと自動で更新される。手動で更新するときは次を実行する。

```bash
claude plugin update security-posture-check@raku1chi-skills
```

更新した内容は、次のセッションか `/reload-plugins` の実行後に反映される。

### スキルとして直接置く

マーケットプレイスを使わずに、スキルのディレクトリを Claude Code のスキル置き場に置いてもよい。

#### すべてのプロジェクトで使う

```bash
git clone https://github.com/raku1chi/claude-skills.git ~/src/claude-skills
mkdir -p ~/.claude/skills
ln -s ~/src/claude-skills/skills/security-posture-check ~/.claude/skills/security-posture-check
```

シンボリックリンクにしておくと、`git pull` するだけで更新が反映される。

#### 特定のプロジェクトだけで使う

```bash
mkdir -p .claude/skills
cp -r ~/src/claude-skills/skills/security-posture-check .claude/skills/
```

## 使い方

Claude Code で次のように頼むと、スキルが使われる（`/security-posture-check` のようにスキル名で明示的に呼び出してもよい。プラグインとして入れた場合の正式な名前は `/security-posture-check:security-posture-check` の形）。

### security-posture-check

- 「このリポジトリのセキュリティ診断をして、対応方針を出して」
- 「公開前にセキュリティで足りないところを洗い出して。結果は security-reports/ に保存して」
- 「AI 機能と Claude Code の設定も含めてセキュリティチェックして。対応が必要なものは Issue にしたい」

診断結果をチャットで示したあと、出力先（ローカルの Markdown レポート / GitHub Issues / 両方）を確認してから書き出す。Issue を作る前には、作成予定の一覧を見せて了承を取る。

#### 必要なもの

- Python 3.8 以上（事実収集スクリプト用。標準ライブラリのみ。無い場合は Claude が手作業で同じ観点を確認する）
- Issue を作る場合: 認証済みの `gh` CLI、または GitHub の MCP ツール（どちらもなければ Issue の下書きをファイルに書き出す）
- 任意: gitleaks、semgrep、trivy などのセキュリティツール（入っていれば使う。インストールはしない）

### open-data-for-apps

- 「オープンデータを使った防災アプリのアイデアを 5 つ出して。商用で出したい」
- 「近くの開いている小児科を探すアプリを作りたい。使えるデータは？」
- 「e-Stat と何を組み合わせると面白いアプリになる？」
- 「OpenStreetMap のデータは商用のアプリで使える？何を表示すればいい？」

アイデア出しでは、案ごとに使うデータとそのつなぎ方を、データ探しでは機能ごとの本命と代わりの候補を、登録の要否・商用利用の可否・注意点つきで返す。気になる案を選ぶと、データの取り方や申請の段取りまで具体化する。

カタログは調査時点（2026 年 10 月）の情報。データ探しでは、Web を見られる環境なら本命のデータの公式ページで最新の規約を確かめるが、本番で使う前には自分でも公式ページの規約を確かめること。カタログを新しくする手順は [references/sources.md](skills/open-data-for-apps/references/sources.md) にある。

#### 必要なもの

- 特になし（Web の検索・取得ができると、調査時点より新しい情報を確かめられる）

## ディレクトリ構成

```
.claude-plugin/
└── marketplace.json    # マーケットプレイスの定義（スキル 1 つにつき 1 エントリ）
skills/
└── <skill-name>/
    ├── SKILL.md        # スキル本体（frontmatter の name / description と手順）
    ├── scripts/        # スキルが実行するスクリプト
    └── references/     # 必要なときだけ読み込む参考資料
```

### スキルを追加するとき

`.claude-plugin/marketplace.json` の `plugins` に次のエントリを足し、`claude plugin validate .` で確かめる。`skills` に挙げたスキルだけがそのプラグインに入る。

```json
{
  "name": "<skill-name>",
  "description": "<プラグイン一覧に出す説明>",
  "source": "./",
  "strict": false,
  "skills": ["./skills/<skill-name>"]
}
```

`version` は書かない。書かなければコミットごとに更新が届く。書くと、変更のたびに値を上げない限り利用者に更新が届かない。
