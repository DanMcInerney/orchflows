"""Realistic wrong outcomes for a booking task, and the labelled final workspaces built from them.

Used by `generate.py` for admission/<task>/labeled and by `synthesize.py` to see which tasks each defect exercises.
Everything is computed with the reference solution (`solve.py`), never with the verifier: a slot is labelled `valid`,
`suboptimal` or `invalid` by the reference's enumeration of valid starts, and structural damage is invalid by
construction, so grading the labelled outcomes checks the verifier against an independent implementation.
An outcome is (docs, result): the parsed calendar and room files plus the parsed result.json, or None for no result.
"""
import copy
import json
import random
from datetime import datetime, timedelta, timezone


def zone_of(doc, window):
    from_text = doc.get("utc_offset")
    if from_text is None:
        return datetime.fromisoformat(window["start"]).tzinfo
    sign = -1 if from_text[0] == "-" else 1
    return timezone(sign * timedelta(hours=int(from_text[1:3]), minutes=int(from_text[4:6])))


def attendee_paths(docs):
    return [f"calendars/{p}.json" for p in docs["request"]["attendees"]]


def paths(docs):
    return [*(f"calendars/{p}.json" for p in docs["calendars"]), *(f"rooms/{r}.json" for r in docs["rooms"])]


def doc_at(docs, path):
    group, name = path.removesuffix(".json").split("/")
    return docs[group][name]


def stamp(moment, tz, seconds=False, zulu=False):
    text = moment.astimezone(tz).isoformat(timespec="minutes")
    if seconds:
        text = text[:16] + ":00" + text[16:]
    return text[:-6] + "Z" if zulu and text.endswith("+00:00") else text


def booking(solve, docs, start, room=None, *, event_id=None, offset=None, targets=None, style=None, first=False):
    """(docs, result) after booking the slot that starts at `start`; entries are written in their owner's offset unless `offset` forces one."""
    style, out = style or {}, copy.deepcopy(docs)
    request, ident = docs["request"], event_id or solve.new_id(docs)
    end = start + timedelta(minutes=request["duration_minutes"])
    window = request["window"]
    chosen = targets if targets is not None else attendee_paths(docs) + ([f"rooms/{room}.json"] if room else [])
    for path in chosen:
        doc = doc_at(out, path)
        tz = offset or zone_of(doc, window)
        entry = {"id": ident, "title": request.get("title", "Meeting"), "kind": "meeting",
                 "start": stamp(start, tz, **{k: style.get(k, False) for k in ("seconds", "zulu")}),
                 "end": stamp(end, tz, **{k: style.get(k, False) for k in ("seconds", "zulu")})}
        if style.get("extra"):
            entry["note"] = "booked by the assistant"
        if style.get("reverse"):
            entry = dict(reversed(list(entry.items())))
        doc["events"].insert(0 if first else len(doc["events"]), entry)
    tz = offset or zone_of({}, window)
    booked = {"start": stamp(start, tz, **{k: style.get(k, False) for k in ("seconds", "zulu")}),
              "end": stamp(end, tz, **{k: style.get(k, False) for k in ("seconds", "zulu")}), "event_id": ident}
    if room:
        booked["room"] = room
    if style.get("extra"):
        booked["note"] = "booked by the assistant"
    if style.get("reverse"):
        booked = dict(reversed(list(booked.items())))
    return out, {"booked": booked}


def refusal(docs, explanation="No time satisfies every attendee and the policy."):
    return copy.deepcopy(docs), {"infeasible": True, "explanation": explanation}


def render(docs, result, indent=2):
    """{relative path: bytes} for the calendar and room files and result.json (when there is one)."""
    dump = lambda doc: (json.dumps(doc, indent=indent) + "\n").encode("utf-8")  # noqa: E731
    files = {path: dump(doc_at(docs, path)) for path in paths(docs)}
    if result is not None:
        files["result.json"] = result if isinstance(result, bytes) else dump(result)
    return files


def label_slot(solve, docs, start, room):
    """valid, suboptimal or invalid for a booking at `start` in `room`, by the reference's enumeration."""
    found = dict(solve.valid_starts(solve.instance_of(docs)))
    if start not in found or (docs["rooms"] and room not in found[start]):
        return "invalid"
    pref = docs["request"]["preference"]
    best = {"earliest": min(found), "latest": max(found)}.get(pref)
    return "valid" if best in (None, start) else "suboptimal"


def label_outcome(solve, docs, outcome):
    """The label of an outcome built from a distorted solve: its slot, or a refusal, judged by the reference."""
    result = outcome[1]
    if result.get("infeasible"):
        return "invalid" if solve.valid_starts(solve.instance_of(docs)) else "valid"
    booked = result["booked"]
    return label_slot(solve, docs, datetime.fromisoformat(booked["start"]), booked.get("room"))


# ---- defects: each returns the outcome (docs, result) a flawed assistant would leave --------------------------

def distorted(solve, docs, edit):
    mod = copy.deepcopy(docs)
    edit(mod)
    chosen = solve.plan(mod)
    return refusal(docs) if chosen is None else booking(solve, docs, *chosen)


