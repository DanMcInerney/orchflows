"""Meeting-scheduling domain for schedule-nosolver: the metabench hook protocol.

`scheduling_rules` holds the exact oracle and checker, `scheduling_naturalplan` the real material.
This module adds recognition, the defects and heuristics scripted members use, and labelled outputs.
"""

from __future__ import annotations

import copy
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import scheduling_naturalplan as _np
from . import scheduling_rules as rules
from .scheduling_rules import INPUT, OUTPUT

NAME = "scheduling"

solve = rules.solve
check = rules.check
valid_slots = rules.valid_slots
convert_natural_plan = _np.convert_natural_plan
natural_plan_answer = _np.natural_plan_answer
fetch_material = _np.fetch_material
load_instances = _np.load_instances


def recognize(workspace, prompt=""):
    """The instance in workspace/input.json when it conforms to the interface, else None."""
    try:
        instance = json.loads((Path(workspace) / INPUT).read_text(encoding="utf-8-sig"))
        rules.model(instance)
    except (OSError, ValueError, TypeError, KeyError):
        return None
    return instance


def apply(workspace, files):
    for rel, data in files.items():
        path = Path(workspace) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


# ---- defects: realistic failures, each wrong on instances where it matters ------------------------

def _shift(stamp, minutes):
    return (datetime.fromisoformat(stamp) + timedelta(minutes=minutes)).isoformat(timespec="minutes")


def _utc(stamp):
    return datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc).isoformat(timespec="minutes")


def _owners(inst):
    return [*inst["participants"], *inst.get("rooms", [])]


def _redo(inst, edit):
    """The oracle's answer for a copy of the instance that `edit` has distorted."""
    mod = copy.deepcopy(inst)
    edit(mod)
    return solve(mod)[0]


def _ignore_participant(inst, rng):
    def edit(mod):
        required = [p for p in mod["participants"] if p.get("required", True)]
        rng.choice([p for p in required if p.get("busy")] or required)["busy"] = []
    return _redo(inst, edit)


def _ignore_constraints(inst, rng):
    return _redo(inst, lambda mod: mod.update(constraints=[]))


def _boundary(inst, rng):
    """Busy blocks read one granule late: a slot overlapping one granule of busy time at its end looks free."""
    def edit(mod):
        gran = mod.get("granularity_minutes", 15)
        for owner in _owners(mod):
            kept = []
            for b in owner.get("busy", []):
                start = _shift(b["start"], gran)
                if rules.stamp(start)[0] < rules.stamp(b["end"])[0]:
                    kept.append({**b, "start": start})
            owner["busy"] = kept
    return _redo(inst, edit)


def _ignore_offsets(inst, rng):
    """Every wall-clock time read as UTC, as when offsets are stripped from timestamps."""
    def edit(mod):
        mod["window"] = {k: _utc(v) for k, v in mod["window"].items()}
        for owner in _owners(mod):
            owner["busy"] = [{**b, "start": _utc(b["start"]), "end": _utc(b["end"])} for b in owner.get("busy", [])]
        for p in mod["participants"]:
            p["utc_offset"] = "+00:00"
    return _redo(inst, edit)


def _never_infeasible(inst, rng):
    """Correct whenever a slot exists; otherwise proposes the slot with the fewest conflicts."""
    m = rules.model(inst)
    if rules.slots(m):
        return solve(inst)[0]
    required = [p for p in m["people"] if p["required"]]

    def conflicts(s):
        e = s + m["dur"]
        rooms_missing = bool(m["rooms"]) and not rules.rooms_for(m, s, e)
        return sum(rules.person_problem(p, s, e) is not None for p in required) + rooms_missing

    s = min(rules.starts(m), key=conflicts, default=m["w0"])
    return rules.slot_file(m, s, m["rooms"][0]["id"] if m["rooms"] else None)


def _always_infeasible(inst, rng):
    return rules.infeasible("There is no time that works for every participant.")


DEFECTS = {
    "ignore_participant": _ignore_participant,
    "ignore_constraints": _ignore_constraints,
    "boundary": _boundary,
    "ignore_offsets": _ignore_offsets,
    "never_infeasible": _never_infeasible,
    "always_infeasible": _always_infeasible,
}


# ---- heuristics: what a hurried implementation would do ------------------------------------------

def _greedy_first(workspace, prompt):
    """The first slot free for everyone, ignoring `preference` and the `constraints` list."""
    instance = recognize(workspace, prompt)
    if instance is None:
        return {}
    mod = copy.deepcopy(instance)
    mod.update(constraints=[], preference="earliest")
    return solve(mod)[0]


