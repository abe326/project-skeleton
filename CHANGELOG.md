# CHANGELOG

スケルトンの版ごとの変更と、**既存プロジェクトへの適用方法**を残す。
版は `VERSION` と一致させる(`python3 scripts/check.py` が照合する)。

書式:

```
## [x.y.z] - YYYY-MM-DD
### 変更
- …
### 既存プロジェクトへの適用
- `python3 <skeleton>/scripts/init.py <既存パス> --merge` で追従する（記録が無い案件は `--name "<表示名>"` も）
- 案件ごとに判断が要る手順だけをここに書く。どの案件でも同じ結果になる定型の手順は `scripts/migrations.json` に書く
  （init.py --merge が自動で流し、この節は対象の版の分だけ抜き出して出す）
```

## [1.6.1] - 2026-10-26

v1.6.0 を取り下げる。CLAUDE.md の節は特定の環境の置き場を前提にしており、どの環境でも使える汎用の一式に入れるものではなかった。
中身は v1.5.0 に戻した（v1.6.0 のコミットを戻すコミット。履歴は書き換えていない）。

### 変更
- 削除: v1.6.0 で足した CLAUDE.md §1 の節と、それに付けた仕組み（`init.py` の節を二重にしない処理・migrations の `replace` の
  `unless` と v1.6.0 の移行・テスト・案件の `README.md` の行・`draft-from-existing` スキルの行・新規生成の案内の語）

### 既存プロジェクトへの適用
- v1.5.0 以前の案件: `--merge` で v1.6.1 にする。何も足されない（v1.6.0 の移行は流れない）
- v1.6.0 に上げた案件: `--merge` で、手を入れていない節は自動で消える。節に書き足していれば CLAUDE.md は衝突として一覧に出る。
  残すか消すかは案件で決め、`.work/一時/YYYYMMDD_skeleton-update/CLAUDE.md` を見て取り込んだら `--merge --resolved` で記録する
  （残しても、次の更新で差し込み直されることはない）

## [1.6.0] - 2026-10-25

取り下げ（v1.6.1 で戻した）。

## [1.5.0] - 2026-09-26

指示しなくても追従し、揃う。類似ツール（Copier・cruft・Nx migrate・Backlog.md・Agent OS・Kiro ほか 23 件）を調べ、
「AI に明示的に指示できない人でも、指示しなくてもいい感じにやってくれる」に合う 7 つを入れた。

### 変更
- 追加: **生成時の記録 `.claude/skeleton.json`**（init.py が書く）。版・スケルトンのコミット・生成時の値・入れたファイルの
  元の内容の sha。`--merge` は記録があれば `--name` を省ける
- 追加: **`--merge` の追従**。手を入れていないファイルは自動で新しい版にする。仕組み（`.claude/`・`scripts/`・タスク管理の
  `.py`・`index.html`）と `CLAUDE.md` は、手を入れていても `git merge-file` の 3-way で混ぜる。概要 HTML は build.py の欄を外して混ぜ、
  欄は案件のものを戻す。書き換える前の中身は `.work/_bk/YYYYMMDD_skeleton-vX.Y.Z/`。衝突したものと、手を入れた内容のファイルは
  書かずに一覧にし、新しい版を `.work/一時/YYYYMMDD_skeleton-update/` に置く（取り込んだら `--merge --resolved` で記録）。
  template から無くなった仕組みは、手を入れていなければ `.work/_bk/` へ片付ける。案件が消したファイルは作り直さない
- 追加: **記録の無い案件への後付け**。CLAUDE.md 1 行目の刻印とスケルトンの git 履歴から元の内容を作り直す。スケルトンに git が無い
  （`--copy` 配備）ときは sha だけで判断する（手を入れていなければ更新、手を入れた仕組みは衝突）
- 追加: **移行の一部スクリプト化** `scripts/migrations.json`。版ごとの定型の手順を `move`・`json_add`・`replace` の 3 つで書き、
  `--merge` が前回の版より後の分を順に流す（冪等）。判断が要る手順は今までどおりこの CHANGELOG に書き、`--merge` が対象の版の
  「既存プロジェクトへの適用」を抜き出して出す。すべては自動化しない（汎用度を保つ）。v1.3.0・v1.4.0 の定型の手順も入れた
