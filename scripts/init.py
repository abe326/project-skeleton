#!/usr/bin/env python3
"""project-skeleton の template から案件フォルダを生成する。

使い方:
  python3 init.py <生成先パス or プロジェクト名> --name <表示名>
                  [--slug <ascii>] [--desc "…"] [--owner "…"]
                  [--areas "CORE:共通コード,OPS:運用"]
                  [--merge] [--no-git] [--dry-run]

第 1 引数にパス区切りが無ければ <job-work ルート>/<引数> に生成する。
job-work ルートはこのスクリプトの位置から求める(リポの親ディレクトリ)。
標準ライブラリのみ使用。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

SKELETON_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKELETON_ROOT / "template"
JOB_ROOT = SKELETON_ROOT.parent

# プレースホルダ置換の対象にする拡張子(小文字、ドット付き)。拡張子なしも対象
TEXT_EXTS = {
    ".md", ".html", ".py", ".json", ".js", ".sh", ".yml", ".yaml", ".toml",
    ".txt", ".example", ".gitignore", ".gitattributes", ".editorconfig",
}

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")

WORK_DIRS = ["証跡", "機密", "一時", "_bk"]
AREAS_JSON = Path("docs/案件/01_タスク管理/areas.json")
BUILD_PY = Path("docs/案件/01_タスク管理/build.py")
CHECK_PY = Path("scripts/check_skeleton.py")


# ---------------------------------------------------------------------------
# 補助
# ---------------------------------------------------------------------------

def setup_stdout() -> None:
    """Windows コンソールでも文字化けしないように UTF-8 へ切り替える。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def read_version() -> str:
    path = SKELETON_ROOT / "VERSION"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def slugify(text: str) -> str:
    """非 ASCII を削り、英数字以外を `-` に置き換えて小文字化する。"""
    ascii_only = text.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_only).strip("-").lower()
    return slug


def resolve_dest(arg: str) -> Path:
    if "/" in arg or "\\" in arg or os.sep in arg:
        return Path(arg).expanduser().resolve()
    return (JOB_ROOT / arg).resolve()


def is_text_file(rel: Path) -> bool:
    suffix = rel.suffix.lower()
    if suffix == "":
        return True
    return suffix in TEXT_EXTS


def parse_areas(spec: str) -> dict[str, str]:
    """`CORE:共通コード,OPS:運用` → {"共通コード": "CORE", "運用": "OPS"}"""
    result: dict[str, str] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise SystemExit(f"エラー: --areas の書式が不正です: {item!r}(PREFIX:名前 の形で指定)")
        prefix, name = item.split(":", 1)
        prefix, name = prefix.strip(), name.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9]*", prefix):
            raise SystemExit(f"エラー: 領域プレフィックスは大文字英数字にしてください: {prefix!r}")
        if not name:
            raise SystemExit(f"エラー: 領域名が空です: {item!r}")
        result[name] = prefix
    return result


