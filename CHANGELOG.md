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
