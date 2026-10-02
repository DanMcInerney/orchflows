"""Realistic wrong answers for a scheduling task, and the labelled outputs built from them.

Used by `generate.py` for admission/<task>/labeled and by `synthesize.py` to see which tasks each defect exercises.
Everything is computed with the reference solution (`solve.py`), never with the verifier: a labelled output is
`valid`, `suboptimal` or `invalid` according to the reference's own enumeration of valid starts, so grading the
labelled outputs checks the verifier against an independent implementation.
"""
import copy
import json
import random
from datetime import datetime, timedelta, timezone


def shift(text, minutes):
    return (datetime.fromisoformat(text) + timedelta(minutes=minutes)).isoformat(timespec="minutes")


def as_utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).isoformat(timespec="minutes")


def owners(inst):
    return [*inst["participants"], *inst.get("rooms", [])]


def classify(oracle, inst, out):
    """valid, suboptimal or invalid for one parsed output.json, by the reference's enumeration."""
    found = dict(oracle.valid_starts(inst))
    if out.get("infeasible") is True:
        ok = not found and isinstance(out.get("explanation"), str) and out["explanation"].strip()
        return "valid" if ok else "invalid"
    try:
        start, end = datetime.fromisoformat(out["start"]), datetime.fromisoformat(out["end"])
    except (KeyError, TypeError, ValueError):
        return "invalid"
    if start.tzinfo is None or end.tzinfo is None or end - start != timedelta(minutes=inst["duration_minutes"]) or start not in found:
        return "invalid"
    if inst.get("rooms") and out.get("room") not in found[start]:
        return "invalid"
    best = {"earliest": min(found), "latest": max(found)}.get(inst["preference"])
    return "valid" if best in (None, start) else "suboptimal"


# ---- defects: each returns the output.json content (a dict) a flawed assistant would give ---------------------

def redo(oracle, inst, edit):
    mod = copy.deepcopy(inst)
    edit(mod)
    return oracle.solve(mod)


def ignore_participant(oracle, inst, rng):
    def edit(mod):
        required = [p for p in mod["participants"] if p.get("required", True)]
        rng.choice([p for p in required if p.get("busy")] or required)["busy"] = []
    return redo(oracle, inst, edit)


def ignore_constraints(oracle, inst, rng):
    return redo(oracle, inst, lambda mod: mod.update(constraints=[]))


def boundary(oracle, inst, rng):
    """Busy time read one granule late, so a slot overlapping a busy block by one granule looks free."""
    def edit(mod):
        step = mod.get("granularity_minutes", 15)
        for owner in owners(mod):
            owner["busy"] = [{**b, "start": shift(b["start"], step)} for b in owner.get("busy", [])
                             if datetime.fromisoformat(shift(b["start"], step)) < datetime.fromisoformat(b["end"])]
    return redo(oracle, inst, edit)


def ignore_offsets(oracle, inst, rng):
    """Every wall-clock time read as UTC."""
    def edit(mod):
        mod["window"] = {k: as_utc(v) for k, v in mod["window"].items()}
        for owner in owners(mod):
            owner["busy"] = [{"start": as_utc(b["start"]), "end": as_utc(b["end"])} for b in owner.get("busy", [])]
        for p in mod["participants"]:
            p["utc_offset"] = "+00:00"
    return redo(oracle, inst, edit)


def optional_required(oracle, inst, rng):
    """Invitees marked optional are treated as required."""
    def edit(mod):
        for p in mod["participants"]:
            p["required"] = True
    return redo(oracle, inst, edit)


def never_infeasible(oracle, inst, rng):
    """Right whenever a slot exists; otherwise the grid start with the fewest broken rules."""
    if oracle.valid_starts(inst):
        return oracle.solve(inst)
    m = oracle.read(inst)
    best, least = m["lo"], None
    start = m["lo"]
    while start + m["duration"] <= m["hi"]:
        end = start + m["duration"]
        count = sum(oracle.blocked(p, start, end) is not None for p in m["people"]) + (bool(m["rooms"]) and not oracle.room_ids(m, start, end))
        if least is None or count < least:
            best, least = start, count
        start += m["step"]
    tz = datetime.fromisoformat(inst["window"]["start"]).tzinfo
    out = {"start": best.astimezone(tz).isoformat(timespec="minutes"),
           "end": (best + m["duration"]).astimezone(tz).isoformat(timespec="minutes")}
    if inst.get("rooms"):
        out["room"] = inst["rooms"][0]["id"]
    return out


def always_infeasible(oracle, inst, rng):
    return {"infeasible": True, "explanation": "There is no time that works for every participant."}


def greedy_first(oracle, inst, rng):
    """The first slot free for everyone: preference and constraints ignored."""
    return redo(oracle, inst, lambda mod: mod.update(constraints=[], preference="earliest"))


DEFECTS = {"ignore_participant": ignore_participant, "ignore_constraints": ignore_constraints, "boundary": boundary,
           "ignore_offsets": ignore_offsets, "optional_required": optional_required, "never_infeasible": never_infeasible, "always_infeasible": always_infeasible,
           "greedy_first": greedy_first}


def exercised(oracle, inst, name, seeds=range(6)):
    """Share of the defect's draws whose output is not full success on this instance."""
    wrong = sum(classify(oracle, inst, DEFECTS[name](oracle, inst, random.Random(seed))) != "valid" for seed in seeds)
    return wrong / len(seeds)