def _random_valid_format(workspace, prompt):
    """A well-formed answer at a random grid start: the right shape with no scheduling behind it."""
    instance = recognize(workspace, prompt)
    if instance is None:
        return {}
    m = rules.model(instance)
    rng = random.Random()
    s = rng.choice(list(rules.starts(m)) or [m["w0"]])
    return rules.slot_file(m, s, rng.choice(m["rooms"])["id"] if m["rooms"] else None)


HEURISTICS = {"greedy_first": _greedy_first, "random_valid_format": _random_valid_format}
FLOORS = ("random_valid_format",)


# ---- labelled outputs ----------------------------------------------------------------------------

def _spread(items, count):
    """Up to `count` items spread evenly over the sequence."""
    if len(items) <= count:
        return list(items)
    return [items[i * (len(items) - 1) // (count - 1)] for i in range(count)]


def labeled(instance):
    """Outputs with expected labels, for testing a grader: valid variants, suboptimal and invalid outputs."""
    m = rules.model(instance)
    valid = rules.slots(m)
    items = []

    def add(files, label, kind):
        if all(files != item["files"] for item in items):
            items.append({"files": files, "label": label, "kind": kind})

    def add_if_rejected(files, kind):
        if check(instance, files)["label"] in rules.REJECTED:
            add(files, "invalid", kind)

    def slot(s, room=None, *args, **options):
        return rules.slot_file(m, s, room, *args, **options)

    for name, defect in DEFECTS.items():
        for seed in (0, 1):
            add_if_rejected(defect(instance, random.Random(seed)), f"defect:{name}")
    first_room = m["rooms"][0]["id"] if m["rooms"] else None
    if not valid:
        add(rules.infeasible(), "valid", "canonical")
        add(rules.infeasible("Nobody can attend: the calendars never line up.", reverse=True), "valid", "explanation-variant")
        add(rules.infeasible(indent=4), "valid", "whitespace-variant")
        add({OUTPUT: rules.dump({"infeasible": True, "explanation": ""})}, "invalid", "empty-explanation")
        add({OUTPUT: rules.dump({"infeasible": True})}, "invalid", "missing-explanation")
        add(slot(m["w0"], first_room), "invalid", "slot-for-infeasible")
        return items

    picks = {"earliest": valid[:1], "latest": valid[-1:]}.get(m["pref"], valid)
    s0, rooms0 = picks[0]
    room0 = rooms0[0] if rooms0 else None
    add(slot(s0, room0), "valid", "canonical")
    zones = [z for z in dict.fromkeys([0, *(p["off"] for p in m["people"]), 330]) if z != m["woff"]]
    for zone in zones[:2]:
        add(slot(s0, room0, zone), "valid", "offset-variant")
    if m["woff"] == 0:
        add(slot(s0, room0, zulu=True), "valid", "offset-variant")
    add(slot(s0, room0, reverse=True), "valid", "key-order-variant")
    add(slot(s0, room0, indent=4), "valid", "whitespace-variant")
    add(slot(s0, room0, seconds=True), "valid", "seconds-variant")
    add(slot(s0, room0, extra="booked"), "valid", "extra-key-variant")
    for room in rooms0[1:3]:
        add(slot(s0, room), "valid", "alternate-optimal")
    others = [v for v in valid if v[0] != s0]
    if m["pref"] == "any":
        for s, rooms in _spread(others, 3):
            add(slot(s, rooms[0] if rooms else None), "valid", "alternate-optimal")
    else:
        for s, rooms in _spread(others, 2):
            add(slot(s, rooms[0] if rooms else None), "suboptimal", "valid-not-optimal")

    base = json.loads(slot(s0, room0)[OUTPUT])
    for gap, kind in ((-m["gran"], "shifted-earlier"), (m["gran"], "shifted-later")):
        add_if_rejected(slot(s0 + gap, room0), kind)
    add_if_rejected({OUTPUT: rules.dump({**base, "end": rules.iso(s0 + m["dur"] + m["gran"], m["woff"])})}, "wrong-duration")
    if m["gran"] > 1:
        add_if_rejected(slot(s0 + 1, room0), "off-grid")
    add_if_rejected(slot(m["w1"] - m["dur"] + m["gran"], room0), "outside-window")
    add({OUTPUT: rules.dump({**base, "start": base["start"][:16], "end": base["end"][:16]})}, "invalid", "no-offset")
    add({OUTPUT: rules.dump({"start": base["start"]})}, "invalid", "missing-end")
    add({OUTPUT: b"The meeting works best on the first morning.\n"}, "invalid", "prose")
    if m["rooms"]:
        add({OUTPUT: rules.dump({**base, "room": "no-such-room"})}, "invalid", "unknown-room")
    return items
