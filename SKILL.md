---
name: new-project
description: 新しい案件・プロジェクトのフォルダをスケルトンから 1 コマンドで作る。「新しいプロジェクトを作って」「スケルトンから作って」「案件フォルダを立ち上げて」「プロジェクトを初期化して」「既存プロジェクトにスケルトンを適用して」で使う。タスク管理・.work 作業領域・概要 HTML・環境情報・CLAUDE.md/rules/skills/hooks が揃った案件フォルダを生成し、既存フォルダには --merge で足りないものだけ追加する。
allowed-tools: Bash(python3 *), Bash(python *)
---

# new-project — スケルトンから案件フォルダを作る

このスキルのフォルダ(= この SKILL.md がある場所)が project-skeleton の正本。
`scripts/init.py` が `template/` を複製し、プレースホルダを埋めて案件フォルダを作る。

## 1. 引数を確認する

ユーザーの依頼から次を読み取る。**足りないのは名前だけ聞く**。他は既定値で進めてよい。

| 引数 | 必須 | 既定 | 備考 |
|---|---|---|---|
| 表示名 `--name` | 必須 | — | 日本語可 |
| 生成先(第 1 引数) | | job-work 直下 `<job-work>/<引数>` | パス区切りを含めばそのパス。既存フォルダなら `--merge` を提案する |
| `--slug` | | 表示名を ASCII 化 | 非 ASCII のみの名前なら聞くか、フォルダ名から決める |
| `--desc` | | 空 | 1 行の説明 |
| `--owner` | | 空 | 担当者 |
| `--areas` | | 無し | 領域プレフィックスの追加 `"CORE:共通コード,OPS:運用"`。既定の 横断/文書/環境/運用 に加える |

既に存在するフォルダへ「スケルトンを適用して」と言われたら `--merge`(既存ファイルは触らず、無いものだけ追加)。
まず `--dry-run` で作成予定を見せてから本実行してもよい。

## 2. 実行する

`<skill dir>` はこの SKILL.md のあるフォルダの絶対パス。

Linux / macOS(dev 機):

```bash
python3 "<skill dir>/scripts/init.py" "<生成先 or 名前>" --name "<表示名>" [--slug x] [--desc "…"] [--owner "…"] [--areas "…"] [--merge]
```

Windows(Git Bash):

```bash
python "<skill dir>/scripts/init.py" "<生成先 or 名前>" --name "<表示名>" [同上]
```

init.py は生成後に `build.py`(タスク一覧のスナップショット)、`git init` + 初回コミット、
`scripts/check_skeleton.py` を続けて実行し、最後に created/skipped/differs と「次にやること」を出す。
`--no-git` で git を、`--dry-run` で書き込み全体を省ける。

## 3. 出力を伝える

- init.py の「次にやること」を**そのまま**ユーザーに提示する
- `環境情報.md` `案件情報.md` `docs/プロジェクト概要.html` の記入を提案する。**勝手に埋めない**(内容を知っているのはユーザー)
- `--merge` で differs が出たら、一覧を見せて「template 側の変更を取り込むか」を聞く
- check_skeleton.py に NG があれば内容を伝えて対処を提案する

## 4. スケルトン自体を直したいとき

- 正本(このフォルダ)の `template/` を編集する。生成先のコピーを直しても他のプロジェクトには反映されない
- `python3 "<skill dir>/scripts/check.py"` で検査してから、`VERSION` を上げ `CHANGELOG.md` に「既存プロジェクトへの適用」を書く
- 既存プロジェクトへは `init.py --merge` で追加分を配り、differs は手で取り込む
- 手順の詳細は同フォルダの `README.md`、グローバル配備は `SETUP.md`
