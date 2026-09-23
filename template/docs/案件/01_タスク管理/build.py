#!/usr/bin/env python3
"""
build.py — open/ closed/ screens/ の *.md を走査して data.js を生成する

Usage:
  python3 build.py            # data.js を生成し、docs/プロジェクト概要.html のスナップショットを更新
  python3 build.py --check    # 何も書かずに検証だけ行う（警告 0 なら終了コード 0、あれば 1）

生成物:
  data.js
    window.TASKS   = [...]   タスク（open/ closed/）
    window.SCREENS = [...]   画面（screens/）。tasks は screens: を持つタスクからの逆引き

  docs/プロジェクト概要.html（= ../../プロジェクト概要.html）
    <!-- BEGIN:task-snapshot --> 〜 <!-- END:task-snapshot --> の内側だけを置換する。
    ファイルやマーカーが無ければ警告のみで続行する。
"""
import datetime
import html
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
OPEN_DIR = BASE_DIR / "open"
CLOSED_DIR = BASE_DIR / "closed"
SCREENS_DIR = BASE_DIR / "screens"
OUT_PATH = BASE_DIR / "data.js"
SNAPSHOT_HTML = BASE_DIR.parent.parent / "プロジェクト概要.html"
SNAPSHOT_BEGIN = "<!-- BEGIN:task-snapshot -->"
SNAPSHOT_END = "<!-- END:task-snapshot -->"

