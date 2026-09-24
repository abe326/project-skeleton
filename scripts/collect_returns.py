#!/usr/bin/env python3
"""案件で直したもののうち、スケルトンへ返す候補を集める(スケルトン側で使う)。

使い方: python3 scripts/collect_returns.py <案件パス> [<案件パス> …]

案件ごとに 2 つを出す。書き込みはしない。取り込むかどうかはスケルトンのセッションで決める。
  1. docs/ハーネス台帳.md の「返す」列に理由が書いてある行(案件の人・Claude が「スケルトンにも入れたい」と判断したもの)
  2. 仕組みのファイル(hook・scripts・skill・rules など)のうち、テンプレと中身が違うもの
     (init.py --merge --dry-run の「仕組み(取り込み推奨)」と同じ判定。案件側で直した可能性がある)
標準ライブラリのみ。exit 0 = 集めた、2 = 使い方の誤り。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SKELETON = Path(__file__).resolve().parent.parent
TEMPLATE = SKELETON / "template"
LEDGER = "docs/ハーネス台帳.md"
EMPTY = {"", "-", "—", "なし"}


def load_init():
    spec = importlib.util.spec_from_file_location("skeleton_init", SKELETON / "scripts/init.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ledger_returns(project: Path) -> list[str]:
    """台帳の「返す」列が空でない行を `HN-xx 内容 — 理由` で返す。列が無い・台帳が無ければ空。"""
    try:
        lines = (project / LEDGER).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    header: list[str] | None = None
    col = -1
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            header, col = None, -1
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
            col = next((i for i, h in enumerate(cells) if h.startswith("返す")), -1)
            continue
        if all(set(c) <= set(":- ") for c in cells) or col < 0 or col >= len(cells):
            continue
        if cells[col] not in EMPTY:
            what = cells[2] if len(cells) > 2 else ""
            out.append(f"{cells[0]} {what} — {cells[col]}")
    return out


def mechanism_diffs(project: Path, init) -> list[str]:
    """テンプレと中身が違う「仕組み」のファイル(ルート相対)。"""
    out: list[str] = []
    for src in sorted(p for p in TEMPLATE.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = src.relative_to(TEMPLATE)
        rel_str = (rel.parent / (".gitignore" if rel.name == "_gitignore" else rel.name)).as_posix()
        if not init.is_mechanism(rel_str) or rel_str in init.GENERATED_SKIP:
            continue
        dst = project / rel_str
        if not dst.is_file():
            continue
        try:
            if not init.same_content(rel_str, dst.read_bytes(), src.read_bytes()):
                out.append(rel_str)
        except OSError:
            pass
    return out


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if not argv or any(a in ("-h", "--help") for a in argv):
        print(__doc__.strip())
        return 0 if argv else 2
    init = load_init()
    for arg in argv:
        project = Path(arg).expanduser().resolve()
        print(f"== {project}")
        if not project.is_dir():
            print("  フォルダが無い")
            continue
        rets = ledger_returns(project)
        print(f"  台帳の「返す」: {len(rets)} 件")
        for r in rets:
            print(f"    - {r}")
        diffs = mechanism_diffs(project, init)
        print(f"  仕組みの差分(テンプレと違う): {len(diffs)} 件")
        for d in diffs:
            print(f"    ~ {d}")
    print()
    print("取り込むかはスケルトンのセッションで決める。取り込んだら template/ を直し、CHANGELOG に「還元元」を書く")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