def run(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    # パイプ経由でも子プロセスの出力と順序が入れ替わらないように先に吐き出す
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.run(cmd, cwd=str(cwd), env=env, check=check)


def git_available() -> bool:
    return shutil.which("git") is not None


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------

def main() -> int:
    setup_stdout()

    parser = argparse.ArgumentParser(
        description="project-skeleton の template から案件フォルダを生成する",
    )
    parser.add_argument("dest", help="生成先パス、またはプロジェクト名(job-work 直下に作る)")
    parser.add_argument("--name", required=True, help="プロジェクトの表示名")
    parser.add_argument("--slug", help="ASCII の識別子(省略時は --name から生成)")
    parser.add_argument("--desc", default="", help="1 行の説明")
    parser.add_argument("--owner", default="", help="担当者")
    parser.add_argument("--areas", default="", help='領域の追加 "CORE:共通コード,OPS:運用"')
    parser.add_argument("--merge", action="store_true", help="既存ディレクトリに無いファイルだけ追加する")
    parser.add_argument("--no-git", action="store_true", help="git init / commit をしない")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずに作成予定の一覧だけ出す")
    args = parser.parse_args()

    if not TEMPLATE_DIR.is_dir():
        print(f"エラー: template が見つかりません: {TEMPLATE_DIR}")
        return 2

    version = read_version()
    dest = resolve_dest(args.dest)
    dest_exists = dest.exists()

    if dest_exists and not dest.is_dir():
        print(f"エラー: 生成先がディレクトリではありません: {dest}")
        return 2
    if dest_exists and any(dest.iterdir()) and not args.merge:
        print(f"エラー: 生成先が既に存在します: {dest}")
        print("       既存プロジェクトにスケルトンを適用するには --merge を付けてください")
        return 2
    if args.merge and not dest_exists:
        print(f"注意: --merge が指定されましたが生成先は存在しません。新規作成として扱います: {dest}")

    slug = args.slug or slugify(args.name) or slugify(dest.name) or "project"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug):
        print(f"エラー: --slug は ASCII の英数字・._- のみにしてください: {slug!r}")
        return 2

    created_date = date.today().isoformat()
    values = {
        "{{PROJECT_NAME}}": args.name,
        "{{PROJECT_SLUG}}": slug,
        "{{PROJECT_DESC}}": args.desc,
        "{{CREATED}}": created_date,
        "{{OWNER}}": args.owner,
        "{{SKELETON_VERSION}}": version,
    }
    areas_to_add = parse_areas(args.areas) if args.areas else {}

    mode = "dry-run" if args.dry_run else ("merge" if args.merge else "new")
    print(f"project-skeleton v{version}")
    print(f"  生成先   : {dest}")
    print(f"  表示名   : {args.name}")
    print(f"  slug     : {slug}")
    print(f"  モード   : {mode}")
    print()

    created: list[str] = []
    skipped: list[str] = []
    differs: list[str] = []
    warnings: list[str] = []
    dirs_to_make: list[Path] = []

    # --- template を走査 -------------------------------------------------
    for dirpath, dirnames, filenames in os.walk(TEMPLATE_DIR):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        rel_dir = Path(dirpath).relative_to(TEMPLATE_DIR)
        dirs_to_make.append(dest / rel_dir)
        for fn in sorted(filenames):
            if fn.endswith(".pyc"):
                continue
            src = Path(dirpath) / fn
            out_name = ".gitignore" if fn == "_gitignore" else fn
            rel = rel_dir / out_name
            dst = dest / rel
            rel_str = rel.as_posix()

            raw = src.read_bytes()
            text_mode = is_text_file(rel)
            rendered: bytes = raw
            if text_mode:
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    warnings.append(f"UTF-8 として読めないためそのままコピー: {rel_str}")
                    text_mode = False
                else:
                    for key, val in values.items():
                        text = text.replace(key, val)
                    leftover = sorted(set(PLACEHOLDER_RE.findall(text)))
                    if leftover:
                        warnings.append(f"未知のプレースホルダが残っています: {rel_str}: {', '.join(leftover)}")
                    rendered = text.encode("utf-8")

            if dst.exists():
                skipped.append(rel_str)
                if text_mode:
                    try:
                        if dst.read_bytes() != rendered:
                            differs.append(rel_str)
                    except OSError:
                        pass
                continue

            created.append(rel_str)
            if args.dry_run:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(rendered)

    # --- dry-run はここで終了 -------------------------------------------
    if args.dry_run:
        print(f"作成予定 ({len(created)} 件):")
        for p in created:
            print(f"  + {p}")
        if skipped:
            print(f"既存のため保持 ({len(skipped)} 件)")
        if differs:
            print(f"template と内容が異なる既存ファイル ({len(differs)} 件):")
            for p in differs:
                print(f"  ~ {p}")
        for w in warnings:
            print(f"警告: {w}")
        print()
        print("dry-run のため書き込み・git・build は行っていません")
        return 0

    # --- ディレクトリ(空ディレクトリも含む) -------------------------
    for d in dirs_to_make:
        d.mkdir(parents=True, exist_ok=True)
    for name in WORK_DIRS:
        (dest / ".work" / name).mkdir(parents=True, exist_ok=True)

    # --- areas.json -----------------------------------------------------
    if areas_to_add:
        areas_path = dest / AREAS_JSON
        if areas_path.exists():
            try:
                data = json.loads(areas_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as e:
                warnings.append(f"areas.json を読めませんでした({e})。領域の追加をスキップ")
                data = None
            if isinstance(data, dict):
                areas = data.setdefault("areas", {})
                if not isinstance(areas, dict):
                    warnings.append("areas.json の areas が辞書ではありません。領域の追加をスキップ")
                else:
                    used = {v: k for k, v in areas.items()}
                    for name, prefix in areas_to_add.items():
                        if name in areas:
                            print(f"  領域 {name!r} は既に存在するため維持({areas[name]})")
                            continue
                        if prefix in used:
                            warnings.append(f"プレフィックス {prefix} は既に領域 {used[prefix]!r} で使われています({name!r} は追加せず)")
                            continue
                        areas[name] = prefix
                        used[prefix] = name
                        print(f"  領域を追加: {name} = {prefix}")
                    areas_path.write_bytes(
                        (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                    )
        else:
            warnings.append(f"{AREAS_JSON.as_posix()} が無いため領域を追加できません")

    # --- 実行ビット -----------------------------------------------------
    exec_files: list[str] = []
    for p in dest.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_file() and p.suffix in (".sh", ".py"):
            exec_files.append(p.relative_to(dest).as_posix())
            try:
                os.chmod(p, p.stat().st_mode | 0o111)
            except OSError:
                pass

    # --- build.py(data.js と概要 HTML のスナップショット) --------------
    build_py = dest / BUILD_PY
    if build_py.exists():
        print()
        print(f"== {BUILD_PY.as_posix()} を実行")
        r = run([sys.executable, str(build_py)], cwd=dest)
        if r.returncode != 0:
            warnings.append(f"build.py が exit {r.returncode} で終了しました")
    else:
        warnings.append(f"{BUILD_PY.as_posix()} が無いため build をスキップ")

    # --- git -----------------------------------------------------------
    if not args.no_git and not (dest / ".git").exists():
        print()
        if not git_available():
            warnings.append("git が見つからないため git init をスキップ")
        else:
            print("== git init")
            r = run(["git", "init", "-b", "main"], cwd=dest)
            if r.returncode != 0:
                # 古い git は -b 未対応
                run(["git", "init"], cwd=dest)
                run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=dest)
            run(["git", "add", "-A"], cwd=dest)
            if exec_files:
                run(["git", "update-index", "--chmod=+x", "--", *exec_files], cwd=dest)
            r = run(["git", "commit", "-q", "-m", f"chore: project-skeleton v{version} から生成"], cwd=dest)
            if r.returncode != 0:
                warnings.append("git commit に失敗しました(user.name / user.email 未設定の可能性)。手動でコミットしてください")
            else:
                print("  初回コミットを作成しました")
    elif (dest / ".git").exists():
        print()
        print("== .git が既にあるため git 操作はスキップ(変更は手動でコミット)")

    # --- check_skeleton.py ----------------------------------------------
    check_py = dest / CHECK_PY
    if check_py.exists():
        print()
        print(f"== {CHECK_PY.as_posix()} を実行")
        r = run([sys.executable, str(check_py)], cwd=dest)
        if r.returncode != 0:
            warnings.append("check_skeleton.py で NG があります(上の出力を確認)")
    else:
        warnings.append(f"{CHECK_PY.as_posix()} が無いため検査をスキップ")

    # --- まとめ -----------------------------------------------------------
    print()
    print("== 結果")
    print(f"  created={len(created)} skipped={len(skipped)} differs={len(differs)}")
    if created:
        print("  作成:")
        for p in created:
            print(f"    + {p}")
    if differs:
        print("  template と内容が異なる既存ファイル(必要なら手で取り込む):")
        for p in differs:
            print(f"    ~ {p}")
    for w in warnings:
        print(f"  警告: {w}")

    print()
    print("== 次にやること")
    print("  1. 環境情報.md / 案件情報.md を埋める(どちらも .gitignore 対象)")
    print("  2. docs/プロジェクト概要.html の目的・方針・フェーズを埋める")
    print("  3. CLAUDE.md §1 の 3 行と Global Constraints をプロジェクト固有の内容にする")
    print("  4. docs/案件/01_タスク管理/areas.json の領域を見直す(--areas で追加済みのものを含む)")
    if differs:
        print("  5. 上の differs を確認し、必要なら template の変更を手で取り込む")
    print("  * 他マシンと同期しているフォルダなら、同期が完了してから git を触る")

    return 0


if __name__ == "__main__":
    sys.exit(main())
