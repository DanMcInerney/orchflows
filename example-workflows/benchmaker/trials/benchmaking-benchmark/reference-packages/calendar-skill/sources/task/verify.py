"""Verifier: grades the final calendar files and result.json against the task's original workspace (environment/).

Credit has three dimensions. `valid` (0.6): the files hold a correct outcome and nothing else changed: for a feasible
request one new entry per attendee and in the booked room, all at one valid slot, or for an infeasible request the
answer in result.json says so and no file gained an entry; any damage to an existing entry or file also loses it.
`optimal` (0.2): earned only by a valid outcome that is the best start for the preference, or for an infeasible request
carries a non-empty explanation. `reported` (0.2): a valid outcome whose result.json is accurate about the files (its
booking is the one they hold, or its infeasibility claim is true). All three dimensions are earned only by a valid
outcome, so no answer is credited for form alone. Full success needs all three. Damage to an existing entry or file and a
reported booking that no file holds are critical failures. Times are compared as instants.
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

WEIGHTS = {"valid": 0.6, "optimal": 0.2, "reported": 0.2}
DAY = 1440
STAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def offset(text):
    sign = -1 if text.startswith("-") else 1
    return 0 if text == "Z" else sign * (int(text[1:3]) * 60 + int(text[4:6]))


def instant(text):
    """Minutes since 0001-01-01T00:00Z for a timestamp with an explicit offset, on a whole minute."""
    match = STAMP.match(text.strip()) if isinstance(text, str) else None
    if not match:
        raise ValueError(f"not a timestamp with an offset: {text!r}")
    y, mo, d, h, mi, sec, frac, zone = match.groups()
    if int(sec or 0) or (frac and int(frac[1:])):
        raise ValueError(f"not a whole minute: {text!r}")
    return date(int(y), int(mo), int(d)).toordinal() * DAY + int(h) * 60 + int(mi) - offset(zone)


def clock(text):
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


class Original:
    """The task's own workspace, and the valid starts it implies."""

    def __init__(self, root):
        root = Path(root)
        self.request, self.policy = read_json(root / "request.json"), read_json(root / "policy.json")
        self.docs = {f"{folder}/{p.name}": read_json(p) for folder in ("calendars", "rooms") for p in sorted((root / folder).glob("*.json"))}
        r = self.request
        self.attendees, self.optional = list(r["attendees"]), list(r.get("optional", []))
        self.duration, self.step = r["duration_minutes"], r.get("granularity_minutes", 15)
        self.lo, self.hi = instant(r["window"]["start"]), instant(r["window"]["end"])
        rules = self.policy.get("rules", [])
        focus = next((x for x in rules if x["type"] == "focus_blocks"), {})
        skip_focus = r.get("priority") == "urgent" and focus.get("urgent_may_override", False)
        self.buffer = next((x["minutes"] for x in rules if x["type"] == "buffer_minutes"), None)
        self.features = [x["feature"] for x in rules if x["type"] == "room_feature" and len(self.attendees) >= x.get("min_attendees", 1)]
        self.people = {pid: self.person(self.docs[f"calendars/{pid}.json"], skip_focus) for pid in self.attendees}
        self.rooms = {Path(path).stem: {"capacity": doc["capacity"], "features": set(doc.get("features", [])),
                                        "busy": [(instant(e["start"]), instant(e["end"])) for e in doc["events"]]}
                      for path, doc in self.docs.items() if path.startswith("rooms/")}
        self.preference = r["preference"]

    def person(self, doc, skip_focus):
        off = offset(doc["utc_offset"])
        spans = sorted((n * DAY - off + clock(w["start"]), n * DAY - off + clock(w["end"]))
                       for n in range(self.lo // DAY - 2, self.hi // DAY + 3) for w in doc["work_hours"]
                       if WEEKDAYS[(n - 1) % 7] in [d.lower() for d in w["days"]])
        work = []
        for a, b in spans:
            if work and a <= work[-1][1]:
                work[-1][1] = max(work[-1][1], b)
            else:
                work.append([a, b])
        busy = [(instant(e["start"]), instant(e["end"])) for e in doc["events"] if not (skip_focus and e.get("kind") == "focus")]
        return {"work": work, "busy": busy}

    def person_ok(self, p, s, e):
        gap = self.buffer or 0
        return (any(a <= s and e <= b for a, b in p["work"]) and not any(a < e and s < b for a, b in p["busy"])
                and not (self.buffer is not None and any(a < e + gap and s - gap < b for a, b in p["busy"])))

    def rooms_at(self, s, e):
        return [rid for rid, r in self.rooms.items() if r["capacity"] >= len(self.attendees) and set(self.features) <= r["features"]
                and not any(a < e and s < b for a, b in r["busy"])]

    def valid(self):
        """{start: [room ids]} for every valid start."""
        found = {}
        for s in range(self.lo, self.hi - self.duration + 1, self.step):
            e = s + self.duration
            rooms = self.rooms_at(s, e)
            if all(self.person_ok(p, s, e) for p in self.people.values()) and (rooms or not self.rooms):
                found[s] = rooms
        return found


def same_entry(before, after):
    """An existing entry is unchanged when each of its fields is, times compared as instants; extra fields are tolerated."""
    for key, value in before.items():
        if key in ("start", "end"):
            try:
                if instant(after.get(key)) != instant(value):
                    return False
            except ValueError:
                return False
        elif after.get(key) != value:
            return False
    return True


def read_final(orig, workspace):
    """({path: (new entries, final doc)}, critical failures, other reasons) after comparing with the original files."""
    final, critical, reasons = {}, [], []
    for path, before in orig.docs.items():
        try:
            doc = read_json(Path(workspace) / path)
        except (OSError, ValueError):
            critical.append(f"{path} was deleted or is no longer valid JSON")
            continue
        if not (isinstance(doc, dict) and isinstance(doc.get("events"), list) and all(isinstance(e, dict) and isinstance(e.get("id"), str) for e in doc["events"])):
            critical.append(f"{path} is no longer a calendar file")
            continue
        critical += [f"{path}: {key!r} was changed" for key, value in before.items() if key != "events" and doc.get(key) != value]
        left = list(doc["events"])
        for event in before["events"]:
            match = next((e for e in left if e["id"] == event["id"] and same_entry(event, e)), None)
            if match is None:
                critical.append(f"{path}: entry {event['id']} was removed or changed")
            else:
                left.remove(match)
        final[path] = left
    for folder in ("calendars", "rooms"):
        for p in sorted((Path(workspace) / folder).glob("*.json")) if (Path(workspace) / folder).is_dir() else []:
            if f"{folder}/{p.name}" not in orig.docs:
                reasons.append(f"{folder}/{p.name} is a new file")
    return final, critical, reasons


def booking(orig, new):
    """(facts of the single booking the files hold, reasons it is not one): structure only, not whether the slot is valid."""
    reasons, found = [], {}
    wanted = {f"calendars/{pid}.json" for pid in orig.attendees}
    invited = {f"calendars/{pid}.json" for pid in orig.optional}
    for path, entries in new.items():
        if path in wanted and len(entries) != 1:
            reasons.append(f"{path} gained {len(entries)} entries, expected exactly one")
        elif path in invited and len(entries) > 1:
            reasons.append(f"{path} gained {len(entries)} entries")
        elif path.startswith("calendars/") and path not in wanted | invited and entries:
            reasons.append(f"{path} gained an entry although that person is not part of the booking")
        if entries and (path in wanted | invited or path.startswith("rooms/")):
            found[path] = entries[0]
    held = [p for p in new if p.startswith("rooms/") and new[p]]
    if orig.rooms and len(held) != 1:
        reasons.append(f"{len(held)} room files gained an entry, expected exactly one")
    if any(len(new[p]) != 1 for p in held):
        reasons.append("a room file gained more than one entry")
    if reasons or not found:
        return None, reasons or ["no file gained an entry"]
    try:
        spans = {(e["id"], instant(e.get("start")), instant(e.get("end"))) for e in found.values()}
    except ValueError as error:
        return None, [str(error)]
    if len(spans) != 1:
        return None, ["the new entries disagree on id or time"]
    ident, s, e = next(iter(spans))
    for path in found:
        if any(x["id"] == ident for x in orig.docs[path]["events"]):
            return None, [f"{path}: the new entry reuses an existing id"]
    return {"id": ident, "start": s, "end": e, "room": Path(held[0]).stem if held else None}, []


def reported_ok(orig, res, facts, truly_infeasible, gained):
    """Whether result.json is accurate: its booking is the one the files hold, or its infeasibility claim is true."""
    if res is None:
        return False
    if res.get("infeasible") is True:
        return truly_infeasible and not gained
    claim = res.get("booked")
    if not isinstance(claim, dict) or facts is None:
        return False
    try:
        same = instant(claim.get("start")) == facts["start"] and instant(claim.get("end")) == facts["end"]
    except ValueError:
        return False
    return same and claim.get("event_id") == facts["id"] and (not orig.rooms or claim.get("room") == facts["room"])


def grade(orig, workspace):
    """(valid, optimal, reported, critical failures, reason)."""
    found = orig.valid()
    new, critical, problems = read_final(orig, workspace)
    gained = any(new.values())
    try:
        res = read_json(Path(workspace) / "result.json")
    except (OSError, ValueError):
        res = None
    res = res if isinstance(res, dict) else None
    if res and isinstance(res.get("booked"), dict) and res.get("infeasible") is not True and not gained:
        critical.append("result.json reports a booking that no file holds")
    facts, why = booking(orig, new)
    if found:
        problems += why
        slot_ok = (bool(facts) and facts["end"] - facts["start"] == orig.duration and facts["start"] in found
                   and (not orig.rooms or facts["room"] in found[facts["start"]]))
        if facts and not slot_ok:
            problems.append("the booked slot breaks a rule, is off the grid or is outside the window, or the room is unsuitable")
        valid = slot_ok and not critical and not problems
        best = {"earliest": min(found), "latest": max(found)}.get(orig.preference)
        optimal = valid and (best is None or facts["start"] == best)
        if valid and not optimal:
            problems.append("valid, but not the best start for the preference")
    else:
        if gained:
            problems.append("entries were added although the request is infeasible")
        if not (res and res.get("infeasible") is True):
            problems.append("result.json does not declare the infeasible request infeasible")
        valid = not critical and not problems
        optimal = valid and isinstance(res.get("explanation"), str) and bool(res["explanation"].strip())
        if valid and not optimal:
            problems.append("an infeasibility answer needs a non-empty explanation")
    reported = bool(valid) and reported_ok(orig, res, facts, not found, gained)
    if res is None and not problems:
        problems.append("result.json is missing or not a JSON object")
    return int(valid), int(optimal), int(reported), critical, "; ".join(critical + problems)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--task", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    orig = Original(Path(args.task) / "environment")
    valid, optimal, reported, critical, reason = grade(orig, args.workspace)
    credit = {"valid": float(valid), "optimal": float(optimal), "reported": float(reported)}
    result = {"grading_status": "scored", "full_success": bool(valid and optimal and reported and not critical),
              "credit": sum(WEIGHTS[k] * v for k, v in credit.items()),
              "dimensions": {k: {"credit": credit[k], "weight": WEIGHTS[k], "required": True} for k in WEIGHTS},
              "critical_failures": critical, "reason": reason}
    Path(args.result).write_text(json.dumps(result), encoding="utf-8")


if __name__ == "__main__":
    main()
