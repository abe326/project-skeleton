# project-skeleton

Claude Code で進める案件・プロジェクトのフォルダを、同じ形で 1 コマンド生成するためのスケルトン。
`template/` が生成元、`scripts/init.py` が生成器。リポ全体がそのまま Claude Code のグローバル skill
`new-project` になる(`~/.claude/skills/new-project` → このリポ)。
python3 の標準ライブラリだけで動き、外部依存はない。

## 構成

```
project-skeleton/
├── SKILL.md                  new-project skill(Claude Code が読む手順)
├── README.md                 このファイル
├── SETUP.md                  グローバル配備の手順(各マシンで 1 回)
├── CHANGELOG.md              版ごとの変更と「既存プロジェクトへの適用」
├── VERSION                   semver。生成物の CLAUDE.md 先頭に埋め込まれる
├── scripts/
│   ├── init.py               template → 案件フォルダを生成(--merge で既存へ適用)
│   ├── check.py              スケルトン自身の検査(template の単体テスト・hook テストも回す)
│   ├── tests/                init.py の単体テスト
│   ├── install-global.sh     ~/.claude/skills/new-project にリンク(Linux / macOS)
│   └── install-global.ps1    同上(Windows、ジャンクション)
└── template/                 生成元。プレースホルダ {{…}} を init.py が埋める
    ├── CLAUDE.md / README.md / CHANGELOG.md / _gitignore / .gitattributes / .editorconfig / .env.example
    ├── 環境情報.md / 案件情報.md           (生成先では .gitignore 対象)
    ├── .claude/settings.json / rules/(3 本)/ ハーネス台帳.md
    │   ├── skills/                        work-placement / scratch / task / update-overview / update-env-info /
    │   │                                  sync-design-docs / audit-design-docs / pickup / harness(9 本)
    │   └── hooks/                         session_context(SessionStart)/ work_area_guard(PreToolUse)/
    │                                      design_docs_reminder(PostToolUse)/ pickup_cue(UserPromptSubmit)/
    │                                      pickup_check(Stop)+ phase.py・drops.py・pickup_state.py・
    │                                      impact_map.py・machine_context.py + tests/
    ├── .work/                             作業領域(証跡・機密・一時・_bk)
    ├── scripts/check_skeleton.py          生成先の検査(--overview / --docs)
    ├── scripts/docs_freshness.py          設計書の鮮度(要確認と未記入)
    ├── scripts/check_drops.py             落ち先の検査(打合せ記録・課題・確認依頼の落ち先なし・ID 不在)
    ├── scripts/tests/                     単体テスト(run_tests.py)
    └── docs/
        ├── プロジェクト概要.html          マーカー付きの 1 枚概要
        ├── 案件/01_タスク管理/            new.py / close.py / screen.py / build.py / areas.json / index.html /
        │                                  README.md(要約)・詳細仕様.md
        ├── 案件/02_打合せ/ ・ 案件/確認依頼一覧.md
        └── 設計書/                         01-overview 〜 09-非機能と縮退 / decisions(ADR)/ runbook/
                                            README.md の影響マップ(変えたもの → 一緒に直す正本)を hook・検査が読む
```

`template/_gitignore` は生成時に `.gitignore` へリネームされる(スケルトンリポ内で効かせないため)。

## 使い方

### new-project skill から(通常)

Claude Code に「`<名前>` のプロジェクトを作って」「既存の `<パス>` にスケルトンを適用して」と頼む。
`SKILL.md` の手順で `init.py` が呼ばれる。配備は `SETUP.md`。

### init.py を直接

```bash
python3 scripts/init.py <生成先パス or プロジェクト名> --name <表示名> \
    [--slug <ascii>] [--desc "…"] [--owner "…"] \
    [--areas "CORE:共通コード,OPS:運用"] [--merge] [--no-git] [--dry-run]
```

