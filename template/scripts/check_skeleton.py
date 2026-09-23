#!/usr/bin/env python3
"""このプロジェクトがスケルトンの構成を保っているかを検査する。

使い方: python3 scripts/check_skeleton.py [--overview] [-v]

出力: `NG <内容>` 行 + 最後に `pass=N fail=M`。fail>0 なら exit 1。
--overview は docs/プロジェクト概要.html の項目だけを検査する。
標準ライブラリのみ使用。プロジェクトルートはこのファイルの親の親。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "CLAUDE.md", "README.md", "CHANGELOG.md", ".gitignore",
    ".gitattributes", ".editorconfig", ".env.example",
    ".claude/settings.json",
    ".claude/rules/work-area.md",
    ".claude/rules/docs-management.md",
    ".claude/rules/secrets.md",
    ".claude/skills/work-placement/SKILL.md",
    ".claude/skills/scratch/SKILL.md",
    ".claude/skills/update-overview/SKILL.md",
    ".claude/skills/update-env-info/SKILL.md",
    ".claude/skills/task/SKILL.md",
    ".claude/hooks/session_context.sh",
    ".claude/hooks/work_area_guard.sh",
    ".claude/hooks/work_area_guard.py",
    ".work/README.md",
    "scripts/check_skeleton.py",
    "docs/README.md",
    "docs/プロジェクト概要.html",
    "docs/案件/README.md",
    "docs/案件/01_タスク管理/README.md",
    "docs/案件/01_タスク管理/new.py",
    "docs/案件/01_タスク管理/close.py",
    "docs/案件/01_タスク管理/screen.py",
    "docs/案件/01_タスク管理/build.py",
    "docs/案件/01_タスク管理/areas.json",
    "docs/案件/01_タスク管理/index.html",
    "docs/案件/01_タスク管理/data.js",
    "docs/案件/02_打合せ/README.md",
    "docs/案件/確認依頼一覧.md",
    "docs/設計書/README.md",
    "docs/設計書/decisions/README.md",
]
REQUIRED_DIRS = [
    ".work/証跡", ".work/機密", ".work/一時", ".work/_bk",
    "docs/案件/01_タスク管理/open",
    "docs/案件/01_タスク管理/closed",
    "docs/案件/01_タスク管理/screens",
]
RULES = ["work-area.md", "docs-management.md", "secrets.md"]

GITIGNORE_REQUIRED = [
    ".work/", "環境情報.md", "案件情報.md", ".env", ".mcp.json",
    ".claude/settings.local.json",
]

OVERVIEW_MARKERS = [
    "updated", "purpose", "principles", "phase", "decisions",
    "task-snapshot", "roadmap", "map", "history",
]

# CLAUDE.md 内のパス記述のうち、実在チェックから除外するパターン
PATH_PATTERN_HINTS = ("YYYY", "MMDD", "NNN", "<", ">", "{", "}", "*", "…", "...", "xxx", "XXX", "用途", "例")

TEXT_EXTS = {
    ".md", ".html", ".py", ".json", ".js", ".sh", ".yml", ".yaml", ".toml",
    ".txt", ".example", ".css",
}

VERBOSE = "-v" in sys.argv[1:]
PASS = 0
FAIL = 0


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    if VERBOSE:
        print(f"OK {msg}")


def ng(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"NG {msg}")


def check(cond: bool, msg: str) -> bool:
    (ok if cond else ng)(msg)
    return cond


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return None


def walk_json_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_json_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_json_strings(v)


def check_overview() -> None:
    overview = ROOT / "docs/プロジェクト概要.html"
    try:
        html = overview.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        ng("docs/プロジェクト概要.html を読めない")
        return
    for name in OVERVIEW_MARKERS:
        b = len(re.findall(rf"<!--\s*BEGIN:{re.escape(name)}\s*-->", html))
        e = len(re.findall(rf"<!--\s*END:{re.escape(name)}\s*-->", html))
        check(b == 1 and e == 1, f"概要 HTML マーカー {name}: BEGIN={b} END={e}")
    check(not re.search(r"<script[^>]*\ssrc=", html, re.I), "概要 HTML に外部 <script src= が無い")
    check(not re.search(r"<link\s[^>]*href=", html, re.I), "概要 HTML に外部 <link href= が無い")
    check(bool(re.search(r'charset="utf-8"', html, re.I)), '概要 HTML に charset="UTF-8" がある')


def check_all() -> None:
    # 必須ファイル・ディレクトリ
    for rel in REQUIRED_FILES:
        check((ROOT / rel).is_file(), f"必須ファイル: {rel}")
    for rel in REQUIRED_DIRS:
        check((ROOT / rel).is_dir(), f"必須ディレクトリ: {rel}")

    # CLAUDE.md 内の相対パスが実在
    claude_md = ROOT / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text(encoding="utf-8", errors="replace")
        seen: set[str] = set()
        for m in re.finditer(r"`((?:docs|\.claude|scripts|\.work)/[^`\s]+)`", text):
            rel = m.group(1)
            if rel in seen or any(h in rel for h in PATH_PATTERN_HINTS):
                continue
            seen.add(rel)
            target = ROOT / rel.rstrip("/")
            check(target.exists(), f"CLAUDE.md が参照するパスが実在: {rel}")
        if not seen:
            ok("CLAUDE.md に検査対象のパス記述なし")

    # skills の frontmatter
    skills_dir = ROOT / ".claude/skills"
    if skills_dir.is_dir():
        for d in sorted(skills_dir.iterdir()):
            if not d.is_dir():
                continue
            fm = parse_frontmatter(d / "SKILL.md")
            if not check(fm is not None, f"skill {d.name}: SKILL.md に frontmatter がある"):
                continue
            check(fm.get("name") == d.name, f"skill {d.name}: name がディレクトリ名と一致({fm.get('name')!r})")
            check(bool(fm.get("description")), f"skill {d.name}: description が非空")

    # rules 3 本
    for name in RULES:
        check((ROOT / ".claude/rules" / name).is_file(), f"rules: {name}")

    # settings.json の hooks が実在
    settings = None
    try:
        settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        ok(".claude/settings.json が JSON として読める")
    except (OSError, json.JSONDecodeError) as e:
        ng(f".claude/settings.json を読めない: {e}")
    if isinstance(settings, dict):
        referenced = set()
        for s in walk_json_strings(settings.get("hooks", {})):
            referenced.update(re.findall(r"\.claude/hooks/[\w./-]+\.(?:sh|py)", s))
        for rel in sorted(referenced):
            check((ROOT / rel).is_file(), f"hooks が参照するスクリプトが実在: {rel}")

    # プレースホルダ残存なし
    leftovers: dict[str, set[str]] = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".work", "__pycache__", "node_modules")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix != "" and p.suffix.lower() not in TEXT_EXTS:
                continue
            try:
                t = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            found = set(re.findall(r"\{\{[A-Z_]+\}\}", t))
            if found:
                leftovers[p.relative_to(ROOT).as_posix()] = found
    if leftovers:
        for f, names in sorted(leftovers.items()):
            ng(f"プレースホルダが残っている {', '.join(sorted(names))}: {f}")
    else:
        ok("プレースホルダの残存なし")

    # 概要 HTML
    check_overview()

    # .gitignore
    gi = ROOT / ".gitignore"
    if gi.is_file():
        lines = {
            l.strip().lstrip("/").rstrip("/")
            for l in gi.read_text(encoding="utf-8", errors="replace").splitlines()
            if l.strip() and not l.strip().startswith("#")
        }
        for entry in GITIGNORE_REQUIRED:
            check(entry.rstrip("/") in lines, f".gitignore に {entry} がある")

    # build.py --check
    build_py = ROOT / "docs/案件/01_タスク管理/build.py"
    if build_py.is_file():
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        r = subprocess.run([sys.executable, str(build_py), "--check"], cwd=str(ROOT), env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if not check(r.returncode == 0, f"build.py --check が exit 0(実際: {r.returncode})"):
            for line in (r.stdout + r.stderr).strip().splitlines()[-10:]:
                print(f"   | {line}")

    # areas.json
    areas_path = ROOT / "docs/案件/01_タスク管理/areas.json"
    if areas_path.is_file():
        try:
            data = json.loads(areas_path.read_text(encoding="utf-8"))
            check(isinstance(data, dict) and isinstance(data.get("areas"), dict),
                  "areas.json の areas が dict")
        except (OSError, json.JSONDecodeError) as e:
            ng(f"areas.json を読めない: {e}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if "--overview" in sys.argv[1:]:
        check_overview()
    else:
        check_all()
    print(f"pass={PASS} fail={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
