"""Убирает уровень из каталога (вызывается workflow по метке `takedown` или вручную: python tools/remove_level.py c12).
Берёт id из аргумента или из ISSUE_BODY (поле 'Level ID')."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from levelcheck import clean_id, parse_issue_form  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
LEVELS = os.path.join(ROOT, "levels")
INDEX = os.path.join(LEVELS, "index.json")


def main():
    if len(sys.argv) > 1:
        lid = clean_id(sys.argv[1], 24)
    else:
        lid = clean_id(parse_issue_form(os.environ.get("ISSUE_BODY", "")).get("level id"), 24)
    if not lid:
        print("ОШИБКА: не указан id уровня", file=sys.stderr)
        sys.exit(1)
    index = []
    if os.path.exists(INDEX):
        with open(INDEX, encoding="utf-8") as fh:
            index = json.load(fh)
    found = any(e.get("id") == lid for e in index)
    index = [e for e in index if e.get("id") != lid]
    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))
    path = os.path.join(LEVELS, lid + ".json")
    if os.path.exists(path):
        os.remove(path)
        found = True
    if not found:
        print("ОШИБКА: уровень %s не найден" % lid, file=sys.stderr)
        sys.exit(1)
    print("removed", lid)


if __name__ == "__main__":
    main()
