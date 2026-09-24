#!/usr/bin/env python3
"""scripts/init.py のテスト(unittest、標準ライブラリのみ)。

実行: python3 scripts/tests/test_init.py
見ること(付録 B §2.1・§2.2・§5.4・§7):
  - 新規生成の案内に「最初はこの 4 つだけ」「今は書かなくてよいもの」が出る
  - --desc / --owner を省くと「(未記入…)」「(未定)」が入り、案内に「空欄のまま残したもの」が出る
  - 生成直後に --merge --dry-run --no-git → differs 0(生成物は比較から外れる)
  - differs は「仕組み」と「内容」に分かれて出る
  - template/CLAUDE.md は 80 行以内
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKELETON = Path(__file__).resolve().parent.parent.parent
INIT_PY = SKELETON / "scripts/init.py"
TEMPLATE = SKELETON / "template"


def load_init():
    spec = importlib.util.spec_from_file_location("skeleton_init", INIT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


INIT = load_init()


def run_init(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(INIT_PY), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )


class GeneratedProjectTest(unittest.TestCase):
    """--desc / --owner なしで 1 回生成し、案内・置換値・merge の差分を見る。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="skel-init-test-")
        cls.dest = Path(cls._tmp.name) / "proj"
        cls.result = run_init(str(cls.dest), "--name", "検証", "--slug", "tinit", "--no-git")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_exit_zero(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)

    def test_next_steps_four_items(self):
        out = self.result.stdout
        self.assertIn("最初はこの 4 つだけ", out)
        for n in ("  1. ", "  2. ", "  3. ", "  4. "):
            self.assertIn(n, out)
        self.assertNotIn("  5. ", out.split("最初はこの 4 つだけ", 1)[1])

    def test_next_steps_not_now(self):
        self.assertIn("今は書かなくてよいもの", self.result.stdout)

    def test_next_steps_trust(self):
        self.assertIn("SETUP.md §8", self.result.stdout)

    def test_unset_listed(self):
        out = self.result.stdout
        self.assertIn("空欄のまま残したもの", out)
        self.assertIn("--desc なし", out)
        self.assertIn("--owner なし", out)

    def test_desc_placeholder(self):
        for rel in ("CLAUDE.md", "README.md", "docs/プロジェクト概要.html", "docs/設計書/01-overview.md"):
            text = (self.dest / rel).read_text(encoding="utf-8")
            self.assertIn(INIT.DESC_UNSET, text, rel)

    def test_owner_placeholder(self):
        for rel in ("README.md", "docs/プロジェクト概要.html", "案件情報.md"):
            text = (self.dest / rel).read_text(encoding="utf-8")
            self.assertIn(INIT.OWNER_UNSET, text, rel)

    def test_no_placeholder_left(self):
        self.assertNotIn("未知のプレースホルダ", self.result.stdout)

    def test_merge_dry_run_differs_zero(self):
        r = run_init(str(self.dest), "--name", "検証", "--slug", "tinit", "--merge", "--dry-run", "--no-git")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("differs=0", r.stdout, r.stdout)
        self.assertIn("比較から外した生成物: 1 件", r.stdout)
        self.assertIn("作成予定 (0 件)", r.stdout)


class DescOwnerGivenTest(unittest.TestCase):
    """--desc / --owner を渡すと「空欄のまま残したもの」は出ない。"""

    def test_given(self):
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            dest = Path(tmp) / "proj"
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit2", "--no-git",
                         "--desc", "テスト用の案件", "--owner", "山田")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("空欄のまま残したもの", r.stdout)
            self.assertIn("最初はこの 4 つだけ", r.stdout)
            claude = (dest / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("テスト用の案件", claude)
            self.assertNotIn(INIT.DESC_UNSET, claude)
            self.assertIn("山田", (dest / "README.md").read_text(encoding="utf-8"))

    def test_only_desc_missing(self):
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            dest = Path(tmp) / "proj"
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit3", "--no-git", "--owner", "山田",
                         "--dry-run")
            # dry-run は案内を出さず、何も作らない
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse(dest.exists())
            self.assertNotIn("最初はこの 4 つだけ", r.stdout)


