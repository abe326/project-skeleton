#!/usr/bin/env python3
"""project-skeleton 自身の検査。

使い方: python3 scripts/check.py [-v]

出力: `NG <内容>` 行 + 最後に `pass=N fail=M`。fail>0 なら exit 1。
-v を付けると OK の行も出す。標準ライブラリのみ使用。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template"

KNOWN_PLACEHOLDERS = {
    "PROJECT_NAME", "PROJECT_SLUG", "PROJECT_DESC",
    "CREATED", "OWNER", "SKELETON_VERSION",
}

ROOT_REQUIRED = [
    "SKILL.md", "README.md", "SETUP.md", "CHANGELOG.md", "VERSION",
    "scripts/init.py", "scripts/check.py",
    "scripts/install-global.sh", "scripts/install-global.ps1",
]

TEMPLATE_REQUIRED = [
    "CLAUDE.md", "README.md", "CHANGELOG.md", "_gitignore",
    ".gitattributes", ".editorconfig", ".env.example",
    "環境情報.md", "案件情報.md",
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
    ".claude/hooks/tests/hook-cases-guard.txt",
    ".claude/hooks/tests/run-all.sh",
    ".work/README.md",
    ".work/証跡/.gitkeep", ".work/機密/.gitkeep", ".work/一時/.gitkeep", ".work/_bk/.gitkeep",
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
    "docs/設計書/01-overview.md",
    "docs/設計書/02-architecture.md",
    "docs/設計書/decisions/README.md",
    "docs/設計書/decisions/ADR-000-テンプレート.md",
]
TEMPLATE_REQUIRED_DIRS = [
    "docs/案件/01_タスク管理/open",
    "docs/案件/01_タスク管理/closed",
    "docs/案件/01_タスク管理/screens",
]

OVERVIEW_MARKERS = [
    "updated", "purpose", "principles", "phase", "decisions",
    "task-snapshot", "roadmap", "map", "history",
]

TEXT_EXTS = {
    ".md", ".html", ".py", ".json", ".js", ".sh", ".yml", ".yaml", ".toml",
    ".txt", ".example", ".gitignore", ".gitattributes", ".editorconfig", ".css",
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


def iter_template_text_files():
    for dirpath, dirnames, filenames in os.walk(TEMPLATE):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix == "" or p.suffix.lower() in TEXT_EXTS:
                yield p


def walk_json_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_json_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_json_strings(v)


# ---------------------------------------------------------------------------

def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # 1. ルートの必須ファイル
    for rel in ROOT_REQUIRED:
        check((ROOT / rel).is_file(), f"ルート必須ファイル: {rel}")

    # 2. SKILL.md の frontmatter
    fm = parse_frontmatter(ROOT / "SKILL.md")
    if check(fm is not None, "SKILL.md に frontmatter がある"):
        check(fm.get("name") == "new-project", "SKILL.md の name が new-project")
        check(bool(fm.get("description")), "SKILL.md の description が非空")

    # 3. VERSION と CHANGELOG
    version = ""
    try:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    check(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), f"VERSION が semver: {version!r}")
    try:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)
        check(m is not None and m.group(1) == version,
              f"CHANGELOG.md の最初の見出しが VERSION と一致: {m.group(1) if m else None} vs {version}")
    except OSError:
        ng("CHANGELOG.md を読めない")

    # 4. template のプレースホルダが既知 6 種のみ
    unknown: dict[str, set[str]] = {}
    for p in iter_template_text_files():
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            ng(f"UTF-8 として読めない: {p.relative_to(ROOT).as_posix()}")
            continue
        for m in re.finditer(r"\{\{([^{}\n]{1,40})\}\}", text):
            if m.group(1).strip() not in KNOWN_PLACEHOLDERS:
                unknown.setdefault(p.relative_to(ROOT).as_posix(), set()).add(m.group(0))
    if unknown:
        for f, names in sorted(unknown.items()):
            ng(f"未知のプレースホルダ {', '.join(sorted(names))}: {f}")
    else:
        ok("template のプレースホルダは既知 6 種のみ")

    # 5. symlink が無い
    links = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            if os.path.islink(p):
                links.append(p.relative_to(ROOT).as_posix())
    if links:
        for l in links:
            ng(f"symlink がある: {l}")
    else:
        ok("リポ内に symlink が無い")

    # 6. .ps1 が UTF-8 BOM
    for p in ROOT.rglob("*.ps1"):
        if ".git" in p.parts:
            continue
        head = p.read_bytes()[:3]
        check(head == b"\xef\xbb\xbf", f".ps1 が UTF-8 BOM: {p.relative_to(ROOT).as_posix()}")

    # 7. template の CLAUDE.md / _gitignore / .gitignore
    check((TEMPLATE / "CLAUDE.md").is_file(), "template/CLAUDE.md がある")
    check((TEMPLATE / "_gitignore").is_file(), "template/_gitignore がある")
    check(not (TEMPLATE / ".gitignore").exists(), "template/.gitignore が無い(_gitignore を使う)")

    # 8. settings.json と hooks
    settings_path = TEMPLATE / ".claude/settings.json"
    settings = None
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        ok("template/.claude/settings.json が JSON として読める")
    except (OSError, json.JSONDecodeError) as e:
        ng(f"template/.claude/settings.json を読めない: {e}")
    if isinstance(settings, dict):
        hooks = settings.get("hooks", {})
        referenced = set()
        for s in walk_json_strings(hooks):
            referenced.update(re.findall(r"\.claude/hooks/[\w./-]+\.sh", s))
        if not referenced:
            ng("settings.json の hooks に .claude/hooks/*.sh の参照が無い")
        for rel in sorted(referenced):
            check((TEMPLATE / rel).is_file(), f"hooks が参照するスクリプトが実在: {rel}")

    # 9. skills の frontmatter
    skills_dir = TEMPLATE / ".claude/skills"
    if skills_dir.is_dir():
        for d in sorted(skills_dir.iterdir()):
            if not d.is_dir():
                continue
            sfm = parse_frontmatter(d / "SKILL.md")
            if not check(sfm is not None, f"skill {d.name}: SKILL.md に frontmatter がある"):
                continue
            check(sfm.get("name") == d.name, f"skill {d.name}: name がディレクトリ名と一致({sfm.get('name')!r})")
            check(bool(sfm.get("description")), f"skill {d.name}: description が非空")
    else:
        ng("template/.claude/skills が無い")

    # 10. 概要 HTML
    overview = TEMPLATE / "docs/プロジェクト概要.html"
    try:
        html = overview.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        html = None
        ng("template/docs/プロジェクト概要.html を読めない")
    if html is not None:
        for name in OVERVIEW_MARKERS:
            b = len(re.findall(rf"<!--\s*BEGIN:{re.escape(name)}\s*-->", html))
            e = len(re.findall(rf"<!--\s*END:{re.escape(name)}\s*-->", html))
            check(b == 1 and e == 1, f"概要 HTML マーカー {name}: BEGIN={b} END={e}")
        check(not re.search(r"<script[^>]*\ssrc=", html, re.I), "概要 HTML に外部 <script src= が無い")
        check(not re.search(r"<link\s", html, re.I), "概要 HTML に <link が無い")
        check(bool(re.search(r'charset="utf-8"', html, re.I)), '概要 HTML に charset="UTF-8" がある')

    # 11. hooks のテスト
    run_all = TEMPLATE / ".claude/hooks/tests/run-all.sh"
    bash = shutil.which("bash")
    if not run_all.is_file():
        ng("template/.claude/hooks/tests/run-all.sh が無い")
    elif bash is None:
        print("skip hooks テスト(bash が無い)")
    else:
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        r = subprocess.run([bash, str(run_all)], cwd=str(TEMPLATE), env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if not check(r.returncode == 0, f"hooks テスト run-all.sh が exit 0(実際: {r.returncode})"):
            tail = (r.stdout + r.stderr).strip().splitlines()[-15:]
            for line in tail:
                print(f"   | {line}")

    # 12. template の必須ファイル
    for rel in TEMPLATE_REQUIRED:
        check((TEMPLATE / rel).is_file(), f"template 必須ファイル: {rel}")
    for rel in TEMPLATE_REQUIRED_DIRS:
        check((TEMPLATE / rel).is_dir(), f"template 必須ディレクトリ: {rel}")
    claude_md = TEMPLATE / "CLAUDE.md"
    if claude_md.is_file():
        first = claude_md.read_text(encoding="utf-8", errors="replace").lstrip().splitlines()[:1]
        check(bool(first) and first[0].startswith("<!-- project-skeleton v"),
              "template/CLAUDE.md の先頭が <!-- project-skeleton v… -->")

    print(f"pass={PASS} fail={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
