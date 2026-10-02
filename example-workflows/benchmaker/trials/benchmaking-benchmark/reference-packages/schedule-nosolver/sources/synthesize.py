"""Writes ../offline-instances/*.json and rejections.jsonl: python synthesize.py

Each slot below describes one task of the offline package: its team, family, request and what must hold of the
result. For every slot the script tries seeds until a candidate passes the admission filters, and logs every try:
the request must be feasible (or deliberately infeasible), only a handful of the grid's starts may be valid so a
guess almost never works, and the defects the slot targets must actually go wrong on it. The reference solution,
not the verifier, is the oracle. Deterministic: seeds are slot ids plus a counter.
"""
import importlib.util
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_calendars as bc  # noqa: E402
import defects  # noqa: E402
from slots import SLOTS  # noqa: E402

spec_ = importlib.util.spec_from_file_location("oracle", HERE / "task" / "solve.py")
oracle = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(oracle)

FIRST = bc.MONDAY.date()
MAX_FRACTION = 0.015
EXERCISED = 0.5
CHOICES = {"nb": ["09:30", "10:00", "10:30", "11:00", "13:00"], "na": ["15:00", "15:30", "16:00", "16:30"],
           "bf": [10, 15, 20, 30]}


def zone_of(pid):
    return bc.zone(bc.person(pid)["utc_offset"])


def constraint(rng, spec, item, first):
    kind, pid, *args = item
    value = args[0] if args else None
    if kind == "rf":
        return {"type": "room_feature", "feature": pid}
    if kind in ("nb", "na"):
        return {"type": "not_before" if kind == "nb" else "not_after", "participant": pid, "time": value or rng.choice(CHOICES[kind])}
    if kind in ("nbd", "nad"):
        return {"type": "not_before" if kind == "nbd" else "not_after", "participant": pid, "day": str(first + timedelta(days=value)), "time": args[1]}
    if kind == "av":
        return {"type": "avoid_day", "participant": pid, "day": str(first + timedelta(days=value))}
    return {"type": "buffer_minutes", "participant": pid, "minutes": value or rng.choice(CHOICES["bf"])}


def start_instance(rng, spec):
    first = FIRST + timedelta(days=spec.get("day", 0))
    tz = zone_of(spec.get("window_of", spec["ids"][0]))
    begin = bc.local(first, spec.get("from", "00:00"), tz)
    people = []
    for pid in spec["ids"] + spec.get("optional", []):
        template = rng.choice(spec["pool"][pid]) if pid in spec.get("pool", {}) else None
        p = bc.person(pid, template)
        if pid in spec.get("optional", []):
            p["required"] = False
        people.append(p)
    return first, {"duration_minutes": spec["dur"], "granularity_minutes": spec.get("gran", 15),
                   "window": {"start": bc.stamp(begin), "end": bc.stamp(begin + timedelta(days=spec["days"], minutes=spec.get("extra", 0)))},
                   "participants": people, "rooms": bc.rooms(*spec["rooms"]) if spec.get("rooms") else [],
                   "constraints": [], "preference": spec["pref"]}


def populate(rng, spec, first, inst, avoid=()):
    for p in inst["participants"]:
        bc.fill_calendar(rng, p, first, spec["days"], spec.get("per_day", (2, 4)), spec.get("habits", ("lunch", "standup")),
                         utc=p["id"] in spec.get("export_utc", ()), avoid=avoid)
    for pid, day in spec.get("off", ()):
        bc.time_off(rng, next(p for p in inst["participants"] if p["id"] == pid), first + timedelta(days=day))
    if inst["rooms"]:
        bc.fill_rooms(rng, inst, first, spec["days"], spec.get("room_per_day", (1, 3)))
    inst["constraints"] = [constraint(rng, spec, c, first) for c in spec.get("constraints", ())]
    bc.owner_busy_sort(inst)