# ---- labelled outputs -----------------------------------------------------------------------------------------

def spread(items, count):
    if len(items) <= count:
        return list(items)
    return [items[i * (len(items) - 1) // (count - 1)] for i in range(count)]


def text(out, **options):
    return (json.dumps(out, **options) + "\n").encode("utf-8")


def slot_out(inst, start, room=None, zone=None, seconds=False, zulu=False):
    tz = zone or datetime.fromisoformat(inst["window"]["start"]).tzinfo
    end = start + timedelta(minutes=inst["duration_minutes"])

    def stamp(moment):
        value = moment.astimezone(tz).isoformat(timespec="minutes")
        if seconds:
            value = value[:16] + ":00" + value[16:]
        return value[:-6] + "Z" if zulu and value.endswith("+00:00") else value

    out = {"start": stamp(start), "end": stamp(end)}
    if room:
        out["room"] = room
    return out


def labeled(oracle, inst):
    """[(kind, label, bytes of output.json)]: valid variants, suboptimal slots and invalid answers, each labelled by the reference."""
    found = oracle.valid_starts(inst)
    items = []

    def add(kind, out_or_bytes, label=None):
        raw = out_or_bytes if isinstance(out_or_bytes, bytes) else text(out_or_bytes, indent=2)
        parsed = None
        try:
            parsed = json.loads(raw)
        except ValueError:
            pass
        truth = classify(oracle, inst, parsed) if isinstance(parsed, dict) else "invalid"
        if label == "valid" and truth != "valid":
            raise AssertionError(f"{kind}: expected a valid output, the reference says {truth}")
        if (label is None or truth == label) and all(raw != r for _, _, r in items):
            items.append((kind, truth, raw))

    for name in DEFECTS:
        for seed in (0, 1):
            out = DEFECTS[name](oracle, inst, random.Random(seed))
            if classify(oracle, inst, out) != "valid":
                add(f"defect:{name}", out)
    tz = datetime.fromisoformat(inst["window"]["start"]).tzinfo
    if not found:
        add("canonical", oracle.solve(inst), "valid")
        add("explanation-variant", {"explanation": "Nobody can attend: the calendars never line up.", "infeasible": True}, "valid")
        add("whitespace-variant", text({"infeasible": True, "explanation": "No common time exists."}, indent=4), "valid")
        add("empty-explanation", {"infeasible": True, "explanation": ""}, "invalid")
        add("missing-explanation", {"infeasible": True}, "invalid")
        add("slot-for-infeasible", slot_out(inst, datetime.fromisoformat(inst["window"]["start"]), inst["rooms"][0]["id"] if inst.get("rooms") else None), "invalid")
        add("prose", b"There is no time that suits everyone this week.\n", "invalid")
        return items
    picks = {"earliest": found[:1], "latest": found[-1:]}.get(inst["preference"], found)
    start, rooms = picks[0]
    room = rooms[0] if rooms else None
    add("canonical", slot_out(inst, start, room), "valid")
    zones = [timezone(timedelta(minutes=m)) for m in (0, 330, -480)]
    for zone in zones:
        add("offset-variant", slot_out(inst, start, room, zone), "valid")
    add("zulu-variant", slot_out(inst, start, room, timezone.utc, zulu=True), "valid")
    canonical = slot_out(inst, start, room)
    add("key-order-variant", dict(reversed(list(canonical.items()))), "valid")
    add("whitespace-variant", text(canonical, indent=4), "valid")
    add("compact-variant", text(canonical, separators=(",", ":")), "valid")
    add("seconds-variant", slot_out(inst, start, room, seconds=True), "valid")
    add("extra-key-variant", {**canonical, "note": "booked"}, "valid")
    add("bom-variant", b"\xef\xbb\xbf" + text(canonical), "valid")
    for other_room in rooms[1:3]:
        add("alternate-room", slot_out(inst, start, other_room), "valid")
    others = [f for f in found if f[0] != start]
    if inst["preference"] == "any":
        for s, r in spread(others, 3):
            add("alternate-start", slot_out(inst, s, r[0] if r else None), "valid")
    else:
        for s, r in spread(others, 3):
            add("valid-not-optimal", slot_out(inst, s, r[0] if r else None), "suboptimal")
    step = timedelta(minutes=inst.get("granularity_minutes", 15))
    for kind, moved in (("shifted-earlier", start - step), ("shifted-later", start + step)):
        add(kind, slot_out(inst, moved, room), "invalid")
    add("off-grid", slot_out(inst, start + timedelta(minutes=1), room), "invalid")
    add("wrong-duration", {**canonical, "end": shift(canonical["end"], inst.get("granularity_minutes", 15))}, "invalid")
    add("outside-window", slot_out(inst, datetime.fromisoformat(inst["window"]["end"]), room), "invalid")
    add("no-offset", {**canonical, "start": canonical["start"][:16], "end": canonical["end"][:16]}, "invalid")
    add("missing-end", {"start": canonical["start"]}, "invalid")
    add("prose", b"The meeting works best on the first morning.\n", "invalid")
    add("wrong-infeasible", {"infeasible": True, "explanation": "No participant can attend this week."}, "invalid")
    if inst.get("rooms"):
        add("unknown-room", {**canonical, "room": "no-such-room"}, "invalid")
        no_room = {k: v for k, v in canonical.items() if k != "room"}
        add("missing-room", no_room, "invalid")
    return items
