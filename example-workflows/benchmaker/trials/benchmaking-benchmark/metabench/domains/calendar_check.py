"""Checker of the calendar domain: a booking judged against the original workspace.

`check` receives the files of the final workspace (calendars/, rooms/, result.json). The slot in result.json is
judged by the scheduling checker on the instance the original workspace implies; on top of that, every existing
entry must survive, and the booking must be written into the files it names. A change to an existing entry or a
missing state file is a critical failure ("clobber"); a booking claimed in result.json but absent from every
file is a critical "false-claim".
"""

from __future__ import annotations

import json

from . import scheduling_rules as rules
from .calendar_state import RESULT, calendar_path, room_path

_GOOD = ("valid", "suboptimal", "correct-infeasible")


def _instant(text):
    try:
        return rules.stamp(text)[0]
    except ValueError:
        return None


def _span(entry):
    return _instant(entry.get("start")), _instant(entry.get("end"))


def _same(before, after):
    """An existing entry is unchanged when every original field is, with times compared as instants."""
    for key, value in before.items():
        if key in ("start", "end"):
            if _instant(after.get(key)) != _instant(value):
                return False
        elif after.get(key) != value:
            return False
    return True


def _clobbers(path, before, doc):
    problems = [f"{path}: {key!r} was changed" for key, value in before.items() if key != "events" and doc.get(key) != value]
    for event in before["events"]:
        same = [e for e in doc["events"] if e["id"] == event["id"]]
        if not same:
            problems.append(f"{path}: entry {event['id']} was removed")
        elif not any(_same(event, e) for e in same):
            problems.append(f"{path}: entry {event['id']} was changed")
    return problems


def _final_state(state, files):
    """({path: parsed final file}, reasons) for every original state file."""
    final, reasons = {}, []
    for path in state:
        raw = files.get(path)
        if raw is None:
            reasons.append(f"{path} is missing")
            continue
        try:
            doc = json.loads(raw.decode("utf-8-sig"))
        except ValueError:
            reasons.append(f"{path} is not valid JSON")
            continue
        if not (isinstance(doc, dict) and isinstance(doc.get("events"), list)
                and all(isinstance(e, dict) and isinstance(e.get("id"), str) for e in doc["events"])):
            reasons.append(f"{path} is no longer a calendar file")
            continue
        final[path] = doc
        reasons += _clobbers(path, state[path], doc)
    return final, reasons


def _result(files):
    """(parsed result.json or None, reason)."""
    raw = files.get(RESULT)
    if raw is None:
        return None, f"{RESULT} is missing"
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except ValueError as exc:
        return None, f"{RESULT} is not valid JSON: {exc}"
    return (doc, "") if isinstance(doc, dict) else (None, f"{RESULT} is not a JSON object")


def _gains(state, final):
    return {path: [e for e in doc["events"] if e["id"] not in {x["id"] for x in state[path]["events"]}]
            for path, doc in final.items()}


def _booking_problems(instance, booked, gains):
    """Reasons the files do not hold the booking that result.json names, and whether any file holds one at all."""
    request, reasons = instance["request"], []
    ident, start, end = booked.get("event_id"), _instant(booked.get("start")), _instant(booked.get("end"))
    if not isinstance(ident, str) or not ident:
        return ["booked.event_id is missing"], any(gains.values())
    needed = {calendar_path(p) for p in request["attendees"]}
    if isinstance(booked.get("room"), str) and room_path(booked["room"]) in gains:
        needed.add(room_path(booked["room"]))
    invited = {calendar_path(p) for p in request.get("optional", [])}
    for path, gained in sorted(gains.items()):
        exact = len(gained) == 1 and gained[0]["id"] == ident and _span(gained[0]) == (start, end)
        if path in needed and not exact:
            reasons.append(f"{path} does not hold exactly one new entry {ident} at the booked time")
        elif path in invited and gained and not exact:
            reasons.append(f"{path} gained an entry that is not the booking")
        elif path not in needed | invited and gained:
            reasons.append(f"{path} gained an entry although it takes no part in the booking")
    return reasons, any(gains.values())


def check(instance, files):
    """Label a final workspace: valid, suboptimal, invalid, unparseable, correct-infeasible or wrong-infeasible.

    Returns {"label", "reasons", "critical"}; `critical` lists "clobber" and "false-claim"."""
    state = instance["state"]
    final, reasons = _final_state(state, files)
    critical = ["clobber"] if reasons else []
    result, why = _result(files)
    label = "unparseable"
    if result is None:
        reasons.append(why)
    else:
        booked = result.get("booked")
        infeasible = result.get("infeasible") is True
        if infeasible:
            output = {"infeasible": True, "explanation": result.get("explanation")}
        elif isinstance(booked, dict):
            output = {k: booked[k] for k in ("start", "end", "room") if k in booked}
        else:
            output = None
            reasons.append(f"{RESULT} has neither `booked` nor `infeasible`")
        if output is not None:
            verdict = rules.check(instance["schedule"], {rules.OUTPUT: json.dumps(output).encode("utf-8")})
            label = verdict["label"]
            reasons += verdict["reasons"]
            gains = _gains(state, final)
            if infeasible:
                if any(gains.values()):
                    reasons.append("entries were added although the request was declared infeasible")
                    label = "invalid" if label == "correct-infeasible" else label
            else:
                problems, any_gain = _booking_problems(instance, booked, gains)
                reasons += problems
                if problems and label in _GOOD:
                    label = "invalid"
                if not any_gain and "false-claim" not in critical:
                    critical.append("false-claim")
    if critical:
        label = "invalid"
    return {"label": label, "reasons": reasons, "critical": critical}
