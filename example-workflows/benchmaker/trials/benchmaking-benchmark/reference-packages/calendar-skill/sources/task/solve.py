"""Reference solution: books the meeting in request.json into the calendar files under policy.json.

It turns the workspace into a list of candidate starts, keeps those that satisfy every rule, picks the earliest, the
latest or (for `any`) the first, adds one entry to each attendee's calendar and to the room's file, and writes
result.json. When no start qualifies it changes no file and writes an infeasibility answer whose explanation is
computed from where the candidate starts were lost.
"""
import argparse
import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def zone(text):
    sign = -1 if text[0] == "-" else 1
    return timezone(sign * timedelta(hours=int(text[1:3]), minutes=int(text[4:6])))


def clock(text):
    hours, minutes = text.split(":")
    return timedelta(hours=int(hours), minutes=int(minutes))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load(workspace):
    """The workspace as {request, policy, calendars: {id: doc}, rooms: {id: doc}}."""
    root = Path(workspace)
    return {"request": read_json(root / "request.json"), "policy": read_json(root / "policy.json"),
            "calendars": {p.stem: read_json(p) for p in sorted((root / "calendars").glob("*.json"))},
            "rooms": {p.stem: read_json(p) for p in sorted((root / "rooms").glob("*.json"))}}


def instance_of(docs):
    """The scheduling request the workspace implies: entries are busy time and the policy becomes constraints."""
    request, rules = docs["request"], docs["policy"].get("rules", [])
    focus = next((r for r in rules if r["type"] == "focus_blocks"), {})
    skip_focus = request.get("priority") == "urgent" and focus.get("urgent_may_override", False)
    attendees = request["attendees"]
    people = []
    for pid in attendees + request.get("optional", []):
        doc = docs["calendars"][pid]
        people.append({"id": pid, "utc_offset": doc["utc_offset"], "work_hours": doc["work_hours"], "required": pid in attendees,
                       "busy": [{"start": e["start"], "end": e["end"]} for e in doc["events"] if not (skip_focus and e.get("kind") == "focus")]})
    constraints = []
    for rule in rules:
        if rule["type"] == "buffer_minutes":
            constraints += [{"type": "buffer_minutes", "participant": pid, "minutes": rule["minutes"]} for pid in attendees]
        elif rule["type"] == "room_feature" and len(attendees) >= rule.get("min_attendees", 1):
            constraints.append({"type": "room_feature", "feature": rule["feature"]})
    return {"duration_minutes": request["duration_minutes"], "granularity_minutes": request.get("granularity_minutes", 15),
            "window": request["window"], "participants": people, "constraints": constraints, "preference": request["preference"],
            "rooms": [{"id": rid, "capacity": doc["capacity"], "features": doc.get("features", []),
                       "busy": [{"start": e["start"], "end": e["end"]} for e in doc["events"]]} for rid, doc in docs["rooms"].items()]}


def intervals(items):
    return [(datetime.fromisoformat(i["start"]), datetime.fromisoformat(i["end"])) for i in items or []]


def working_time(person, lo, hi):
    tz, spans = person["zone"], []
    day = lo.astimezone(tz).date() - timedelta(days=1)
    while day <= hi.astimezone(tz).date() + timedelta(days=1):
        midnight = datetime.combine(day, time(), tzinfo=tz)
        for entry in person["work_hours"]:
            if DAYS[day.weekday()] in entry["days"]:
                spans.append((midnight + clock(entry["start"]), midnight + clock(entry["end"])))
        day += timedelta(days=1)
    merged = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def read(instance):
    window = instance["window"]
    lo, hi = datetime.fromisoformat(window["start"]), datetime.fromisoformat(window["end"])
    people = {}
    for p in instance["participants"]:
        people[p["id"]] = {"id": p["id"], "zone": zone(p["utc_offset"]), "required": p["required"], "work_hours": p["work_hours"],
                           "busy": intervals(p["busy"]), "rules": []}
    features = []
    for c in instance["constraints"]:
        if c["type"] == "room_feature":
            features.append(c["feature"])
        else:
            people[c["participant"]]["rules"].append(c)
    for p in people.values():
        p["work"] = working_time(p, lo, hi)
    rooms = [{"id": r["id"], "capacity": r["capacity"], "features": set(r["features"]), "busy": intervals(r["busy"])} for r in instance["rooms"]]
    return {"lo": lo, "hi": hi, "duration": timedelta(minutes=instance["duration_minutes"]),
            "step": timedelta(minutes=instance["granularity_minutes"]), "preference": instance["preference"],
            "people": [p for p in people.values() if p["required"]], "rooms": rooms, "features": features}


