#!/usr/bin/env python3
"""
new.py — 新規タスク／課題の md 雛形を open/ に作成する

Usage:
  python3 new.py <area>
  python3 new.py <area> "タイトル"
  python3 new.py <area> "タイトル" --kind 課題

例:
  python3 new.py 横断 "ログイン画面のバリデーション追加"
  python3 new.py 文書
  python3 new.py 運用 "バックアップ世代数の扱い" --kind 課題

分類（kind）: タスク（既定）＝実行して完了させる作業／課題＝意思決定・すり合わせが
必要な未決事項（決着したら close.py でクローズ）。

領域 → プレフィックスの対応表は同じフォルダの areas.json に置く。
未知の area は先頭3文字を大文字化して採番する。
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
OPEN_DIR = BASE_DIR / "open"
CLOSED_DIR = BASE_DIR / "closed"
AREAS_JSON = BASE_DIR / "areas.json"


def load_area_prefix() -> dict[str, str]:
    """
    areas.json から 領域 → プレフィックス の対応表を読む。
    形式: {"areas": {"横断": "QA", "文書": "DOC", ...}}
    ファイルが無い／壊れている場合は警告を出して空表で続行する（自動採番のみ）。
    """
    if not AREAS_JSON.exists():
        print(f"警告: {AREAS_JSON.name} が見つかりません（未知 area の自動採番のみ）", file=sys.stderr)
        return {}
    try:
        data = json.loads(AREAS_JSON.read_text(encoding="utf-8"))
        areas = data.get("areas", {})
        if not isinstance(areas, dict):
            raise ValueError("'areas' が辞書ではありません")
        return {str(k): str(v) for k, v in areas.items()}
    except (OSError, ValueError) as e:
        print(f"警告: {AREAS_JSON.name} を読めません: {e}", file=sys.stderr)
        return {}


AREA_PREFIX: dict[str, str] = load_area_prefix()


def area_to_prefix(area: str) -> str:
    """area 名をプレフィックスに変換する。未知の area は先頭3文字大文字。"""
    return AREA_PREFIX.get(area, area[:3].upper())


def next_id(prefix: str) -> str:
    """
    open/ と closed/ の両方で同一プレフィックスを持つ既存 md の最大連番 + 1 を採番する。
    例: QA-01.md, QA-02.md が存在すれば QA-03 を返す。
    （closed/ を見ないとクローズ済みタスクと ID が重複するため両方走査する）
    """
    pattern = re.compile(
        r"^" + re.escape(prefix) + r"-(\d+)", re.IGNORECASE
    )
    max_num = 0
    for folder in (OPEN_DIR, CLOSED_DIR):
        for md in folder.glob("*.md"):
            m = pattern.match(md.stem)
            if m:
                max_num = max(max_num, int(m.group(1)))
    # 2桁ゼロ埋め
    return f"{prefix}-{max_num + 1:02d}"


def slugify(title: str, id_: str) -> str:
    """
    タイトルから安全なスラッグを生成する（最大40文字）。
    スペース・記号はアンダースコアに置換。タイトルが空なら id_ を返す。
    """
    if not title:
        return id_
    slug = re.sub(r'[\s/\\:*?"<>|]+', "_", title)
    slug = slug[:40].strip("_")
    return slug if slug else id_


# 本文テンプレート（9 セクション）。用件を上に、背景を下に並べる。
# 「完了条件」の 3 条件はプロジェクトごとに README で定義し直す。
TASK_BODY = """## 概要
（このタスクで何をするか。1〜3行で用件だけ）

## 対応の意義（なぜやるか）
- 対応しないデメリット: …
- 対応するメリット: …

## 対応後の変更点（利用者視点）
（利用者から見た UI/UX の変化。純粋なバックグラウンド処理のみなら「なし」）

## 対応計画の概要
- 作業項目を箇条書き

## 対応計画の詳細
（各作業項目の具体。対象ファイル・データモデル・移行方針・技術判断）

## 影響・依存
（他タスク・画面・設計書・レビュー観点との関係）

## 完了条件（クローズ3条件）
1. 対象環境へ適用済み
2. 確認者（プロジェクトで定める）の確認
3. 正本（環境情報・設計書・台帳等）への反映
（コード変更を伴わないタスクは条件2のみでクローズ可。その旨を明記する）

## 過去の経緯
（これまでの打合せ・決定の変遷。「なぜ今この結論か」）

## 参照情報
（打合せ出典・設計書・関連コミット・関連タスク ID・関連画面 ID）
"""

ISSUE_BODY = """## 概要
（何を決める必要があるか。1〜3行）

## 論点
- …

## 決定候補
- 案A: …
- 案B: …

## 決着条件
（誰が・何をもって決着とするか。決着したら close.py でクローズし、実装は別タスクに起票）

## 過去の経緯
（これまでの打合せ・決定の変遷）

## 参照情報
（打合せ出典・設計書・関連タスク ID・関連画面 ID）
"""


def make_template(id_: str, title: str, area: str, today: str, kind: str = "タスク") -> str:
    """タスク／課題 md のフロントマター＋本文雛形を生成する。"""
    body = ISSUE_BODY if kind == "課題" else TASK_BODY
    return (
        "---\n"
        f"id: {id_}\n"
        f"title: {title}\n"
        f"area: {area}\n"
        f"kind: {kind}\n"
        "status: 未着手\n"
        "priority: 中\n"
        "epic: \n"
        "owner: \n"
        "tags: []\n"
        "screens: []\n"
        "source: \n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "closed: \n"
        "---\n"
        "\n"
        + body
    )


def main() -> None:
    args = list(sys.argv[1:])

    # --kind オプション（タスク｜課題。省略時はタスク）
    kind = "タスク"
    if "--kind" in args:
        i = args.index("--kind")
        if i + 1 >= len(args) or args[i + 1] not in ("タスク", "課題"):
            print("エラー: --kind には タスク または 課題 を指定してください", file=sys.stderr)
            sys.exit(1)
        kind = args[i + 1]
        del args[i:i + 2]

    if len(args) < 1:
        print("Usage: python3 new.py <area> [\"タイトル\"] [--kind タスク|課題]", file=sys.stderr)
        print(f"利用可能な area（areas.json）: {', '.join(AREA_PREFIX.keys()) or '（なし）'}", file=sys.stderr)
        sys.exit(1)

    area = args[0]
    title = args[1] if len(args) >= 2 else ""

    prefix = area_to_prefix(area)
    id_ = next_id(prefix)
    today = datetime.date.today().isoformat()
    slug = slugify(title, id_)
    filename = f"{id_}_{slug}.md"
    filepath = OPEN_DIR / filename

    if filepath.exists():
        print(f"エラー: {filepath} はすでに存在します", file=sys.stderr)
        sys.exit(1)

    OPEN_DIR.mkdir(parents=True, exist_ok=True)
    content = make_template(id_, title, area, today, kind)
    filepath.write_text(content, encoding="utf-8", newline="\n")
    print(f"作成: open/{filename}（分類: {kind}）")

    # data.js を更新
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "build.py")],
        capture_output=False,
    )
    if result.returncode != 0:
        print("警告: build.py の実行に失敗しました", file=sys.stderr)


if __name__ == "__main__":
    main()
