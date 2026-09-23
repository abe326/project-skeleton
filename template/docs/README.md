# {{PROJECT_NAME}} ドキュメント

`docs/` は **Git 管理対象で共有する前提**。秘密（URL・ID・パスワード・鍵）は書かない（`.claude/rules/secrets.md`）。

## 索引

| パス | 内容 | 更新の仕方 |
|:--|:--|:--|
| `プロジェクト概要.html` | 目的・思想・現在地・直近の決定・将来対応・構成図と環境の入口・更新履歴。**人が最初に読む 1 枚** | `update-overview` スキル（タスクの状況は `build.py` が自動で書く） |
| `案件/` | 共有記録。タスク管理（作業の正本）・打合せ記録・確認依頼一覧 | `task` スキル、`.claude/rules/docs-management.md` |
| `案件/01_タスク管理/index.html` | タスクと画面の一覧 | `python3 docs/案件/01_タスク管理/build.py` |
| `設計書/` | 設計の正本。`01-overview.md`（何を作るか）・`02-architecture.md`（どう作るか）・`decisions/`（ADR） | 変えたら `設計書/README.md` の「一緒に直す正本」表を見る |

運用ルール（置き場・秘密・作業領域）は `.claude/rules/` にある。設計書は「方針」、`.claude/rules/` は「日々のルール」と役割を分ける。

## 推奨読書順

### 初めて触る人

1. `プロジェクト概要.html` — 目的・原則・いまどこにいるか
2. `設計書/01-overview.md` — 何を作っているか
3. `設計書/02-architecture.md` — どう作っているか
4. `案件/01_タスク管理/index.html` — いま何が動いているか
5. `README.md`（ルート）— 動かし方

### 作業を再開する人（毎セッション）

1. `プロジェクト概要.html` の「3. 現在地」
2. `案件/01_タスク管理/data.js`（SessionStart hook が件数を出す）
3. `案件情報.md`（ルート直下・Git 管理外）の日程・先方待ち

### 設計を変える人

1. `設計書/decisions/README.md` — 既存の判断を確認
2. `設計書/decisions/ADR-000-テンプレート.md` — 新しい判断はこの型で
3. 変えたら `update-overview` スキルで概要 HTML の「直近の決定」へ
