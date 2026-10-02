"""Outputs of the calendar domain: bookings written into the state files, defects, heuristics, labelled outputs.

An output is the whole final state: every calendars/ and rooms/ file plus result.json, as {path: bytes}.
The oracle's answer is the scheduling domain's, written into the files the interface names.
"""

from __future__ import annotations

import copy
import json
import random

from . import scheduling
from . import scheduling_rules as rules
from .calendar_check import check
from .calendar_state import RESULT, calendar_path, recognize, room_path, schedule_instance


def default_targets(instance, room=None):
    """The files a booking goes into: each required attendee's calendar and the booked room's."""
    return [calendar_path(p) for p in instance["request"]["attendees"]] + ([room_path(room)] if room else [])


def new_event_id(instance):
    taken = {e["id"] for doc in instance["state"].values() for e in doc["events"]}
    return next(f"bk-{n}" for n in range(1, len(taken) + 2) if f"bk-{n}" not in taken)


def booking_docs(instance, start, room=None, *, event_id=None, offset=None, targets=None):
    """(parsed files, parsed result.json) after booking the slot that starts at minute `start`.

    An entry is written in its owner's UTC offset, and result.json in the window's, unless `offset` forces one."""
    m = rules.model(instance["schedule"])
    event_id = event_id or new_event_id(instance)
    zones = {calendar_path(p["id"]): p["off"] for p in m["people"]}
    docs = copy.deepcopy(instance["state"])
    for path in default_targets(instance, room) if targets is None else targets:
        zone = zones.get(path, m["woff"]) if offset is None else offset
        docs[path]["events"].append({"id": event_id, "title": instance["request"].get("title", "Meeting"), "kind": "meeting",
                                     "start": rules.iso(start, zone), "end": rules.iso(start + m["dur"], zone)})
    zone = m["woff"] if offset is None else offset
    body = {"start": rules.iso(start, zone), "end": rules.iso(start + m["dur"], zone), **({"room": room} if room else {}),
            "event_id": event_id}
    return docs, {"booked": body}


def refusal_docs(instance, explanation=rules.EXPLANATION):
    return copy.deepcopy(instance["state"]), {"infeasible": True, "explanation": explanation}


def render(docs, result=None, indent=2):
    files = {path: rules.dump(doc, indent=indent) for path, doc in docs.items()}
    if result is not None:
        files[RESULT] = rules.dump(result, indent=indent)
    return files


def booking(instance, start, room=None, *, indent=2, **options):
    return render(*booking_docs(instance, start, room, **options), indent=indent)


def _translate(instance, scheduling_files):
    """The calendar output for one scheduling output.json."""
    out = json.loads(scheduling_files[rules.OUTPUT])
    if out.get("infeasible"):
        return render(*refusal_docs(instance, out["explanation"]))
    return booking(instance, rules.stamp(out["start"])[0], out.get("room"))


def solve(instance, limit=12):
    """Preference-optimal outputs, at most `limit`, canonical first; a correct refusal when nothing fits."""
    return [_translate(instance, files) for files in scheduling.solve(instance["schedule"], limit)]


# ---- defects ---------------------------------------------------------------------------------------

def _without(policy, kind):
    return {**policy, "rules": [r for r in policy["rules"] if r["type"] != kind]}


def _books_as(instance, **changes):
    """The oracle's booking for a distorted copy of the workspace, written into the real files."""
    mod = {**instance, **changes}
    return _translate(instance, scheduling.solve(schedule_instance(mod))[0])


def _policy_blind_buffer(instance, rng):
    return _books_as(instance, policy=_without(instance["policy"], "buffer_minutes"))


def _policy_blind_focus(instance, rng):
    """Focus blocks read as free time."""
    state = {path: {**doc, "events": [e for e in doc["events"] if e.get("kind") != "focus"]}
             if path.startswith("calendars/") else doc for path, doc in instance["state"].items()}
    return _books_as(instance, state=state)


def _policy_blind_room_feature(instance, rng):
    return _books_as(instance, policy=_without(instance["policy"], "room_feature"))


def _double_book(instance, rng):
    """Room calendars are not consulted: the first room that seats everyone is taken."""
    state = {path: {**doc, "events": []} if path.startswith("rooms/") else doc for path, doc in instance["state"].items()}
    return _books_as(instance, state=state)


