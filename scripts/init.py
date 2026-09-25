#!/usr/bin/env python3
"""project-skeleton の template から案件フォルダを生成する。

使い方:
  python3 init.py <生成先パス or プロジェクト名> --name <表示名>
                  [--slug <ascii>] [--desc "…"] [--owner "…"]
                  [--areas "CORE:共通コード,OPS:運用"]
                  [--merge [--resolved]] [--no-git] [--dry-run]

第 1 引数にパス区切りが無ければ <job-work ルート>/<引数> に生成する。
job-work ルートはこのスクリプトの位置から求める(リポの親ディレクトリ)。

生成・merge のたびに生成先の `.claude/skeleton.json`(記録)に、版・生成時の値・入れたファイルの元の内容の sha を残す。
--merge は記録(無ければ CLAUDE.md 1 行目の刻印とスケルトンの git 履歴)から「元の内容」を求め、
手を入れていないファイルは自動で更新、仕組みのファイルは 3-way で混ぜる。衝突と内容のファイルは書かずに一覧で出す。
版ごとの定型の移行は scripts/migrations.json、判断が要る手順は CHANGELOG.md の「既存プロジェクトへの適用」。
標準ライブラリのみ使用(3-way の混ぜ合わせだけ git merge-file を使う。無ければ衝突として出す)。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import date
from pathlib import Path, PurePosixPath

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

SKELETON_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKELETON_ROOT / "template"
JOB_ROOT = SKELETON_ROOT.parent
MIGRATIONS_JSON = SKELETON_ROOT / "scripts/migrations.json"
CHANGELOG_MD = SKELETON_ROOT / "CHANGELOG.md"

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

# 生成先の記録。init.py だけが書く
RECORD_REL = ".claude/skeleton.json"
RECORD_NOTE = "project-skeleton の init.py が書く記録（版・生成時の値・入れたファイルの元の内容の sha）。手で直さない"
# 生成先 CLAUDE.md の 1 行目。記録の無い案件は、ここから版と作成日を読む
STAMP_RE = re.compile(r"<!--\s*project-skeleton v(\d+\.\d+\.\d+)\s+generated\s+(\d{4}-\d{2}-\d{2})\s*-->")

# --desc / --owner を省いたときの置換値（プレースホルダは増やさず、空欄を「未記入」と読めるようにする）
DESC_UNSET = "（未記入: 何の案件かを 1 行で書く）"
OWNER_UNSET = "（未定）"

# --merge の比較から外す生成物。SKIP は比較しない、MASK は両側の BEGIN:x〜END:x の中身を空にしてから比べる
# どちらも自動では書き換えない
GENERATED_SKIP = {"docs/案件/01_タスク管理/data.js"}
GENERATED_MASK = {
    "docs/プロジェクト概要.html": ["task-snapshot", "updated", "open-issues", "milestones", "recent-decisions"],
}
# differs のうち「仕組み」（取り込み推奨）に分けるもの。それ以外は「内容」
MECHANISM_PREFIXES = (".claude/", "scripts/")
MECHANISM_TASK_DIR = "docs/案件/01_タスク管理/"
# 仕組みでなくても 3-way で混ぜるもの（案件が §1 などを書き換えても、決まりの改善は届けたい）
MERGE3_EXTRA = {"CLAUDE.md"}
# migrations.json で使える操作（版ごとの専用コードは書かず、この 3 つの組み合わせで書く）
MIGRATION_OPS = ("move", "json_add", "replace")

NEXT_STEPS_NEW = """\
== 次にやること（Sketch フェーズ。最初はこの 4 つだけでよい）
  1. 打合せ・会話で出たことを記録する   docs/案件/02_打合せ/YYYYMMDD_タイトル.md（Claude に「打合せを記録して」でよい）
  2. 決まっていないことを課題にする     python3 docs/案件/01_タスク管理/new.py 横断 "…" --kind 課題
  3. 目的とスコープを 1 行ずつ書く      docs/設計書/01-概要.md §1・§3
  4. 現在地を 1 行書く                  docs/プロジェクト概要.html「3. 現在地」（Claude に「現在地を直して」でよい）

  今は書かなくてよいもの（必要になったら Claude が案内する）:
    環境情報.md / 01 以外の設計書（要るときに scripts/add_doc.py で足す） / runbook / ADR / 画面（screens） / areas.json / CLAUDE.md §5・§6 / ハーネス台帳"""
NEXT_STEPS_UNSET_HEAD = "  空欄のまま残したもの:"
NEXT_STEPS_UNSET_DESC = "    - 案件の説明（--desc なし）: CLAUDE.md §1・README.md・概要 HTML・01-概要.md §1 に「（未記入…）」"
NEXT_STEPS_UNSET_OWNER = "    - 担当（--owner なし）: README.md・概要 HTML の「管理」・案件情報.md §1 に「（未定）」"
NEXT_STEPS_TAIL = """\
  初めて Claude Code で開くとき: 対話起動（claude）でフォルダを開き、ワークスペースを信頼する（SETUP.md §8）
  * 他マシンと同期しているフォルダなら、同期が完了してから git を触る"""
NEXT_STEPS_MERGE_TAIL = """\
  既存案件の固定の置き場・入れ子のリポは .claude/project.json に書く（テンプレのコードは書き換えない）
  初めて Claude Code で開くとき: 対話起動（claude）でフォルダを開き、ワークスペースを信頼する（SETUP.md §8）
  * 他マシンと同期しているフォルダなら、同期が完了してから git を触る"""


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


def version_tuple(v: str | None) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in (v or "").split("."))
    except ValueError:
        return (0,)


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


def out_rel(src_rel: str) -> str:
    """template 内の相対パス → 生成先の相対パス（`_gitignore` は `.gitignore` になる）。"""
    p = PurePosixPath(src_rel)
    return str(p.with_name(".gitignore")) if p.name == "_gitignore" else str(p)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_values(name: str, slug: str, desc: str, owner: str, created: str, version: str) -> dict[str, str]:
    return {
        "{{PROJECT_NAME}}": name,
        "{{PROJECT_SLUG}}": slug,
        "{{PROJECT_DESC}}": desc or DESC_UNSET,
        "{{CREATED}}": created,
        "{{OWNER}}": owner or OWNER_UNSET,
        "{{SKELETON_VERSION}}": version,
    }


def render(raw: bytes, rel: str, values: dict[str, str]) -> tuple[bytes, bool, list[str]]:
    """template の中身のプレースホルダを埋める。(埋めた中身, テキストとして扱ったか, 残ったプレースホルダ)。
    テキストの拡張子でも UTF-8 として読めなければ、そのまま返す（テキスト扱いしない）。"""
    if not is_text_file(Path(rel)):
        return raw, False, []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw, False, []
    for key, val in values.items():
        text = text.replace(key, val)
    return text.encode("utf-8"), True, sorted(set(PLACEHOLDER_RE.findall(text)))


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


def mask_markers(text: str, names: list[str]) -> str:
    """BEGIN:x〜END:x の中身を空にする（build.py が書き換える欄を比較から外す）。"""
    for name in names:
        text = re.sub(rf"(<!--\s*BEGIN:{re.escape(name)}\s*-->).*?(<!--\s*END:{re.escape(name)}\s*-->)",
                      r"\1\2", text, flags=re.S)
    return text


def same_content(rel_str: str, existing: bytes, rendered: bytes) -> bool:
    if existing == rendered:
        return True
    names = GENERATED_MASK.get(rel_str)
    if not names:
        return False
    try:
        return mask_markers(existing.decode("utf-8"), names) == mask_markers(rendered.decode("utf-8"), names)
    except UnicodeDecodeError:
        return False


def same_number_doc(dest: Path, rel_str: str) -> bool:
    """rel_str が docs/設計書/NN-*.md で、生成先に同じ NN の別の文書があるか（拡張子は問わない。template/ の中は対象外）。"""
    m = re.fullmatch(r"docs/設計書/(\d{2})-[^/]+\.md", rel_str)
    if not m:
        return False
    return any(p.is_file() and p.name != Path(rel_str).name
               for p in (dest / "docs/設計書").glob(f"{m.group(1)}-*"))


def is_mechanism(rel_str: str) -> bool:
    if rel_str.startswith(MECHANISM_PREFIXES):
        return True
    return rel_str.startswith(MECHANISM_TASK_DIR) and (rel_str.endswith(".py") or rel_str.endswith("/index.html"))


def mergeable(rel_str: str) -> bool:
    """案件で手を入れたファイルでも 3-way で混ぜてよいか。"""
    return is_mechanism(rel_str) or rel_str in MERGE3_EXTRA


def safe_rel(p: object) -> bool:
    """migrations.json のパスがルート相対で、外へ出ないか。"""
    if not isinstance(p, str) or not p or p.startswith(("/", "\\")) or ":" in p:
        return False
    return ".." not in p.replace("\\", "/").split("/")


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
# スケルトンの git 履歴（元の内容を作り直すため）
# ---------------------------------------------------------------------------

_TREE_CACHE: dict[str, dict[str, bytes] | None] = {}
_VERSION_CACHE: dict[str, str | None] = {}


def skeleton_git(*args: str) -> str | None:
    """スケルトンのリポで git を実行して stdout を返す。git もリポも無い・失敗なら None。"""
    if not git_available() or not (SKELETON_ROOT / ".git").exists():
        return None
    try:
        r = subprocess.run(["git", "-C", str(SKELETON_ROOT), *args], capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def template_commit() -> str | None:
    """template/ と VERSION に未コミットの変更が無ければ HEAD。あれば None（元の内容は sha でだけ見る）。"""
    head = skeleton_git("rev-parse", "HEAD")
    status = skeleton_git("status", "--porcelain", "--", "template", "VERSION")
    if not head or status is None or status.strip():
        return None
    return head.strip()


def template_tree(commit: str) -> dict[str, bytes] | None:
    """commit 時点の template/ を {生成先の相対パス: 置換前の中身}。読めなければ None。"""
    if commit in _TREE_CACHE:
        return _TREE_CACHE[commit]
    tree: dict[str, bytes] | None = None
    if git_available() and (SKELETON_ROOT / ".git").exists():
        try:
            r = subprocess.run(["git", "-C", str(SKELETON_ROOT), "archive", "--format=tar", commit, "template"],
                               capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            r = None
        if r is not None and r.returncode == 0:
            tree = {}
            with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
                for m in tf.getmembers():
                    if not m.isfile() or not m.name.startswith("template/"):
                        continue
                    src_rel = m.name[len("template/"):]
                    if "__pycache__" in src_rel.split("/") or src_rel.endswith(".pyc"):
                        continue
                    f = tf.extractfile(m)
                    if f is not None:
                        tree[out_rel(src_rel)] = f.read()
    _TREE_CACHE[commit] = tree
    return tree


def version_at(commit: str) -> str | None:
    if commit not in _VERSION_CACHE:
        v = skeleton_git("show", f"{commit}:VERSION")
        _VERSION_CACHE[commit] = v.strip() if v else None
    return _VERSION_CACHE[commit]


def commits_for_version(ver: str) -> list[str]:
    """VERSION が ver だったコミット（template か VERSION を変えたもの）を新しい順に最大 5 件。"""
    out = skeleton_git("log", "--format=%H", "--", "template", "VERSION")
    if not out:
        return []
    found: list[str] = []
    for h in out.split():
        v = version_at(h)
        if v == ver:
            found.append(h)
            if len(found) >= 5:
                break
        elif found or version_tuple(v) < version_tuple(ver):
            break
    return found


# ---------------------------------------------------------------------------
# 記録（.claude/skeleton.json）
# ---------------------------------------------------------------------------

def load_record(dest: Path) -> tuple[dict | None, str | None]:
    """(記録, 読めなかった理由)。無ければ (None, None)。"""
    try:
        data = json.loads((dest / RECORD_REL).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, None
    except (OSError, ValueError) as e:
        return None, f"{RECORD_REL} を読めない（{e}）。記録が無いものとして扱い、作り直す"
    if not isinstance(data, dict):
        return None, f"{RECORD_REL} の形が違う。記録が無いものとして扱い、作り直す"
    if not isinstance(data.get("files"), dict):
        data["files"] = {}
    if not isinstance(data.get("values"), dict):
        data["values"] = {}
    return data, None


def read_stamp(dest: Path) -> tuple[str, str] | None:
    """生成先 CLAUDE.md の刻印 → (版, 作成日)。"""
    try:
        with (dest / "CLAUDE.md").open(encoding="utf-8") as f:
            head = "".join(f.readline() for _ in range(3))
    except (OSError, UnicodeDecodeError):
        return None
    m = STAMP_RE.search(head)
    return (m.group(1), m.group(2)) if m else None


class Bases:
    """「元の内容」= 前回この案件に入れた template の中身（置換後）を返す。

    記録があれば、ファイルごとの sha とコミットから。記録が無く刻印があれば、刻印の版のコミットから作り直す。
    中身が作り直せないときも、記録の sha があれば「手を入れていないか」だけは分かる。
    """

    def __init__(self, record: dict | None, legacy_commit: str | None, legacy_values: dict[str, str] | None):
        self.record_files: dict = (record or {}).get("files", {}) if record else {}
        self.record_values = self._values_from_record(record) if record else None
        self.legacy_commit = legacy_commit
        self.legacy_values = legacy_values

    @staticmethod
    def _values_from_record(record: dict) -> dict[str, str]:
        v = record.get("values", {})
        return {k: str(v.get(k, "") or "") for k in ("name", "slug", "desc", "owner", "created", "skeleton_version")}

    def known(self, rel: str) -> bool:
        """前回入れたファイルか（案件が消したのかを見分けるため）。"""
        if self.record_files:
            return rel in self.record_files
        tree = template_tree(self.legacy_commit) if self.legacy_commit else None
        return bool(tree) and rel in tree

    def rels(self) -> list[str]:
        if self.record_files:
            return list(self.record_files)
        tree = template_tree(self.legacy_commit) if self.legacy_commit else None
        return list(tree or {})

    def get(self, rel: str) -> tuple[bytes | None, str | None, str | None]:
        """(元の内容, その sha, その元になったコミット)。分からなければ None。"""
        if self.record_files:
            entry = self.record_files.get(rel)
            if not isinstance(entry, dict):
                return None, None, None
            sha = entry.get("sha") if isinstance(entry.get("sha"), str) else None
            commit = entry.get("commit") if isinstance(entry.get("commit"), str) else None
            content = self._render_at(commit, rel, self.record_values) if commit and self.record_values else None
            if content is not None and sha and sha256(content) != sha:
                content = None   # 作り直しが記録と合わない（値が変わった等）。sha だけで見る
            return content, sha, commit
        if self.legacy_commit and self.legacy_values is not None:
            content = self._render_at(self.legacy_commit, rel, self.legacy_values)
            if content is not None:
                return content, sha256(content), self.legacy_commit
        return None, None, None

    @staticmethod
    def _render_at(commit: str, rel: str, v: dict[str, str]) -> bytes | None:
        tree = template_tree(commit)
        if not tree or rel not in tree:
            return None
        version = v.get("skeleton_version") or version_at(commit) or ""
        values = make_values(v["name"], v["slug"], v["desc"], v["owner"], v["created"], version)
        return render(tree[rel], rel, values)[0]


def pick_legacy_commit(dest: Path, ver: str, values: dict[str, str]) -> str | None:
    """刻印の版に当たるコミットのうち、案件のファイルと一致する数が最も多いもの。"""
    best, best_n = None, -1
    for commit in commits_for_version(ver):
        tree = template_tree(commit)
        if not tree:
            continue
        rv = make_values(values["name"], values["slug"], values["desc"], values["owner"], values["created"], ver)
        n = 0
        for rel, raw in tree.items():
            p = dest / rel
            try:
                if p.is_file() and p.read_bytes() == render(raw, rel, rv)[0]:
                    n += 1
            except OSError:
                pass
        if n > best_n:
            best, best_n = commit, n
    return best


def keep_generated(new: bytes, cur: bytes, names: list[str]) -> bytes:
    """new の BEGIN:x〜END:x の中身を、cur の同じマーカーの中身に差し替える（build.py が作った欄を残す）。"""
    text, old = new.decode("utf-8"), cur.decode("utf-8")
    for name in names:
        rx = rf"(<!--\s*BEGIN:{re.escape(name)}\s*-->)(.*?)(<!--\s*END:{re.escape(name)}\s*-->)"
        m = re.search(rx, old, flags=re.S)
        if m:
            text = re.sub(rx, lambda x: x.group(1) + m.group(2) + x.group(3), text, count=1, flags=re.S)
    return text.encode("utf-8")


def merge3(cur: bytes, base: bytes, new: bytes) -> tuple[bytes | None, bool]:
    """git merge-file で 3-way。(結果, 衝突したか)。git が無い・失敗なら (None, True)。"""
    if not git_available():
        return None, True
    with tempfile.TemporaryDirectory(prefix="skeleton-merge-") as tmp:
        paths = []
        for name, data in (("cur", cur), ("base", base), ("new", new)):
            p = Path(tmp) / name
            p.write_bytes(data)
            paths.append(str(p))
        try:
            r = subprocess.run(["git", "merge-file", "-p", "-L", "案件", "-L", "元", "-L", "スケルトン", *paths],
                               capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None, True
    if r.returncode < 0 or r.returncode > 127:
        return None, True
    return r.stdout, r.returncode != 0


def json_ok(rel: str, data: bytes) -> bool:
    if not rel.endswith(".json"):
        return True
    try:
        json.loads(data.decode("utf-8"))
        return True
    except (UnicodeDecodeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# 移行（migrations.json）と CHANGELOG の手順
# ---------------------------------------------------------------------------

def load_migrations() -> list[dict]:
    try:
        data = json.loads(MIGRATIONS_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("migrations") if isinstance(data, dict) else None
    return [m for m in items if isinstance(m, dict)] if isinstance(items, list) else []


def _json_add(obj, path: list, value) -> str:
    """path の配列に value を足す。最後のキーが無ければ空の配列を作る。途中が無ければ missing。"""
    node = obj
    for key in path[:-1]:
        if isinstance(node, dict) and isinstance(key, str) and key in node:
            node = node[key]
        elif isinstance(node, list) and isinstance(key, int) and -len(node) <= key < len(node):
            node = node[key]
        else:
            return "missing"
    last = path[-1]
    if isinstance(node, dict) and isinstance(last, str):
        target = node.setdefault(last, [])
    elif isinstance(node, list) and isinstance(last, int) and -len(node) <= last < len(node):
        target = node[last]
    else:
        return "missing"
    if not isinstance(target, list):
        return "missing"
    target.append(value)
    return "added"


def apply_op(dest: Path, op: dict, dry: bool) -> tuple[str, str]:
    """1 つの操作を適用する。(結果, 説明)。結果は done / skip / manual。"""
    kind = op.get("op")
    if kind == "move":
        src, dst = op.get("from"), op.get("to")
        if not (safe_rel(src) and safe_rel(dst)):
            return "manual", f"move: パスが不正 {src!r} → {dst!r}"
        s, d = dest / str(src), dest / str(dst)
        if not s.exists():
            return "skip", f"move {src}（無い）"
        if d.exists():
            return "manual", f"move {src} → {dst}（移動先が既にある。中身を見て手で揃える）"
        if not dry:
            d.parent.mkdir(parents=True, exist_ok=True)
            s.rename(d)
        return "done", f"move {src} → {dst}"
    if kind in ("json_add", "replace"):
        rel = op.get("file")
        if not safe_rel(rel):
            return "manual", f"{kind}: パスが不正 {rel!r}"
        p = dest / str(rel)
        try:
            text = p.read_text(encoding="utf-8")
        except FileNotFoundError:
            return "skip", f"{kind} {rel}（無い）"
        except (OSError, UnicodeDecodeError) as e:
            return "manual", f"{kind} {rel}（読めない: {e}）"
        if kind == "replace":
            old, new = op.get("old"), op.get("new")
            if not isinstance(old, str) or not isinstance(new, str) or not old:
                return "manual", f"replace {rel}: old / new が不正"
            if text.count(old) != 1:
                return "skip", f"replace {rel}（置き換え元が{'無い' if old not in text else '複数ある'}）"
            if not dry:
                p.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
            return "done", f"replace {rel}: {old} → {new}"
        unless = op.get("unless")
        path = op.get("path")
        if isinstance(unless, str) and unless and unless in text:
            return "skip", f"json_add {rel}（{unless} は既にある）"
        if not isinstance(path, list) or not path:
            return "manual", f"json_add {rel}: path が不正"
        try:
            obj = json.loads(text)
        except ValueError as e:
            return "manual", f"json_add {rel}（JSON として読めない: {e}）"
        if _json_add(obj, path, op.get("value")) != "added":
            return "manual", f"json_add {rel}: {'/'.join(map(str, path))} が無い（手で足す）"
        if not dry:
            p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return "done", f"json_add {rel}: {'/'.join(map(str, path))}"
    return "manual", f"知らない操作 {kind!r}"


def run_migrations(dest: Path, since: str | None, current: str, dry: bool) -> list[tuple[str, str, str]]:
    """since より後・current 以下の版の操作を版の順に流す。[(版, 結果, 説明)]。since が None なら全部（冪等）。"""
    out: list[tuple[str, str, str]] = []
    for m in sorted(load_migrations(), key=lambda m: version_tuple(str(m.get("version")))):
        ver = str(m.get("version"))
        if since and version_tuple(ver) <= version_tuple(since):
            continue
        if version_tuple(ver) > version_tuple(current):
            continue
        for op in m.get("ops", []) if isinstance(m.get("ops"), list) else []:
            if isinstance(op, dict):
                status, desc = apply_op(dest, op, dry)
                out.append((ver, status, desc))
    return out


def changelog_steps(since: str | None, current: str) -> list[tuple[str, str]]:
    """CHANGELOG.md の「既存プロジェクトへの適用」節のうち、since より後・current 以下の版を古い順に。"""
    try:
        text = CHANGELOG_MD.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[tuple[str, str]] = []
    for sec in re.split(r"(?m)^## \[", text)[1:]:
        m = re.match(r"(\d+\.\d+\.\d+)\]", sec)
        if not m:
            continue
        ver = m.group(1)
        if (since and version_tuple(ver) <= version_tuple(since)) or version_tuple(ver) > version_tuple(current):
            continue
        sub = re.search(r"(?ms)^### 既存プロジェクトへの適用[^\n]*\n(.*?)(?=^##+ |\Z)", sec)
        if sub and sub.group(1).strip():
            out.append((ver, sub.group(1).strip()))
    return sorted(out, key=lambda x: version_tuple(x[0]))


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def print_list(title: str, items: list[str], indent: str) -> None:
    if items:
        print(f"{indent}{title}({len(items)} 件):")
        for p in items:
            print(f"{indent}  ~ {p}")


def print_differs(differs: list[str], generated: int, indent: str = "  ") -> None:
    """differs を「仕組み」と「内容」に分けて出す。"""
    mech = [p for p in differs if is_mechanism(p)]
    content = [p for p in differs if not is_mechanism(p)]
    if mech:
        print(f"{indent}template と異なる既存ファイル・仕組み（取り込み推奨）({len(mech)} 件):")
        for p in mech:
            print(f"{indent}  ~ {p}")
    if content:
        print(f"{indent}template と異なる既存ファイル・内容（案件側で書き換え済みのはず。必要な節だけ）({len(content)} 件):")
        for p in content:
            print(f"{indent}  ~ {p}")
    if generated:
        print(f"{indent}比較から外した生成物: {generated} 件")


def print_merge_result(r: dict, indent: str) -> None:
    print_list("自動で更新（案件で手を入れていなかった）", r["updated"], indent)
    print_list("自動でマージ（案件の変更を残して新しい版を混ぜた）", r["merged"], indent)
    print_list(f"衝突（書いていない。新しい版と衝突の印入りの案を {r['proposal_dir']}/ に置いた）", r["conflicts"], indent)
    print_differs(r["differs"], r["generated"], indent)
    if r["differs"] and r["proposal_dir"]:
        print(f"{indent}  （新しい版の中身は {r['proposal_dir']}/ に置いた。取り込んだら --merge --resolved で記録する）")
    print_list("片付け（template から無くなった・手を入れていない。.work/_bk/ へ移した）", r["retired"], indent)
    print_list("template から無くなったが案件で手を入れている（残した。要らなければ片付ける）", r["removed_kept"], indent)
    print_list("案件で消したファイル（作り直していない）", r["project_removed"], indent)
    if r["local"]:
        mech = [p for p in r["local"] if is_mechanism(p)]
        print(f"{indent}案件で直したもの（template 側は変わっていない）: {len(r['local'])} 件"
              + (f"。うち仕組み {len(mech)} 件（スケルトンにも入れたいなら docs/ハーネス台帳.md の「返す」列へ）" if mech else ""))


def print_next_steps_new(args: argparse.Namespace, differs: list[str]) -> None:
    print()
    print(NEXT_STEPS_NEW)
    if not args.desc or not args.owner:
        print(NEXT_STEPS_UNSET_HEAD)
        if not args.desc:
            print(NEXT_STEPS_UNSET_DESC)
        if not args.owner:
            print(NEXT_STEPS_UNSET_OWNER)
    if differs:
        print("  上の differs を確認し、必要なら template の変更を手で取り込む")
    print(NEXT_STEPS_TAIL)


def print_next_steps_merge(r: dict, first: bool, steps: list[tuple[str, str]], manual_ops: int) -> None:
    lines: list[str] = []
    if r["conflicts"] or r["differs"]:
        where = f"（新しい版は {r['proposal_dir']}/）" if r["proposal_dir"] else ""
        lines.append(f"衝突・内容の一覧を見て、案件に合わせて取り込む{where}。取り込んだら --merge --resolved で記録する")
    if steps or manual_ops:
        lines.append("上の「CHANGELOG の手順」と「移行」の手で残ったもののうち、自動で済んでいないものを案件に合わせて進める")
    if first:
        lines.append("既存の資料から下書きを作る: draft-from-existing スキル（概要・現在地・案件情報・project.json の下書き）")
    lines.append("フェーズを設定する: python3 .claude/hooks/phase.py --set <Sketch|Build>\n"
                 "     （設定しないと Sketch 扱いになり、Build 中の案件では設計書追随が弱まる。設定済みなら不要）")
    lines.append("python3 scripts/check_skeleton.py で fail=0 を確かめる")
    lines.append("タスク管理を使うなら python3 docs/案件/01_タスク管理/build.py（--merge では build を実行していない）")
    print()
    print("== 次にやること（既存プロジェクトへの適用）")
    for i, line in enumerate(lines, 1):
        print(f"  {i}. {line}")
    print(NEXT_STEPS_MERGE_TAIL)


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------

def main() -> int:
    setup_stdout()

    parser = argparse.ArgumentParser(
        description="project-skeleton の template から案件フォルダを生成する",
    )
    parser.add_argument("dest", help="生成先パス、またはプロジェクト名(job-work 直下に作る)")
    parser.add_argument("--name", help="プロジェクトの表示名(新規は必須。--merge で記録があれば省略可)")
    parser.add_argument("--slug", help="ASCII の識別子(省略時は記録か --name から生成)")
    parser.add_argument("--desc", default="", help="1 行の説明")
    parser.add_argument("--owner", default="", help="担当者")
    parser.add_argument("--areas", default="", help='領域の追加 "CORE:共通コード,OPS:運用"')
    parser.add_argument("--merge", action="store_true",
                        help="既存ディレクトリに適用する(無いファイルを足し、手を入れていないものは新しい版にする)")
    parser.add_argument("--resolved", action="store_true",
                        help="--merge と一緒に: 衝突・内容の一覧のファイルを取り込み済みとして記録する")
    parser.add_argument("--no-git", action="store_true", help="git init / commit をしない")
    parser.add_argument("--dry-run", action="store_true", help="書き込まずに作成予定の一覧だけ出す")
    args = parser.parse_args()

    if not TEMPLATE_DIR.is_dir():
        print(f"エラー: template が見つかりません: {TEMPLATE_DIR}")
        return 2

    version = read_version()
    dest = resolve_dest(args.dest)
    dest_exists = dest.exists()
    merging = bool(args.merge and dest_exists)

    if dest_exists and not dest.is_dir():
        print(f"エラー: 生成先がディレクトリではありません: {dest}")
        return 2
    if dest_exists and any(dest.iterdir()) and not args.merge:
        print(f"エラー: 生成先が既に存在します: {dest}")
        print("       既存プロジェクトにスケルトンを適用するには --merge を付けてください")
        return 2
    if args.merge and not dest_exists:
        print(f"注意: --merge が指定されましたが生成先は存在しません。新規作成として扱います: {dest}")

    warnings: list[str] = []
    record, record_problem = load_record(dest) if merging else (None, None)
    if record_problem:
        warnings.append(record_problem)
    stamp = read_stamp(dest) if merging and record is None else None
    rv = Bases._values_from_record(record) if record else {}

    name = args.name or rv.get("name", "")
    if not name:
        print("エラー: --name が必要です（記録 .claude/skeleton.json が無いため）")
        return 2
    slug = args.slug or rv.get("slug") or slugify(name) or slugify(dest.name) or "project"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug):
        print(f"エラー: --slug は ASCII の英数字・._- のみにしてください: {slug!r}")
        return 2
    desc = args.desc or rv.get("desc", "")
    owner = args.owner or rv.get("owner", "")
    today = date.today().isoformat()
    created = rv.get("created") or (stamp[1] if stamp else today)
    # {{SKELETON_VERSION}} は「どの版から作ったか」。merge で新しい版を入れても生成時の版のまま埋める
    # （刻印・初版の行・改訂履歴の「新規作成」が版を上げるたびに差分にならないように）
    gen_version = rv.get("skeleton_version") or (stamp[0] if stamp else version)
    values = make_values(name, slug, desc, owner, created, gen_version)
    areas_to_add = parse_areas(args.areas) if args.areas else {}

    # 前回入れた版（記録 ＞ 刻印）と元の内容
    since = str(record.get("version")) if record and record.get("version") else (stamp[0] if stamp else None)
    legacy_commit = None
    if merging and record is None and stamp:
        legacy_values = {"name": name, "slug": slug, "desc": desc, "owner": owner, "created": created,
                         "skeleton_version": stamp[0]}
        legacy_commit = pick_legacy_commit(dest, stamp[0], legacy_values)
        if legacy_commit is None:
            warnings.append(f"刻印 v{stamp[0]} のスケルトンの履歴が見つからないため、元の内容は分からない（差分の一覧だけ出す）")
    else:
        legacy_values = None
    bases = Bases(record, legacy_commit, legacy_values)
    top_commit = template_commit()

    mode = "dry-run" if args.dry_run else ("merge" if args.merge else "new")
    print(f"project-skeleton v{version}")
    print(f"  生成先   : {dest}")
    print(f"  表示名   : {name}")
    print(f"  slug     : {slug}")
    print(f"  モード   : {mode}")
    if merging:
        src = "記録" if record else ("刻印" if stamp else "不明")
        print(f"  前回の版 : {('v' + since) if since else '不明'}（{src}）")
    print()

    stamp_day = today.replace("-", "")
    bk_dir = Path(".work/_bk") / f"{stamp_day}_skeleton-v{version}"
    proposal_dir = Path(".work/一時") / f"{stamp_day}_skeleton-update"

    created_files: list[str] = []
    skipped: list[str] = []
    new_record: dict[str, dict] = {}
    res = {"updated": [], "merged": [], "conflicts": [], "differs": [], "local": [], "retired": [],
           "removed_kept": [], "project_removed": [], "generated": 0, "proposal_dir": ""}
    uptodate = 0
    dirs_to_make: list[Path] = []
    template_rels: set[str] = set()

    def entry(sha: str | None, commit: str | None) -> dict:
        return {"sha": sha, "commit": commit}

    def keep_base(rel: str, base_sha: str | None, base_commit: str | None) -> None:
        if args.resolved:
            new_record[rel] = entry(sha256(rendered), top_commit)
        elif base_sha:
            new_record[rel] = entry(base_sha, base_commit)

    def backup(rel: str, data: bytes) -> None:
        if args.dry_run:
            return
        p = dest / bk_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def propose(rel: str, new: bytes, merged: bytes | None = None) -> None:
        res["proposal_dir"] = proposal_dir.as_posix()
        if args.dry_run:
            return
        p = dest / proposal_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(new)
        if merged is not None:
            p.with_name(p.name + ".merged").write_bytes(merged)

    # --- template を走査 -------------------------------------------------
    for dirpath, dirnames, filenames in os.walk(TEMPLATE_DIR):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        rel_dir = Path(dirpath).relative_to(TEMPLATE_DIR)
        dirs_to_make.append(dest / rel_dir)
        for fn in sorted(filenames):
            if fn.endswith(".pyc"):
                continue
            src = Path(dirpath) / fn
            rel_str = out_rel((rel_dir / fn).as_posix())
            template_rels.add(rel_str)
            dst = dest / rel_str

            rendered, text_mode, leftover = render(src.read_bytes(), rel_str, values)
            if is_text_file(Path(rel_str)) and not text_mode:
                warnings.append(f"UTF-8 として読めないためそのままコピー: {rel_str}")
            if leftover:
                warnings.append(f"未知のプレースホルダが残っています: {rel_str}: {', '.join(leftover)}")

            if not dst.exists():
                if merging and bases.known(rel_str) and rel_str not in GENERATED_SKIP:
                    # 前回入れたのに無い = 案件が消した。作り直さない
                    res["project_removed"].append(rel_str)
                    _, base_sha, base_commit = bases.get(rel_str)
                    if base_sha:
                        new_record[rel_str] = entry(base_sha, base_commit)
                    continue
                if same_number_doc(dest, rel_str):
                    # 既存案件に同じ番号の設計書（旧い名前・独自の名前）があれば作らない（番号が 2 本にならないように）
                    skipped.append(rel_str)
                    warnings.append(f"同じ番号の設計書が既にあるため作らない: {rel_str}")
                    continue
                created_files.append(rel_str)
                if rel_str not in GENERATED_SKIP:
                    new_record[rel_str] = entry(sha256(rendered), top_commit)
                if not args.dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(rendered)
                continue

            skipped.append(rel_str)
            if rel_str in GENERATED_SKIP:
                res["generated"] += 1
                continue
            try:
                cur = dst.read_bytes()
            except OSError:
                continue
            if same_content(rel_str, cur, rendered):
                uptodate += 1
                new_record[rel_str] = entry(sha256(rendered), top_commit)
                continue
            base, base_sha, base_commit = bases.get(rel_str)
            if rel_str in GENERATED_MASK and base is not None:
                # build.py が書く欄を外して 3 つを比べ、結果には案件の欄を戻す
                names = GENERATED_MASK[rel_str]
                try:
                    cm, bm, nm = (mask_markers(x.decode("utf-8"), names) for x in (cur, base, rendered))
                except UnicodeDecodeError:
                    cm = bm = nm = None
                if cm is not None and cm == bm:
                    backup(rel_str, cur)
                    if not args.dry_run:
                        dst.write_bytes(keep_generated(rendered, cur, names))
                    res["updated"].append(rel_str)
                    new_record[rel_str] = entry(sha256(rendered), top_commit)
                    continue
                if cm is not None and bm == nm:
                    res["local"].append(rel_str)
                    new_record[rel_str] = entry(base_sha, top_commit or base_commit)
                    continue
                if cm is not None:
                    merged, conflict = merge3(cm.encode("utf-8"), bm.encode("utf-8"), nm.encode("utf-8"))
                    if merged is not None and not conflict:
                        backup(rel_str, cur)
                        if not args.dry_run:
                            dst.write_bytes(keep_generated(merged, cur, names))
                        res["merged"].append(rel_str)
                        new_record[rel_str] = entry(sha256(rendered), top_commit)
                        continue
                    res["conflicts"].append(rel_str)
                    keep_base(rel_str, base_sha, base_commit)
                    propose(rel_str, rendered, merged)
                    continue
            if not text_mode or rel_str in GENERATED_MASK or base_sha is None:
                # 元の内容が分からない・生成物を含む → 今までどおり一覧だけ
                res["differs"].append(rel_str)
                keep_base(rel_str, base_sha, base_commit)
                if text_mode:
                    propose(rel_str, rendered)
                continue
            cur_sha = sha256(cur)
            if cur_sha == base_sha:
                # 手を入れていない → 新しい版にする
                backup(rel_str, cur)
                if not args.dry_run:
                    dst.write_bytes(rendered)
                res["updated"].append(rel_str)
                new_record[rel_str] = entry(sha256(rendered), top_commit)
                continue
            if base_sha == sha256(rendered):
                # template 側は変わっていない。案件の変更はそのまま
                res["local"].append(rel_str)
                new_record[rel_str] = entry(base_sha, top_commit or base_commit)
                continue
            if not mergeable(rel_str):
                res["differs"].append(rel_str)
                keep_base(rel_str, base_sha, base_commit)
                propose(rel_str, rendered)
                continue
            merged, conflict = merge3(cur, base, rendered) if base is not None else (None, True)
            if merged is not None and not conflict and json_ok(rel_str, merged):
                backup(rel_str, cur)
                if not args.dry_run:
                    dst.write_bytes(merged)
                res["merged"].append(rel_str)
                new_record[rel_str] = entry(sha256(rendered), top_commit)
                continue
            res["conflicts"].append(rel_str)
            keep_base(rel_str, base_sha, base_commit)
            propose(rel_str, rendered, merged)

    # --- template から無くなったもの（前回入れた仕組みで、手を入れていなければ .work/_bk/ へ） ----
    if merging:
        for rel_str in sorted(set(bases.rels()) - template_rels):
            p = dest / rel_str
            if rel_str in GENERATED_SKIP or not p.is_file():
                continue
            base, base_sha, base_commit = bases.get(rel_str)
            try:
                cur = p.read_bytes()
            except OSError:
                continue
            if is_mechanism(rel_str) and base_sha and sha256(cur) == base_sha:
                res["retired"].append(rel_str)
                if not args.dry_run:
                    backup(rel_str, cur)
                    p.unlink()
            else:
                res["removed_kept"].append(rel_str)
                if base_sha:
                    new_record[rel_str] = entry(base_sha, base_commit)

    differs = res["differs"]

    # --- 移行（版ごとの定型操作）と CHANGELOG の手順 ----------------------
    mig: list[tuple[str, str, str]] = run_migrations(dest, since, version, args.dry_run) if merging else []
    steps = changelog_steps(since, version) if merging else []
    manual_ops = sum(1 for _, s, _ in mig if s == "manual")

    # --- dry-run はここで終了 -------------------------------------------
    if args.dry_run:
        print(f"作成予定 ({len(created_files)} 件):")
        for p in created_files:
            print(f"  + {p}")
        if skipped:
            print(f"既存のため保持 ({len(skipped)} 件)")
        print(f"updated={len(res['updated'])} merged={len(res['merged'])} conflicts={len(res['conflicts'])} "
              f"differs={len(differs)} retired={len(res['retired'])}")
        print_merge_result(res, indent="")
        print_migrations(mig, indent="")
        if mig:
            print("（dry-run の移行は今のファイルに対する見込み。上の自動更新で済むものは、本実行では「既にある」で飛ばす）")
        for w in warnings:
            print(f"警告: {w}")
        print()
        print("dry-run のため書き込み・git・build は行っていません")
        return 0

    # --- ディレクトリ(空ディレクトリも含む) -------------------------
    for d in dirs_to_make:
        d.mkdir(parents=True, exist_ok=True)
    for wd in WORK_DIRS:
        (dest / ".work" / wd).mkdir(parents=True, exist_ok=True)

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
                    for area_name, prefix in areas_to_add.items():
                        if area_name in areas:
                            print(f"  領域 {area_name!r} は既に存在するため維持({areas[area_name]})")
                            continue
                        if prefix in used:
                            warnings.append(f"プレフィックス {prefix} は既に領域 {used[prefix]!r} で使われています({area_name!r} は追加せず)")
                            continue
                        areas[area_name] = prefix
                        used[prefix] = area_name
                        print(f"  領域を追加: {area_name} = {prefix}")
                    areas_path.write_bytes(
                        (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                    )
        else:
            warnings.append(f"{AREAS_JSON.as_posix()} が無いため領域を追加できません")

    # --- 記録 -------------------------------------------------------------
    rec_out = {
        "_説明": RECORD_NOTE,
        "version": version,
        "commit": top_commit,
        "generated": (record or {}).get("generated") or (stamp[1] if stamp else created),
        "updated": today,
        "values": {"name": name, "slug": slug, "desc": desc, "owner": owner, "created": created,
                   "skeleton_version": gen_version},
        "files": dict(sorted(new_record.items())),
    }
    record_path = dest / RECORD_REL
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes((json.dumps(rec_out, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    # --- 実行ビット(今回書いたファイルだけ。既存の案件のファイルや node_modules は触らない) ---
    exec_files: list[str] = []
    for rel_str in created_files:
        p = dest / rel_str
        if p.suffix in (".sh", ".py"):
            exec_files.append(rel_str)
            try:
                os.chmod(p, p.stat().st_mode | 0o111)
            except OSError:
                pass

    # --- build.py(data.js と概要 HTML のスナップショット) --------------
    # --merge では実行しない(案件の既存の build.py が data.js を書き換え、dry-run と結果がずれるため)
    build_py = dest / BUILD_PY
    if merging:
        pass
    elif build_py.exists():
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
    print(f"  created={len(created_files)} skipped={len(skipped)} differs={len(differs)}"
          + (f" updated={len(res['updated'])} merged={len(res['merged'])} conflicts={len(res['conflicts'])}"
             f" retired={len(res['retired'])}" if merging else ""))
    if created_files:
        print("  作成:")
        for p in created_files:
            print(f"    + {p}")
    if merging:
        if res["updated"] or res["merged"] or res["retired"]:
            print(f"  書き換える前の中身: {bk_dir.as_posix()}/")
        print_merge_result(res, indent="  ")
        print_migrations(mig, indent="  ")
        print_changelog(steps, since)
    else:
        print_differs(differs, res["generated"], indent="  ")
    for w in warnings:
        print(f"  警告: {w}")

    if merging:
        print_next_steps_merge(res, record is None, steps, manual_ops)
    else:
        print_next_steps_new(args, differs)
    return 0


def print_migrations(mig: list[tuple[str, str, str]], indent: str) -> None:
    done = [f"v{v} {d}" for v, s, d in mig if s == "done"]
    manual = [f"v{v} {d}" for v, s, d in mig if s == "manual"]
    if done:
        print(f"{indent}移行（自動で済んだ定型の手順）({len(done)} 件):")
        for d in done:
            print(f"{indent}  + {d}")
    if manual:
        print(f"{indent}移行（自動ではできなかった。手で進める）({len(manual)} 件):")
        for d in manual:
            print(f"{indent}  ! {d}")


def print_changelog(steps: list[tuple[str, str]], since: str | None) -> None:
    if not steps:
        return
    head = f"v{since} より後" if since else "前回の版が不明のため全部"
    print()
    print(f"== CHANGELOG の「既存プロジェクトへの適用」（{head}。案件に合わせて読む。定型の手順は上の「移行」で済んでいる）")
    for ver, body in steps:
        print(f"  --- v{ver}")
        for line in body.splitlines():
            print(f"    {line}")


if __name__ == "__main__":
    sys.exit(main())
