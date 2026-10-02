"""Building blocks for synthetic calendar workspaces: calendars with focus blocks, rooms, policies and squeezing.

Casts, work-hour templates and the meeting generator come from the schedule-nosolver package's sources
(build_calendars.py); this module turns them into calendar and room files and narrows the valid starts under the
team's policy, so a guess at a slot almost never works. `synthesize.py` composes it into the committed instances.
"""
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

SCHEDULE = Path(__file__).resolve().parents[2] / "schedule-nosolver" / "sources"
_spec = importlib.util.spec_from_file_location("schedule_build_calendars", SCHEDULE / "build_calendars.py")
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)

TITLES = ["Sprint planning", "Design crit", "Customer call", "1:1", "Roadmap review", "Pipeline sync", "Vendor call", "Interview",
          "Team sync", "Budget check-in", "Incident review", "Training", "Handover", "Retro", "Dentist"]
FOCUS = ["Focus: design", "Focus: writing", "Focus: code review", "Focus: planning", "Focus: reports"]


def event_docs(rng, pid, busy):
    """Calendar entries for the generated busy intervals: stand-ups, lunches and meetings with ids and titles."""
    events = []
    for n, b in enumerate(sorted(busy, key=lambda x: datetime.fromisoformat(x["start"])), 1):
        a, z = datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"])
        length = int((z - a).total_seconds() // 60)
        title = "Stand-up" if length == 15 else "Lunch" if length == 60 and (a.hour, a.minute) in ((12, 0), (12, 30)) else rng.choice(TITLES)
        events.append({"id": f"{pid}-{n:03d}", "title": title, "kind": "meeting", **b})
    return events


def add_focus(rng, doc, pid, first, days, count):
    """Focus blocks of two to three hours inside working time, as entries of kind focus."""
    tz = bc.zone(doc["utc_offset"])
    for _ in range(rng.randint(*count)):
        day = first + timedelta(days=rng.randrange(days))
        spans = bc.working_days(doc, day)
        if not spans:
            continue
        w = rng.choice(spans)
        begin = bc.local(day, w["start"], tz) + timedelta(minutes=15 * rng.randrange(0, 14))
        end = begin + timedelta(minutes=rng.choice([120, 150, 180]))
        if end <= bc.local(day, w["end"], tz):
            n = len(doc["events"]) + 1
            doc["events"].append({"id": f"{pid}-{n:03d}", "title": rng.choice(FOCUS), "kind": "focus", "start": bc.stamp(begin), "end": bc.stamp(end)})


def calendars(rng, spec, first):
    docs = {}
    for pid in spec["ids"] + spec.get("optional", []) + spec.get("others", []):
        template = rng.choice(spec["pool"][pid]) if pid in spec.get("pool", {}) else None
        p = bc.person(pid, template)
        bc.fill_calendar(rng, p, first, spec["days"], spec.get("per_day", (2, 4)), spec.get("habits", ("lunch", "standup")),
                         utc=pid in spec.get("export_utc", ()), avoid=spec.get("avoid", ()))
        doc = {"utc_offset": p["utc_offset"], "work_hours": p["work_hours"], "events": event_docs(rng, pid, p["busy"])}
        add_focus(rng, doc, pid, first, spec["days"], spec.get("focus", (1, 3)))
        docs[pid] = doc
    return docs


def rooms(rng, spec, first, window_zone):
    docs = {}
    for rid, capacity, features in spec.get("rooms", ()):
        doc = {"capacity": capacity, "features": list(features), "events": []}
        for n in range(spec["days"]):
            for _ in range(rng.randint(*spec.get("room_per_day", (1, 3)))):
                begin = bc.local(first + timedelta(days=n), "00:00", window_zone) + timedelta(minutes=60 * rng.randint(8, 16) + 15 * rng.randint(0, 3))
                end = begin + timedelta(minutes=rng.choice([30, 60, 90, 120]))
                doc["events"].append({"id": f"{rid}-{len(doc['events']) + 1:03d}", "title": rng.choice(TITLES[:9]), "kind": "meeting",
                                      "start": bc.stamp(begin), "end": bc.stamp(end)})
        docs[rid] = doc
    return docs


def rules_of(spec):
    out = []
    for kind, *args in spec.get("policy", ()):
        if kind == "buffer":
            out.append({"type": "buffer_minutes", "minutes": args[0]})
        elif kind == "focus":
            out.append({"type": "focus_blocks", "urgent_may_override": args[0]})
        else:
            out.append({"type": "room_feature", "min_attendees": args[1], "feature": args[0]})
    return {"rules": out}


def workspace(rng, spec, first, tz, request):
    return {"request": request, "policy": rules_of(spec), "calendars": calendars(rng, spec, first), "rooms": rooms(rng, spec, first, tz)}


def squeeze(rng, solve, docs, ceiling, keep=(), tries=400):
    """Add meetings to attendees' calendars until at most `ceiling` valid starts remain; starts in `keep` stay valid.

    Returns the valid starts. A block that would remove every valid start, or a kept one, is undone."""
    instance = solve.instance_of(docs)
    model = solve.read(instance)
    starts = [s for s, _ in solve.valid_starts(instance)]
    by_id = {p["id"]: p for p in model["people"]}
    step = docs["request"].get("granularity_minutes", 15)
    for _ in range(tries):
        if len(starts) <= ceiling:
            break
        target = rng.choice([s for s in starts if s not in keep] or starts)
        owner = rng.choice(docs["request"]["attendees"])
        tz = bc.zone(docs["calendars"][owner]["utc_offset"])
        length = rng.choice([30, 45, 60, 90])
        begin = target.astimezone(tz) - timedelta(minutes=step * rng.randint(0, max(0, length // step - 1)))
        begin = begin.replace(minute=begin.minute - begin.minute % 15, second=0, microsecond=0)
        end = begin + timedelta(minutes=length)
        events = docs["calendars"][owner]["events"]
        events.append({"id": f"{owner}-{len(events) + 1:03d}", "title": rng.choice(TITLES), "kind": "meeting", "start": bc.stamp(begin), "end": bc.stamp(end)})
        by_id[owner]["busy"].append((begin, end))
        remaining = [s for s in starts if solve.blocked(by_id[owner], s, s + model["duration"]) is None]
        if not remaining or any(k not in remaining for k in keep):
            events.pop()
            by_id[owner]["busy"].pop()
            continue
        starts = remaining
    return starts


def block(docs, owner, begin, end, title="Busy"):
    events = docs["calendars"][owner]["events"]
    events.append({"id": f"{owner}-{len(events) + 1:03d}", "title": title, "kind": "meeting", "start": bc.stamp(begin), "end": bc.stamp(end)})


def grid_size(docs):
    r = docs["request"]
    lo, hi = datetime.fromisoformat(r["window"]["start"]), datetime.fromisoformat(r["window"]["end"])
    return int((hi - lo - timedelta(minutes=r["duration_minutes"])) / timedelta(minutes=r.get("granularity_minutes", 15))) + 1