def blocked(p, start, end):
    """The first rule of this attendee that the slot [start, end) breaks, or None."""
    if not any(a <= start and end <= b for a, b in p["work"]):
        return "work hours"
    if any(a < end and start < b for a, b in p["busy"]):
        return "busy time"
    for c in p["rules"]:
        gap = timedelta(minutes=c["minutes"])
        if any(a < end + gap and start - gap < b for a, b in p["busy"]):
            return "buffer"
    return None


def room_ids(m, start, end):
    return [r["id"] for r in m["rooms"] if r["capacity"] >= len(m["people"]) and set(m["features"]) <= r["features"]
            and not any(a < end and start < b for a, b in r["busy"])]


def valid_starts(instance):
    """[(start, [eligible room ids])] for every valid start, earliest first."""
    m = read(instance)
    found, start = [], m["lo"]
    while start + m["duration"] <= m["hi"]:
        end = start + m["duration"]
        rooms = room_ids(m, start, end)
        if not any(blocked(p, start, end) for p in m["people"]) and (rooms or not m["rooms"]):
            found.append((start, rooms))
        start += m["step"]
    return found


def explain(instance):
    m = read(instance)
    starts, start = [], m["lo"]
    while start + m["duration"] <= m["hi"]:
        starts.append(start)
        start += m["step"]
    lost = {p["id"]: sum(blocked(p, s, s + m["duration"]) is not None for s in starts) for p in m["people"]}
    text = ", ".join(f"{who} {count}" for who, count in sorted(lost.items(), key=lambda kv: -kv[1]))
    reason = f"None of the {len(starts)} candidate starts in the window works for every attendee under the policy. Starts each attendee rules out: {text}."
    if m["rooms"]:
        reason += f" No suitable room is free at {sum(not room_ids(m, s, s + m['duration']) for s in starts)} of them."
    return reason


def new_id(docs):
    taken = {e["id"] for group in ("calendars", "rooms") for doc in docs[group].values() for e in doc["events"]}
    return next(f"bk-{n}" for n in range(1, len(taken) + 2) if f"bk-{n}" not in taken)


def plan(docs):
    """(start, room) of the booking, or None when the request is infeasible."""
    instance, request = instance_of(docs), docs["request"]
    found = valid_starts(instance)
    if not found:
        return None
    start, rooms = {"latest": found[-1:]}.get(request["preference"], found[:1])[0]
    return start, (rooms[0] if rooms else None)


def book(docs):
    """(new docs, result.json content) after the booking, or the unchanged docs and an infeasibility answer."""
    request, chosen = docs["request"], plan(docs)
    if chosen is None:
        return docs, {"infeasible": True, "explanation": explain(instance_of(docs))}
    start, room = chosen
    end = start + timedelta(minutes=request["duration_minutes"])
    ident, tz = new_id(docs), datetime.fromisoformat(request["window"]["start"]).tzinfo
    entry = lambda moment: moment.astimezone(tz).isoformat(timespec="minutes")  # noqa: E731
    owners = [docs["calendars"][p] for p in request["attendees"]] + ([docs["rooms"][room]] if room else [])
    for doc in owners:
        own = zone(doc["utc_offset"]) if "utc_offset" in doc else tz
        doc["events"].append({"id": ident, "title": request.get("title", "Meeting"), "kind": "meeting",
                              "start": start.astimezone(own).isoformat(timespec="minutes"), "end": end.astimezone(own).isoformat(timespec="minutes")})
    booked = {"start": entry(start), "end": entry(end), "event_id": ident}
    if room:
        booked["room"] = room
    return docs, {"booked": booked}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", required=True)
    root = Path(parser.parse_args().workspace)
    docs, result = book(load(root))
    for group in ("calendars", "rooms") if "booked" in result else ():
        for name, doc in docs[group].items():
            (root / group / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
