#!/usr/bin/env python3
"""設計書の鮮度を機械的に見る。

使い方: python3 scripts/docs_freshness.py [--days N] [--quiet] [--strict] [--json] [--list]

対象: docs/設計書/**/*.md（decisions/・runbook/・README.md を除く）。各文書の冒頭 20 行にある鮮度メタ行

    > 最終更新: YYYY-MM-DD（<タスクID>: 要点）／ 対象: <glob を・区切り> / repo@<short-sha> ／ 鮮度: 90日

を読み、次のどれかに当たる文書を「要確認」として挙げる。

  (a) メタ行が無い・日付が読めない
  (b) 今日 − 最終更新 > N 日（既定 30。--days N ＞ 環境変数 DOCS_FRESHNESS_DAYS ＞ 既定。
      メタ行の「鮮度: N日」が最優先。0 で無効）
  (c) 対象にパスがあり sha が実在し、git diff <sha>..HEAD -- <パス…> が非空 → ソース変更あり
  (c') git status --porcelain -- <パス…> が非空 → 未コミット変更あり
  (c'') パスがあるのに sha が無い → 鮮度検証不可。sha が git に無い → sha 不在
  git が無いとき (c) 系は見ない。

出力: 既定は `docs/設計書/xx.md: 理由; 理由` を 1 行ずつ + `N 本の要確認`（exit 0）。
--quiet は整数だけ（異常時は無出力・exit 0。session_context.sh 用）。--strict は N>0 で exit 1。
--json は [{"path","reasons"}]。--list は全文書の最終更新・対象の一覧（audit-design-docs 用）。
標準ライブラリのみ。プロジェクトルートはこのファイルの親の親。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN_DIR = ROOT / "docs/設計書"
EXCLUDE_DIRS = {"decisions", "runbook"}
HEAD_LINES = 20
DEFAULT_DAYS = 30

DATE_RE = re.compile(r"最終更新[:：]\s*(\d{4}-\d{2}-\d{2})")
TARGET_RE = re.compile(r"対象[:：]\s*(.*?)(?:\s*/\s*repo@|\s*／\s*鮮度|$)")
SHA_RE = re.compile(r"repo@([0-9a-fA-F]{7,40})")
DAYS_RE = re.compile(r"鮮度[:：]\s*(\d+)\s*日")


def iter_docs() -> list[Path]:
    if not DESIGN_DIR.is_dir():
        return []
    out = []
    for p in sorted(DESIGN_DIR.rglob("*.md")):
        rel = p.relative_to(DESIGN_DIR).parts
        if rel[0] in EXCLUDE_DIRS or p.name == "README.md":
            continue
        out.append(p)
    return out


def git(*args: str) -> str | None:
    """成功なら stdout、git が無い・失敗なら None。"""
    try:
        r = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def parse_meta(text: str) -> dict:
    head = "\n".join(text.splitlines()[:HEAD_LINES])
    meta: dict = {"date": None, "targets": [], "paths": [], "sha": None, "days": None, "raw_target": ""}
    m = DATE_RE.search(head)
    if m:
        try:
            meta["date"] = date.fromisoformat(m.group(1))
        except ValueError:
            pass
    line = next((l for l in head.splitlines() if "対象" in l and "最終更新" in l), "")
    m = TARGET_RE.search(line)
    if m:
        meta["raw_target"] = m.group(1).strip()
        tokens = [t.strip("`") for t in re.split(r"[・,、\s]+", m.group(1)) if t.strip("`")]
        meta["targets"] = tokens
        meta["paths"] = [t for t in tokens if any(c in t for c in "/*.")]
    m = SHA_RE.search(line)
    if m:
        meta["sha"] = m.group(1)
    m = DAYS_RE.search(line)
    if m:
        meta["days"] = int(m.group(1))
    return meta


def drop_ignored(paths: list[str], has_git: bool) -> list[str]:
    """.gitignore 対象（案件情報.md 等）は履歴を持たないので突合対象から外す。"""
    if not paths or not has_git:
        return paths
    try:
        r = subprocess.run(["git", "check-ignore", "--", *paths], cwd=str(ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=15)
        ignored = set(r.stdout.split())
    except (OSError, subprocess.SubprocessError):
        return paths
    return [p for p in paths if p not in ignored]


def evaluate(path: Path, days_default: int, has_git: bool, today: date) -> tuple[list[str], dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ["読めない"], {}
    meta = parse_meta(text)
    reasons: list[str] = []
    if meta["date"] is None:
        return ["メタ行なし（> 最終更新: YYYY-MM-DD（…）／ 対象: … が冒頭に無い、または日付が不正）"], meta
    days = meta["days"] if meta["days"] is not None else days_default
    if days > 0 and (today - meta["date"]).days > days:
        reasons.append(f"{(today - meta['date']).days} 日更新なし（閾値 {days} 日）")
    paths = drop_ignored(meta["paths"], has_git)
    if paths and has_git:
        sha = meta["sha"]
        if not sha:
            reasons.append("sha なし（鮮度検証不可）")
        elif git("cat-file", "-e", sha + "^" + "{commit}") is None:
            reasons.append(f"sha 不在（{sha}）")
        else:
            out = git("diff", "--name-only", f"{sha}..HEAD", "--", *paths) or ""
            changed = [l for l in out.splitlines() if l.strip()]
            if changed:
                reasons.append(f"ソース変更あり（{sha}..HEAD で {len(changed)} 件: {', '.join(changed[:3])}）")
        out = git("status", "--porcelain", "--", *paths) or ""
        dirty = [l for l in out.splitlines() if l.strip()]
        if dirty:
            reasons.append(f"未コミット変更あり（{len(dirty)} 件）")
    return reasons, meta


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    quiet, strict, as_json, as_list = "--quiet" in argv, "--strict" in argv, "--json" in argv, "--list" in argv
    days = DEFAULT_DAYS
    env_days = os.environ.get("DOCS_FRESHNESS_DAYS")
    if env_days and env_days.isdigit():
        days = int(env_days)
    if "--days" in argv:
        try:
            days = int(argv[argv.index("--days") + 1])
        except (IndexError, ValueError):
            print("--days には整数を指定する", file=sys.stderr)
            return 2

    try:
        docs = iter_docs()
        has_git = git("rev-parse", "--is-inside-work-tree") is not None
        today = date.today()
        results = []
        for p in docs:
            reasons, meta = evaluate(p, days, has_git, today)
            results.append((p.relative_to(ROOT).as_posix(), reasons, meta))
    except Exception as e:  # --quiet は無出力で通す（session_context.sh が行を出さない）
        if not quiet:
            print(f"エラー: {e}", file=sys.stderr)
        return 0

    flagged = [(rel, reasons) for rel, reasons, _ in results if reasons]
    if quiet:
        print(len(flagged))
        return 0
    if as_list:
        for rel, _, meta in results:
            d = meta.get("date")
            print(f"{d.isoformat() if d else '----------'}\t{rel}\t対象: {meta.get('raw_target') or '—'}"
                  f"{'  repo@' + meta['sha'] if meta.get('sha') else ''}")
        return 0
    if as_json:
        print(json.dumps([{"path": rel, "reasons": reasons} for rel, reasons in flagged], ensure_ascii=False))
    else:
        for rel, reasons in flagged:
            print(f"{rel}: {'; '.join(reasons)}")
        print(f"{len(flagged)} 本の要確認")
    return 1 if strict and flagged else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