- 追加: **ずれの検知** `.claude/hooks/skeleton_drift.py`。SessionStart に「スケルトン: vX → vY が出ている」を出し、Claude が
  作業の区切りで利用者に 1 行で更新を提案する。スケルトンの場所は `PROJECT_SKELETON_DIR` ＞ `~/.claude/skills/new-project`。
  `check_skeleton.py` は版の遅れを WARN、案件で直した仕組みを INFO で出す（NG にしない。記録が壊れていれば NG）
- 追加: **完了条件の警告**。タスクの「完了条件」をチェックリストにし、`[ ]` が残ったまま `close.py` を実行すると警告する
  （閉じるのは止めない）。番号付きの旧い形は見ない
- 追加: **既存フォルダを読んで下書き** `draft-from-existing` スキル。既存の資料・設定・コードの構成から、01-概要 §1・§3、
  概要 HTML の現在地、案件情報・環境情報、project.json の下書きを作り、利用者には直してほしい点だけを聞く。
  記録の無い案件への初めての `--merge` で案内する
- 追加: **保存を起点にした促し** `.claude/project.json` の `save_cues`。glob に当たるファイルを Claude が書いたら、
  ファイルごとにセッション 1 回「[保存の促し] …」を出す（案件で足せる。コードは書き換えない）。既定は 2 つ
  （スケルトン由来の仕組みを直したら台帳の「返す」列・環境情報を直したら docs に転記しない）
- 変更: `{{SKELETON_VERSION}}` は生成時の版のまま埋める（刻印・初版の行・改訂履歴の「新規作成」が、版を上げるたびに差分に
  ならないように）。今の版は記録の `version`
- 変更: CLAUDE.md §2 に「スケルトン: vX → vY が出たら、区切りで 1 行提案」を 1 行

### 既存プロジェクトへの適用
- `python3 <skeleton>/scripts/init.py <既存パス> --merge`（記録が無いので初回は `--name "<表示名>"` も）を 1 回。以後は記録が作られ、
  SessionStart の知らせと `--merge` で追従する
  - 刻印（CLAUDE.md 1 行目）がある案件は、手を入れていないファイルが自動で新しい版になる。刻印の無い案件（既存の案件に後から
    入れたもの）は今までどおり差分の一覧になるので、仕組みのファイルを取り込んでから `--merge --resolved` で記録する
  - `.claude/project.json` の `save_cues`・`settings.json` の定型の追加は migrations で自動（済んでいれば何もしない）
- 初めて入れた案件は、`draft-from-existing` スキルで空欄の下書きを作る
- 起票済みのタスクの完了条件（番号付き）は書き換えなくてよい（警告は新しい形だけ）

## [1.4.1] - 2026-09-24

v1.4.0 の仕上げ。設計書テンプレートの本文を業務を選ばない言葉にし、本物の Claude Code（`claude -p`・sonnet、4 回・計 1.36 USD）で
確かめて見つかった穴を埋めた。

### 変更
- 変更: 設計書テンプレート（01・02〜09）の本文を、開発に限らない言葉に。開発の具体（ブランチ・デプロイなど）は、
  SaaS・インフラの管理や PM の例と並べて「例」として残した。節の番号・05 §9 の表の検査対象の列は変えていない
- 追加: 設計書追随 hook が、**まだ足していない文書に関わる変更**で「[文書の候補] … add_doc.py 05」を、
  **Sketch の間に実装・設定の変更を始めたとき**「[フェーズ] Build の目安に当たる」を知らせる（どちらもセッションで 1 回）。
  実地確認で、05 を足していないと認証のコードを作っても何も知らせず、Sketch のままになっていた
  - `impact_map.addable_docs()` が `docs/設計書/template/catalog.json` の影響マップの行で判定する
- 修正: 落ち先 `候補: 07 §4` は、07 がまだ無くても `docs/設計書/template/` にあれば正しい落ち先とする（足すときに反映する先）。
  実地確認で、AI が「文書不在」の警告を避けて「記録のみ」に逃げていた。`反映済:` は今までどおり実在する文書だけ
