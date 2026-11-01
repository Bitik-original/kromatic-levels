"""Проверка и очистка уровней KROMATIC. Зеркалит cleanLevel() из игры: принимаем только белый список."""
import base64
import gzip
import json
import re
import zlib

LV_TYPES = {"Platform", "Zombie", "Player", "Door", "Elevator", "Spikes", "Plate", "Lever", "Spawner",
            "Button", "Spring", "Saw", "Checkpoint", "Goal"}
MAX_CODE_CHARS = 60000        # лимит тела GitHub Issue ~65k
MAX_JSON_BYTES = 400_000      # защита от zip-бомб
MAX_OBJECTS = 1500
MAX_LEVELS = 500              # сколько уровней держим в index.json
TEXT_BAD = re.compile(r"[^A-Z0-9 .,:!?*\-_/<>\[\]%()'+=|#]")
ID_BAD = re.compile(r"[^A-Za-z0-9_-]")
THUMB_RE = re.compile(r"^data:image/png;base64,[A-Za-z0-9+/=]{1,16000}$")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class LevelError(ValueError):
    pass


def clean_text(v, n):
    return TEXT_BAD.sub("", str(v if v is not None else "").upper()).strip()[:n]


def clean_id(v, n):
    return ID_BAD.sub("", str(v if v is not None else ""))[:n]


def num(v, lo, hi, default):
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError, OverflowError):
        return default
    return max(lo, min(hi, v))


def decode_code(code: str) -> dict:
    """KRM1:<base64 gzip json> или KRM0:<base64 json>."""
    code = re.sub(r"[\s`]", "", code or "")
    if not code or len(code) > MAX_CODE_CHARS:
        raise LevelError("код пустой или слишком длинный")
    m = re.match(r"^(KRM[01]):([A-Za-z0-9+/=]+)$", code)
    if not m:
        raise LevelError("неверный формат кода (ожидается KRM1:... или KRM0:...)")
    try:
        raw = base64.b64decode(m.group(2), validate=True)
        if m.group(1) == "KRM1":
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            raw = d.decompress(raw, MAX_JSON_BYTES + 1)
            if d.unconsumed_tail:
                raise LevelError("распакованный уровень слишком большой")
        if len(raw) > MAX_JSON_BYTES:
            raise LevelError("уровень слишком большой")
        return json.loads(raw.decode("utf-8"))
    except LevelError:
        raise
    except Exception as e:  # noqa: BLE001
        raise LevelError("не удалось прочитать код: %s" % e)


def clean_level(raw) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("objects"), list):
        raise LevelError("в уровне нет списка objects")
    objs, ids = [], set()
    for o in raw["objects"][:MAX_OBJECTS]:
        if not isinstance(o, dict) or o.get("type") not in LV_TYPES:
            continue
        oid = clean_id(o.get("id"), 16)
        if not oid or oid in ids:
            continue
        ids.add(oid)
        c = {"id": oid, "type": o["type"],
             "x": num(o.get("x"), -100000, 100000, 0), "y": num(o.get("y"), -100000, 100000, 0),
             "w": num(o.get("w"), 1, 20000, 16), "h": num(o.get("h"), 1, 20000, 16)}
        if isinstance(o.get("to"), list):
            c["to"] = [t for t in (clean_id(v, 16) for v in o["to"][:50]) if t]
        if o.get("inv"):
            c["inv"] = 1
        if o.get("all"):
            c["all"] = 1
        if "dx" in o:
            c["dx"] = num(o["dx"], -20000, 20000, 0)
        if "dy" in o:
            c["dy"] = num(o["dy"], -20000, 20000, 0)
        objs.append(c)
    # связи только на существующие объекты
    for c in objs:
        if "to" in c:
            c["to"] = [t for t in c["to"] if t in ids]
    types = [c["type"] for c in objs]
    if types.count("Player") != 1:
        raise LevelError("в уровне должен быть ровно один Player")
    if "Goal" not in types:
        raise LevelError("в уровне нет Goal (финиша)")
    out = {"name": clean_text(raw.get("name"), 16) or "UNNAMED", "objects": objs}
    t = raw.get("thumb")
    if isinstance(t, str) and THUMB_RE.match(t):
        try:
            if base64.b64decode(t.split(",", 1)[1], validate=True)[:8] == PNG_MAGIC:
                out["thumb"] = t
        except Exception:  # noqa: BLE001
            pass
    return out


def parse_issue_form(body: str) -> dict:
    """Разбор тела GitHub Issue Form: '### Заголовок\\n\\nзначение'."""
    fields = {}
    body = (body or "").replace("\r\n", "\n").replace("\r", "\n")   # с сайта GitHub тело приходит с CRLF
    for m in re.finditer(r"^### (.+?)\s*\n\n(.*?)(?=\n### |\Z)", body or "", re.S | re.M):
        fields[m.group(1).strip().lower()] = m.group(2).strip()
    return fields
