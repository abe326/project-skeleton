#!/usr/bin/env python3
"""scripts/collect_returns.py(案件からスケルトンへ返す候補を集める)のテスト。

実行: python3 scripts/tests/test_collect_returns.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKELETON = Path(__file__).resolve().parent.parent.parent
SCRIPT = SKELETON / "scripts/collect_returns.py"
TEMPLATE = SKELETON / "template"

LEDGER = """# ハーネス台帳

| ID | 観点 | 内容 | きっかけ(日付・出典) | 状態 | 定義先 | 更新 | 返す |
|---|---|---|---|---|---|---|---|
| HN-01 | 置き場 | 固定パスを許可 | 2026-09-24 | 定義済 | `.claude/project.json` | 2026-09-24 | 他の案件でも要る |
| HN-02 | 秘密 | 何か | 2026-09-24 | 候補 | — | 2026-09-24 | — |
"""


def run(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=60)


class CollectReturnsTest(unittest.TestCase):
    def test_ledger_and_mechanism_diff(self):
        with tempfile.TemporaryDirectory(prefix="skel-returns-") as tmp:
            root = Path(tmp) / "案件"
            (root / "docs").mkdir(parents=True)
            (root / "docs/ハーネス台帳.md").write_text(LEDGER, encoding="utf-8")
            hooks = root / ".claude/hooks"
            hooks.mkdir(parents=True)
            shutil.copy2(TEMPLATE / ".claude/hooks/phase.py", hooks / "phase.py")                 # 同じ → 出ない
            shutil.copy2(TEMPLATE / ".claude/hooks/drops.py", hooks / "drops.py")
            with (hooks / "drops.py").open("a", encoding="utf-8") as f:
                f.write("\n# 案件で直した\n")                                                    # 違う → 出る
            r = run(str(root))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("台帳の「返す」: 1 件", r.stdout)
            self.assertIn("HN-01 固定パスを許可 — 他の案件でも要る", r.stdout)
            self.assertNotIn("HN-02", r.stdout)
            self.assertIn("~ .claude/hooks/drops.py", r.stdout)
            self.assertNotIn("~ .claude/hooks/phase.py", r.stdout)

    def test_ledger_without_column(self):
        with tempfile.TemporaryDirectory(prefix="skel-returns-") as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs/ハーネス台帳.md").write_text(
                "| ID | 観点 | 内容 |\n|---|---|---|\n| HN-01 | x | y |\n", encoding="utf-8")
            r = run(str(root))
            self.assertIn("台帳の「返す」: 0 件", r.stdout)

    def test_usage(self):
        self.assertEqual(run().returncode, 2)


if __name__ == "__main__":
    unittest.main()