def _clobber(instance, rng):
    """The right booking, but one calendar is rewritten from scratch and keeps only the new entry."""
    files = solve(instance)[0]
    docs = {path: json.loads(files[path]) for path in instance["state"]}
    result = json.loads(files[RESULT])
    booked = result.get("booked", {})
    paths = default_targets(instance, booked.get("room")) if booked else [calendar_path(p) for p in instance["request"]["attendees"]]
    victims = [p for p in paths if instance["state"][p]["events"]]
    if victims:
        victim = rng.choice(sorted(victims))
        old = {e["id"] for e in instance["state"][victim]["events"]}
        docs[victim]["events"] = [e for e in docs[victim]["events"] if e["id"] not in old]
    return render(docs, result)


def _claims_done(instance, rng):
    """result.json reports the right booking and no file holds it."""
    return render(copy.deepcopy(instance["state"]), json.loads(solve(instance)[0][RESULT]))


DEFECTS = {
    "policy_blind_buffer": _policy_blind_buffer,
    "policy_blind_focus": _policy_blind_focus,
    "policy_blind_room_feature": _policy_blind_room_feature,
    "clobber": _clobber,
    "double_book": _double_book,
    "claims_done": _claims_done,
}


def _busy_only(workspace, prompt):
    """What a hurried assistant does: the earliest slot free of every entry, ignoring the policy's rules."""
    instance = recognize(workspace, prompt)
    if instance is None:
        return {}
    schedule = {**schedule_instance({**instance, "policy": {"rules": []}}), "preference": "earliest"}
    return _translate(instance, scheduling.solve(schedule)[0])


HEURISTICS = {"busy_only": _busy_only}


# ---- labelled outputs ------------------------------------------------------------------------------

def _style(doc, *, seconds=False, zulu=False, extra=False, reverse=False):
    doc = dict(doc)
    for key in ("start", "end"):
        if key in doc:
            text = doc[key]
            text = text[:16] + ":00" + text[16:] if seconds else text
            doc[key] = text[:-6] + "Z" if zulu and text.endswith("+00:00") else text
    if extra:
        doc["note"] = "booked by the assistant"
    return dict(reversed(list(doc.items()))) if reverse else doc


def variant(instance, start, room=None, *, indent=2, first=False, optional=False, **style):
    """A booking written differently: other offsets, key order, whitespace, seconds, an extra key, entry position."""
    targets = default_targets(instance, room)
    if optional:
        targets += [calendar_path(p) for p in instance["request"].get("optional", [])]
    offset = style.pop("offset", None)
    docs, result = booking_docs(instance, start, room, offset=offset, targets=targets)
    for path in targets:
        events = docs[path]["events"]
        events[-1] = _style(events[-1], **style)
        if first:
            events.insert(0, events.pop())
    result["booked"] = _style(result["booked"], **style)
    return render(docs, result, indent=indent)


