# project-skeleton 開発ガイド

このリポはスケルトンの正本で、リポのルート自体がグローバル skill `new-project` になる(`SKILL.md`)。
生成元は `template/`、生成器は `scripts/init.py`(生成先に記録 `.claude/skeleton.json` を書き、`--merge` で新しい版に追従させる)。使い方・構成は `README.md`、配備は `SETUP.md`、版の履歴は `CHANGELOG.md`。

## 作業の前に

- 相談・決定・計画の記録は、このリポの外の相談用ノートにある(読む許可は各マシンの `.claude/settings.local.json` の `permissions.additionalDirectories`)。まずそこの `README.md` で現在地と未解決の論点を確かめる
- 計画・決定は相談用ノートに、変更内容はこのリポの `CHANGELOG.md` に残す

## 変更の手順

1. `template/` を直す(生成先のコピーを直しても他の案件には届かない)
2. `python3 scripts/check.py` → `fail=0`(template の単体テスト・hook テスト・init のテストも回る)
3. 生成して確かめる: `python3 scripts/init.py <作業用の一時フォルダ>/<名前> --name 検証 --slug x` → 生成先で `python3 scripts/check_skeleton.py`
4. 版を上げるときは `VERSION` と `CHANGELOG.md`(「既存プロジェクトへの適用」を必ず書く)。どの案件でも同じ結果になる定型の手順は `scripts/migrations.json`(move / json_add / replace)に書き、判断が要る手順だけを CHANGELOG に書く(すべては自動化しない)
5. commit → push(main)

## 守ること

- 個人名・ホスト名・メールアドレス・実在の顧客名を書かない(公開前提)
- skill の frontmatter に `allowed-tools` を書かない(未信頼のワークスペースで起動が拒否される。`check.py` が見る)
- **`template/` の中で `new.py`・`build.py`・`close.py` を実行しない**(テンプレートが汚れる)。確認は生成先で行う
- `template/CLAUDE.md` は 80 行以内。プレースホルダは既存 6 種のみ。python は標準ライブラリだけ。UTF-8・BOM なし・LF(`.ps1` だけ BOM)
- ハーネスの候補の台帳は `docs/ハーネス台帳.md`(`.claude/` の中は Claude Code が編集のたびに承認を求めるため外に置く)

## サブエージェントに任せるとき

- 指示に必ず入れる: 削除系(`rm`・`rmdir`・`find -delete`・`shutil.rmtree`)と `sed -i` を使わない / 編集は Edit・Write ツール / Bash は 1 回に 1 つの単純なコマンド / 作り直しは新しい名前のフォルダで / `PYTHONDONTWRITEBYTECODE=1`
  (これらは承認待ちで無言停止する原因になった)
- 1 ファイル 1 担当に固定し、進捗を 1 ファイルごとに追記させる。停止を疑ったら会話記録(`~/.claude/projects/<プロジェクト>/<セッション>/subagents/agent-*.jsonl`)の末尾で、結果の無いツール呼び出しを確かめる
- 実地確認(`claude -p`)はメインで行う(サブエージェントからの入れ子実行は拒否されることがある)
