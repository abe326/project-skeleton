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