- 第 1 引数にパス区切りが無ければ、このリポの**親ディレクトリ**直下に作る
- `--merge`: 既存フォルダに無いファイルだけ追加。既存は触らず、template と内容が異なるものは differs として一覧
- `--dry-run`: 書き込み・git・build を一切せず、作成予定だけ出す
- 生成後に `build.py` → `git init` + 初回コミット → `scripts/check_skeleton.py` を続けて実行する

### 検査

```bash
python3 scripts/check.py                       # スケルトン自身(NG 行 + pass=N fail=M)
python3 <生成先>/scripts/check_skeleton.py     # 生成先(同じ形式。--overview で概要 HTML だけ)
```

## 生成されるプロジェクトの要点

- `CLAUDE.md` 先頭に `<!-- project-skeleton vX.Y.Z generated YYYY-MM-DD -->`。どの版から作ったかが分かる
- `.claude/rules/`(作業領域・文書管理・機密)、`.claude/skills/`(work-placement / scratch / update-overview / update-env-info / task / sync-design-docs / audit-design-docs / pickup / harness)、`.claude/hooks/`(セッション文脈の注入・作業領域ガード・設計書追随・依頼文の手がかり・区切りの拾い)
- フェーズ(立ち上げ / 開発 / 運用)で厳しさが変わる。表は `python3 .claude/hooks/phase.py --table`、切り替えは `--set`。立ち上げ期は拾うだけ
- 作業中に出た決定・未決・あとでやることは「反映済・タスク・未決」のどれかに落とす(打合せ記録の各行に落ち先、未決の正本は課題 md)。ハーネスは `.claude/ハーネス台帳.md` に候補として書き、承認後に定義する
- skill に `allowed-tools` を書かない(未信頼のワークスペースで起動が拒否されるため。`check.py` が見る)
- `.work/` は git 管理外の作業領域。証跡・機密・一時・_bk の 4 枠
- `docs/案件/01_タスク管理/` は Markdown ファイル 1 枚 = 1 タスク。`build.py` が `data.js` と概要 HTML のスナップショットを更新
- `環境情報.md` `案件情報.md` `.env` は `.gitignore` 対象。公開しない情報はここに書く

## 外部から参照されているもの

移動・改名するときは以下を追従させる。

| 参照元 | 内容 |
|---|---|
| 各マシンの `~/.claude/skills/new-project` | このリポへのシンボリックリンク(Windows はジャンクション)。マシンごとに 1 回 `install-global` を実行 |
| 各マシンの `~/.claude/CLAUDE.md` | 「## 新規プロジェクト」節の 1 行(`SETUP.md` §4)。フォルダ名を書いている |
| 生成済みプロジェクトの `CLAUDE.md` 先頭行 | 版番号のみ。パスは持たない |

## スケルトンの更新手順

1. `template/` を直す(生成先のコピーを直しても他には反映されない)
2. `python3 scripts/check.py` で fail=0 を確認
3. `VERSION` を上げ、`CHANGELOG.md` の先頭に版・日付・変更・**既存プロジェクトへの適用**を書く
4. 既存プロジェクトへは `python3 scripts/init.py <既存パス> --name "<表示名>" --merge` で追加分を配り、differs は手で取り込む
5. リンク配備なら各マシンは自動で新版を見る。`--copy` で配備したマシンは `install-global --copy --force` で更新

## 制約

- **同期フォルダの中にリンクを置かない**。このリポは同期対象でよいが、`~/.claude/skills/new-project` のリンクは同期対象外の場所に置く(同期ツールがリンクをコピーや実体に変えるため)。リポ内にも symlink を置かない(`check.py` が見る)
- python3 が必要(標準ライブラリのみ)。Windows は `winget install Python.Python.3.12`
- git は無くても生成はできる(初回コミットだけ省かれる)
- 個人名・ホスト名・メールアドレス・実在の顧客名をこのリポに書かない(公開前提)