def policy_blind_buffer(solve, docs, rng):
    return distorted(solve, docs, lambda m: m["policy"].update(rules=[r for r in m["policy"]["rules"] if r["type"] != "buffer_minutes"]))


def policy_blind_room_feature(solve, docs, rng):
    return distorted(solve, docs, lambda m: m["policy"].update(rules=[r for r in m["policy"]["rules"] if r["type"] != "room_feature"]))


def policy_blind_focus(solve, docs, rng):
    def edit(m):
        for doc in m["calendars"].values():
            doc["events"] = [e for e in doc["events"] if e.get("kind") != "focus"]
    return distorted(solve, docs, edit)


def double_book(solve, docs, rng):
    def edit(m):
        for doc in m["rooms"].values():
            doc["events"] = []
    return distorted(solve, docs, edit)


def holders(docs):
    """Attendees whose calendars already hold entries a booking must preserve."""
    return [p for p in attendee_paths(docs) if doc_at(docs, p)["events"]]


def clobber(solve, docs, rng):
    """The right booking, but one attendee's calendar is rewritten from scratch and keeps only the new entry.
    Only an attendee with existing entries has anything to lose."""
    chosen = solve.plan(docs)
    if chosen is None:
        return refusal(docs)
    out, result = booking(solve, docs, *chosen)
    if holders(docs):
        victim = doc_at(out, rng.choice(holders(docs)))
        victim["events"] = victim["events"][-1:]
    return out, result


def claims_done(solve, docs, rng):
    """result.json reports the right booking and no file holds it."""
    chosen = solve.plan(docs)
    if chosen is None:
        return refusal(docs)
    return copy.deepcopy(docs), booking(solve, docs, *chosen)[1]


DEFECTS = {"policy_blind_buffer": policy_blind_buffer, "policy_blind_focus": policy_blind_focus,
           "policy_blind_room_feature": policy_blind_room_feature, "clobber": clobber, "double_book": double_book,
           "claims_done": claims_done}


def defect_label(solve, docs, name, outcome):
    if name == "clobber":
        return "invalid" if solve.plan(docs) and holders(docs) else "valid"
    if name == "claims_done":
        return "invalid" if solve.plan(docs) else "valid"
    return label_outcome(solve, docs, outcome)


def busy_only(solve, docs, rng):
    """A content-blind assistant: the earliest slot free of every entry, the policy and the preference ignored."""
    return distorted(solve, docs, lambda m: (m["policy"].update(rules=[]), m["request"].update(preference="earliest")))


def pays_blind(solve, docs):
    """Does the content-blind assistant earn credit here (a valid or merely suboptimal booking)? A task where it does
    would reward ignoring the policy."""
    return label_outcome(solve, docs, busy_only(solve, docs, random.Random(0))) != "invalid"


def exercised(solve, docs, name, seeds=range(3)):
    """Share of the defect's draws whose outcome is not full success on this workspace."""
    wrong = 0
    for seed in seeds:
        outcome = DEFECTS[name](solve, docs, random.Random(seed))
        wrong += defect_label(solve, docs, name, outcome) != "valid"
    return wrong / len(seeds)


# ---- labelled outcomes ----------------------------------------------------------------------------------------

