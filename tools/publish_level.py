"""Публикует уровень из Issue (вызывается workflow после метки `approved`).
Читает ISSUE_BODY и ISSUE_NUMBER из окружения, пишет levels/<id>.json и обновляет levels/index.json.
При ошибке завершается с кодом 1 и пишет причину в stderr (её workflow покажет в комментарии)."""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from levelcheck import MAX_LEVELS, LevelError, clean_id, clean_level, clean_text, decode_code, parse_issue_form  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
LEVELS = os.path.join(ROOT, "levels")
INDEX = os.path.join(LEVELS, "index.json")


def main():
    body = os.environ.get("ISSUE_BODY", "")
    number = int(os.environ["ISSUE_NUMBER"])
    f = parse_issue_form(body)
    # все три подтверждения обязательны
    conf = f.get("confirmations", "")
    if conf.count("- [x]") + conf.count("- [X]") < 3:
        raise LevelError("не отмечены все подтверждения")
    author = clean_text(f.get("nickname"), 16) or "ANON"
    level = clean_level(decode_code(f.get("level code", "")))
    lid = "c%d" % number
    assert clean_id(lid, 24) == lid

    os.makedirs(LEVELS, exist_ok=True)
    index = []
    if os.path.exists(INDEX):
        with open(INDEX, encoding="utf-8") as fh:
            index = json.load(fh)
    index = [e for e in index if e.get("id") != lid]
    if len(index) >= MAX_LEVELS:
        raise LevelError("достигнут лимит уровней в каталоге (%d)" % MAX_LEVELS)

    level_file = {"name": level["name"], "author": author, "objects": level["objects"]}
    if "thumb" in level:
        level_file["thumb"] = level["thumb"]
    with open(os.path.join(LEVELS, lid + ".json"), "w", encoding="utf-8") as fh:
        json.dump(level_file, fh, ensure_ascii=False, separators=(",", ":"))

    entry = {"id": lid, "name": level["name"], "author": author, "n": len(level["objects"]),
             "date": datetime.date.today().isoformat()}
    if "thumb" in level:
        entry["thumb"] = level["thumb"]
    index.append(entry)
    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))
    print("published", lid, level["name"], "by", author)


if __name__ == "__main__":
    try:
        main()
    except LevelError as e:
        print("ОШИБКА: %s" % e, file=sys.stderr)
        sys.exit(1)
