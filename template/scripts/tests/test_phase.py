"""phase.py（フェーズの読み書き・厳しさの表・CLI）のテスト。"""
from __future__ import annotations

import difflib
import json
import os
import subprocess
import unittest
from unittest import mock

from _util import TempProject, overview_html, run_py, write

import phase

OV = "docs/プロジェクト概要.html"
CLI = (".claude/hooks/phase.py",)


class ReadPhase(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop(phase.ENV_PHASE, None)

    def tearDown(self):
        self.env.stop()

    def test_three_values(self):
        for p in phase.PHASES:
            with TempProject() as root:
                write(root / OV, overview_html(p))
                self.assertEqual(phase.read_phase(root), p)
                self.assertEqual(phase.phase_status(root), (p, None))

    def test_no_attribute(self):
        with TempProject() as root:
            write(root / OV, overview_html(None))
            self.assertEqual(phase.phase_status(root), ("立ち上げ", "属性なし"))

    def test_bad_value(self):
        with TempProject() as root:
            write(root / OV, overview_html("本番"))
            self.assertEqual(phase.read_phase(root), "立ち上げ")
            self.assertEqual(phase.phase_status(root)[1], "不正な値: 本番")

    def test_no_file(self):
        with TempProject() as root:
            self.assertEqual(phase.phase_status(root), ("立ち上げ", "読めない"))

    def test_attribute_outside_marker_is_ignored(self):
        with TempProject() as root:
            write(root / OV, overview_html(None).replace("<body>", '<body data-phase="運用">'))
            self.assertEqual(phase.read_phase(root), "立ち上げ")

    def test_env_wins(self):
        with TempProject() as root:
            write(root / OV, overview_html("開発"))
            os.environ[phase.ENV_PHASE] = "運用"
            self.assertEqual(phase.read_phase(root), "運用")
            os.environ[phase.ENV_PHASE] = "でたらめ"   # 3 値以外は無視
            self.assertEqual(phase.read_phase(root), "開発")


class Strictness(unittest.TestCase):
    def test_all_cells_valid(self):
        for key, row in phase.STRICTNESS.items():
            self.assertEqual(set(row), set(phase.PHASES), key)
            for v in row.values():
                self.assertIn(v, phase.LEVELS, key)
            self.assertIn(key, phase.LABELS, key)

    def test_only_shape_and_secret_block(self):
        blocking = {k for k, row in phase.STRICTNESS.items() if "block" in row.values()}
        self.assertEqual(blocking, {"work_area_guard", "secret_scan", "skeleton_shape",
                                    "design_docs_shape", "harness_shape"})

    def test_level(self):
        self.assertEqual(phase.level("design_docs_reminder", "立ち上げ"), "info")
        self.assertEqual(phase.level("design_docs_reminder", "開発"), "warn")
        self.assertEqual(phase.level("pickup", "立ち上げ"), "warn")
        self.assertEqual(phase.level("docs_stale_days", "立ち上げ"), "none")
        self.assertEqual(phase.level("未知のキー", "開発"), "none")
        self.assertEqual(phase.level("pickup", "本番"), "none")


class Cli(unittest.TestCase):
    def test_set_changes_two_lines_only(self):
        with TempProject(copy=CLI) as root:
            before = overview_html("立ち上げ")
            write(root / OV, before)
            r = run_py(root / CLI[0], "--set", "開発")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("立ち上げ → 開発", r.stdout)
            after = (root / OV).read_text(encoding="utf-8")
            changed = [l for l in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
                       if l.startswith("-") and not l.startswith("---")]
            self.assertEqual(len(changed), 2, changed)
            self.assertIn('data-phase="開発"', after)
            self.assertIn('<div class="name">開発</div>', after)
            self.assertIn('<div class="name">マーカー外</div>', after)
            self.assertEqual(run_py(root / CLI[0]).stdout.strip(), "開発")

    def test_set_adds_attribute(self):
        with TempProject(copy=CLI) as root:
            write(root / OV, overview_html(None, name="着手"))
            r = run_py(root / CLI[0], "--set", "運用")
            self.assertEqual(r.returncode, 0, r.stderr)
            after = (root / OV).read_text(encoding="utf-8")
            self.assertIn('<div class="phase" data-phase="運用">', after)
            self.assertIn('<div class="name">運用</div>', after)

    def test_set_keeps_crlf(self):
        with TempProject(copy=CLI) as root:
            write(root / OV, overview_html("立ち上げ").replace("\n", "\r\n"))
            run_py(root / CLI[0], "--set", "開発")
            data = (root / OV).read_bytes()
            self.assertEqual(data.count(b"\r\n"), data.count(b"\n"))

    def test_set_bad_value(self):
        with TempProject(copy=CLI) as root:
            write(root / OV, overview_html("立ち上げ"))
            r = run_py(root / CLI[0], "--set", "本番")
            self.assertEqual(r.returncode, 2)
            self.assertIn('data-phase="立ち上げ"', (root / OV).read_text(encoding="utf-8"))

    def test_set_without_block(self):
        with TempProject(copy=CLI) as root:
            write(root / OV, "<html></html>")
            self.assertEqual(run_py(root / CLI[0], "--set", "開発").returncode, 2)

    def test_table_rows(self):
        with TempProject(copy=CLI) as root:
            out = run_py(root / CLI[0], "--table").stdout
            rows = [l for l in out.splitlines() if l.startswith("| `")]
            self.assertEqual(len(rows), len(phase.STRICTNESS))

    def test_json(self):
        with TempProject(copy=CLI) as root:
            write(root / OV, overview_html("開発"))
            d = json.loads(run_py(root / CLI[0], "--json").stdout)
            self.assertEqual(d, {"phase": "開発", "problem": None, "suggest": None})

    def test_env_wins_in_cli(self):
        with TempProject(copy=CLI) as root:
            write(root / OV, overview_html("開発"))
            r = run_py(root / CLI[0], env={"CLAUDE_SKELETON_PHASE": "運用"})
            self.assertEqual(r.stdout.strip(), "運用")


def _git(root, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=str(root), capture_output=True, text=True)


class Suggest(unittest.TestCase):
    def test_suggest_after_source_commit(self):
        with TempProject() as root:
            if _git(root, "init", "-q").returncode != 0:
                self.skipTest("git が無い")
            write(root / OV, overview_html("立ち上げ"))
            write(root / "CLAUDE.md", "x\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "init")
            self.assertIsNone(phase.suggest(root, "立ち上げ"))      # 生成直後は提案しない
            write(root / "src/app.py", "print(1)\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "src")
            s = phase.suggest(root, "立ち上げ")
            self.assertIsNotNone(s)
            self.assertIn("1 件", s)
            self.assertIsNone(phase.suggest(root, "開発"))
            self.assertIsNone(phase.suggest(root, "運用"))

    def test_no_git(self):
        with TempProject() as root:
            self.assertIsNone(phase.suggest(root / "無い", "立ち上げ"))


if __name__ == "__main__":
    unittest.main()