def spread(items, count):
    if len(items) <= count:
        return list(items)
    return [items[i * (len(items) - 1) // (count - 1)] for i in range(count)]


def labeled(solve, docs):
    """[(kind, label, files)]: valid variants, suboptimal and invalid outcomes as final workspace files."""
    instance = solve.instance_of(docs)
    found = solve.valid_starts(instance)
    pref, step = docs["request"]["preference"], docs["request"].get("granularity_minutes", 15)
    items = []

    def add(kind, label, outcome=None, files=None, expect=None):
        files = files if files is not None else render(*outcome)
        if expect and label != expect:
            raise AssertionError(f"{kind}: expected {expect}, built {label}")
        if all(files != f for _, _, f in items):
            items.append((kind, label, files))

    for name, defect in DEFECTS.items():
        for seed in (0, 1):
            outcome = defect(solve, docs, random.Random(seed))
            label = defect_label(solve, docs, name, outcome)
            if label != "valid":
                add(f"defect:{name}", label, outcome)
    tz = datetime.fromisoformat(docs["request"]["window"]["start"]).tzinfo
    if not found:
        base = refusal(docs)
        add("canonical", "valid", base, expect="valid")
        add("explanation-variant", "valid", refusal(docs, "Nobody can attend: the calendars never line up."), expect="valid")
        add("whitespace-variant", "valid", None, render(*base, indent=4), expect="valid")
        add("empty-explanation", "invalid", (docs, {"infeasible": True, "explanation": ""}))
        add("missing-explanation", "invalid", (docs, {"infeasible": True}))
        lo = datetime.fromisoformat(docs["request"]["window"]["start"])
        room = next(iter(docs["rooms"]), None)
        add("slot-for-infeasible", "invalid", booking(solve, docs, lo, room))
        add("no-result", "invalid", (docs, None))
        add("entry-with-refusal", "invalid", (booking(solve, docs, lo, room)[0], base[1]))
        add("claims-done", "invalid", (docs, booking(solve, docs, lo, room)[1]))
        add("prose", "invalid", None, render(docs, b"Nothing fits this week.\n"))
        return items
    picks = {"earliest": found[:1], "latest": found[-1:]}.get(pref, found)
    start, rooms0 = picks[0]
    room = rooms0[0] if rooms0 else None
    base = booking(solve, docs, start, room)
    add("canonical", "valid", base, expect="valid")
    for zone in (timezone.utc, timezone(timedelta(minutes=330)), timezone(timedelta(minutes=-480))):
        add("offset-variant", "valid", booking(solve, docs, start, room, offset=zone), expect="valid")
    add("zulu-variant", "valid", booking(solve, docs, start, room, offset=timezone.utc, style={"zulu": True}), expect="valid")
    add("key-order-variant", "valid", booking(solve, docs, start, room, style={"reverse": True}), expect="valid")
    add("whitespace-variant", "valid", None, render(*base, indent=4), expect="valid")
    add("compact-variant", "valid", None, render(*base, indent=None), expect="valid")
    add("seconds-variant", "valid", booking(solve, docs, start, room, style={"seconds": True}), expect="valid")
    add("extra-key-variant", "valid", booking(solve, docs, start, room, style={"extra": True}), expect="valid")
    add("entry-order-variant", "valid", booking(solve, docs, start, room, first=True), expect="valid")
    invited = [f"calendars/{p}.json" for p in docs["request"].get("optional", [])]
    if invited:
        add("invited-optional", "valid", booking(solve, docs, start, room, targets=attendee_paths(docs) + invited + ([f"rooms/{room}.json"] if room else [])), expect="valid")
    for other in rooms0[1:3]:
        add("alternate-room", "valid", booking(solve, docs, start, other), expect="valid")
    others = [f for f in found if f[0] != start]
    for s, r in spread(others, 3):
        add("alternate-start" if pref == "any" else "valid-not-optimal", "valid" if pref == "any" else "suboptimal",
            booking(solve, docs, s, r[0] if r else None), expect="valid" if pref == "any" else "suboptimal")
    for kind, moved in (("shifted-earlier", start - timedelta(minutes=step)), ("shifted-later", start + timedelta(minutes=step))):
        label = label_slot(solve, docs, moved, room)
        if label == "invalid":
            add(kind, label, booking(solve, docs, moved, room))
    add("wrong-infeasible", "invalid", refusal(docs))
    add("no-result", "invalid", (base[0], None))
    add("prose", "invalid", None, render(base[0], b"Booked it.\n"))
    add("wrong-event-id", "invalid", (base[0], {"booked": {**base[1]["booked"], "event_id": "someone-else"}}))
    wrong_time = booking(solve, docs, start + timedelta(minutes=step), room, event_id=base[1]["booked"]["event_id"])[0]
    add("state-result-mismatch", "invalid", (wrong_time, base[1]))
    attendee = attendee_paths(docs)[0]
    gone = copy.deepcopy(base[0])
    doc_at(gone, attendee)["events"].pop()
    add("missing-attendee-entry", "invalid", (gone, base[1]))
    if room:
        gone = copy.deepcopy(base[0])
        doc_at(gone, f"rooms/{room}.json")["events"].pop()
        add("missing-room-entry", "invalid", (gone, base[1]))
    twice = copy.deepcopy(base[0])
    doc_at(twice, attendee)["events"].append({**doc_at(twice, attendee)["events"][-1], "id": "bk-again"})
    add("duplicate-entry", "invalid", (twice, base[1]))
    owners = holders(docs)
    holder = owners[0] if owners else attendee
    if owners:
        reuse = copy.deepcopy(base[0])
        taken = doc_at(docs, holder)["events"][0]["id"]
        doc_at(reuse, holder)["events"][-1]["id"] = taken
        add("id-reuse", "invalid", (reuse, {"booked": {**base[1]["booked"], "event_id": taken}}))
    strangers = [p for p in docs["calendars"] if f"calendars/{p}.json" not in attendee_paths(docs) + invited]
    if strangers:
        stray = copy.deepcopy(base[0])
        stray["calendars"][strangers[0]]["events"].append(copy.deepcopy(doc_at(base[0], attendee)["events"][-1]))
        add("entry-for-bystander", "invalid", (stray, base[1]))
    entry_edits = (("clobber:removed-entry", lambda d: d["events"].pop(0)),
                   ("clobber:edited-entry", lambda d: d["events"][0].update(title=d["events"][0].get("title", "") + " (edited)")),
                   ("clobber:moved-entry", lambda d: d["events"][0].update(start=stamp(datetime.fromisoformat(d["events"][0]["start"]) + timedelta(minutes=15), tz))))
    for kind, edit in (*(entry_edits if owners else ()), ("clobber:changed-work-hours", lambda d: d.update(work_hours=[]))):
        broken = copy.deepcopy(base[0])
        edit(doc_at(broken, holder))
        add(kind, "invalid", (broken, base[1]))
    deleted = render(base[0], base[1])
    del deleted[holder]
    add("clobber:deleted-file", "invalid", None, deleted)
    return items