- 修正: 設計書の番号の判定を拡張子を問わない形に揃えた（`drops.design_doc_exists`）。設計書の中の参照探しから `template/` を外した

### 既存プロジェクトへの適用
- `--merge` で differs に出る仕組み（`design_docs_reminder.py`・`impact_map.py`・`drops.py`）を取り込む。設計書テンプレートは
  `docs/設計書/template/` の中なので、案件の設計書には影響しない（足してある文書は案件のもの）

## [1.4.0] - 2026-09-24

開発に限らず、PM 業務・運用保守・インフラや SaaS の管理でも使える「AI と仕事を始める初日の一式」へ。業務ごとに分岐はしない。
使い方は強制せず、利用者が使いながら直していける形にする。
思想: **人が見るものはシンプルに、AI が読むものは詳細に。1 つの事柄の正本は 1 か所。**

### 変更
- 変更: フェーズを 2 段の **Sketch／Build** に（旧: 立ち上げ／開発／運用）
  - Sketch = 情報を集めている段階（旧「立ち上げ」の厳しさ）。Build = 外部へ出し始めた・設計が始まった段階（旧「運用」の厳しさ）
  - 切り替えは AI が判断して行い、報告で 1 行伝える（確認は挟まない）。旧い値は読み替える（`phase.normalize()`）
- 変更: **設計書を育てる**。生成時は `01-概要.md` と索引だけ。02〜09 の元は `docs/設計書/template/` に置き、
  必要になったら `scripts/add_doc.py <番号>` で足す（template の写し・索引・影響マップの行をまとめて入れる。足すかは候補 → 承認）
  - 名前を業務を選ばないものに: 01 概要・02 構成・03 関係者・04 原則・05 セキュリティ・06 品質と確認・07 変更と反映・08 利用者の運用・09 非機能と障害時
  - 影響マップの行は文書ごとに持ち、まだ無い文書を指さない。05 §9 と deny の照合は 05 を番号で探し、無ければ対象ゼロ
  - `CLAUDE.md` §7 は表をやめ、「open だけ読む・作業ログ・決定の正本・読む文書は設計書 README の『知りたいこと』」に
- 変更: **決まったことの正本を課題 md の `## 決定` に一本化**（SSoT）
  - その場で決まったことも `new.py … --decided` で起票してすぐ閉じ、打合せ記録からは `→ <ID>`、設計書からは「（決定 <ID>）」で指す
  - ADR には長い理由だけを書き、課題から指す。「直近の決定」は、落ち先が課題の ID の打合せの決定行を二重に数えない
  - AI が常に読むのは open だけ。closed は ID で指されたときだけ（`CLAUDE.md`・`task` スキル・SessionStart）
- 追加: **作業ログ**（`docs/案件/作業ログ/`。生成物）。`scripts/work_log.py` が正本（タスク・課題の日付・決定・打合せ記録）から作る
  - `最新.md`（直近 14 日。AI が最初に読む）・`README.md`（月ごとの索引）・`YYYY-MM.md`（月ごとのアーカイブ）
  - 1 行 1 件で題と ID のリンクだけ。本文は写さない。起票した日に閉じたものは 1 行にまとめる
  - build.py の最後と、作業の区切り（Stop hook `work_log.sh`）で作り直す。SessionStart はタスクの行に件数だけ
- 追加: **直したものを返す道**。ハーネス台帳に「返す」列。スケルトン側の `scripts/collect_returns.py <案件…>` が、
  返す行と仕組みのファイルの差分を一覧にする
- 追加: **決まりは初期値**。`CLAUDE.md` の冒頭と template の `README.md`「合わせ方」に、変え方・外し方の一覧
- 変更: `init.py --merge` は、同じ番号の設計書が既にある案件にテンプレの設計書を作らない（番号が 2 本にならない）
- 変更: new-project skill の説明を、開発以外の仕事でも呼ばれる言葉に広げた。プロダクト概要を「AI と仕事を始める初日の一式」として書き直した

