#!/usr/bin/env python3
"""List the times a meeting can start in a booking workspace.

Reads request.json, policy.json, calendars/ and rooms/ from the workspace and prints, earliest first, every start on
the request's grid at which all required attendees are inside their work hours and free of every entry, focus blocks
included, with the policy's buffer_minutes kept clear, and for which a room that seats everyone is free.

Not checked: room features, and the policy's exception that lets an urgent request book over focus blocks.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
DAY = 1440
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
NOTE = "Room features and the urgent-request exception for focus blocks are not checked."


def stamp(text):
    """(minutes since the epoch, UTC offset in minutes) of an ISO 8601 timestamp that carries an offset."""
    moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError(f"timestamp has no UTC offset: {text}")
    return (moment - EPOCH) // timedelta(minutes=1), moment.utcoffset() // timedelta(minutes=1)


def minute(text):
    return stamp(text)[0]


def offset(text):
    minutes = int(text[1:3]) * 60 + int(text[4:6])
    return -minutes if text[0] == "-" else minutes


def clock(text):
    return int(text[:2]) * 60 + int(text[3:5])


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def working(hours, zone, first, last):
    """The person's working time as merged (start, end) minutes covering the window."""
    spans = []
    for day in range((first + zone) // DAY - 1, (last + zone) // DAY + 2):
        for entry in hours:
            if WEEKDAYS[(day + 3) % 7] in [str(d).lower()[:3] for d in entry["days"]]:
                spans.append((day * DAY - zone + clock(entry["start"]), day * DAY - zone + clock(entry["end"])))
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def entries(owner):
    return [(minute(e["start"]), minute(e["end"])) for e in owner["events"]]


def clearance(busy, buffer):
    """Each busy interval widened by the buffer on both sides: the time a new meeting must stay out of."""
    return [(start - buffer, end + buffer) for start, end in busy]


def overlaps(spans, start, end):
    return any(a < end and start < b for a, b in spans)


def compute(workspace):
    root = Path(workspace)
    request, policy = read(root / "request.json"), read(root / "policy.json")
    attendees = request["attendees"]
    length, step = int(request["duration_minutes"]), int(request.get("granularity_minutes", 15))
    (first, zone), last = stamp(request["window"]["start"]), minute(request["window"]["end"])
    buffer = next((int(r["minutes"]) for r in policy.get("rules", []) if r.get("type") == "buffer_minutes"), 0)
    people = {}
    for name in attendees:
        calendar = read(root / "calendars" / f"{name}.json")
        people[name] = (working(calendar["work_hours"], offset(calendar["utc_offset"]), first, last),
                        clearance(entries(calendar), buffer))
    rooms = {path.stem: read(path) for path in sorted((root / "rooms").glob("*.json"))}
    seats = [name for name, room in rooms.items() if room["capacity"] >= len(attendees)]
    taken = {name: entries(rooms[name]) for name in seats}

    def text(value):
        return (EPOCH + timedelta(minutes=value)).astimezone(timezone(timedelta(minutes=zone))).isoformat(timespec="minutes")

    slots = []
    for start in range(first, last - length + 1, step):
        end = start + length
        if all(any(a <= start and end <= b for a, b in hours) and not overlaps(busy, start, end)
               for hours, busy in people.values()):
            free = [name for name in seats if not overlaps(taken[name], start, end)]
            if not rooms or free:
                slots.append({"start": text(start), "end": text(end), **({"rooms": free} if rooms else {})})
    return {"attendees": attendees, "duration_minutes": length, "granularity_minutes": step, "buffer_minutes": buffer,
            "total": len(slots), "slots": slots, "note": NOTE}


def main(argv=None):
    parser = argparse.ArgumentParser(description="List the times a meeting can start in a booking workspace.")
    parser.add_argument("--workspace", default=".", help="the booking workspace (default: the current directory)")
    parser.add_argument("--limit", type=int, default=10, help="how many slots to list; 0 lists all (default: 10)")
    parser.add_argument("--latest", action="store_true", help="list the latest slots first")
    args = parser.parse_args(argv)
    try:
        result = compute(args.workspace)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"free_slots: cannot read the workspace: {error!r}", file=sys.stderr)
        return 2
    slots = result["slots"][::-1] if args.latest else result["slots"]
    result["slots"] = slots[:args.limit] if args.limit else slots
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