def adjacent_blocks(rng, inst, slot):
    """Meetings that end exactly when the slot starts and start exactly when it ends, plus a duplicate and an overlapping entry."""
    dur = timedelta(minutes=inst["duration_minutes"])
    first, second, third = required(inst)[:3]
    for owner, begin, end in ((first, slot - timedelta(minutes=45), slot), (second, slot + dur, slot + dur + timedelta(minutes=30)),
                              (third, slot - timedelta(minutes=30), slot), (third, slot - timedelta(minutes=60), slot - timedelta(minutes=15)),
                              (first, slot - timedelta(minutes=45), slot)):
        bc.add_busy(owner, begin, end)
    bc.owner_busy_sort(inst)


def required(inst):
    return [p for p in inst["participants"] if p.get("required", True)]


def kill_with_blocks(rng, inst, starts, near_miss=True):
    """Meetings for required participants that remove every start in `starts`, overlapping each slot's last granule."""
    step, dur = inst.get("granularity_minutes", 15), inst["duration_minutes"]
    for s in starts:
        owner = rng.choice(required(inst))
        tz = bc.zone(owner["utc_offset"])
        begin = (s + timedelta(minutes=dur - step if near_miss else 0)).astimezone(tz)
        begin = begin.replace(minute=begin.minute - begin.minute % 15, second=0, microsecond=0)
        bc.add_busy(owner, begin, begin + timedelta(minutes=rng.choice([30, 45, 60])))
    bc.owner_busy_sort(inst)


def finish_infeasible(rng, spec, inst, first):
    kind = spec["kind"]
    ceiling = 3
    if kind == "last-slot":
        starts = bc.squeeze(rng, oracle, inst, ceiling)
        kill_with_blocks(rng, inst, starts)
    elif kind == "rooms":
        starts = bc.squeeze(rng, oracle, inst, ceiling)
        for r in inst["rooms"]:
            if "video" in r["features"]:
                for s in starts:
                    b = s - timedelta(minutes=15)
                    r["busy"].append({"start": bc.stamp(b), "end": bc.stamp(b + timedelta(minutes=inst["duration_minutes"] + 30))})
    elif kind == "clash":
        for item in spec["clash"]:
            inst["constraints"].append(constraint(rng, spec, item, first))
            if not oracle.valid_starts(inst):
                break
    elif kind == "offday":
        starts = bc.squeeze(rng, oracle, inst, 8)
        days = {}
        for pid in spec["ids"]:
            tz = zone_of(pid)
            days = {s.astimezone(tz).date() for s in starts}
            if len(days) == 1:
                inst["constraints"].append({"type": "avoid_day", "participant": pid, "day": str(next(iter(days)))})
                break
    elif kind == "short":
        starts = [s for s, _ in oracle.valid_starts(inst)]
        kill_with_blocks(rng, inst, starts[:6], near_miss=False)
        starts = [s for s, _ in oracle.valid_starts(inst)]
        kill_with_blocks(rng, inst, starts, near_miss=False)
    bc.owner_busy_sort(inst)


def make(rng, spec):
    """(instance, [reasons it fails]) for one candidate."""
    first, inst = start_instance(rng, spec)
    if spec.get("kind") != "zones":
        count = len(oracle.valid_starts(inst))
        lo, hi = spec.get("base", (15, 400))
        if not lo <= count <= hi:
            return inst, [f"the people's work hours leave {count} shared starts before any meeting; wanted {lo} to {hi}, so the overlap is not the intended kind"]
    avoid, keep = [], []
    window = [datetime.fromisoformat(inst["window"][k]) for k in ("start", "end")]
    dur = timedelta(minutes=spec["dur"])
    if spec.get("keep") == "last":
        keep = [window[1] - dur]
    elif spec.get("keep") == "adjacent":
        keep = [bc.local(first + timedelta(days=1), "14:00", window[0].tzinfo)]
    avoid = [(k, k + dur) for k in keep]
    populate(rng, spec, first, inst, avoid)
    if spec.get("keep") == "adjacent":
        adjacent_blocks(rng, inst, keep[0])
    if keep and keep[0] not in [s for s, _ in oracle.valid_starts(inst)]:
        return inst, ["the slot the task is built around is not valid, so the construction failed"]
    if spec.get("kind"):
        if spec["kind"] in ("last-slot", "rooms", "offday", "clash") and not oracle.valid_starts(inst):
            return inst, ["no valid start for the blocker to remove, so the request is already infeasible"]
        finish_infeasible(rng, spec, inst, first)
        left = len(oracle.valid_starts(inst))
        return inst, [] if left == 0 else [f"the blocker left {left} valid starts, so the request is not infeasible"]
    cap = max(1, int(MAX_FRACTION * bc.grid_size(inst)))
    cap = min(cap, spec.get("cap", cap))
    found = oracle.valid_starts(inst)
    if not found:
        return inst, ["the calendars and limits leave no valid start, so the request would be infeasible by accident"]
    starts = bc.squeeze(rng, oracle, inst, cap, keep=keep)
    if not 1 <= len(starts) <= cap:
        return inst, [f"too guessable: {len(starts)} valid starts remain after adding meetings, above the cap of {cap} (1.5% of the grid)"]
    return inst, []