### 既存プロジェクトへの適用
- `python3 <skeleton>/scripts/init.py <既存パス> --name "<表示名>" --merge` で新しいファイルを足す
  - 足されるもの: `docs/設計書/template/`、`scripts/add_doc.py`・`work_log.py`、`.claude/hooks/work_log.sh`、テスト
  - 既存の設計書（旧い名前・独自の番号）はそのまま。同じ番号のテンプレの設計書は作られない
- フェーズ: 概要 HTML の `data-phase` はそのままでよい（立ち上げ → Sketch、開発・運用 → Build と読む）。
  書き換えるなら `python3 .claude/hooks/phase.py --set Build`
- `.claude/settings.json` は differs に出るので手で取り込む: Stop hook に `work_log.sh` を足す（作業ログを区切りで作り直す）
- 取り込むと挙動が変わる仕組み（differs の「仕組み」）: `phase.py`・`session_context.sh`・`drops.py`（直近の決定の数え方）・
  `check_skeleton.py`（設計書の必須は 01 だけ）・`build.py`（最後に作業ログ）。案件側で直していたら `collect_returns.py` の対象になる
- 決定の書き方: 過去の記録（`→ 反映済: NN §n`）は書き直さない。新しく書く決定から課題に起票して ID で指す
- ハーネス台帳に「返す」列を足す（表の最後の列。空欄でよい）
- 一度 `python3 scripts/work_log.py` を回して作業ログを作る（タスク管理を使っていれば `build.py` でもよい）

## [1.3.0] - 2026-09-24

v1.2.0 を既存案件 2 つに当てる分析で見つかった、スケルトン側の不具合と、案件ごとの形を受け止められない箇所 9 件への対応。
方針: **案件ごとの違いは設定ファイル 1 本（`.claude/project.json`）と差し込み口 1 つで受け、テンプレのコードは案件で書き換えずに済むようにする。**

### 変更
- 追加: `.claude/project.json` と共有モジュール `.claude/hooks/project_config.py`
  - `work_area_allow`: 置き場ガードが通すルート相対の glob（案件の仕組みが固定で使う置き場。例 `.work/一時/tldv同期/**`）
  - `nested_repos`: 中に別の git リポがあるフォルダ。影響マップの正本の解決と、鮮度メタの `<リポ名>@<sha>` に使う
  - 読めない・壊れているときは既定値（空）で動き、hook は止めない。形の誤りは `check_skeleton.py` が NG にする
- 追加: 設計書追随の差し込み口 `.claude/hooks/impact_map_local.py`（任意）。`targets(rel_path) -> list[str]` の結果を
  影響マップの表の結果に足す（先勝ち・除外・フォールバックなど表で書きにくい判定用）。置いたら表にそれを指す行を書く
  （表を唯一の入口に保つ。`check_skeleton.py` が見る）
- 追加: 鮮度メタで入れ子リポの sha を並べられる（`/ repo@abc1234・sub-repo@def5678`）。`docs_freshness.py` が
  `git -C <入れ子リポ>` で差分・未コミットを見る
- 変更: `init.py --merge` は build.py を実行しない（dry-run と結果がずれ、案件の data.js を書き換えていた）。
  実行ビットは今回作ったファイルにだけ付ける（生成先の全走査をやめた）
- 変更: hook のテスト一式を `.claude/hooks/tests/skeleton/` へ移した（既存案件の `tests/run-all.sh` や `hook-cases*.txt`
  の glob とぶつかっていた）。設計書追随のケースはテンプレの影響マップの実物ではなく `reminder-fixture/` の固定の表で流す
- 変更: 打合せ記録の `## 要約` > `### 決定事項` のような H3 の区切りも読む（会議ツールの要約をそのまま貼る形）
- 修正: agents の検査で `_` 始まりのファイル（`_共通.md` などの共通の本文）に `model` を求めていた

### 既存プロジェクトへの適用
- `python3 <skeleton>/scripts/init.py <既存パス> --name "<表示名>" --merge` で新しいファイル（`project_config.py`・
  `project.json`・`tests/skeleton/**`・`test_project_config.py`）を追加し、differs に出た仕組みを取り込む。
  build は走らないので、タスク管理を使うなら取り込み後に `python3 docs/案件/01_タスク管理/build.py`
