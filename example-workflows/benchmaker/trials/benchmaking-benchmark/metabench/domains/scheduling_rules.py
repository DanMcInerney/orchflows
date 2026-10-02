"""Rules of the scheduling domain: parsing, the exact oracle and the checker.

The oracle enumerates every start on the granularity grid and applies the rules in the task's
interface.md; the checker judges an output file against the same rules. Instants are integer
minutes since the Unix epoch, so values compare as instants and never as strings.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

INPUT = "input.json"
OUTPUT = "output.json"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_EPOCH_DAY = date(1970, 1, 1).toordinal()
_MINUTE = timedelta(minutes=1)
_DAY = 1440
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_PREFERENCES = ("earliest", "latest", "any")
REJECTED = ("invalid", "unparseable", "wrong-infeasible")
_CONSTRAINT_NAMES = {"nb": "not_before", "na": "not_after", "av": "avoid_day", "bf": "buffer_minutes"}
EXPLANATION = "No slot fits every required participant's calendar, work hours and constraints."


# ---- parsing -------------------------------------------------------------------------------------

def stamp(text):
    """Return (minute since the epoch, UTC offset in minutes) for an ISO 8601 timestamp with an offset."""
    if not isinstance(text, str):
        raise ValueError(f"timestamp must be a string: {text!r}")
    try:
        moment = datetime.fromisoformat(text.strip())
    except ValueError:
        raise ValueError(f"not an ISO 8601 timestamp: {text!r}") from None
    if moment.tzinfo is None:
        raise ValueError(f"timestamp has no UTC offset: {text!r}")
    delta = moment - _EPOCH
    if delta % _MINUTE:
        raise ValueError(f"timestamp is not a whole minute: {text!r}")
    return delta // _MINUTE, moment.utcoffset() // _MINUTE


def iso(minute, offset):
    zone = timezone(timedelta(minutes=offset))
    return (_EPOCH + timedelta(minutes=minute)).astimezone(zone).isoformat(timespec="minutes")


def _offset(text):
    digits = isinstance(text, str) and len(text) == 6 and text[3] == ":" and text[1:3].isdecimal() and text[4:].isdecimal()
    if not (digits and text[0] in "+-" and int(text[1:3]) < 24 and int(text[4:]) < 60):
        raise ValueError(f"utc_offset must look like +02:00: {text!r}")
    minutes = int(text[1:3]) * 60 + int(text[4:])
    return -minutes if text[0] == "-" else minutes


def _clock(text, what):
    if isinstance(text, str) and len(text) == 5 and text[2] == ":" and text[:2].isdecimal() and text[3:].isdecimal():
        minutes = int(text[:2]) * 60 + int(text[3:])
        if int(text[3:]) < 60 and minutes <= _DAY:
            return minutes
    raise ValueError(f"{what} must be HH:MM from 00:00 to 24:00: {text!r}")


def _day(text):
    try:
        return date.fromisoformat(text).toordinal() - _EPOCH_DAY
    except (TypeError, ValueError):
        raise ValueError(f"day must be YYYY-MM-DD: {text!r}") from None


def _need(obj, key, kind, default=...):
    if not isinstance(obj, dict):
        raise ValueError(f"expected an object, got {type(obj).__name__}")
    if key not in obj:
        if default is ...:
            raise ValueError(f"missing {key!r}")
        return default
    value = obj[key]
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ValueError(f"{key!r} has the wrong type")
    return value


def _busy(owner):
    spans = []
    for item in _need(owner, "busy", list, []):
        start, end = stamp(_need(item, "start", str))[0], stamp(_need(item, "end", str))[0]
        if end <= start:
            raise ValueError("a busy interval must end after it starts")
        spans.append((start, end))
    return spans


def _work(entries, off, w0, w1):
    """Working time as merged absolute (start, end) minutes covering the window."""
    rules = []
    for entry in entries:
        names = [str(d).lower() for d in _need(entry, "days", list)]
        if any(n not in _WEEKDAYS for n in names):
            raise ValueError(f"work_hours days must be among Mon..Sun: {names}")
        start, end = _clock(entry.get("start"), "work_hours start"), _clock(entry.get("end"), "work_hours end")
        if end <= start:
            raise ValueError("work_hours must end after they start")
        rules.append(({_WEEKDAYS.index(n) for n in names}, start, end))
    spans = sorted(
        (n * _DAY - off + a, n * _DAY - off + b)
        for n in range((w0 + off) // _DAY - 1, (w1 + off) // _DAY + 2)
        for weekdays, a, b in rules
        if (n + 3) % 7 in weekdays
    )
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def model(inst):
    """Validate an instance and return its integer-minute form; ValueError when it does not conform."""
    dur = _need(inst, "duration_minutes", int)
    gran = _need(inst, "granularity_minutes", int, 15)
    if dur < 1 or gran < 1:
        raise ValueError("duration_minutes and granularity_minutes must be positive")
    window = _need(inst, "window", dict)
    (w0, woff), (w1, _) = stamp(_need(window, "start", str)), stamp(_need(window, "end", str))
    if w1 <= w0:
        raise ValueError("window must end after it starts")
    pref = _need(inst, "preference", str)
    if pref not in _PREFERENCES:
        raise ValueError(f"preference must be one of {_PREFERENCES}")
    people, by_id = [], {}
    for item in _need(inst, "participants", list):
        pid = _need(item, "id", str)
        if not pid or pid in by_id:
            raise ValueError(f"participant ids must be unique and non-empty: {pid!r}")
        off = _offset(_need(item, "utc_offset", str))
        person = {"id": pid, "off": off, "required": _need(item, "required", bool, True),
                  "work": _work(_need(item, "work_hours", list), off, w0, w1), "busy": _busy(item), "cons": []}
        people.append(by_id.setdefault(pid, person))
    need = sum(p["required"] for p in people)
    if not need:
        raise ValueError("at least one participant must be required")
    rooms = []
    for item in _need(inst, "rooms", list, []):
        rid = _need(item, "id", str)
        if not rid or any(r["id"] == rid for r in rooms):
            raise ValueError(f"room ids must be unique and non-empty: {rid!r}")
        features = _need(item, "features", list, [])
        if not all(isinstance(f, str) for f in features):
            raise ValueError("room features must be strings")
        rooms.append({"id": rid, "cap": _need(item, "capacity", int), "features": set(features), "busy": _busy(item)})
    features = set()
    for item in _need(inst, "constraints", list, []):
        kind = _need(item, "type", str)
        if kind == "room_feature":
            features.add(_need(item, "feature", str))
            continue
        person = by_id.get(_need(item, "participant", str))
        if person is None:
            raise ValueError("a constraint names an unknown participant")
        if kind in ("not_before", "not_after"):
            only = _day(item["day"]) if "day" in item else None
            person["cons"].append(("nb" if kind == "not_before" else "na", _clock(item.get("time"), "time"), only))
        elif kind == "avoid_day":
            person["cons"].append(("av", _day(item.get("day")), None))
        elif kind == "buffer_minutes":
            minutes = _need(item, "minutes", int)
            if minutes < 0:
                raise ValueError("buffer minutes must not be negative")
            person["cons"].append(("bf", minutes, None))
        else:
            raise ValueError(f"unknown constraint type {kind!r}")
    return {"dur": dur, "gran": gran, "w0": w0, "w1": w1, "woff": woff, "pref": pref, "people": people,
            "rooms": rooms, "features": features, "need": need}


# ---- the rules -----------------------------------------------------------------------------------

def person_problem(p, s, e):
    """Why a required participant cannot take the slot [s, e), or None."""
    if not any(a <= s and e <= b for a, b in p["work"]):
        return f"{p['id']} is outside work hours"
    if any(a < e and s < b for a, b in p["busy"]):
        return f"{p['id']} is busy"
    day = (s + p["off"]) // _DAY
    base = day * _DAY - p["off"]
    for kind, arg, only in p["cons"]:
        if kind == "nb":
            bad = (only is None or only == day) and s < base + arg
        elif kind == "na":
            bad = (only is None or only == day) and e > base + arg
        elif kind == "av":
            low = arg * _DAY - p["off"]
            bad = s < low + _DAY and low < e
        else:
            bad = any(a < e + arg and s - arg < b for a, b in p["busy"])
        if bad:
            return f"{p['id']} violates {_CONSTRAINT_NAMES[kind]}"
    return None


def rooms_for(m, s, e):
    return [r["id"] for r in m["rooms"]
            if r["cap"] >= m["need"] and m["features"] <= r["features"] and not any(a < e and s < b for a, b in r["busy"])]


def starts(m):
    return range(m["w0"], m["w1"] - m["dur"] + 1, m["gran"])


def slots(m):
    """Every valid (start, eligible rooms) on the grid, ascending by start."""
    required = [p for p in m["people"] if p["required"]]
    found = []
    for s in starts(m):
        e = s + m["dur"]
        if any(person_problem(p, s, e) for p in required):
            continue
        rooms = rooms_for(m, s, e)
        if m["rooms"] and not rooms:
            continue
        found.append((s, rooms))
    return found


def valid_slots(instance):
    """[(start minute since the epoch, [eligible room ids])] for every valid start, ascending."""
    return slots(model(instance))


# ---- output files --------------------------------------------------------------------------------

def dump(obj, **options):
    return (json.dumps(obj, **options) + "\n").encode("utf-8")


def slot_file(m, s, room=None, off=None, *, seconds=False, zulu=False, reverse=False, indent=None, extra=None):
    off = m["woff"] if off is None else off

    def text(minute):
        t = iso(minute, off)
        if seconds:
            t = t[:16] + ":00" + t[16:]
        return t[:-6] + "Z" if zulu and off == 0 else t

    body = {"start": text(s), "end": text(s + m["dur"])}
    if room is not None:
        body["room"] = room
    if extra:
        body["note"] = extra
    if reverse:
        body = dict(reversed(list(body.items())))
    return {OUTPUT: dump(body, indent=indent)}


def infeasible(text=EXPLANATION, reverse=False, **options):
    body = {"infeasible": True, "explanation": text}
    return {OUTPUT: dump(dict(reversed(list(body.items()))) if reverse else body, **options)}


def _verdict(label, *reasons):
    return {"label": label, "reasons": list(reasons)}


def solve(instance, limit=12):
    """Preference-optimal outputs, at most `limit`, canonical first; a correct infeasibility when nothing fits."""
    m = model(instance)
    valid = slots(m)
    if not valid:
        return [infeasible()]
    picks = {"earliest": valid[:1], "latest": valid[-1:]}.get(m["pref"], valid)
    return [slot_file(m, s, room) for s, rooms in picks for room in (rooms or [None])][:limit]


def check(instance, files):
    """Label an output: valid, suboptimal, invalid, unparseable, correct-infeasible or wrong-infeasible."""
    m = model(instance)
    raw = files.get(OUTPUT)
    if raw is None:
        return _verdict("unparseable", f"{OUTPUT} is missing")
    try:
        out = json.loads(raw.decode("utf-8-sig"))
    except ValueError as exc:
        return _verdict("unparseable", f"{OUTPUT} is not valid JSON: {exc}")
    if not isinstance(out, dict):
        return _verdict("unparseable", f"{OUTPUT} is not a JSON object")
    if out.get("infeasible") is True:
        explanation = out.get("explanation")
        reasons = [] if isinstance(explanation, str) and explanation.strip() else ["infeasible answer lacks an explanation"]
        valid = slots(m)
        if valid:
            return _verdict("wrong-infeasible", f"a valid slot exists at {iso(valid[0][0], m['woff'])}", *reasons)
        return _verdict("invalid" if reasons else "correct-infeasible", *reasons)
    try:
        s, e = stamp(out.get("start"))[0], stamp(out.get("end"))[0]
    except ValueError as exc:
        return _verdict("unparseable", str(exc))
    reasons = []
    if e - s != m["dur"]:
        reasons.append(f"the slot lasts {e - s} minutes, expected {m['dur']}")
    if s < m["w0"] or e > m["w1"]:
        reasons.append("the slot is outside the window")
    elif (s - m["w0"]) % m["gran"]:
        reasons.append(f"the start is not on the {m['gran']}-minute grid anchored at the window start")
    for p in m["people"]:
        if p["required"] and (problem := person_problem(p, s, e)):
            reasons.append(problem)
    if m["rooms"]:
        room = out.get("room")
        if not isinstance(room, str) or room not in {r["id"] for r in m["rooms"]}:
            reasons.append("room is missing or unknown")
        elif room not in rooms_for(m, s, e):
            reasons.append(f"room {room} cannot host this slot")
    if reasons:
        return _verdict("invalid", *reasons)
    valid = slots(m)
    best = {"earliest": valid[0][0], "latest": valid[-1][0]}.get(m["pref"])
    if best is not None and s != best:
        return _verdict("suboptimal", f"valid, but the {m['pref']} valid start is {iso(best, m['woff'])}")
    return _verdict("valid")
