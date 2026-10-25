#!/usr/bin/env python3
"""scripts/init.py のテスト(unittest、標準ライブラリのみ)。

実行: python3 scripts/tests/test_init.py
見ること(付録 B §2.1・§2.2・§5.4・§7):
  - 新規生成の案内に「最初はこの 4 つだけ」「今は書かなくてよいもの」が出る
  - --desc / --owner を省くと「(未記入…)」「(未定)」が入り、案内に「空欄のまま残したもの」が出る
  - 生成直後に --merge --dry-run --no-git → differs 0(生成物は比較から外れる)
  - differs は「仕組み」と「内容」に分かれて出る(元の内容が分からないとき)
  - template/CLAUDE.md は 80 行以内
  - 記録 .claude/skeleton.json と追従(v1.5.0): スケルトンを一時フォルダに写して版を上げ、
    手を入れていないものは更新・仕組みは 3-way・衝突は書かずに案・内容は一覧・無くなった仕組みは片付け・
    案件が消したものは作り直さない・migrations の冪等・CHANGELOG の手順・刻印からの作り直し・git 無しの縮退
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
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


def run_init(*args: str, init_py: Path = INIT_PY) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(init_py), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")


def copy_skeleton(dst: Path, version: str, with_git: bool) -> Path:
    """スケルトンの写し(scripts・template・VERSION・CHANGELOG・migrations)を作る。with_git なら 1 コミット目まで。"""
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for rel in ("scripts", "template"):
        shutil.copytree(SKELETON / rel, dst / rel, ignore=ignore)
    (dst / "VERSION").write_text(version + "\n", encoding="utf-8")
    (dst / "CHANGELOG.md").write_text("# CHANGELOG\n", encoding="utf-8")
    (dst / "scripts/migrations.json").write_text('{"migrations": []}\n', encoding="utf-8")
    if with_git:
        git(dst, "init", "-q")
        git(dst, "add", "-A")
        git(dst, "commit", "-q", "-m", f"v{version}")
    return dst


def edit(path: Path, fn) -> None:
    path.write_text(fn(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")


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
        for rel in ("CLAUDE.md", "README.md", "docs/プロジェクト概要.html", "docs/設計書/01-概要.md"):
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
        """元の内容が分からない(記録なし・スケルトンに git 無し)ときは、今までどおり差分を 2 分類で一覧にする。"""
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            skel = copy_skeleton(Path(tmp) / "skel", "9.0.0", with_git=False)
            init_py = skel / "scripts/init.py"
            dest = Path(tmp) / "proj"
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit4", "--no-git", init_py=init_py)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            (dest / ".claude/skeleton.json").unlink()
            with (dest / ".claude/hooks/phase.py").open("a", encoding="utf-8") as f:
                f.write("\n# 案件側の変更\n")
            with (dest / "docs/設計書/01-概要.md").open("a", encoding="utf-8") as f:
                f.write("\n案件側の追記\n")
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit4", "--merge", "--dry-run", "--no-git",
                         init_py=init_py)
            out = r.stdout
            self.assertIn("differs=2", out)
            mech_head = out.index("仕組み（取り込み推奨）")
            content_head = out.index("内容（案件側で書き換え済みのはず")
            self.assertLess(mech_head, out.index(".claude/hooks/phase.py"))
            self.assertLess(mech_head, content_head)
            self.assertLess(content_head, out.index("docs/設計書/01-概要.md"))

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


class MergeSameNumberDocTest(unittest.TestCase):
    def test_existing_number_is_not_duplicated(self):
        """既存案件に 01 の設計書（旧い名前）があれば、テンプレの 01-概要.md を作らない。"""
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            dest = Path(tmp) / "proj"
            (dest / "docs/設計書").mkdir(parents=True)
            (dest / "docs/設計書/01-overview.md").write_text("# 01 既存\n", encoding="utf-8")
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit7", "--merge", "--no-git")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse((dest / "docs/設計書/01-概要.md").exists())
            self.assertIn("同じ番号の設計書が既にあるため作らない: docs/設計書/01-概要.md", r.stdout)
            self.assertTrue((dest / "docs/設計書/template/05-セキュリティ.md").is_file())   # template/ の中は作る

    def test_existing_number_other_extension(self):
        """既存の 01 が .html でも、同じ番号として扱う。merge 後の検査で 01 の必須も通る。"""
        with tempfile.TemporaryDirectory(prefix="skel-init-test-") as tmp:
            dest = Path(tmp) / "proj"
            (dest / "docs/設計書").mkdir(parents=True)
            (dest / "docs/設計書/01-目標構成.html").write_text("<p>既存</p>\n", encoding="utf-8")
            r = run_init(str(dest), "--name", "検証", "--slug", "tinit8", "--merge", "--no-git")
            self.assertFalse((dest / "docs/設計書/01-概要.md").exists())
            self.assertNotIn("必須ファイル: docs/設計書/01", r.stdout)
            self.assertNotIn("作業ログ/最新.md", r.stdout.split("== 結果")[0])   # 生成物の参照は検査しない


@unittest.skipUnless(shutil.which("git"), "git が無い")
class FollowTest(unittest.TestCase):
    """スケルトンの写しで v9.0.0 から案件を作り、v9.1.0 に上げて --merge する。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="skel-follow-test-")
        tmp = Path(cls._tmp.name)
        skel = tmp / "skel"
        copy_skeleton(skel, "9.0.0", with_git=False)
        # v9.0.0 にだけある仕組み(v9.1.0 で消す)
        (skel / "template/scripts/old_tool.py").write_text("print('old')\n", encoding="utf-8")
        (skel / "template/scripts/old_kept.py").write_text("print('kept')\n", encoding="utf-8")
        git(skel, "init", "-q")
        git(skel, "add", "-A")
        git(skel, "commit", "-q", "-m", "v9.0.0")
        cls.skel = skel
        cls.init_py = skel / "scripts/init.py"
        cls.dest = tmp / "proj"
        cls.gen = run_init(str(cls.dest), "--name", "追従", "--slug", "follow", "--no-git", init_py=cls.init_py)
        cls.rec0 = json.loads((cls.dest / ".claude/skeleton.json").read_text(encoding="utf-8"))
        cls.legacy = tmp / "legacy"
        shutil.copytree(cls.dest, cls.legacy)

        d = cls.dest
        edit(d / ".claude/hooks/phase.py", lambda s: s + "\n# 案件で足した行\n")          # 仕組み・混ぜられる
        edit(d / "scripts/work_log.py", lambda s: s.replace("#!/usr/bin/env python3", "#!/usr/bin/env python3\n# 案件の 2 行目", 1))
        edit(d / "docs/設計書/01-概要.md", lambda s: s + "\n案件の追記\n")                 # 内容
        (d / "docs/案件/確認依頼一覧.md").unlink()                                       # 案件が消した
        edit(d / "scripts/old_kept.py", lambda s: s + "# 案件の変更\n")
        edit(d / ".claude/project.json", lambda s: s)                                    # 変えない

        t = skel / "template"
        edit(t / ".claude/rules/secrets.md", lambda s: s + "\n<!-- v9.1.0 -->\n")        # 手を入れていない → 更新
        edit(t / ".claude/hooks/phase.py", lambda s: s.replace("#!/usr/bin/env python3", "#!/usr/bin/env python3\n# v9.1.0 の変更", 1))
        edit(t / "scripts/work_log.py", lambda s: s.replace("#!/usr/bin/env python3", "#!/usr/bin/env python3\n# スケルトンの 2 行目", 1))
        edit(t / "docs/設計書/01-概要.md", lambda s: s + "\nv9.1.0 の追記\n")
        (t / "scripts/old_tool.py").unlink()
        (t / "scripts/old_kept.py").unlink()
        (t / "scripts/new_tool.py").write_text("print('new')\n", encoding="utf-8")
        (skel / "VERSION").write_text("9.1.0\n", encoding="utf-8")
        (skel / "CHANGELOG.md").write_text(
            "# CHANGELOG\n\n## [9.1.0] - 2026-09-26\n### 変更\n- x\n### 既存プロジェクトへの適用\n- 手で確かめる: 追従テスト用の手順\n\n"
            "## [9.0.0] - 2026-09-25\n### 既存プロジェクトへの適用\n- 前の版の手順(出ない)\n", encoding="utf-8")
        (skel / "scripts/migrations.json").write_text(json.dumps({"migrations": [
            {"version": "9.1.0", "ops": [
                {"op": "json_add", "file": ".claude/project.json", "path": ["work_area_allow"], "value": "tools/**",
                 "unless": "tools/**"},
                {"op": "move", "from": "no/such", "to": "x"},
            ]},
            {"version": "9.0.0", "ops": [{"op": "json_add", "file": ".claude/project.json",
                                          "path": ["work_area_allow"], "value": "old/**", "unless": "old/**"}]},
        ]}, ensure_ascii=False), encoding="utf-8")
        git(skel, "add", "-A")
        git(skel, "commit", "-q", "-m", "v9.1.0")

        cls.phase_before = (d / ".claude/hooks/phase.py").read_text(encoding="utf-8")
        cls.dry = run_init(str(d), "--merge", "--dry-run", "--no-git", init_py=cls.init_py)
        cls.phase_after_dry = (d / ".claude/hooks/phase.py").read_text(encoding="utf-8")
        cls.res = run_init(str(d), "--merge", "--no-git", init_py=cls.init_py)
        cls.day = date.today().strftime("%Y%m%d")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_generated_record(self):
        self.assertEqual(self.gen.returncode, 0, self.gen.stdout + self.gen.stderr)
        self.assertEqual(self.rec0["version"], "9.0.0")
        self.assertTrue(self.rec0["commit"])
        self.assertEqual(self.rec0["values"]["name"], "追従")
        self.assertIn(".claude/hooks/phase.py", self.rec0["files"])
        self.assertNotIn("docs/案件/01_タスク管理/data.js", self.rec0["files"])

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self.dry.returncode, 0, self.dry.stdout + self.dry.stderr)
        self.assertEqual(self.phase_before, self.phase_after_dry)
        self.assertIn("自動でマージ", self.dry.stdout)
        self.assertIn("前回の版 : v9.0.0（記録）", self.dry.stdout)

    def test_name_optional_with_record(self):
        self.assertEqual(self.res.returncode, 0, self.res.stdout + self.res.stderr)
        self.assertIn("表示名   : 追従", self.res.stdout)

    def test_untouched_updated_with_backup(self):
        d = self.dest
        self.assertIn("<!-- v9.1.0 -->", (d / ".claude/rules/secrets.md").read_text(encoding="utf-8"))
        bk = d / f".work/_bk/{self.day}_skeleton-v9.1.0/.claude/rules/secrets.md"
        self.assertTrue(bk.is_file())
        self.assertNotIn("<!-- v9.1.0 -->", bk.read_text(encoding="utf-8"))

    def test_mechanism_merged(self):
        text = (self.dest / ".claude/hooks/phase.py").read_text(encoding="utf-8")
        self.assertIn("# v9.1.0 の変更", text)
        self.assertIn("# 案件で足した行", text)

    def test_conflict_not_written(self):
        d = self.dest
        text = (d / "scripts/work_log.py").read_text(encoding="utf-8")
        self.assertIn("# 案件の 2 行目", text)
        self.assertNotIn("# スケルトンの 2 行目", text)
        prop = d / f".work/一時/{self.day}_skeleton-update/scripts/work_log.py"
        self.assertTrue(prop.is_file())
        self.assertIn("<<<<<<<", prop.with_name("work_log.py.merged").read_text(encoding="utf-8"))
        self.assertIn("衝突", self.res.stdout)

    def test_content_listed_not_merged(self):
        text = (self.dest / "docs/設計書/01-概要.md").read_text(encoding="utf-8")
        self.assertNotIn("v9.1.0 の追記", text)
        self.assertIn("docs/設計書/01-概要.md", self.res.stdout.split("内容（案件側")[1])

    def test_project_removed_not_recreated(self):
        self.assertFalse((self.dest / "docs/案件/確認依頼一覧.md").exists())
        self.assertIn("案件で消したファイル", self.res.stdout)

    def test_removed_from_template(self):
        d = self.dest
        self.assertFalse((d / "scripts/old_tool.py").exists())
        self.assertTrue((d / f".work/_bk/{self.day}_skeleton-v9.1.0/scripts/old_tool.py").is_file())
        self.assertTrue((d / "scripts/old_kept.py").is_file())
        self.assertIn("template から無くなったが案件で手を入れている", self.res.stdout)
        self.assertTrue((d / "scripts/new_tool.py").is_file())

    def test_migrations_and_changelog(self):
        cfg = json.loads((self.dest / ".claude/project.json").read_text(encoding="utf-8"))
        self.assertIn("tools/**", cfg["work_area_allow"])
        self.assertNotIn("old/**", cfg["work_area_allow"])             # 前回の版以前は流さない
        self.assertIn("移行（自動で済んだ定型の手順）", self.res.stdout)
        self.assertIn("追従テスト用の手順", self.res.stdout)
        self.assertNotIn("前の版の手順", self.res.stdout)

    def test_record_and_second_run(self):
        rec = json.loads((self.dest / ".claude/skeleton.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["version"], "9.1.0")
        self.assertEqual(rec["values"]["skeleton_version"], "9.0.0")   # 刻印・初版の行は生成時の版のまま
        self.assertIn("project-skeleton v9.0.0 generated", (self.dest / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertEqual(rec["files"]["scripts/work_log.py"], self.rec0["files"]["scripts/work_log.py"])  # 衝突は元のまま
        self.assertNotIn("scripts/old_tool.py", rec["files"])
        again = run_init(str(self.dest), "--merge", "--no-git", init_py=self.init_py)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("衝突", again.stdout)                            # まだ取り込んでいない
        self.assertNotIn("移行（自動で済んだ", again.stdout)            # 同じ版では流さない
        self.assertIn("updated=0 merged=0", again.stdout)
        resolved = run_init(str(self.dest), "--merge", "--resolved", "--no-git", init_py=self.init_py)
        self.assertEqual(resolved.returncode, 0, resolved.stdout)
        last = run_init(str(self.dest), "--merge", "--dry-run", "--no-git", init_py=self.init_py)
        self.assertIn("conflicts=0 differs=0", last.stdout)

    def test_legacy_stamp(self):
        """記録が無くても、CLAUDE.md の刻印とスケルトンの履歴から元の内容を作り直して更新できる。"""
        d = self.legacy
        (d / ".claude/skeleton.json").unlink()
        r = run_init(str(d), "--merge", "--no-git", init_py=self.init_py)
        self.assertNotEqual(r.returncode, 0)                          # 記録が無いときは --name が要る
        self.assertIn("--name が必要", r.stdout)
        r = run_init(str(d), "--name", "追従", "--slug", "follow", "--merge", "--no-git", init_py=self.init_py)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("前回の版 : v9.0.0（刻印）", r.stdout)
        self.assertIn("<!-- v9.1.0 -->", (d / ".claude/rules/secrets.md").read_text(encoding="utf-8"))
        self.assertIn("# v9.1.0 の変更", (d / ".claude/hooks/phase.py").read_text(encoding="utf-8"))
        self.assertIn("draft-from-existing", r.stdout)                # 初めての記録 → 下書きの案内
        self.assertTrue((d / ".claude/skeleton.json").is_file())


class NoGitSkeletonTest(unittest.TestCase):
    """スケルトンに git が無いときは sha だけで判断する(手を入れていなければ更新、手を入れた仕組みは衝突)。"""

    def test_hash_only(self):
        with tempfile.TemporaryDirectory(prefix="skel-nogit-test-") as tmp:
            skel = copy_skeleton(Path(tmp) / "skel", "9.0.0", with_git=False)
            init_py = skel / "scripts/init.py"
            dest = Path(tmp) / "proj"
            r = run_init(str(dest), "--name", "縮退", "--slug", "nogit", "--no-git", init_py=init_py)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIsNone(json.loads((dest / ".claude/skeleton.json").read_text(encoding="utf-8"))["commit"])
            edit(dest / ".claude/hooks/phase.py", lambda s: s + "\n# 案件\n")
            edit(skel / "template/.claude/hooks/phase.py", lambda s: "# 新\n" + s)
            edit(skel / "template/.claude/rules/secrets.md", lambda s: s + "\n新\n")
            (skel / "VERSION").write_text("9.1.0\n", encoding="utf-8")
            r = run_init(str(dest), "--merge", "--no-git", init_py=init_py)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((dest / ".claude/rules/secrets.md").read_text(encoding="utf-8").endswith("\n新\n"))
            self.assertIn(".claude/hooks/phase.py", r.stdout.split("衝突（書いていない")[1])


class OwnedSectionTest(unittest.TestCase):
    """CLAUDE.md の職務記述(v1.6.0): 節が無ければ足す・案件が先に書いていれば触らない(二重にしない)。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="skel-owned-test-")
        tmp = Path(cls._tmp.name)
        skel = copy_skeleton(tmp / "skel", "9.0.0", with_git=False)
        claude = skel / "template/CLAUDE.md"
        real = claude.read_text(encoding="utf-8")
        span = INIT.section_span(real, "職務記述")
        claude.write_text(real[:span[0]] + real[span[1]:], encoding="utf-8", newline="\n")   # 節の無い旧い版
        git(skel, "init", "-q")
        git(skel, "add", "-A")
        git(skel, "commit", "-q", "-m", "v9.0.0")
        init_py = skel / "scripts/init.py"
        cls.dests = {}
        for key in ("edited", "own", "nostamp"):
            d = tmp / key
            r = run_init(str(d), "--name", "節", "--slug", key, "--no-git", init_py=init_py)
            assert r.returncode == 0, r.stdout + r.stderr
            cls.dests[key] = d
        edit(cls.dests["edited"] / "CLAUDE.md", lambda s: s.replace(INIT.DESC_UNSET, "案件で書いた説明", 1))
        edit(cls.dests["own"] / "CLAUDE.md", lambda s: s + "\n## 9. 職務記述\n\n- 受ける依頼: 案件が先に書いた\n")
        nostamp = cls.dests["nostamp"]
        edit(nostamp / "CLAUDE.md", lambda s: s.split("\n", 1)[1])
        (nostamp / ".claude/skeleton.json").unlink()

        claude.write_text(real, encoding="utf-8", newline="\n")
        (skel / "VERSION").write_text("9.1.0\n", encoding="utf-8")
        ops = [op for m in INIT.load_migrations() if m["version"] == "1.6.0" for op in m["ops"]]
        (skel / "scripts/migrations.json").write_text(
            json.dumps({"migrations": [{"version": "9.1.0", "ops": ops}]}, ensure_ascii=False), encoding="utf-8")
        git(skel, "add", "-A")
        git(skel, "commit", "-q", "-m", "v9.1.0")
        cls.res = {}
        for key, d in cls.dests.items():
            extra = ("--name", "節", "--slug", key) if key == "nostamp" else ()
            cls.res[key] = run_init(str(d), "--merge", "--no-git", *extra, init_py=init_py)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def text(self, key: str) -> str:
        r = self.res[key]
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return (self.dests[key] / "CLAUDE.md").read_text(encoding="utf-8")

    def headings(self, text: str) -> int:
        return sum(1 for line in text.splitlines() if line.startswith("#") and "職務記述" in line)

    def test_added_when_missing(self):
        text = self.text("edited")
        self.assertEqual(self.headings(text), 1)
        self.assertIn("案件で書いた説明", text)
        self.assertLess(text.index("### 職務記述"), text.index("## 2. "))

    def test_project_section_kept(self):
        text = self.text("own")
        self.assertEqual(self.headings(text), 1)
        self.assertIn("案件が先に書いた", text)
        self.assertNotIn("このフォルダの中で済む作業を書く", text)

    def test_inserted_by_migration_without_record(self):
        text = self.text("nostamp")
        self.assertIn("CLAUDE.md", self.res["nostamp"].stdout.split("内容（案件側")[1])   # 3-way できない → 一覧
        self.assertEqual(self.headings(text), 1)
        self.assertLess(text.index("### 職務記述"), text.index("## 2. "))
        again = run_init(str(self.dests["nostamp"]), "--merge", "--no-git", init_py=self.dests["nostamp"].parent / "skel/scripts/init.py")
        self.assertEqual(self.headings((self.dests["nostamp"] / "CLAUDE.md").read_text(encoding="utf-8")), 1, again.stdout)


class UnitTest(unittest.TestCase):
    def test_owned_section_in_template_and_migration(self):
        """職務記述の節が template にあり、v1.6.0 の移行で差し込む中身と一致する。"""
        text = (TEMPLATE / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIsNotNone(INIT.section_span(text, "職務記述"))
        ops = [op for m in INIT.load_migrations() if m["version"] == "1.6.0" for op in m["ops"]]
        self.assertTrue(ops)
        for op in ops:
            self.assertIn(op["new"], text)

    def test_drop_owned(self):
        base = "# T\n\n## 1. A\n\na\n\n## 2. B\n"
        new = "# T\n\n## 1. A\n\na\n\n### 職務記述\n\n- x\n\n## 2. B\n"
        cur = base + "\n## 9. 職務記述\n\n- 案件\n"
        self.assertEqual(INIT.drop_owned("CLAUDE.md", cur.encode(), base.encode(), new.encode()).decode(), base)
        self.assertEqual(INIT.drop_owned("CLAUDE.md", base.encode(), base.encode(), new.encode()).decode(), new)
        self.assertEqual(INIT.drop_owned("README.md", cur.encode(), base.encode(), new.encode()).decode(), new)

    def test_is_mechanism(self):
        f = INIT.is_mechanism
        self.assertTrue(f(".claude/settings.json"))
        self.assertTrue(f("scripts/check_skeleton.py"))
        self.assertTrue(f("docs/案件/01_タスク管理/new.py"))
        self.assertTrue(f("docs/案件/01_タスク管理/index.html"))
        self.assertFalse(f("docs/案件/01_タスク管理/README.md"))
        self.assertFalse(f("docs/設計書/05-セキュリティ.md"))
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

    def test_changelog_steps(self):
        steps = INIT.changelog_steps("1.3.0", "1.4.1")
        self.assertEqual([v for v, _ in steps], ["1.4.0", "1.4.1"])
        self.assertTrue(all(body for _, body in steps))

    def test_migrations_json_ops_known(self):
        for m in INIT.load_migrations():
            for op in m["ops"]:
                self.assertIn(op["op"], INIT.MIGRATION_OPS)

    def test_apply_op_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="skel-op-test-") as tmp:
            d = Path(tmp)
            (d / "s.json").write_text('{"a": {"b": [1]}}\n', encoding="utf-8")
            op = {"op": "json_add", "file": "s.json", "path": ["a", "b"], "value": {"x": "mark"}, "unless": "mark"}
            self.assertEqual(INIT.apply_op(d, op, dry=False)[0], "done")
            self.assertEqual(INIT.apply_op(d, op, dry=False)[0], "skip")
            self.assertEqual(json.loads((d / "s.json").read_text(encoding="utf-8"))["a"]["b"], [1, {"x": "mark"}])
            missing = {"op": "json_add", "file": "s.json", "path": ["z", "y"], "value": 1}
            self.assertEqual(INIT.apply_op(d, missing, dry=False)[0], "manual")
            (d / "t.txt").write_text("aa X bb\n", encoding="utf-8")
            rep = {"op": "replace", "file": "t.txt", "old": "X", "new": "Y"}
            self.assertEqual(INIT.apply_op(d, rep, dry=False)[0], "done")
            self.assertEqual(INIT.apply_op(d, rep, dry=False)[0], "skip")
            self.assertEqual(INIT.apply_op(d, {"op": "move", "from": "../x", "to": "y"}, dry=False)[0], "manual")
            (d / "m1").write_text("1", encoding="utf-8")
            mv = {"op": "move", "from": "m1", "to": "sub/m2"}
            self.assertEqual(INIT.apply_op(d, mv, dry=True)[0], "done")
            self.assertTrue((d / "m1").exists())                      # dry は動かさない
            self.assertEqual(INIT.apply_op(d, mv, dry=False)[0], "done")
            self.assertTrue((d / "sub/m2").exists())
            self.assertEqual(INIT.apply_op(d, mv, dry=False)[0], "skip")

    def test_mergeable(self):
        self.assertTrue(INIT.mergeable("CLAUDE.md"))
        self.assertTrue(INIT.mergeable(".claude/settings.json"))
        self.assertFalse(INIT.mergeable("docs/設計書/01-概要.md"))

    def test_template_claude_md_lines(self):
        n = len((TEMPLATE / "CLAUDE.md").read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(n, 80)


if __name__ == "__main__":
    unittest.main(verbosity=1)