class MergeClassifyTest(unittest.TestCase):
    """生成後に仕組みと内容を 1 つずつ書き換え、merge の differs が 2 分類で出ることを見る。"""

    def test_two_kinds(self):
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            dest = Path(tmp) / "proj"
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit4", "--no-git")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with (dest / ".claude/hooks/phase.py").open("a", encoding="utf-8") as f:
                f.write("\n# 案件側の変更\n")
            with (dest / "docs/設計書/01-overview.md").open("a", encoding="utf-8") as f:
                f.write("\n案件側の追記\n")
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit4", "--merge", "--dry-run", "--no-git")
            out = r.stdout
            self.assertIn("differs=2", out)
            mech_head = out.index("仕組み（取り込み推奨）")
            content_head = out.index("内容（案件側で書き換え済みのはず")
            self.assertLess(mech_head, out.index(".claude/hooks/phase.py"))
            self.assertLess(mech_head, content_head)
            self.assertLess(content_head, out.index("docs/設計書/01-overview.md"))

    def test_merge_next_steps(self):
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            dest = Path(tmp) / "proj"
            run_init(str(dest), "--name", "検証", "--slug", "tinit5", "--no-git")
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit5", "--merge", "--no-git")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("既存プロジェクトへの適用", r.stdout)
            self.assertIn("phase.py --set", r.stdout)
            self.assertNotIn("最初はこの 4 つだけ", r.stdout)

    def test_merge_side_effects(self):
        """--merge は build.py を実行せず、既存ファイルの実行ビットを変えない。新しく作ったものには付ける。"""
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            dest = Path(tmp) / "proj"
            (dest / "docs/案件/01_タスク管理").mkdir(parents=True)
            marker = dest / "build-ran.txt"
            (dest / "docs/案件/01_タスク管理/build.py").write_text(
                # check_skeleton.py が呼ぶ --check（書き込まない）は数えない
                f"import sys\nfrom pathlib import Path\nif '--check' not in sys.argv:\n"
                f"    Path({str(marker)!r}).write_text('x')\n", encoding="utf-8")
            own = dest / "tools/own.py"
            own.parent.mkdir()
            own.write_text("print('案件のスクリプト')\n", encoding="utf-8")
            os.chmod(own, 0o644)
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit6", "--merge", "--no-git")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse(marker.exists(), "merge で build.py が実行された")
            self.assertIn("build.py", r.stdout.split("既存プロジェクトへの適用", 1)[1])
            self.assertEqual(own.stat().st_mode & 0o111, 0, "既存ファイルに実行ビットが付いた")
            if os.name != "nt":
                self.assertTrue((dest / ".claude/hooks/phase.py").stat().st_mode & 0o100)


class UnitTest(unittest.TestCase):
    def test_is_mechanism(self):
        f = INIT.is_mechanism
        self.assertTrue(f(".claude/settings.json"))
        self.assertTrue(f("scripts/check_skeleton.py"))
        self.assertTrue(f("docs/案件/01_タスク管理/new.py"))
        self.assertTrue(f("docs/案件/01_タスク管理/index.html"))
        self.assertFalse(f("docs/案件/01_タスク管理/README.md"))
        self.assertFalse(f("docs/設計書/05-セキュリティ設計.md"))
        self.assertFalse(f("CLAUDE.md"))

    def test_mask_markers(self):
        a = "x<!-- BEGIN:updated -->2026-01-01<!-- END:updated -->y"
        b = "x<!-- BEGIN:updated -->2026-09-23<!-- END:updated -->y"
        self.assertTrue(INIT.same_content("docs/プロジェクト概要.html", a.encode(), b.encode()))
        self.assertFalse(INIT.same_content("docs/プロジェクト概要.html", (a + "z").encode(), b.encode()))
        # MASK の対象外のファイルは中身どおりに比べる
        self.assertFalse(INIT.same_content("README.md", a.encode(), b.encode()))

    def test_generated_skip(self):
        self.assertIn("docs/案件/01_タスク管理/data.js", INIT.GENERATED_SKIP)

    def test_mask_names_exist_in_template(self):
        """GENERATED_MASK のマーカーが概要 HTML の雛形に実在する(名前の食い違いで比較除外が空振りしない)。"""
        html = (TEMPLATE / "docs/プロジェクト概要.html").read_text(encoding="utf-8")
        missing = [n for n in INIT.GENERATED_MASK["docs/プロジェクト概要.html"] if f"BEGIN:{n}" not in html]
        self.assertEqual(missing, [], f"概要 HTML に無いマーカー: {missing}")

    def test_template_claude_md_lines(self):
        n = len((TEMPLATE / "CLAUDE.md").read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(n, 80)


if __name__ == "__main__":
    unittest.main(verbosity=1)