- v1.2.0 から生成した案件は、旧テストを移す: `.claude/hooks/tests/` 直下の `run-all.sh`・`hook-cases-*.txt`・
  `run_*_cases.py`・`drops-cases/` を、merge で入った `tests/skeleton/` の同名と見比べ、案件で足したケースがあれば
  `tests/skeleton/` 側へ写してから旧ファイルを片付ける。`.claude/settings.json` の allow の
  `Bash(bash .claude/hooks/tests/run-all.sh)` を `…/tests/skeleton/run-all.sh` に直す
- 既存案件で置き場ガードが案件の固定パスを止めるなら、`work_area_guard.py` を書き換えずに `.claude/project.json` の
  `work_area_allow` に足す。入れ子リポがあれば `nested_repos` に書く
- 影響マップの表で書けない判定をコードで持っている案件は、その判定を `.claude/hooks/impact_map_local.py` の
  `targets()` に移し、`docs/設計書/README.md` の影響マップにそれを指す行を 1 行足す

## [1.2.0] - 2026-09-23

v1.1.0 を架空の案件で実際に使ったレビュー(初動が重い・決定が落ちる・未決の置き場が 4 つ・設計書追随が空振り・
AI の動作がマシンのグローバル設定に左右される)への対応。**増やす決まりは 1 つだけ**: 作業中に出たもの
(決定・未決・あとでやること・ハーネス候補)は「反映済・タスク・未決」のどれかに落とす。止めるのは
「落ちていない」「形が壊れている」「秘密を書いた」ときだけで、空欄・未記入・未決の多さでは止めない。

### 変更
- 追加: フェーズ(立ち上げ / 開発 / 運用)
  - 正本は概要 HTML の phase ブロックの `data-phase`。厳しさの表は `.claude/hooks/phase.py` の 1 か所
    (`python3 .claude/hooks/phase.py --table` で表示、`--set 開発` で切り替え)。切り替えはユーザーが決め、
    `update-overview` スキルで行う
  - 立ち上げ期は拾うだけ。設計書は未記入でよく、設計書追随 hook はセッション 1 回の情報にとどまる
- 追加: 拾って流す
  - 未決の正本を課題 md(`kind: 課題`)に一本化。設計書は「(未決 QA-01)」で参照し、U-xx は廃止。
    課題は `## 決定` の 1 行目と落ち先が無いと `close.py` で閉じられない
  - 打合せ記録の `## 決定` `## 未決` `## 宿題` の各行に落ち先(`→ 反映済: 01 §3` / `→ APP-03` /
    `→ 未決 QA-01` / `→ 候補: 05 §3` / `→ ハーネス候補 HN-01`)
  - hook: UserPromptSubmit `pickup_cue`(依頼文の手がかりを記録)、Stop `pickup_check`(ターンの終わりに
    機械判定し、落ち先の無いものがあるときだけ 1 回だけ続行させる)。`CLAUDE_PICKUP=off` で止められる
  - skill `pickup`、検査 `scripts/check_drops.py`、共有モジュール `drops.py`・`pickup_state.py`
  - `sync-design-docs` の判定を「矛盾しないか」から「この変更で何が決まったかを 1 行拾う」へ
- 追加: 見える化と期限
  - タスク・課題に任意の `due`(課題は `decider` も)。概要 HTML の「現在地」に build.py が
    「決めてほしいこと」「次の節目」「直近の決定」を自動生成(旧 `decisions` マーカーは `recent-decisions` へ)
- 追加: ハーネスは候補から承認で定義する
  - skill `harness`(観点カタログ 11 観点。記入欄ではなく Claude が漏れに気づく目)と `docs/ハーネス台帳.md`。
    Claude は候補を台帳に書くまで、定義はユーザーの承認後。`.claude/agents/` は `model` 必須
- 追加: 案件で揃う範囲
  - `SETUP.md` §8(案件で揃うもの / マシンに左右されるもの、初回は対話起動でワークスペースを信頼、
    グローバル plugin は案件の `enabledPlugins` で止められる)。SessionStart に「マシン側」の 1 行
  - `settings.json`: 読むだけのコマンドとテスト実行を allow、履歴破壊系を deny(05 §9 を決定に)、
    `env.CLAUDE_CODE_SUBAGENT_MODEL=sonnet`
