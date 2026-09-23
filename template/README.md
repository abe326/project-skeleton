# {{PROJECT_NAME}}

{{PROJECT_DESC}}

## まず読むもの

- `docs/プロジェクト概要.html` — 目的・設計原則・現在地・将来対応・構成図。ブラウザで開く
- `docs/README.md` — ドキュメントの索引と推奨読書順
- `docs/案件/01_タスク管理/index.html` — タスクの一覧（`build.py` で生成）

## Claude Code で開く前に

- **初回は対話起動（`claude`）でこのフォルダを開き、ワークスペースを信頼する。** 信頼する前に `claude -p` で動かすと `.claude/settings.json` の許可が効かず、skill やテストが権限で止まる
- 案件で揃うのは `CLAUDE.md`・`.claude/`（rules・skills・hooks・settings.json）・`docs/ハーネス台帳.md`。マシンの `~/.claude/` の指示・plugin・hook は合算されて動く。混ざっていればセッション開始時に「マシン側:」の行が出る
- 抑え方と書き分けの表は project-skeleton の `SETUP.md` §8「案件で Claude Code を使うとき」

## セットアップ

```
# 1. 依存の導入
#
# 2. 環境変数
cp .env.example .env    # 値は 環境情報.md（Git 管理外）を見て埋める
#
# 3. 起動
#
```

## 作業の決めごと

Claude Code で作業する前提の構成。ルールは `CLAUDE.md` と `.claude/rules/` にある。

- 秘密は `環境情報.md` と `.env` にだけ書く（どちらも Git 管理外）
- 一時ファイルは `.work/一時/YYYYMMDD_用途/` に置く（ルート直下に散らかさない）
- 置き場のチェックは `.claude/hooks/work_area_guard.py`（PreToolUse hook）が行う。**python が PATH に無いマシンでは素通りになる**ので、Windows は `winget install Python.Python.3.12` で入れておく
- `.claude/settings.json` の `permissions.deny` は履歴の破壊と `--no-verify` を止める（`docs/設計書/05-セキュリティ設計.md` §9 と対応）。本番環境への操作など止めたいコマンドは `harness` スキルで 05 §9 と一緒に足す
- サブエージェントの既定モデルは `settings.json` の `env`（`CLAUDE_CODE_SUBAGENT_MODEL=sonnet`）で揃えている

---

作成: {{CREATED}} ／ 管理: {{OWNER}} ／ project-skeleton v{{SKELETON_VERSION}}
