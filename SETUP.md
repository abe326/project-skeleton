# SETUP — グローバル初期設定(各マシンで 1 回ずつ)

## 0. 何が起きるか

```
~/.claude/skills/new-project  ──(リンク)──▶  <このリポ>/
                                              ├── SKILL.md     ← Claude Code はここを skill として読む
                                              ├── scripts/init.py
                                              └── template/
```

- 正本は **このリポ 1 箇所**。`~/.claude/skills/` にはリンクだけを置き、コピーは作らない
  (コピーを作ると正本を直しても反映されず、版がずれる)
- `~/.claude` は**マシンごとに別物**。マシン A で設定してもマシン B には効かない。各マシンで 1 回ずつ行う
- 同期フォルダ(複数マシンで同期しているフォルダ)の**中にリンクを置かない**。`~/.claude` は同期対象外なので問題ない
- Windows はシンボリックリンクではなく**ジャンクション**を使う(管理者権限が要らず、Claude Code から普通のフォルダに見える)

## 1. 前提ツール

| ツール | 確認 | 入れ方 |
|---|---|---|
| python3(3.9 以上) | `python3 --version`(Windows は `python --version`) | Windows: `winget install Python.Python.3.12` → 新しいターミナルで `python --version`。Linux: ディストリのパッケージ |
| git | `git --version` | 無くても生成はできる(初回コミットが省かれるだけ) |
| Claude Code | `claude --version` | — |

Windows で `python --version` が何も出さない(または Microsoft Store が開く)ときは、
「アプリ実行エイリアス」のスタブが呼ばれている。上の winget で本体を入れるか、
設定 → アプリ → アプリ実行エイリアス で python のエイリアスを無効にする。

## 2. Linux / macOS

```bash
cd <このリポ>
bash scripts/install-global.sh          # ~/.claude/skills/new-project → このリポ のリンクを作る
```

- 既に同じ先へのリンクがあれば `OK 設定済み` と出て終わる
- 別の先を指している・ディレクトリがある場合は警告して止まる。置き換えるなら `--force`
- リンクが使えない環境(一部の共有ストレージ等)は `--copy` でコピー配備。`INSTALLED-AS-COPY.txt` が置かれ、正本を更新したら `--copy --force` で配り直す

## 3. Windows(PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File "<このリポ>\scripts\install-global.ps1"
```

- 既存が同じ先のジャンクションなら `OK 設定済み`。違えば警告して止まる。置き換えるなら `-Force`
- コピー配備は `-Copy`
- **Git Bash で `install-global.sh` を実行しない**。Git Bash の `ln -s` はコピーになり、正本と分かれる(スクリプト側でも止まるようにしてある)

## 4. `~/.claude/CLAUDE.md` に足す文面

スクリプトは `~/.claude/CLAUDE.md` を編集しない。Claude か人が以下をそのまま追記する(既に同じ節があれば何もしない)。

```markdown
## 新規プロジェクト

