#!/usr/bin/env bash
# SessionStart hook: タスクの状況・概要 HTML の鮮度・環境情報の有無・当日の一時フォルダ数を 5 行以内で注入する。
# stdout はそのまま Claude のコンテキストに入る。秘密情報は出力しない。python が無くても動く。常に exit 0。
set -u
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

PY=""
if python3 -c "pass" >/dev/null 2>&1; then PY=python3
elif python -c "pass" >/dev/null 2>&1; then PY=python
fi

echo "## セッションコンテキスト（session_context.sh 自動注入）"

# 1) タスク（data.js の window.TASKS から open 件数・うち課題・最高優先）
TM="docs/案件/01_タスク管理"
DATA="$TM/data.js"
if [ -f "$DATA" ]; then
  line=""
  if [ -n "$PY" ]; then
    line=$("$PY" - "$DATA" <<'PYEOF' 2>/dev/null
import json, sys
s = open(sys.argv[1], encoding="utf-8").read()
i = s.find("window.TASKS")
if i < 0:
    sys.exit(1)
j = s.find("[", i)
arr, _ = json.JSONDecoder().raw_decode(s[j:])
op = [t for t in arr if t.get("state") == "open"]
issue = sum(1 for t in op if t.get("kind") == "課題")
top = sum(1 for t in op if t.get("priority") == "最高")
prog = sum(1 for t in op if t.get("status") == "進行中")
print(f"{len(op)} 件（課題 {issue}・最高 {top}・進行中 {prog}）")
PYEOF
    )
  fi
  if [ -z "$line" ]; then
    # python 無し・解析失敗時の概算（state/kind/priority を独立に数えるので厳密ではない）
    open_n=$(grep -o '"state" *: *"open"' "$DATA" 2>/dev/null | wc -l | tr -d ' ')
    issue_n=$(grep -o '"kind" *: *"課題"' "$DATA" 2>/dev/null | wc -l | tr -d ' ')
    top_n=$(grep -o '"priority" *: *"最高"' "$DATA" 2>/dev/null | wc -l | tr -d ' ')
    line="${open_n:-0} 件（課題 ${issue_n:-0}・最高 ${top_n:-0}。grep 概算）"
  fi
  echo "- タスク: open ${line}。一覧は ${TM}/index.html、起票・クローズは task スキル。着手前に work-placement スキルで紐づけ先を確定"
else
  echo "- タスク: ${DATA} が未生成（python3 ${TM}/build.py で生成）。着手前に work-placement スキルで紐づけ先を確定"
fi

# 2) 概要 HTML の最終更新日（BEGIN:updated … END:updated の間の日付）
OV="docs/プロジェクト概要.html"
if [ -f "$OV" ]; then
  upd=$(awk '/BEGIN:updated/{f=1} f{print} /END:updated/{f=0}' "$OV" 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
  echo "- 概要 HTML（${OV}）の最終更新: ${upd:-不明}。「3. 現在地」を読んでから着手。動いたら update-overview スキル"
else
  echo "- 概要 HTML（${OV}）が無い"
fi

# 3) 環境情報.md の有無（Git 管理外の正本。中身は出さない）
if [ -f "環境情報.md" ]; then
  echo "- 環境情報.md: あり（秘密の正本。値は転記しない。変えたら update-env-info スキル）"
else
  echo "- 環境情報.md: 無し（環境が増えたら update-env-info スキルで作る）"
fi

# 4) 当日の一時フォルダ数（.work/一時/YYYYMMDD_*）
today=$(date +%Y%m%d)
n=$(ls -d ".work/一時/${today}_"* 2>/dev/null | wc -l | tr -d ' ')
echo "- .work/一時/ の本日フォルダ: ${n:-0} 個。一時ファイルは .work/一時/${today}_用途/ へ（scratch スキル）"

exit 0