def _spread(items, count):
    if len(items) <= count:
        return list(items)
    return [items[i * (len(items) - 1) // (count - 1)] for i in range(count)]


def _first_event(instance, paths):
    return next(((p, i) for p in paths for i in range(len(instance["state"][p]["events"]))), None)


def _clobbers(instance, base):
    """The oracle's output with an existing entry or a calendar's own field damaged: (kind, files) pairs."""
    paths = [p for p in instance["state"] if instance["state"][p]["events"]]
    found = _first_event(instance, paths)
    docs = {p: json.loads(base[p]) for p in instance["state"]}
    out = []

    def damaged(kind, edit):
        mod = copy.deepcopy(docs)
        edit(mod)
        out.append((kind, render(mod, json.loads(base[RESULT]))))

    if found:
        path, n = found
        damaged("clobber:removed-entry", lambda d: d[path]["events"].pop(n))
        damaged("clobber:edited-entry", lambda d: d[path]["events"][n].update(title=d[path]["events"][n].get("title", "") + " (edited)"))
        minute, zone = rules.stamp(instance["state"][path]["events"][n]["start"])
        damaged("clobber:moved-entry", lambda d: d[path]["events"][n].update(start=rules.iso(minute + 15, zone)))
    owner = next((p for p in instance["state"] if p.startswith("calendars/")), None)
    if owner:
        damaged("clobber:changed-work-hours", lambda d: d[owner].update(work_hours=[]))
    return out


def labeled(instance):
    """Outputs with expected labels, for testing a grader: valid variants, suboptimal and invalid outputs."""
    m = rules.model(instance["schedule"])
    valid = rules.slots(m)
    items = []

    def add(files, label, kind):
        if all(files != item["files"] for item in items):
            items.append({"files": files, "label": label, "kind": kind})

    def add_if_rejected(files, kind):
        if check(instance, files)["label"] in rules.REJECTED:
            add(files, "invalid", kind)

    for name, defect in DEFECTS.items():
        for seed in (0, 1):
            add_if_rejected(defect(instance, random.Random(seed)), f"defect:{name}")
    base = solve(instance)[0]
    for kind, files in _clobbers(instance, base):
        add_if_rejected(files, kind)
    docs = {p: json.loads(base[p]) for p in instance["state"]}
    if not valid:
        add(base, "valid", "canonical")
        add(render(*refusal_docs(instance, "Nobody can attend: the calendars never line up.")), "valid", "explanation-variant")
        add(render(*refusal_docs(instance), indent=4), "valid", "whitespace-variant")
        add(render(*refusal_docs(instance, "")), "invalid", "empty-explanation")
        add(render(docs, {"infeasible": True}), "invalid", "missing-explanation")
        add_if_rejected(booking(instance, m["w0"], m["rooms"][0]["id"] if m["rooms"] else None), "slot-for-infeasible")
        add(render(docs, None), "invalid", "no-result")
        return items

    picks = {"earliest": valid[:1], "latest": valid[-1:]}.get(m["pref"], valid)
    s0, rooms0 = picks[0]
    room0 = rooms0[0] if rooms0 else None
    add(base, "valid", "canonical")
    zones = [z for z in dict.fromkeys([0, *(p["off"] for p in m["people"]), 330]) if z != m["woff"]]
    for zone in zones[:2]:
        add(variant(instance, s0, room0, offset=zone), "valid", "offset-variant")
    if m["woff"] == 0:
        add(variant(instance, s0, room0, zulu=True), "valid", "offset-variant")
    add(variant(instance, s0, room0, reverse=True), "valid", "key-order-variant")
    add(variant(instance, s0, room0, indent=4), "valid", "whitespace-variant")
    add(variant(instance, s0, room0, indent=None), "valid", "whitespace-variant")
    add(variant(instance, s0, room0, seconds=True), "valid", "seconds-variant")
    add(variant(instance, s0, room0, extra=True), "valid", "extra-key-variant")
    add(variant(instance, s0, room0, first=True), "valid", "entry-order-variant")
    if instance["request"].get("optional"):
        add(variant(instance, s0, room0, optional=True), "valid", "invited-optional")
    for room in rooms0[1:3]:
        add(booking(instance, s0, room), "valid", "alternate-optimal")
    others = [v for v in valid if v[0] != s0]
    if m["pref"] == "any":
        for s, rooms in _spread(others, 3):
            add(booking(instance, s, rooms[0] if rooms else None), "valid", "alternate-optimal")
    else:
        for s, rooms in _spread(others, 2):
            add(booking(instance, s, rooms[0] if rooms else None), "suboptimal", "valid-not-optimal")

    for gap, kind in ((-m["gran"], "shifted-earlier"), (m["gran"], "shifted-later")):
        add_if_rejected(booking(instance, s0 + gap, room0), kind)
    add_if_rejected(render(*refusal_docs(instance)), "wrong-infeasible")
    add_if_rejected(render(docs, None), "no-result")
    add_if_rejected(render(docs, {"booked": {**json.loads(base[RESULT])["booked"], "event_id": "someone-else"}}), "wrong-event-id")
    wrong_time, _ = booking_docs(instance, s0 + m["gran"], room0, event_id=json.loads(base[RESULT])["booked"]["event_id"])
    add_if_rejected(render(wrong_time, json.loads(base[RESULT])), "state-result-mismatch")
    attendee = calendar_path(instance["request"]["attendees"][0])
    gone = copy.deepcopy(docs)
    gone[attendee]["events"].pop()
    add_if_rejected(render(gone, json.loads(base[RESULT])), "missing-attendee-entry")
    if room0:
        gone = copy.deepcopy(docs)
        gone[room_path(room0)]["events"].pop()
        add_if_rejected(render(gone, json.loads(base[RESULT])), "missing-room-entry")
    twice = copy.deepcopy(docs)
    twice[attendee]["events"].append({**twice[attendee]["events"][-1], "id": "bk-again"})
    add_if_rejected(render(twice, json.loads(base[RESULT])), "duplicate-entry")
    strangers = [p for p in instance["state"] if p.startswith("calendars/") and p not in
                 {calendar_path(a) for a in [*instance["request"]["attendees"], *instance["request"].get("optional", [])]}]
    if strangers:
        stray = copy.deepcopy(docs)
        stray[strangers[0]]["events"].append(copy.deepcopy(docs[attendee]["events"][-1]))
        add_if_rejected(render(stray, json.loads(base[RESULT])), "entry-for-bystander")
    return items
