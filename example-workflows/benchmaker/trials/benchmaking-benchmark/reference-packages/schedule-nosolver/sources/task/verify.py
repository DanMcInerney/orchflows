"""Verifier: grades the solver's output.json against the task's own input.json, never the workspace copy.

Credit has two dimensions. `valid` (0.6): the answer is correct about feasibility and breaks no rule, so a slot
satisfies every rule and an infeasibility answer is made only when no valid slot exists. `optimal` (0.4): the slot
is the best one for the request's preference, or, for an infeasible request, the answer carries the explanation the
interface requires; `optimal` is earned only by a valid answer. Times are compared as instants.
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

WEIGHTS = {"valid": 0.6, "optimal": 0.4}
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
    return (date(int(y), int(mo), int(d)).toordinal() * DAY + int(h) * 60 + int(mi)) - offset(zone), offset(zone)


def clock(text):
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def day_number(text):
    return date.fromisoformat(text).toordinal()


def spans(items):
    return [(instant(i["start"])[0], instant(i["end"])[0]) for i in items or []]


class Request:
    def __init__(self, doc):
        self.duration = doc["duration_minutes"]
        self.step = doc.get("granularity_minutes", 15)
        (self.lo, _), (self.hi, _) = instant(doc["window"]["start"]), instant(doc["window"]["end"])
        self.preference = doc["preference"]
        self.people = [self.person(p) for p in doc["participants"] if p.get("required", True)]
        by_id = {p["id"]: p for p in self.people}
        self.features = []
        for c in doc.get("constraints", []):
            if c["type"] == "room_feature":
                self.features.append(c["feature"])
            elif c["participant"] in by_id:
                by_id[c["participant"]]["rules"].append(c)
        self.rooms = [{"id": r["id"], "capacity": r["capacity"], "features": set(r.get("features", [])),
                       "busy": spans(r.get("busy"))} for r in doc.get("rooms", [])]

    def person(self, p):
        off = offset(p["utc_offset"])
        days = range(self.lo // DAY - 2, self.hi // DAY + 3)
        work = sorted((n * DAY - off + clock(w["start"]), n * DAY - off + clock(w["end"]))
                      for n in days for w in p["work_hours"] if WEEKDAYS[(n - 1) % 7] in [d.lower() for d in w["days"]])
        merged = []
        for a, b in work:
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        return {"id": p["id"], "off": off, "work": merged, "busy": spans(p.get("busy")), "rules": []}

    def person_problem(self, p, s, e):
        if not any(a <= s and e <= b for a, b in p["work"]):
            return f"{p['id']} is outside work hours"
        if any(a < e and s < b for a, b in p["busy"]):
            return f"{p['id']} is busy"
        local_day = (s + p["off"]) // DAY
        midnight = local_day * DAY - p["off"]
        for c in p["rules"]:
            kind = c["type"]
            if kind in ("not_before", "not_after") and "day" in c and day_number(c["day"]) != local_day:
                continue
            first = day_number(c["day"]) * DAY - p["off"] if kind == "avoid_day" else 0
            if ((kind == "not_before" and s < midnight + clock(c["time"]))
                    or (kind == "not_after" and e > midnight + clock(c["time"]))
                    or (kind == "avoid_day" and s < first + DAY and first < e)
                    or (kind == "buffer_minutes" and any(a < e + c["minutes"] and s - c["minutes"] < b for a, b in p["busy"]))):
                return f"{p['id']} breaks {kind}"
        return None

    def rooms_at(self, s, e):
        return [r["id"] for r in self.rooms if r["capacity"] >= len(self.people) and set(self.features) <= r["features"]
                and not any(a < e and s < b for a, b in r["busy"])]

    def valid(self):
        """{start: [room ids]} for every valid start."""
        found = {}
        for s in range(self.lo, self.hi - self.duration + 1, self.step):
            e = s + self.duration
            rooms = self.rooms_at(s, e)
            if not any(self.person_problem(p, s, e) for p in self.people) and (rooms or not self.rooms):
                found[s] = rooms
        return found


def grade(request, raw):
    """(valid, optimal, reason) for the bytes of output.json."""
    try:
        out = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, AttributeError):
        return 0, 0, "output.json is missing or not valid JSON"
    if not isinstance(out, dict):
        return 0, 0, "output.json is not a JSON object"
    valid = request.valid()
    if out.get("infeasible") is True:
        if valid:
            return 0, 0, "declared the request infeasible, but a valid slot exists"
        explained = isinstance(out.get("explanation"), str) and bool(out["explanation"].strip())
        return 1, int(explained), "" if explained else "an infeasibility answer needs a non-empty explanation"
    try:
        s, e = instant(out.get("start"))[0], instant(out.get("end"))[0]
    except ValueError as error:
        return 0, 0, str(error)
    if not valid:
        return 0, 0, "gave a slot, but the request is infeasible"
    if e - s != request.duration:
        return 0, 0, f"the slot lasts {e - s} minutes, not {request.duration}"
    if s not in valid:
        return 0, 0, "the slot breaks a rule, is off the grid or is outside the window"
    if request.rooms:
        room = out.get("room")
        if not isinstance(room, str) or room not in valid[s]:
            return 0, 0, "the room is missing, unknown or not suitable"
    best = {"earliest": min(valid), "latest": max(valid)}.get(request.preference)
    return 1, int(best is None or s == best), "" if best in (None, s) else "valid, but not the best start for the preference"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--task", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    request = Request(json.loads((Path(args.task) / "environment" / "input.json").read_text(encoding="utf-8")))
    try:
        raw = (Path(args.workspace) / "output.json").read_bytes()
    except OSError:
        raw = b""
    valid, optimal, reason = grade(request, raw)
    credit = {"valid": float(valid), "optimal": float(optimal)}
    result = {"grading_status": "scored", "full_success": bool(valid and optimal),
              "credit": sum(WEIGHTS[k] * v for k, v in credit.items()),
              "dimensions": {k: {"credit": credit[k], "weight": WEIGHTS[k], "required": True} for k in WEIGHTS},
              "critical_failures": [], "reason": reason}
    Path(args.result).write_text(json.dumps(result), encoding="utf-8")


if __name__ == "__main__":
    main()
