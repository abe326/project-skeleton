#!/usr/bin/env python3
"""
close.py — タスクを open/ から closed/ へ移動（またはその逆）

Usage:
  python3 close.py <ID>             # クローズ: open/ → closed/
  python3 close.py --reopen <ID>    # 再オープン: closed/ → open/

例:
  python3 close.py QA-03
  python3 close.py --reopen QA-03

フロントマター書き換えユーティリティ（split_frontmatter / set_field / rewrite_md /
find_md）は screen.py からも import して使う。
"""
import datetime
import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
OPEN_DIR = BASE_DIR / "open"
CLOSED_DIR = BASE_DIR / "closed"


# ---------------------------------------------------------------------------
# フロントマター書き換えユーティリティ
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, list[str], str]:
    """
    テキストを (open_delimiter, fm_lines, rest) に分割する。

    open_delimiter: "---\n"（先頭行）
    fm_lines:       フロントマター本体の行リスト（keepends=True）
    rest:           "---\n" + 本文（フロントマター終端以降）

    フロントマターが無ければ ("", [], text) を返す。
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", [], text

    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break

    if end is None:
        return "", [], text

    open_delim = lines[0]                     # "---\n"
    fm_lines = lines[1:end]                   # フロントマター行（改行付き）
    rest = "".join(lines[end:])               # "---\n" + 本文

    return open_delim, fm_lines, rest


def set_field(fm_lines: list[str], field: str, value: str) -> list[str]:
    """
    fm_lines 内の `field:` 行を `field: value` に書き換えて返す。
    該当行が無ければ末尾に追加する。
    """
    result = []
    found = False
    for line in fm_lines:
        # 行頭が `field:` で始まる行を対象にする
        if re.match(rf"^{re.escape(field)}\s*:", line):
            result.append(f"{field}: {value}\n")
            found = True
        else:
            result.append(line)
    if not found:
        result.append(f"{field}: {value}\n")
    return result


def rewrite_md(text: str, updates: dict[str, str]) -> str:
    """
    md テキストのフロントマター内の複数フィールドを一括書き換えて返す。
    """
    open_delim, fm_lines, rest = split_frontmatter(text)
    if not open_delim:
        # フロントマターが無い場合は変更しない
        return text

    for field, value in updates.items():
        fm_lines = set_field(fm_lines, field, value)

    return open_delim + "".join(fm_lines) + rest


# ---------------------------------------------------------------------------
# ファイル検索
# ---------------------------------------------------------------------------

def find_md(folder: Path, id_: str) -> Path | None:
    """
    フォルダ内で ID に対応する「本体」の md ファイルを返す。
    ファイル名は `<ID>.md` または `<ID>_<slug>.md` 形式を想定。

    同じ ID prefix の付随資料（`<ID>_内容_YYYYMMDD.md` 等・フロントマター無し）が
    併置されている場合があるため、候補が複数あるときはフロントマターに
    `id: <ID>` を持つファイルを本体として優先する。
    """
    id_upper = id_.upper()
    candidates = []
    for md in folder.glob("*.md"):
        stem_upper = md.stem.upper()
        # 完全一致 or `<ID>_` で始まる
        if stem_upper == id_upper or stem_upper.startswith(f"{id_upper}_"):
            candidates.append(md)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    for md in candidates:
        _, fm_lines, _ = split_frontmatter(md.read_text(encoding="utf-8"))
        for line in fm_lines:
            if re.match(rf"^id\s*:\s*{re.escape(id_)}\s*$", line.strip(), re.IGNORECASE):
                return md
    return candidates[0]


def move_attachments(src_dir: Path, dst_dir: Path, id_: str, main_md: Path) -> None:
    """
    タスク本体と同じ ID prefix の付随資料（`<ID>_*.md` / `.png` / `.html` 等）を
    本体と同じフォルダへ随伴移動する（付随資料の併置ルールに追随）。
    """
    id_upper = id_.upper()
    for f in sorted(src_dir.glob("*")):
        if f.name == main_md.name or not f.is_file():
            continue
        if f.stem.upper().startswith(f"{id_upper}_"):
            (dst_dir / f.name).write_bytes(f.read_bytes())
            f.unlink()
            print(f"付随資料: {f.name}  {src_dir.name}/ → {dst_dir.name}/")


# ---------------------------------------------------------------------------
# クローズ / 再オープン
# ---------------------------------------------------------------------------

def do_close(id_: str, today: str) -> None:
    """open/ → closed/ に移動し、status/closed/updated を更新する。"""
    src = find_md(OPEN_DIR, id_)
    if src is None:
        print(f"エラー: open/ に ID '{id_}' が見つかりません", file=sys.stderr)
        sys.exit(1)

    text = src.read_text(encoding="utf-8")
    new_text = rewrite_md(text, {
        "status":  "完了",
        "closed":  today,
        "updated": today,
    })

    CLOSED_DIR.mkdir(parents=True, exist_ok=True)
    dst = CLOSED_DIR / src.name
    dst.write_text(new_text, encoding="utf-8", newline="\n")
    src.unlink()
    print(f"クローズ: {src.name}  open/ → closed/")
    move_attachments(OPEN_DIR, CLOSED_DIR, id_, src)


def do_reopen(id_: str, today: str) -> None:
    """closed/ → open/ に移動し、status をリセット・closed をクリアする。"""
    src = find_md(CLOSED_DIR, id_)
    if src is None:
        print(f"エラー: closed/ に ID '{id_}' が見つかりません", file=sys.stderr)
        sys.exit(1)

    text = src.read_text(encoding="utf-8")
    new_text = rewrite_md(text, {
        "status":  "未着手",
        "closed":  "",
        "updated": today,
    })

    OPEN_DIR.mkdir(parents=True, exist_ok=True)
    dst = OPEN_DIR / src.name
    dst.write_text(new_text, encoding="utf-8", newline="\n")
    src.unlink()
    print(f"再オープン: {src.name}  closed/ → open/")
    move_attachments(CLOSED_DIR, OPEN_DIR, id_, src)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    if not args:
        print("Usage: python3 close.py <ID>", file=sys.stderr)
        print("       python3 close.py --reopen <ID>", file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today().isoformat()

    if args[0] == "--reopen":
        if len(args) < 2:
            print("エラー: --reopen には ID が必要です", file=sys.stderr)
            sys.exit(1)
        do_reopen(args[1], today)
    else:
        do_close(args[0], today)

    # data.js を更新
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "build.py")],
        capture_output=False,
    )
    if result.returncode != 0:
        print("警告: build.py の実行に失敗しました", file=sys.stderr)


if __name__ == "__main__":
    main()
