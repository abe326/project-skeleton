# CHANGELOG

スケルトンの版ごとの変更と、**既存プロジェクトへの適用方法**を残す。
版は `VERSION` と一致させる(`python3 scripts/check.py` が照合する)。

書式:

```
## [x.y.z] - YYYY-MM-DD
### 変更
- …
### 既存プロジェクトへの適用
- `python3 <skeleton>/scripts/init.py <既存パス> --name "<表示名>" --merge` で足りない
  ファイルを追加し、differs に出たファイルは手で取り込む
- 手作業が要るものはここに列挙する
```

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
  - skill `harness`(観点カタログ 11 観点。記入欄ではなく Claude が漏れに気づく目)と `.claude/ハーネス台帳.md`。
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
