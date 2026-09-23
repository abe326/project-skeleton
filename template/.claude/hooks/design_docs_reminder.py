#!/usr/bin/env python3
"""PostToolUse hook (Write|Edit|MultiEdit): ソースを変えたら設計書の更新候補をその場で思い出させる。

stdin の JSON から tool_input.file_path を読み、docs/設計書/README.md の影響マップ
（「## 変えたもの → 一緒に直す正本」表。解釈は impact_map.py）に当たれば、
hookSpecificOutput.additionalContext に更新候補を 1 行で返す。ブロックはしない（常に exit 0）。

  - ルート外・.work/・.claude/・docs/案件/01_タスク管理/ 配下は対象外
  - 同じ候補の組み合わせは session_id ごとに 1 回だけ出す（ノイズ抑制）。state は
    tempfile.gettempdir()/claude_docs_reminder_<session_id>.json。環境変数
    CLAUDE_DOCS_REMINDER_STATE_DIR で置き場を変えられる。session_id が無ければ毎回出す
  - 例外はすべて握りつぶして exit 0（編集を妨げない）
パスの正規化は work_area_guard.py と同じ（Windows / Git Bash / WSL 表記を吸収）。
"""
import json
import os
import re
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from impact_map import load_impact_map, match_rows, resolve_targets  # noqa: E402
from work_area_guard import relative_to_root  # noqa: E402

SKIP_PREFIXES = (".work/", ".claude/", "docs/案件/01_タスク管理/")
README = "docs/設計書/README.md"


def state_path(session_id: str) -> str:
    d = os.environ.get("CLAUDE_DOCS_REMINDER_STATE_DIR") or tempfile.gettempdir()
    safe = re.sub(r"[^A-Za-z0-9]", "_", session_id)[:128]
    return os.path.join(d, f"claude_docs_reminder_{safe}.json")


def already_seen(session_id: str, key: str) -> bool:
    """既出なら True。未出なら記録して False。"""
    path = state_path(session_id)
    seen: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            seen = list(json.load(f).get("seen", []))
    except Exception:
        pass
    if key in seen:
        return True
    seen.append(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"seen": seen}, f)
    except Exception:
        pass
    return False


def main() -> int:
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
        if data.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
            return 0
        tool_input = data.get("tool_input") or {}
        file_path = tool_input.get("file_path") or tool_input.get("path")
        if not file_path or not isinstance(file_path, str):
            return 0
        root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        rel = relative_to_root(file_path, root)
        if rel is None or rel.startswith(SKIP_PREFIXES):
            return 0
        rows = match_rows(rel, load_impact_map(os.path.join(root, README)))
        targets: list[str] = []
        for r in rows:
            targets += [t for t in r.targets if t not in targets]
        candidates = [t for t in resolve_targets(targets, root) if t != rel]
        if not candidates:
            return 0
        session_id = data.get("session_id")
        if isinstance(session_id, str) and session_id and already_seen(session_id, "|".join(sorted(candidates))):
            return 0
        msg = (f"[設計書追随] {rel} を変更。更新候補: {'、'.join(candidates)}。"
               f"同じ作業の中で sync-design-docs スキル（影響マップ: {README}）")
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}},
                         ensure_ascii=False))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