- 変更: 初日を軽く
  - `init.py` の案内を「最初はこの 4 つだけ」と「今は書かなくてよいもの」に。`--desc` `--owner` 未指定は
    「(未記入…)」「(未定)」を入れて案内
  - タスク README を約 70 行の要約と `詳細仕様.md` に分割。雛形のままの設計書は「未記入 N 本」と情報表示
  - SessionStart の注入は 8 行以内(フェーズ・設計書の要確認と未記入・拾いもの・ハーネス候補・マシン側)
- 修正: skill の `allowed-tools` を全て削除(template の 4 本とスケルトンの `SKILL.md`)。
  未信頼のワークスペースで起動が拒否される原因だった
- 修正: 秘密検出をスキーム不問の URL 資格情報・記号入りの値・既知のトークン形式に広げ、対象を docs/ 全体・
  CLAUDE.md・.claude/ へ。誤検知は行に `secret-scan: ok <理由>` で除外
- 修正: `new.py` を argparse 化(`-h` は何も作らない、未登録 area は止める、接頭辞は読み替え、
  `--priority --owner --due --tag --add-area --decider --decided --to`、1 行目に確定 ID)。既定の領域に「仕様: SPEC」
- 修正: `init.py --merge` の比較から build の生成物を外し、differs を「仕組み」と「内容」に分けて出す

### 既存プロジェクトへの適用(v1.1.0 → v1.2.0)
1. `python3 <skeleton>/scripts/init.py <案件> --name "<表示名>" --merge --dry-run` で差分を見る
2. `--merge` で新規ファイルを入れる(phase.py・machine_context.py・drops.py・pickup_*・check_drops.py・
   skill pickup / harness・ハーネス台帳.md・詳細仕様.md・scripts/tests/ ほか)
3. 「仕組み」の differs を取り込む(独自の変更が無ければ置き換え): `check_skeleton.py`・`docs_freshness.py`・
   `session_context.sh`・`design_docs_reminder.py`・`new.py`・`close.py`・`build.py`・`index.html`・`run-all.sh`・
   `hook-cases-reminder.txt`
4. **フェーズを設定する**: `python3 .claude/hooks/phase.py --set <立ち上げ|開発|運用>`
   (設定しないと立ち上げ扱いになり、開発中の案件では設計書追随が弱まる)
5. 「内容」の differs を手で取り込む: `CLAUDE.md`(§2・制約 4・7・8。既存の制約 8 以降は番号をずらす)、
   `settings.json`(UserPromptSubmit と Stop の hook、allow・deny・env。案件で足した allow は残す)、
   skill 6 本(`allowed-tools` 行の削除を含む)、`docs/設計書/README.md`(影響マップの打合せ行・書き方)、
   05 §9、`rules/docs-management.md`、`02_打合せ/README.md`、`確認依頼一覧.md`、`案件情報.md` §3・§4、
   タスク README(要約に差し替え。案件で書き換えたクローズ基準は残す)、`areas.json`(仕様: SPEC)
6. データを移す(`python3 scripts/check_drops.py` を見ながら): 設計書の U-xx と案件情報 §4 の未決を課題に起票、
   確認依頼一覧の `[ ]` 行に ID、概要 HTML の手書きの「直近の決定」を打合せ記録か課題(`new.py --decided`)へ
   移してから `decisions` マーカーを `recent-decisions` 等に差し替え。古い打合せ記録の落ち先は
   `→ 反映済: 記録のみ（v1.2.0 移行前）` でよい
7. 案件で足していたハーネス(skill・agents・hook)は台帳に「定義済」で 1 行ずつ。agents に `model` が無ければ書く
8. `python3 scripts/check_skeleton.py` → fail=0。秘密検出の範囲が広がるので、NG は値を `環境情報.md` へ移す
9. 初回は対話起動でワークスペースを信頼する(SETUP.md §8)。非対話の一括処理では `CLAUDE_PICKUP=off`

## [1.1.0] - 2026-09-23

