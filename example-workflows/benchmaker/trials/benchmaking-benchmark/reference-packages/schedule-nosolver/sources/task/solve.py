"""Reference solution: computes the booking from input.json and writes it to output.json.

It enumerates every start on the request's grid, keeps those that satisfy every rule, and writes the earliest,
the latest or (for `any`) the first of them, with a room when rooms exist. When no start qualifies it writes an
infeasibility answer whose explanation is computed from where the candidate starts were lost.
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


def intervals(items):
    return [(datetime.fromisoformat(i["start"]), datetime.fromisoformat(i["end"])) for i in items or []]


def working_time(person, lo, hi):
    """The person's merged working intervals (aware datetimes) that can touch [lo, hi]."""
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
        people[p["id"]] = {"id": p["id"], "zone": zone(p["utc_offset"]), "required": p.get("required", True),
                           "work_hours": p["work_hours"], "busy": intervals(p.get("busy")), "rules": []}
    features = []
    for c in instance.get("constraints", []):
        if c["type"] == "room_feature":
            features.append(c["feature"])
        else:
            people[c["participant"]]["rules"].append(c)
    for p in people.values():
        p["work"] = working_time(p, lo, hi)
    rooms = [{"id": r["id"], "capacity": r["capacity"], "features": set(r.get("features", [])), "busy": intervals(r.get("busy"))}
             for r in instance.get("rooms", [])]
    return {"lo": lo, "hi": hi, "duration": timedelta(minutes=instance["duration_minutes"]),
            "step": timedelta(minutes=instance.get("granularity_minutes", 15)), "preference": instance["preference"],
            "people": [p for p in people.values() if p["required"]], "rooms": rooms, "features": features}


def blocked(p, start, end):
    """The first rule of this required participant that the slot [start, end) breaks, or None."""
    if not any(a <= start and end <= b for a, b in p["work"]):
        return "work hours"
    if any(a < end and start < b for a, b in p["busy"]):
        return "busy time"
    midnight = datetime.combine(start.astimezone(p["zone"]).date(), time(), tzinfo=p["zone"])
    for c in p["rules"]:
        if c["type"] in ("not_before", "not_after") and "day" in c and c["day"] != midnight.date().isoformat():
            continue
        if c["type"] == "not_before" and start < midnight + clock(c["time"]):
            return "not_before"
        if c["type"] == "not_after" and end > midnight + clock(c["time"]):
            return "not_after"
        if c["type"] == "avoid_day":
            first = datetime.combine(datetime.fromisoformat(c["day"]).date(), time(), tzinfo=p["zone"])
            if start < first + timedelta(days=1) and first < end:
                return "avoid_day"
        if c["type"] == "buffer_minutes":
            gap = timedelta(minutes=c["minutes"])
            if any(a < end + gap and start - gap < b for a, b in p["busy"]):
                return "buffer_minutes"
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
    """Why no start works: how many candidate starts each requirement removes on its own."""
    m = read(instance)
    starts, lost, start = [], {}, m["lo"]
    while start + m["duration"] <= m["hi"]:
        starts.append(start)
        start += m["step"]
    for p in m["people"]:
        lost[p["id"]] = sum(blocked(p, s, s + m["duration"]) is not None for s in starts)
    text = ", ".join(f"{who} {count}" for who, count in sorted(lost.items(), key=lambda kv: -kv[1]))
    reason = f"None of the {len(starts)} candidate starts in the window works for every required participant. Starts each rules out: {text}."
    if m["rooms"]:
        short = sum(not room_ids(m, s, s + m["duration"]) for s in starts)
        reason += f" No suitable room is free at {short} of them."
    return reason


def solve(instance):
    """The output.json content, as a dict."""
    found = valid_starts(instance)
    if not found:
        return {"infeasible": True, "explanation": explain(instance)}
    start, rooms = {"latest": found[-1:], "earliest": found[:1]}.get(instance["preference"], found[:1])[0]
    tz = datetime.fromisoformat(instance["window"]["start"]).tzinfo
    end = start + timedelta(minutes=instance["duration_minutes"])
    out = {"start": start.astimezone(tz).isoformat(timespec="minutes"), "end": end.astimezone(tz).isoformat(timespec="minutes")}
    if instance.get("rooms"):
        out["room"] = rooms[0]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", required=True)
    workspace = Path(parser.parse_args().workspace)
    instance = json.loads((workspace / "input.json").read_text(encoding="utf-8"))
    (workspace / "output.json").write_text(json.dumps(solve(instance), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