- 新しい案件・プロジェクトは `new-project` skill(`~/.claude/skills/new-project` → `[個人開発]project-skeleton`)で作る
- スケルトンを直すときは正本を編集して `CHANGELOG.md` と `VERSION` を上げる。手順は同フォルダの `SETUP.md`
```

## 5. 動作確認

1. Claude Code を**新規セッション**で起動し、`/` を打って `new-project` が候補に出る
2. `python3 ~/.claude/skills/new-project/scripts/init.py /tmp/skel-dry --name テスト --dry-run` が作成予定の一覧を出す
   (Windows は `python "$env:USERPROFILE\.claude\skills\new-project\scripts\init.py" "$env:TEMP\skel-dry" --name テスト --dry-run`)
3. `python3 ~/.claude/skills/new-project/scripts/check.py` が `fail=0`

## 6. Claude Code に「スケルトンの初期設定をして」と頼まれたときの手順

1. OS を判定する(`uname` / `$OSTYPE` / `$env:OS`)
2. §1 の前提ツールを確認し、無ければ入れ方を示す(インストール自体はユーザー確認のうえ)
3. §2 または §3 のスクリプトを実行し、出力を確認する
4. §4 の追記を提案する。`~/.claude/CLAUDE.md` に「## 新規プロジェクト」節が既にあれば何もしない
5. §5 の動作確認を行い、結果を報告する
6. **必ず伝える**: 「`~/.claude` はマシンごとに別です。もう一方のマシンでも同じ手順が必要です」
7. リンク作成に失敗したら `--copy`(Windows は `-Copy`)で配備し、コピー配備であることと更新時の再配備を伝える
8. 生成した案件を初めて開くときは、§8 の 1(対話起動でワークスペースを信頼する)を伝える

## 7. 外す

```bash
# Linux / macOS
rm ~/.claude/skills/new-project              # リンクを消す(正本は残る)
```

```powershell
# Windows(Remove-Item -Recurse は使わない。ジャンクション先の正本まで消える恐れがある)
cmd /c rmdir "$env:USERPROFILE\.claude\skills\new-project"
```

コピー配備の場合はフォルダごと削除してよい(`INSTALLED-AS-COPY.txt` があるのがコピー)。
`~/.claude/CLAUDE.md` の「## 新規プロジェクト」節も消す。

## 8. 案件で Claude Code を使うとき(案件ごと・マシンごとに 1 回)

1. **初回は対話起動でワークスペースを信頼する。** `cd <案件>` → `claude` → 信頼の確認で承認する。
   信頼する前に非対話(`claude -p`)で動かすと、案件の `.claude/settings.json` の `permissions.allow` が効かず、
   テストや Bash が権限で止まる(`Skill(<名前>)` を allow に書いても効かない。v1.2.0 の段階 0 で確認)。
   テンプレートの skill は `allowed-tools` を持たない(持つと未信頼のワークスペースで起動が拒否されるため)
2. 案件で揃うもの / マシンに左右されるもの

   | 区分 | もの | 置き場 | 揃い方 |
   |---|---|---|---|
   | **案件で揃う**(Git に載る) | 指示・制約 | `CLAUDE.md`、`.claude/rules/` | clone すれば同じ |
   | | 権限・hook・環境変数 | `.claude/settings.json`(`permissions`・`hooks`・`env`) | 同じ。**ただしワークスペースを信頼していないと permissions が効かない** |
   | | skill・エージェント定義 | `.claude/skills/`、`.claude/agents/` | 同じ |
   | | ハーネス台帳・検査 | `.claude/ハーネス台帳.md`、`scripts/check_skeleton.py` | 同じ |
   | | MCP(案件用) | `.mcp.json` | 同じ。初回に承認が要る |
   | **マシンに左右される** | 全案件共通の指示 | `~/.claude/CLAUDE.md` | 常に読み込まれ、案件からは外せない |
   | | グローバルの hook・plugin・環境変数 | `~/.claude/settings.json`(`hooks`・`enabledPlugins`・`env`) | 案件の hook と**合算**される。plugin の SessionStart 注入・Stop hook もここ |
   | | 個人の上書き | `.claude/settings.local.json`(Git 管理外) | そのマシンだけ |
   | | ワークスペースの信頼 | `~/.claude.json` | マシンごと・フォルダごとに 1 回 |
   | | モデル・effort | 起動時の選択、`~/.claude/settings.json` | セッションごと |
   | | ツール | python3・git・テストランナー | マシンごと。無いときの振る舞いは台帳の「品質ゲート」で決める |

   サブエージェントの既定モデルは、案件の `env.CLAUDE_CODE_SUBAGENT_MODEL`(テンプレートは `sonnet`)が
   ユーザー側の同じキーより優先される(段階 0 で確認)
3. **マシン側の混入を確かめる**: セッション開始時の「マシン側: plugin N 個(名前)・hook M 本」の行を見る。
   出ていなければ混入なし。「ワークスペース未信頼」が出たら 1 に戻る
4. **混入を案件で抑える**(抑えたら案件の `.claude/ハーネス台帳.md` に「マシン依存」として 1 行残す)
   - **plugin**: 案件の `settings.json`(マシン固有なら `settings.local.json`)の `enabledPlugins` で
     `{"<plugin 名>@<マーケット>": false}` にする。plugin 単位で読み込みから外れ、その plugin の
     SessionStart 注入・hook・skill が止まる(段階 0 で確認)。例: ターンごとにレビューを出す Stop hook は
     `security-guidance` plugin 由来だった
   - **ユーザー設定の hook**(`~/.claude/settings.json` の `hooks`): 案件からは外せない。止めるならグローバル
     hook の冒頭で案件を見分けて抜ける
     (`head -1 "$CLAUDE_PROJECT_DIR/CLAUDE.md" | grep -q project-skeleton && exit 0`)。`~/.claude` は
     マシンごとに別なので、両方のマシンに入れる
   - 案件の `disableAllHooks: true` は使わない(案件の hook も止まる)
5. **自動実行**(cron・CI)で案件の設定だけにしたいときは `claude -p --setting-sources project,local`
