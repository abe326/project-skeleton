#!/usr/bin/env bash
# project-skeleton をグローバル skill `new-project` として配備する(Linux / macOS)。
#
#   bash scripts/install-global.sh [--force] [--copy]
#
#   既定  : ~/.claude/skills/new-project → このリポ のシンボリックリンクを作る
#   --force: 既存のリンク・ディレクトリを置き換える
#   --copy : リンクではなくコピーで配備する(INSTALLED-AS-COPY.txt を置く)
set -euo pipefail

SKELETON="$(cd "$(dirname "$0")/.." && pwd -P)"
LINK="$HOME/.claude/skills/new-project"
FORCE=0
COPY=0

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --copy)  COPY=1 ;;
    -h|--help)
      sed -n '2,9p' "$0"
      exit 0 ;;
    *) echo "不明な引数: $arg" >&2; exit 2 ;;
  esac
done

case "${OSTYPE:-}" in
  msys*|cygwin*)
    echo "Windows では scripts/install-global.ps1 を使ってください" >&2
    echo "(Git Bash の ln -s はコピーになり、正本と分かれてしまいます)" >&2
    echo "  powershell -ExecutionPolicy Bypass -File \"$SKELETON/scripts/install-global.ps1\"" >&2
    exit 1 ;;
esac

if [ ! -f "$SKELETON/SKILL.md" ]; then
  echo "エラー: $SKELETON に SKILL.md がありません" >&2
  exit 1
fi

mkdir -p "$HOME/.claude/skills"

# --- 既存の確認 ---------------------------------------------------------
if [ -L "$LINK" ]; then
  current="$(cd "$LINK" 2>/dev/null && pwd -P || readlink "$LINK")"
  if [ "$COPY" -eq 0 ] && [ "$current" = "$SKELETON" ]; then
    echo "OK 設定済み: $LINK -> $SKELETON"
    exit 0
  fi
  if [ "$FORCE" -eq 0 ]; then
    echo "警告: $LINK は別の先を指しています: $current" >&2
    echo "      置き換えるには --force を付けてください" >&2
    exit 1
  fi
  rm "$LINK"
elif [ -e "$LINK" ]; then
  if [ "$FORCE" -eq 0 ]; then
    echo "警告: $LINK が既に存在します(リンクではありません)" >&2
    echo "      置き換えるには --force を付けてください(既存は削除されます)" >&2
    exit 1
  fi
  rm -rf "$LINK"
fi

# --- 配備 -----------------------------------------------------------------
if [ "$COPY" -eq 1 ]; then
  cp -R "$SKELETON" "$LINK"
  rm -rf "$LINK/.git"
  {
    echo "このフォルダは project-skeleton のコピーです(リンクではありません)。"
    echo "正本: $SKELETON"
    echo "コピー日: $(date +%Y-%m-%d)"
    echo "正本を更新したら install-global.sh --copy --force で配備し直してください。"
  } > "$LINK/INSTALLED-AS-COPY.txt"
  echo "コピーで配備しました: $LINK"
else
  ln -s "$SKELETON" "$LINK"
  echo "リンクを作成しました: $LINK -> $SKELETON"
fi

# --- 検証 -----------------------------------------------------------------
fail=0
if [ -r "$LINK/SKILL.md" ]; then
  echo "OK $LINK/SKILL.md を読めます"
else
  echo "NG $LINK/SKILL.md を読めません" >&2
  fail=1
fi
if [ -n "$(find "$SKELETON" -path "$SKELETON/.git" -prune -o -type l -print | head -n 1)" ]; then
  echo "NG リポ内に symlink があります(同期・公開の妨げになります)" >&2
  find "$SKELETON" -path "$SKELETON/.git" -prune -o -type l -print >&2
  fail=1
else
  echo "OK リポ内に symlink はありません"
fi

cat <<EOS

次に:
  1. Claude Code を新規セッションで起動し、\`/\` を打って new-project が出ることを確認
  2. ~/.claude/CLAUDE.md への追記は SETUP.md §4 の文面をそのまま使う
  3. ~/.claude はマシンごとに別です。もう一方のマシンでも同じ手順が必要です
EOS

exit "$fail"