### 変更
- 追加: 設計書を常に更新し続ける仕組み
  - `docs/設計書/` に 03〜09(ステークホルダー / 設計原則 / セキュリティ設計 / 品質設計 /
    開発運用設計 / 利用者運用設計 / 非機能と縮退)と `runbook/` を追加。各設計書は 2 行目に
    鮮度メタ行(`> 最終更新: … ／ 対象: … / repo@<sha>`)、末尾に `## 改訂履歴` を持つ
  - `docs/設計書/README.md` の「変えたもの → 一緒に直す正本」表を機械可読な影響マップにした
    (1 列目 glob・2 列目 文書)。hook・検査・skill が同じ表を読む
  - skill `sync-design-docs`(変えたその場で追随)/ `audit-design-docs`(節目の総点検。リストアップまで)
  - hook `design_docs_reminder`(PostToolUse Write|Edit|MultiEdit。影響マップに当たるソースを変えたら
    更新候補を additionalContext で 1 回だけ出す)。共有モジュール `.claude/hooks/impact_map.py`、
    テスト `hooks/tests/hook-cases-reminder.txt`(run-all.sh に統合)
  - `scripts/docs_freshness.py`(メタ行の日付・対象 glob・sha から要確認の設計書を出す。
    `--quiet` / `--strict` / `--json` / `--list` / `--days N`)。`session_context.sh` の 5 行目で本数を注入
  - `check_skeleton.py --docs` / `check.py` の設計書検査(メタ行・改訂履歴・索引の漏れと死に索引・
    影響マップの解決・秘密らしき文字列(password= / URL 埋め込み資格情報)・docs_freshness の整数返し)
  - `CLAUDE.md` §7(設計書の扱い)・制約 7、`docs/README.md` の「作業種別 → 読む文書」、
    `案件情報.md` のロール ID 列
- 修正: `check_skeleton.py` の必須ファイルに `docs/設計書/01-overview.md` `02-architecture.md` が無かった
- 修正: `update-overview` の手順 6 が「秘密らしき文字列を検出する」と書いていたが `--overview` は
  検出しない。実装に合わせ `check_skeleton.py --docs` の秘密検出を指すようにした

### 既存プロジェクトへの適用
- `python3 <skeleton>/scripts/init.py <既存パス> --name "<表示名>" --merge` で新規ファイル
  (設計書 03〜09・runbook・skill 2 本・hook 3 本・テストケース・docs_freshness.py)が入る
- differs に出る次は手で取り込む: `CLAUDE.md`(§7・制約 7)、`.claude/settings.json`(PostToolUse)、
  `docs/README.md`、`docs/設計書/README.md`(影響マップ)、`案件情報.md`、
  `.claude/hooks/session_context.sh`(5 行目)、`.claude/hooks/tests/run-all.sh`、
  `scripts/check_skeleton.py`、`.claude/skills/update-env-info/SKILL.md`、
  `.claude/skills/update-overview/SKILL.md`、`.claude/rules/docs-management.md`、`docs/プロジェクト概要.html`
- 既存の設計書(01・02 と自作分)には 2 行目にメタ行、末尾に `## 改訂履歴` を足す。
  `python3 scripts/check_skeleton.py --docs` が NG を列挙する

## [1.0.0] - 2026-09-23

### 変更
- 初版。Claude Code 専用のプロジェクトスケルトン
  - `template/`: CLAUDE.md / rules / skills / hooks / `.work` 作業領域 / タスク管理
    (`docs/案件/01_タスク管理`)/ 概要 HTML / 設計書 / 環境情報・案件情報
  - `scripts/init.py`: template から案件フォルダを生成(`--merge` で既存へ適用)
  - `scripts/check.py`: スケルトン自身の検査
  - `template/scripts/check_skeleton.py`: 生成先の検査
  - `scripts/install-global.sh` / `.ps1`: `~/.claude/skills/new-project` への配備
  - `SKILL.md`: new-project skill

### 既存プロジェクトへの適用
- 初版のため対象なし。スケルトン以前に手で作ったプロジェクトへ入れる場合は
  `init.py --merge` を実行し、differs に出た `CLAUDE.md` 等は内容を見て取り込む
