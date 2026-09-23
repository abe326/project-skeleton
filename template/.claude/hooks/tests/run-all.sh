#!/usr/bin/env bash
# hooks の回帰テスト。
#   1) work_area_guard: hook-cases-guard.txt の各行（<期待>\t<file_path>[\t<root>]）を PreToolUse の JSON にして
#      work_area_guard.sh へ流し、期待どおり allow / block になるかを見る
#   2) design_docs_reminder: hook-cases-reminder.txt の各行（<期待>\t<file_path>\t<含む文字列>\t<session_id>\t<root>）を
#      PostToolUse の JSON にして design_docs_reminder.sh へ流し、additionalContext の有無と内容を見る
#      （影響マップは template の docs/設計書/README.md の実物を使う）
#      3〜5 列目の空欄は `-` で書く。bash の `IFS=$'\t' read` は連続するタブを 1 つに畳むので、空のタブ区切りは列ずれを起こす。
#      末尾の列は省略してよい（guard 側は省略可能な列が最後の 1 つだけなので、この問題は起きない）
# 使い方: bash .claude/hooks/tests/run-all.sh   （pass=N fail=M を 1 本で出し、fail>0 なら exit 1）
set -u
here="$(cd "$(dirname "$0")" && pwd)"
root_default="$(cd "$here/../../.." && pwd)"
export CLAUDE_DOCS_REMINDER_STATE_DIR="$(mktemp -d)"
trap 'rm -rf "$CLAUDE_DOCS_REMINDER_STATE_DIR"' EXIT

PY=""
if python3 -c "pass" >/dev/null 2>&1; then PY=python3
elif python -c "pass" >/dev/null 2>&1; then PY=python
else echo "python が無いので実行できない"; exit 1
fi

pass=0; fail=0

# --- 1) work_area_guard ------------------------------------------------------
hook="$here/../work_area_guard.sh"
cases="$here/hook-cases-guard.txt"
while IFS=$'\t' read -r expect path root; do
  case "$expect" in ''|'#'*) continue ;; esac
  [ -n "${root:-}" ] || root="$root_default"
  json=$("$PY" -c 'import json,sys; print(json.dumps({"tool_name":"Write","tool_input":{"file_path":sys.argv[1]}}, ensure_ascii=False))' "$path")
  err=$(printf '%s' "$json" | CLAUDE_PROJECT_DIR="$root" bash "$hook" 2>&1 >/dev/null)
  rc=$?
  if [ "$rc" -eq 2 ]; then got=block; else got=allow; fi
  if [ "$got" = "$expect" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    printf 'NG guard expect=%s got=%s (rc=%s) : %s  [root=%s]\n    %s\n' "$expect" "$got" "$rc" "$path" "$root" "$err"
  fi
done < "$cases"

# --- 2) design_docs_reminder ---------------------------------------------------
hook="$here/../design_docs_reminder.sh"
cases="$here/hook-cases-reminder.txt"
# {WIN} = template ルートの Windows 形式（/mnt/c/x → C:\x、/c/x → C:\x）。変換できなければそのまま。
# ルート列の {WIN} は、Windows 上ではその形を、それ以外では実際に開ける root_default を使う（file_path 側だけ Windows 形式で流す）
win_root=$("$PY" -c 'import re,sys; p=sys.argv[1]; m=re.match(r"^/(?:mnt/)?([a-zA-Z])/(.*)$", p); print(m.group(1).upper()+":\\"+m.group(2).replace("/","\\") if m else p)' "$root_default")
case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) win_root_for_env="$win_root" ;; *) win_root_for_env="$root_default" ;; esac

run_reminder() {  # $1=tool_name $2=file_path $3=session_id $4=root → stdout
  local json
  json=$("$PY" -c 'import json,sys; d={"tool_name":sys.argv[1],"tool_input":{"file_path":sys.argv[2]}}
if sys.argv[3]: d["session_id"]=sys.argv[3]
print(json.dumps(d, ensure_ascii=False))' "$1" "$2" "$3")
  printf '%s' "$json" | CLAUDE_PROJECT_DIR="$4" bash "$hook" 2>/dev/null
}

while IFS=$'\t' read -r expect path want sid root; do
  case "$expect" in ''|'#'*) continue ;; esac
  [ "${want:-}" != "-" ] || want=""            # `-` は空欄
  [ "${sid:-}" != "-" ] || sid=""
  [ "${root:-}" != "-" ] || root=""
  path="${path//\{WIN\}/$win_root}"
  root="${root:-}"; root="${root//\{WIN\}/$win_root_for_env}"
  [ -n "$root" ] || root="$root_default"
  out=$(run_reminder Write "$path" "${sid:-}" "$root")
  case "$out" in *additionalContext*) got=remind ;; *) got=none ;; esac
  ok=1
  [ "$got" = "$expect" ] || ok=0
  if [ "$ok" -eq 1 ] && [ -n "${want:-}" ]; then
    case "$out" in *"$want"*) ;; *) ok=0 ;; esac
  fi
  if [ "$ok" -eq 1 ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    printf 'NG reminder expect=%s got=%s want=%s : %s  [sid=%s root=%s]\n    %s\n' "$expect" "$got" "${want:-}" "$path" "${sid:-}" "$root" "$out"
  fi
done < "$cases"

# tool_name が Read なら何も出さない
out=$(run_reminder Read "src/auth/login.py" "" "$root_default")
if [ -z "$out" ]; then pass=$((pass+1)); else fail=$((fail+1)); printf 'NG reminder tool_name=Read で出力があった:\n    %s\n' "$out"; fi

echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
