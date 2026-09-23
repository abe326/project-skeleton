---
name: task
description: docs/案件/01_タスク管理/ のタスクを扱う手順。起票（「タスクにして」「起票して」「課題として残して」）、クローズ（「完了にして」「閉じて」）、再オープン、画面の追加・ステータス変更（「画面を足して」「SCR-01 を実装中に」）、一覧確認（「open のタスクは」「何が残ってる」）、data.js / index.html の更新（「ビルドして」）、work-placement スキルで新規起票が決まったときに使う。new.py / close.py / screen.py / build.py の CLI を使い、9 セクションを埋める。
allowed-tools: Bash(python3 *) Bash(python *)
---

# task

作業の正本はタスク md（`docs/案件/01_タスク管理/open/<ID>_タイトル.md`）。起票・クローズ・画面管理・一覧生成は同じフォルダの CLI で行い、手で ID を採番したりファイルを移動したりしない。詳細は `docs/案件/01_タスク管理/README.md`。

## CLI（`docs/案件/01_タスク管理/` で実行）

| 操作 | コマンド | 結果 |
|:--|:--|:--|
| 起票 | `python3 new.py <area> "タイトル"` | `open/<ID>_タイトル.md` を雛形付きで作る（ID は `areas.json` の領域プレフィックス + 連番） |
| 課題として起票 | `python3 new.py <area> "タイトル" --kind 課題` | kind が 課題 のタスク |
| クローズ | `python3 close.py <ID>` | `open/` → `closed/` へ移動、status を 完了 に |
| 再オープン | `python3 close.py <ID> --reopen` | `closed/` → `open/` へ戻す |
| 画面の追加 | `python3 screen.py new "<名前>" --path /x` | `screens/` に SCR-NN を作る |
| 画面のステータス | `python3 screen.py set SCR-01 実装中` | 未着手 / 実装中 / 確認待ち / 完了 / 保留 |
| 一覧生成 | `python3 build.py` | `data.js`（`window.TASKS` / `window.SCREENS`）と `index.html` を再生成し、概要 HTML の `task-snapshot` を更新 |
| 検査のみ | `python3 build.py --check` | 生成せずに frontmatter の欠落・不正値を報告 |

領域（area）は `areas.json` にある。**領域を足すときは `areas.json` と `README.md` の対応表を同じ作業で更新する**。

## 起票の手順

1. `work-placement` スキルで「新規起票」と決まっている、またはユーザーの指示があること
2. 領域を選ぶ（`areas.json`）。迷うなら AskUserQuestion
3. `new.py` で起票し、生成された md を Read する
4. frontmatter を埋める: `kind`（タスク / 課題）、`status`（未着手 / 進行中 / 方針確定 / 確認待ち / 保留 / 完了）、`priority`（最高 / 高 / 中 / 低）、`screens`（関係する画面 ID の配列。無ければ `[]`）
5. 本文の 9 セクションを埋める（分からない節は「未定」と書き、空のまま消さない）

| # | セクション | 書くこと |
|:--|:--|:--|
| 1 | 概要 | 何をするか 1〜3 文 |
| 2 | 対応の意義 | なぜ今やるか。やらないと何が困るか |
| 3 | 対応後の変更点 | 利用者・運用者から見て何が変わるか |
| 4 | 対応計画の概要 | 手順の骨子（箇条書き 3〜7 行） |
| 5 | 対応計画の詳細 | 具体的な作業・ファイル・コマンド |
| 6 | 影響・依存 | 他タスク・他システム・関係者への影響と依存 |
| 7 | 完了条件 | 何をもって完了とするか（検証可能な形で） |
| 8 | 過去の経緯 | 作業中の判断・試行・却下した案を日付付きで追記していく |
| 9 | 参照情報 | 関連タスク ID・ADR・証跡パス（`.work/証跡/<ID>_内容/`）・打合せ記録 |

6. `python3 build.py` で一覧を更新する

## クローズの手順

1. 「完了条件」を満たしたことを本文（過去の経緯）に日付付きで書く
2. 証跡が `.work/証跡/<ID>_内容/` にあるなら「参照情報」にパスを書く
3. `python3 close.py <ID>` → `python3 build.py`
4. フェーズ・方針・ロードマップに効く完了なら `update-overview` スキル、環境・関係者・日程に効くなら `update-env-info` スキルを続ける

## 画面（screens）の付け方

- UI を持つプロジェクトで、タスクがどの画面に関係するかを `screens:` に SCR-ID で書く（`screens: [SCR-01, SCR-03]`）
- 画面が無ければ `screen.py new` で先に作る。画面の実装状況は `screen.py set` で変える（タスクの status とは別）
- UI を持たないプロジェクトでは `screens: []` のままでよい

## 禁止事項

- ID を手で採番する、md を手で `closed/` へ移す（CLI を使う）
- frontmatter に規定外の値を書く（`build.py --check` が検出する）
- 9 セクションのうち空のものを消す（「未定」と書いて残す）
- タスク md に秘密の実値を書く（`環境情報.md` を参照させる）
- `data.js` / `index.html` を手で編集する（`build.py` の生成物）

## 関連

- `docs/案件/01_タスク管理/README.md` — CLI とスキーマの正本
- `.claude/skills/work-placement/SKILL.md` — 起票が要るかの判断
- `.claude/rules/docs-management.md` — タスク付随資料の併置規約
