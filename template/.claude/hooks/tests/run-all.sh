#!/usr/bin/env bash
# work_area_guard の回帰テスト。hook-cases-guard.txt の各行（<期待>\t<file_path>[\t<root>]）を
# PreToolUse の JSON にして work_area_guard.sh へ流し、期待どおり allow / block になるかを集計する。
# 使い方: bash .claude/hooks/tests/run-all.sh   （pass=N fail=M を出し、fail>0 なら exit 1）
set -u
here="$(cd "$(dirname "$0")" && pwd)"
hook="$here/../work_area_guard.sh"
cases="$here/hook-cases-guard.txt"
root_default="$(cd "$here/../../.." && pwd)"

PY=""
if python3 -c "pass" >/dev/null 2>&1; then PY=python3
elif python -c "pass" >/dev/null 2>&1; then PY=python
else echo "python が無いので実行できない"; exit 1
fi

pass=0; fail=0
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
    printf 'NG expect=%s got=%s (rc=%s) : %s  [root=%s]\n    %s\n' "$expect" "$got" "$rc" "$path" "$root" "$err"
  fi
done < "$cases"

echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