VALID_STATUS = {"未着手", "進行中", "方針確定", "確認待ち", "保留", "完了"}
VALID_PRIORITY = {"最高", "高", "中", "低"}
VALID_KIND = {"タスク", "課題"}  # 分類（省略時はタスク）
VALID_SCREEN_STATUS = {"未着手", "実装中", "確認待ち", "完了", "保留"}
LIST_FIELDS = {"tags", "screens"}
PRIORITY_RANK = {"最高": 0, "高": 1, "中": 2, "低": 3}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    PyYAML を使わず Python 標準ライブラリのみでフロントマターをパースする。

    先頭の `---` から次の `---` までを取り出し、各行を最初の `:` で分割。
    tags / screens フィールドは `[a, b]` インラインリスト形式で扱う。
    本文はフロントマター終端以降の全文を返す。

    Returns:
        (fields dict, body str) のタプル。
        フロントマターが無ければ ({}, text) を返す。
    """
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        return {}, text

    # 終端 `---` を探す
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break

    if end is None:
        return {}, text

    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:])

    fields: dict = {}
    for line in fm_lines:
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()

        if key in LIST_FIELDS:
            # `[]` または `[a, b, c]` 形式
            inner = val.strip("[]").strip()
            if inner:
                fields[key] = [t.strip().strip("\"'") for t in inner.split(",") if t.strip()]
            else:
                fields[key] = []
        else:
            # 値が同一の囲み引用符（" または '）で挟まれていれば除去する。
            # 例: title: "[エピック] ..." → [エピック] ...
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("\"", "'"):
                val = val[1:-1]
            fields[key] = val

    return fields, body


def id_sort_key(item: dict) -> tuple:
    """
    ID を (prefix, number) でソートするキーを返す。
    例: QA-03 → ("QA", 3)、SCR-01 → ("SCR", 1)
    マッチしない場合は (id_string, 0) でフォールバック。
    """
    id_val = item.get("id", "")
    m = re.match(r"^([A-Za-z]+)-?(\d+)$", id_val)
    if m:
        return (m.group(1).upper(), int(m.group(2)))
    return (id_val, 0)


def read_md_files(folder: Path):
    """フォルダ内の *.md を (path, fields, body) で順に返す。id の無い md（付随資料）は除く。"""
    if not folder.is_dir():
        return
    for md_path in sorted(folder.glob("*.md")):
        if md_path.name.startswith("."):
            continue  # .gitkeep など隠しファイルはスキップ
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"⚠ 読み込み失敗 ({md_path.name}): {e}", file=sys.stderr)
            continue
        fields, body = parse_frontmatter(text)
        if not fields.get("id"):
            # frontmatter に id が無い md はタスク／画面ではなく付随資料
            # （「<ID>_内容_YYYYMMDD.md」併置規約）
            continue
        yield md_path, fields, body


def scan_folder(folder: Path, state: str) -> list[dict]:
    """
    フォルダ内の *.md を走査してタスクリストを返す。
    state はフォルダ名由来（"open" | "closed"）。
    """
    tasks = []
    for _, fields, body in read_md_files(folder):
        tasks.append({
            "id":       fields.get("id", ""),
            "title":    fields.get("title", ""),
            "area":     fields.get("area", ""),
            "status":   fields.get("status", ""),
            "priority": fields.get("priority", ""),
            "kind":     fields.get("kind", "") or "タスク",
            "epic":     fields.get("epic", ""),
            "owner":    fields.get("owner", ""),
            "tags":     fields.get("tags", []),
            "screens":  fields.get("screens", []),
            "source":   fields.get("source", ""),
            "created":  fields.get("created", ""),
            "updated":  fields.get("updated", ""),
            "closed":   fields.get("closed", ""),
            "state":    state,
            "body":     body,
        })
    return tasks


def scan_screens(folder: Path) -> list[dict]:
    """screens/ 内の *.md を走査して画面リストを返す。tasks は後で link_screens が埋める。"""
    screens = []
    for md_path, fields, body in read_md_files(folder):
        screens.append({
            "id":      fields.get("id", ""),
            "name":    fields.get("name", "") or md_path.stem,
            "path":    fields.get("path", ""),
            "status":  fields.get("status", ""),
            "owner":   fields.get("owner", ""),
            "tags":    fields.get("tags", []),
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "state":   "screen",
            "body":    body,
            "tasks":   [],
        })
    return screens


def link_screens(tasks: list[dict], screens: list[dict]) -> list[str]:
    """
    タスクの screens: から画面側の tasks を逆引き計算する。
    未知の SCR 参照は警告として返す。
    """
    warnings = []
    by_id = {s["id"]: s for s in screens}
    for t in tasks:
        for scr_id in t.get("screens", []):
            scr = by_id.get(scr_id)
            if scr is None:
                warnings.append(f"⚠ {t['id']}: screens に未知の画面 ID '{scr_id}'")
                continue
            scr["tasks"].append({
                "id":     t["id"],
                "title":  t["title"],
                "state":  t["state"],
                "status": t["status"],
                "kind":   t["kind"],
            })
    for s in screens:
        s["tasks"].sort(key=id_sort_key)
    return warnings


def validate_tasks(tasks: list[dict]) -> list[str]:
    """
    タスクリストをバリデーションして警告メッセージのリストを返す。
    警告は出すが処理は止めない。
    """
    warnings = []
    seen_ids: dict[str, str] = {}
    required_fields = ["id", "title", "area", "status", "priority"]

    for i, t in enumerate(tasks):
        label = t.get("id") or f"[index {i}]"

        # ID 重複チェック
        tid = t.get("id", "")
        if tid:
            if tid in seen_ids:
                warnings.append(
                    f"⚠ ID重複: {tid}（{seen_ids[tid]}/ と {t['state']}/ に同名ID）"
                )
            else:
                seen_ids[tid] = t["state"]

        # 必須欄欠落チェック
        for field in required_fields:
            if not t.get(field):
                warnings.append(f"⚠ {label}: 必須欄 '{field}' が空")

        # 許可値チェック（値がある場合のみ）
        s = t.get("status", "")
        if s and s not in VALID_STATUS:
            warnings.append(
                f"⚠ {label}: status '{s}' は許可値外"
                f"（許可: {'/'.join(sorted(VALID_STATUS))}）"
            )
        p = t.get("priority", "")
        if p and p not in VALID_PRIORITY:
            warnings.append(
                f"⚠ {label}: priority '{p}' は許可値外"
                f"（許可: {'/'.join(sorted(VALID_PRIORITY))}）"
            )
        k = t.get("kind", "")
        if k and k not in VALID_KIND:
            warnings.append(
                f"⚠ {label}: kind '{k}' は許可値外"
                f"（許可: {'/'.join(sorted(VALID_KIND))}）"
            )

    return warnings


def validate_screens(screens: list[dict]) -> list[str]:
    """画面リストをバリデーションして警告メッセージのリストを返す。"""
    warnings = []
    seen: set[str] = set()
    for s in screens:
        label = s.get("id") or "[画面]"
        if s["id"] in seen:
            warnings.append(f"⚠ 画面ID重複: {s['id']}")
        seen.add(s["id"])
        if not s.get("name"):
            warnings.append(f"⚠ {label}: 必須欄 'name' が空")
        st = s.get("status", "")
        if not st:
            warnings.append(f"⚠ {label}: 必須欄 'status' が空")
        elif st not in VALID_SCREEN_STATUS:
            warnings.append(
                f"⚠ {label}: status '{st}' は許可値外"
                f"（許可: {'/'.join(sorted(VALID_SCREEN_STATUS))}）"
            )
    return warnings


# ---------------------------------------------------------------------------
# プロジェクト概要 HTML のスナップショット
# ---------------------------------------------------------------------------

def build_snapshot_html(tasks: list[dict], screens: list[dict]) -> str:
    """概要 HTML に埋め込む断片（<p> と <table> のみ・外部依存なし）を生成する。"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    open_tasks = [t for t in tasks if t["state"] == "open"]
    closed_count = sum(1 for t in tasks if t["state"] == "closed")
    issue_count = sum(1 for t in open_tasks if t["kind"] == "課題")
    pending_count = sum(1 for t in open_tasks if t["status"] == "確認待ち")
    active_count = sum(1 for t in open_tasks if t["status"] == "進行中")
    scr_done = sum(1 for s in screens if s["status"] == "完了")

    top = sorted(
        open_tasks,
        key=lambda t: (PRIORITY_RANK.get(t["priority"], 9), id_sort_key(t)),
    )[:10]

    e = html.escape
    lines = [
        f"<p>生成: {now} ／ OPEN {len(open_tasks)} 件（課題 {issue_count}・確認待ち {pending_count}・進行中 {active_count}）"
        f"／ CLOSED {closed_count} 件</p>",
        f"<p>画面: 完了 {scr_done} / {len(screens)}</p>",
    ]
    if top:
        lines.append("<table>")
        lines.append("<tr><th>ID</th><th>タイトル</th><th>優先度</th><th>状態</th></tr>")
        for t in top:
            lines.append(
                f"<tr><td>{e(t['id'])}</td><td>{e(t['title'])}</td>"
                f"<td>{e(t['priority'])}</td><td>{e(t['status'])}</td></tr>"
            )
        lines.append("</table>")
    else:
        lines.append("<p>OPEN のタスクはありません。</p>")
    return "\n".join(lines) + "\n"


