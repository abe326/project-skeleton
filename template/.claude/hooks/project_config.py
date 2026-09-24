#!/usr/bin/env python3
"""案件ごとの設定 `.claude/project.json` を読む共有モジュール。標準ライブラリのみ。

テンプレのコード（hook・scripts）を案件で書き換えずに、案件の形の違いをここで受ける。
work_area_guard.py・impact_map.py・scripts/docs_freshness.py・scripts/check_skeleton.py が import する。

  work_area_allow  ルート相対の glob のリスト。置き場ガードが止めずに通す（仕組みの固定パス。例
                   `playwright.config.ts`・`.work/依存監査ログ.md`・`.work/一時/tldv同期/**`）。glob の解釈は impact_map.glob_matches
  nested_repos     ルート相対のフォルダのリスト。中に別の git リポがある（例 `repos/sub-repo`）。
                   影響マップの正本の解決と、鮮度メタの `<リポ名>@<sha>` の突き合わせに使う

`_` で始まるキーは説明用として無視する。読めない・壊れている・型が違うときは既定値（空）にして止めない。
形の誤りは `problems()` が返し、check_skeleton.py が NG にする。
"""
from __future__ import annotations

import json
import os

CONFIG = ".claude/project.json"
DEFAULTS: dict[str, list[str]] = {"work_area_allow": [], "nested_repos": []}


def _norm(p: str) -> str:
    p = p.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.rstrip("/") if p != "/" else p


def _read(root: str):
    """(中身, 読めなかった理由)。ファイルが無ければ ({}, None)。"""
    path = os.path.join(root, CONFIG)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return {}, None
    except OSError as e:
        return None, f"読めない（{e}）"
    try:
        return json.loads(text), None
    except ValueError as e:
        return None, f"JSON として読めない（{e}）"


def load(root: str) -> dict[str, list[str]]:
    """設定を返す。無い・壊れているキーは既定値。リストの中の文字列以外は捨てる。"""
    data, _ = _read(root)
    out = {k: list(v) for k, v in DEFAULTS.items()}
    if not isinstance(data, dict):
        return out
    for key in DEFAULTS:
        v = data.get(key)
        if isinstance(v, list):
            out[key] = [_norm(x) for x in v if isinstance(x, str) and _norm(x)]
    return out


def problems(root: str) -> list[str]:
    """形の誤り（check_skeleton.py 用）。無ければ空。"""
    data, err = _read(root)
    if err:
        return [f"{CONFIG}: {err}"]
    if not isinstance(data, dict):
        return [f"{CONFIG}: 最上位が JSON のオブジェクトでない"]
    out: list[str] = []
    for key, v in data.items():
        if key.startswith("_"):
            continue
        if key not in DEFAULTS:
            out.append(f"{CONFIG}: 知らないキー {key!r}（使えるのは {' / '.join(DEFAULTS)}。説明は `_` で始まるキーに）")
            continue
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            out.append(f"{CONFIG}: {key} は文字列のリスト")
            continue
        for x in v:
            n = _norm(x)
            if not n or n.startswith("/") or ":" in n or ".." in n.split("/"):
                out.append(f"{CONFIG}: {key} の {x!r} はルート相対のパスにする（絶対パス・.. は不可）")
            elif key == "nested_repos" and not os.path.isdir(os.path.join(root, n)):
                out.append(f"{CONFIG}: nested_repos の {x!r} がフォルダとして実在しない")
    return out


def nested_repo_of(rel: str, repos: list[str]) -> str | None:
    """rel（ルート相対 posix）を含む入れ子リポ（最長一致）。無ければ None。"""
    hits = [r for r in repos if rel == r or rel.startswith(r + "/")]
    return max(hits, key=len) if hits else None
