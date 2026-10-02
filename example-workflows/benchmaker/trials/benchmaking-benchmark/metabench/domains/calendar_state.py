"""State of the calendar-skill workspace: reading it, the scheduling instance it implies, the policy text.

A workspace holds request.json, policy.json, policy.md, calendars/<person>.json and, optionally,
rooms/<room>.json. `load` turns it into an instance {"request", "policy", "state", "schedule"}: `state` is the
parsed calendar and room files and `schedule` the scheduling-domain instance whose rules decide which bookings
are valid. The calendar's own rules (policy rule types, preservation, the booking written into the files) are
in calendar_check and calendar_outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import scheduling_rules as rules

REQUEST, POLICY, POLICY_TEXT, RESULT = "request.json", "policy.json", "policy.md", "result.json"
CALENDARS, ROOMS = "calendars", "rooms"
RULE_TYPES = ("buffer_minutes", "focus_blocks", "room_feature")
PRIORITIES = ("normal", "urgent")


def calendar_path(person):
    return f"{CALENDARS}/{person}.json"


def room_path(room):
    return f"{ROOMS}/{room}.json"


# ---- reading and validating -----------------------------------------------------------------------

def _read(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{what}: {exc}") from None


def _object(value, what):
    if not isinstance(value, dict):
        raise ValueError(f"{what} must be an object")
    return value


def _names(value, what):
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value) or len(set(value)) != len(value):
        raise ValueError(f"{what} must be a list of distinct non-empty strings")
    return value


def _events(owner, rel):
    events = owner.get("events")
    if not isinstance(events, list):
        raise ValueError(f"{rel}: events must be a list")
    seen = set()
    for event in events:
        ident = event.get("id") if isinstance(event, dict) else None
        if not isinstance(ident, str) or not ident or ident in seen:
            raise ValueError(f"{rel}: every entry needs a unique non-empty string id")
        seen.add(ident)
        if rules.stamp(event.get("start"))[0] >= rules.stamp(event.get("end"))[0]:
            raise ValueError(f"{rel}: entry {ident} must end after it starts")


def read_state(workspace):
    """{relative path: parsed JSON} for every file under calendars/ and rooms/."""
    root = Path(workspace)
    state = {}
    for folder in (CALENDARS, ROOMS):
        for path in sorted((root / folder).glob("*.json")):
            rel = path.relative_to(root).as_posix()
            state[rel] = _object(_read(path, rel), rel)
            _events(state[rel], rel)
    return state


def _rules_of(policy):
    policy = _object(policy, POLICY)
    rule_list = policy.get("rules")
    if not isinstance(rule_list, list):
        raise ValueError(f"{POLICY}: rules must be a list")
    seen = set()
    for rule in rule_list:
        kind = _object(rule, "a policy rule").get("type")
        if kind not in RULE_TYPES:
            raise ValueError(f"{POLICY}: unknown rule type {kind!r}")
        if kind != "room_feature" and kind in seen:
            raise ValueError(f"{POLICY}: {kind} may appear once")
        seen.add(kind)
        if kind == "buffer_minutes" and not (type(rule.get("minutes")) is int and rule["minutes"] >= 0):
            raise ValueError(f"{POLICY}: buffer_minutes needs a non-negative integer `minutes`")
        if kind == "focus_blocks" and not isinstance(rule.get("urgent_may_override", False), bool):
            raise ValueError(f"{POLICY}: urgent_may_override must be true or false")
        if kind == "room_feature" and not (isinstance(rule.get("feature"), str) and rule["feature"]
                                           and type(rule.get("min_attendees", 1)) is int and rule.get("min_attendees", 1) >= 1):
            raise ValueError(f"{POLICY}: room_feature needs `feature` and a positive integer `min_attendees`")
    return rule_list


def schedule_instance(instance):
    """The scheduling-domain instance for the workspace's request, policy and state.

    Every entry is busy time; a person's focus entry is not when the policy lets an urgent request book over focus blocks.
    The buffer rule becomes a `buffer_minutes` constraint for each required attendee, and a room_feature rule whose
    attendee threshold is met becomes a `room_feature` constraint."""
    request, state = _object(instance["request"], REQUEST), instance["state"]
    required, optional = _names(request.get("attendees"), "attendees"), _names(request.get("optional", []), "optional")
    if not required or set(required) & set(optional):
        raise ValueError("attendees must be non-empty and disjoint from optional")
    if request.get("priority", "normal") not in PRIORITIES:
        raise ValueError(f"priority must be one of {PRIORITIES}")
    for person in (*required, *optional):
        if calendar_path(person) not in state:
            raise ValueError(f"{calendar_path(person)} is missing")
    policy_rules = _rules_of(instance["policy"])
    focus = next((r for r in policy_rules if r["type"] == "focus_blocks"), {})
    skip_focus = request.get("priority") == "urgent" and focus.get("urgent_may_override", False)

    def busy(doc, ignore_focus=False):
        return [{"start": e["start"], "end": e["end"]} for e in doc["events"] if not (ignore_focus and e.get("kind") == "focus")]

    constraints = []
    for rule in policy_rules:
        if rule["type"] == "buffer_minutes":
            constraints += [{"type": "buffer_minutes", "participant": p, "minutes": rule["minutes"]} for p in required]
        elif rule["type"] == "room_feature" and len(required) >= rule.get("min_attendees", 1):
            constraints.append({"type": "room_feature", "feature": rule["feature"]})
    schedule = {
        "duration_minutes": request.get("duration_minutes"),
        "granularity_minutes": request.get("granularity_minutes", 15),
        "window": request.get("window"),
        "participants": [
            {"id": p, "utc_offset": state[calendar_path(p)].get("utc_offset"), "required": p in required,
             "work_hours": state[calendar_path(p)].get("work_hours"), "busy": busy(state[calendar_path(p)], skip_focus)}
            for p in (*required, *optional)],
        "rooms": [{"id": Path(path).stem, "capacity": doc.get("capacity"), "features": doc.get("features", []),
                   "busy": busy(doc)} for path, doc in state.items() if path.startswith(f"{ROOMS}/")],
        "constraints": constraints,
        "preference": request.get("preference"),
    }
    rules.model(schedule)
    return schedule


def load(workspace):
    """The instance for a workspace; ValueError says why a workspace does not conform."""
    root = Path(workspace)
    instance = {"request": _read(root / REQUEST, REQUEST), "policy": _read(root / POLICY, POLICY), "state": read_state(root)}
    instance["schedule"] = schedule_instance(instance)
    return instance


def recognize(workspace, prompt=""):
    """The instance in the workspace when it conforms to the interface, else None."""
    try:
        return load(workspace)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def collect(workspace):
    """{relative path: bytes} for the files a result is judged on: calendars/, rooms/ and result.json."""
    root = Path(workspace)
    paths = [p for folder in (CALENDARS, ROOMS) for p in sorted((root / folder).glob("*.json"))]
    if (root / RESULT).is_file():
        paths.append(root / RESULT)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in paths}


# ---- the policy text and building workspaces ------------------------------------------------------

def render_policy(policy):
    """policy.md for a policy.json: the baseline rules, then one line per rule, in the policy's order."""
    lines = [
        "- Book only while every required attendee is working, in that person's own time zone, and never over another "
        "entry on a required attendee's calendar.",
        "- Optional attendees never restrict the time.",
        "- The meeting lies inside the request's window and starts on its granularity grid, counted from the start of the "
        "window. The request's `preference` picks the earliest or latest valid start; `any` accepts every valid start.",
        "- When rooms exist, book one that is free for the whole meeting and seats every required attendee.",
        "- Never change or remove an existing entry; a booking only adds one.",
    ]
    for rule in _rules_of(policy):
        if rule["type"] == "buffer_minutes":
            lines.append(f"- Keep at least {rule['minutes']} minutes between the new meeting and every other entry on each "
                         "required attendee's calendar, before and after.")
        elif rule["type"] == "focus_blocks":
            lines.append("- Focus blocks (entries of kind `focus`) are protected like meetings. " + (
                "A request with priority `urgent` may be booked over them." if rule.get("urgent_may_override")
                else "Not even an urgent request may be booked over them."))
        else:
            count = rule.get("min_attendees", 1)
            who = f"When {count} or more people must attend, the" if count > 1 else "The"
            lines.append(f"- {who} room needs the `{rule['feature']}` feature.")
    team = f" for {policy['team']}" if policy.get("team") else ""
    return f"# Booking policy{team}\n\nEvery meeting is booked under these rules.\n\n" + "\n".join(lines) + "\n"


def build_workspace(directory, *, request, policy, calendars, rooms=None):
    """Write a workspace: request.json, policy.json, policy.md rendered from it, one file per calendar and room."""
    root = Path(directory)
    files = {REQUEST: request, POLICY: policy, **{calendar_path(k): v for k, v in calendars.items()},
             **{room_path(k): v for k, v in (rooms or {}).items()}}
    for rel, doc in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(rules.dump(doc, indent=2))
    (root / POLICY_TEXT).write_text(render_policy(policy), encoding="utf-8", newline="\n")
    return root