def update_snapshot(tasks: list[dict], screens: list[dict], check: bool) -> None:
    """
    docs/プロジェクト概要.html のマーカー内側を置換して書き戻す。
    ファイルやマーカーが無ければ注記のみで続行する（検証の警告数には数えない）。
    check=True のときは書き込まない。
    """
    if not SNAPSHOT_HTML.exists():
        print(f"注記: {SNAPSHOT_HTML} が無いためスナップショットはスキップ", file=sys.stderr)
        return
    text = SNAPSHOT_HTML.read_text(encoding="utf-8")
    b = text.find(SNAPSHOT_BEGIN)
    e = text.find(SNAPSHOT_END, b + len(SNAPSHOT_BEGIN)) if b >= 0 else -1
    if b < 0 or e < 0:
        print(f"注記: {SNAPSHOT_HTML.name} に {SNAPSHOT_BEGIN} / {SNAPSHOT_END} の対が無いためスキップ", file=sys.stderr)
        return
    if check:
        print(f"検証: {SNAPSHOT_HTML.name} のスナップショット対象あり（--check のため未更新）")
        return
    fragment = "\n" + build_snapshot_html(tasks, screens)
    new_text = text[:b + len(SNAPSHOT_BEGIN)] + fragment + text[e:]
    SNAPSHOT_HTML.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"更新: {SNAPSHOT_HTML.name} のスナップショット")


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> int:
    check = "--check" in sys.argv[1:]

    tasks: list[dict] = []
    tasks.extend(scan_folder(OPEN_DIR, "open"))
    tasks.extend(scan_folder(CLOSED_DIR, "closed"))
    # ID 順（プレフィックス → 数値）で安定ソート
    tasks.sort(key=id_sort_key)

    screens = scan_screens(SCREENS_DIR)
    screens.sort(key=id_sort_key)

    # バリデーション警告を stderr に出力（処理は継続）
    warnings = validate_tasks(tasks) + validate_screens(screens) + link_screens(tasks, screens)
    for w in warnings:
        print(w, file=sys.stderr)

    open_count = sum(1 for t in tasks if t["state"] == "open")
    closed_count = sum(1 for t in tasks if t["state"] == "closed")
    issue_open = sum(1 for t in tasks if t["state"] == "open" and t["kind"] == "課題")
    scr_done = sum(1 for s in screens if s["status"] == "完了")
    summary = (
        f"{len(tasks)}件（open {open_count}〔うち課題 {issue_open}〕 / closed {closed_count}）"
        f"、画面 {len(screens)}件（完了 {scr_done}）"
    )

    if check:
        print(f"検証: {summary}、警告 {len(warnings)} 件")
        update_snapshot(tasks, screens, check=True)
        return 1 if warnings else 0

    # data.js 書き出し
    content = (
        "window.TASKS = "
        + json.dumps(tasks, ensure_ascii=False, indent=2)
        + ";\n"
        "window.SCREENS = "
        + json.dumps(screens, ensure_ascii=False, indent=2)
        + ";\n"
    )
    OUT_PATH.write_text(content, encoding="utf-8", newline="\n")
    print(f"生成: {summary}")

    update_snapshot(tasks, screens, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