def exercise(inst):
    return {name: defects.exercised(oracle, inst, name, range(3)) for name in defects.DEFECTS}


MANUAL = [
    ("anchor tasks: one participant, empty calendar", "rejected", "A random well-formed slot is valid on most of them, so the guessing floor would earn credit; no anchors are admitted"),
    ("Natural Plan records committed as tasks", "rejected", "The data is fetched, not vendored: generate.py --instances DIR converts fetched records. Records use one shared offset and day-specific preferences, so they cannot cover offsets, rooms or optional attendees"),
    ("credit for a well-formed answer", "rejected", "Any parseable slot would earn credit, so floors that write a slot would score on every task; credit is gated on correctness"),
    ("named IANA time zones in requests", "rejected", "The interface fixes offsets; daylight-saving changes would need tzdata and are listed as a coverage gap in research/catalog.md"),
    ("per-task answer keys in tests/", "rejected", "A key can be copied or drift from the instance; the verifier recomputes every valid start from environment/input.json"),
]


def run(write=True, limit=120):
    out = HERE.parent / "offline-instances"
    out.mkdir(exist_ok=True)
    log, chosen = [], {}
    for spec in SLOTS:
        for n in range(limit):
            rng = random.Random(f"{spec['id']}:{n}")
            inst, problems = make(rng, spec)
            row = {"candidate": f"{spec['id']}#{n}", "family": spec["family"], "source_group": spec["group"]}
            if not problems:
                seen = exercise(inst)
                problems = [f"the {d} defect is not exercised (wrong on {seen[d]:.0%} of draws), so the task would not detect it" for d in spec.get("must", ()) if seen[d] < EXERCISED]
            if problems:
                log.append({**row, "disposition": "rejected", "reason": "; ".join(problems)})
                continue
            found = oracle.valid_starts(inst)
            log.append({**row, "disposition": "admitted",
                        "reason": f"{len(found)} valid starts of {bc.grid_size(inst)}" if found else "no valid start, as designed"})
            chosen[spec["id"]] = (spec, inst, n)
            break
        else:
            print("no candidate for", spec["id"], file=sys.stderr)
    if write:
        for old in out.glob("*.json"):
            old.unlink()
        for slot_id, (spec, inst, n) in chosen.items():
            doc = {"id": slot_id, "family": spec["family"], "source_group": spec["group"], "title": spec["title"],
                   "difficulty": spec["why"], "expert_minutes": spec["minutes"], "smoke": spec.get("smoke", False),
                   "quick": spec.get("quick", False), "instance": inst}
            (out / f"{slot_id}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        log += [{"candidate": c, "family": "-", "source_group": "-", "disposition": d, "reason": r} for c, d, r in MANUAL]
        (HERE / "rejections.jsonl").write_text("".join(json.dumps(r) + "\n" for r in log), encoding="utf-8")
    return chosen, log


if __name__ == "__main__":
    chosen, log = run()
    print(len(chosen), "instances;", sum(r["disposition"] == "rejected" for r in log), "rejected candidates")
