#!/usr/bin/env python3
"""PostToolUse hook (Write|Edit|MultiEdit): 触ったファイルを記録し、設計書・落ち先を思い出させる。

stdin の JSON から tool_input.file_path を読み、次の順に処理する。ブロックはしない（常に exit 0）。

  1. ルート内なら、触ったパスを pickup_state に記録する（Stop hook pickup_check.py の材料。.work/ も記録）
  2. 打合せ記録（docs/案件/02_打合せ/*.md）: フェーズに関係なく、ファイルごとにセッション 1 回
     「[落ち先] … 各行に落ち先 …」を返す（影響マップは引かない）
  3. それ以外は docs/設計書/README.md の影響マップ（解釈は impact_map.py。差し込み口
     .claude/hooks/impact_map_local.py があればその targets() の結果も足す）に当たれば、
     phase.level("design_docs_reminder", <フェーズ>) で出し分ける
       none → 何も出さない
       info（立ち上げ）→ セッションで 1 回だけ「[設計書候補] … 立ち上げ期は直さなくてよい …」
       warn（開発・運用）→ 候補の組み合わせごとに 1 回「[設計書追随] … 区切りで、決まったことを 1 行拾う」
     既出のキーにフェーズを含めるので、フェーズを切り替えた直後にはもう一度出る

  - .work/・.claude/・docs/案件/01_タスク管理/ 配下は 2・3 の対象外
  - フェーズは phase.read_phase(root)。import できない・読めないときは「立ち上げ」扱い（静かな側に倒す）
  - 既出の記録は pickup_state.already_seen（state は tempfile.gettempdir()/claude_docs_reminder_<session_id>.json。
    環境変数 CLAUDE_DOCS_REMINDER_STATE_DIR で置き場を変えられる）。session_id が無ければ毎回出す
  - 例外はすべて握りつぶして exit 0（編集を妨げない）
パスの正規化は work_area_guard.py と同じ（Windows / Git Bash / WSL 表記を吸収）。
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from impact_map import load_impact_map, local_targets, match_rows, resolve_targets  # noqa: E402
from work_area_guard import relative_to_root  # noqa: E402

SKIP_PREFIXES = (".work/", ".claude/", "docs/案件/01_タスク管理/")
README = "docs/設計書/README.md"
MEETING_DIR = "docs/案件/02_打合せ/"


def _pickup_state():
    try:
        import pickup_state  # noqa: WPS433
        return pickup_state
    except Exception:
        return None


def already_seen(session_id, key: str) -> bool:
    """既出なら True。session_id が無い・状態を扱えないときは False（毎回出す）。"""
    if not isinstance(session_id, str) or not session_id:
        return False
    ps = _pickup_state()
    if ps is None:
        return False
    try:
        return ps.already_seen(session_id, key)
    except Exception:
        return False


def record_touch(session_id, rel: str) -> None:
    ps = _pickup_state()
    if ps is None:
        return
    try:
        ps.append(session_id, "touch", rel)
    except Exception:
        pass


def current_level(root: str) -> tuple[str, str]:
    """(フェーズ, design_docs_reminder のレベル)。分からなければ (立ち上げ, info)。"""
    try:
        import phase as phase_mod  # noqa: WPS433
        ph = phase_mod.read_phase(root)
        return ph, phase_mod.level("design_docs_reminder", ph)
    except Exception:
        return "立ち上げ", "info"


def is_meeting(rel: str) -> bool:
    if not rel.startswith(MEETING_DIR) or not rel.endswith(".md"):
        return False
    name = rel[len(MEETING_DIR):]
    return "/" not in name and name != "README.md"


def candidate_example(candidates: list[str]) -> str:
    """落ち先の書き方の例（候補: 05 §n）。設計書の番号が取れなければ NN。"""
    for c in candidates:
        m = re.match(r"^docs/設計書/(\d{2})-", c)
        if m:
            return f"候補: {m.group(1)} §n"
    return "候補: NN §n"


def emit(msg: str) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}},
                     ensure_ascii=False))


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
        if rel is None:
            return 0
        session_id = data.get("session_id")
        record_touch(session_id, rel)

        # 打合せ記録: フェーズより先に分岐。影響マップは引かない
        if is_meeting(rel):
            if already_seen(session_id, f"meeting:{rel}"):
                return 0
            emit(f"[落ち先] {rel}: 決定・未決・宿題の各行に落ち先（→ 反映済: 01 §3 / → APP-03 / → 未決 QA-01）。"
                 "ID は起票してから書く。区切りで pickup スキル")
            return 0

        if rel.startswith(SKIP_PREFIXES):
            return 0
        rows = match_rows(rel, load_impact_map(os.path.join(root, README)))
        targets: list[str] = []
        for r in rows:
            targets += [t for t in r.targets if t not in targets]
        targets += [t for t in local_targets(rel, root) if t not in targets]   # 差し込み口（任意）
        candidates = [t for t in resolve_targets(targets, root) if t != rel]
        if not candidates:
            return 0

        phase, lvl = current_level(root)
        if lvl == "none":
            return 0
        if lvl == "info":
            # 立ち上げ期: 候補の組み合わせに関係なくセッションで 1 回だけ
            if already_seen(session_id, f"phase:{phase}:info"):
                return 0
            emit(f"[設計書候補] {rel} の変更は {'、'.join(candidates)} に関わる。{phase}期は直さなくてよい。"
                 f"決まったことなら落ち先に「→ {candidate_example(candidates)}」と書く（pickup スキル）")
            return 0
        if already_seen(session_id, f"phase:{phase}|" + "|".join(sorted(candidates))):
            return 0
        emit(f"[設計書追随] {rel} を変更。更新候補: {'、'.join(candidates)}。"
             f"区切りで、決まったことを 1 行拾う（sync-design-docs スキル。影響マップ: {README}）")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
