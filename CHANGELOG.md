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
