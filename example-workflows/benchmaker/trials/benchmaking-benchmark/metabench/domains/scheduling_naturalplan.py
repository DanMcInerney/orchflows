"""Natural Plan calendar scheduling as scheduling instances, and the material fetch.

Natural Plan (google-deepmind/natural-plan, code Apache-2.0, data CC BY 4.0) stores each calendar
scheduling record as prompt text; this module reads that text back into the instance shape of the
schedule-nosolver interface. Nothing from the dataset is committed: `fetch_material` downloads it.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path

MATERIAL_JSON = Path(__file__).resolve().parents[2] / "meta-tasks" / "schedule-nosolver" / "material.json"
SOURCE_FILE = "calendar_scheduling.json"
KEPT_FIELDS = ("num_people", "num_days", "duration", "prompt_0shot", "golden_plan")

# Natural Plan names weekdays only. Instances use this fixed week, every participant at UTC+00:00.
_MONDAY = date(2026, 10, 5)
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_DAY = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
_HEADER = re.compile(
    r"You need to schedule a meeting for (?P<who>.+?) for (?P<length>half an hour|one hour|\d+(?:\.\d+)? hours?) "
    rf"between the work hours of (?P<start>\d{{1,2}}:\d{{2}}) to (?P<end>\d{{1,2}}:\d{{2}}) on (?:either )?(?P<days>{_DAY}[^.]*)\."
)
_FREE = re.compile(r"^(?:'s calendar is wide open|\s*is free|\s*has no meetings) the (?:entire|whole) (?:day|week)\.$")
_BUSY = re.compile(r"^\s*(?:is busy on|has meetings on|has blocked their calendar on) (?P<spans>.+?);?$")
_SPAN = re.compile(r"(\d{1,2}:\d{2}) to (\d{1,2}:\d{2})")
_VERB = r"(?:can not meet|do not want to meet|would rather not meet|would like to avoid more meetings)"
_PREFERENCE = re.compile(rf"^(?P<who>[A-Z][a-z]+) {_VERB} on (?P<day>{_DAY})(?: (?P<when>before|after) (?P<time>\d{{1,2}}:\d{{2}}))?$")
_MORE = re.compile(rf"^(?P<day>{_DAY})(?: (?P<when>before|after) (?P<time>\d{{1,2}}:\d{{2}}))?$")
_ANSWER = re.compile(rf"proposed time: ({_DAY}), (\d{{1,2}}:\d{{2}}) - (\d{{1,2}}:\d{{2}})")


def _clock(text):
    hours, minutes = text.split(":")
    return f"{int(hours):02d}:{minutes}"


def _stamp(day, clock):
    return f"{_MONDAY + timedelta(days=_WEEKDAYS.index(day))}T{_clock(clock)}+00:00"


def _task(record):
    prompt = record.get("prompt_0shot") or record.get("prompt_5shot")
    if not isinstance(prompt, str) or "TASK:" not in prompt:
        raise ValueError("the record has no TASK prompt")
    return prompt[prompt.rindex("TASK:"):].split("SOLUTION:")[0]


def _busy_spans(text):
    """The (day, start, end) triples in 'Monday during 9:00 to 9:30, 10:00 to 11:00, Tuesday during ...'."""
    parts = re.split(rf"(?:^|,\s*)({_DAY}) during ", text)
    if parts[0].strip() or len(parts) < 3:
        raise ValueError(f"unreadable calendar: {text!r}")
    return [(day, a, b) for day, spans in zip(parts[1::2], parts[2::2]) for a, b in _SPAN.findall(spans)]


def convert_natural_plan(record):
    """The schedule-nosolver instance for one Natural Plan calendar scheduling record."""
    task = _task(record)
    head = _HEADER.search(task)
    if head is None:
        raise ValueError("the task sentence is not in Natural Plan's calendar scheduling form")
    names = re.split(r", | and ", head["who"])
    days = re.findall(_DAY, head["days"])
    minutes = {"half an hour": 30, "one hour": 60}.get(head["length"])
    if minutes is None:
        minutes = round(float(head["length"].split()[0]) * 60)
    lines = task.split("Here are the existing schedules for everyone during the day")[1].split("\n")[1:]
    lines = [line for line in lines if line.strip()]
    participants = []
    for name, line in zip(names, lines):
        if not line.startswith(name):
            raise ValueError(f"expected {name}'s calendar, found {line!r}")
        rest = line[len(name):].strip()
        busy = []
        if not _FREE.match(rest):
            found = _BUSY.match(rest)
            if found is None:
                raise ValueError(f"unreadable calendar line: {line!r}")
            busy = [{"start": _stamp(d, a), "end": _stamp(d, b)} for d, a, b in _busy_spans(found["spans"])]
        participants.append({
            "id": name, "utc_offset": "+00:00", "required": True, "busy": busy,
            "work_hours": [{"days": [d[:3] for d in days], "start": _clock(head["start"]), "end": _clock(head["end"])}],
        })
    if len(participants) != len(names):
        raise ValueError("fewer calendars than participants")
    constraints, who, earliest = [], None, False
    for sentence in (s.strip() for s in " ".join(lines[len(names):]).split(".")):
        if not sentence or sentence.startswith("Find a time"):
            continue
        if re.search(r"earl\w*st availability", sentence):
            earliest = True
            continue
        found = _PREFERENCE.match(sentence)
        if found:
            who = found["who"]
        else:
            found = _MORE.match(sentence)
        if found is None or who not in names:
            raise ValueError(f"unreadable preference sentence: {sentence!r}")
        day = str(_MONDAY + timedelta(days=_WEEKDAYS.index(found["day"])))
        if found["when"] is None:
            constraints.append({"type": "avoid_day", "participant": who, "day": day})
        else:
            kind = "not_before" if found["when"] == "before" else "not_after"
            constraints.append({"type": kind, "participant": who, "time": _clock(found["time"]), "day": day})
    return {
        "duration_minutes": minutes,
        "granularity_minutes": 30,
        "window": {"start": _stamp(days[0], head["start"]), "end": _stamp(days[-1], head["end"])},
        "participants": participants,
        "rooms": [],
        "constraints": constraints,
        "preference": "earliest" if earliest else "any",
    }


def natural_plan_answer(record):
    """output.json files for the record's golden plan, written in the instance's UTC+00:00 form."""
    found = _ANSWER.search(record["golden_plan"])
    if found is None:
        raise ValueError(f"unreadable golden plan: {record['golden_plan']!r}")
    day, start, end = found.groups()
    body = {"start": _stamp(day, start), "end": _stamp(day, end)}
    return {"output.json": (json.dumps(body) + "\n").encode("utf-8")}


def load_instances(path):
    """{record id: instance} for every record in a calendar_scheduling.json style file."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    instances = {}
    for record_id, record in records.items():
        try:
            instances[record_id] = convert_natural_plan(record)
        except ValueError as exc:
            raise ValueError(f"{record_id}: {exc}") from None
    return instances


def fetch_material(store, opener=urllib.request.urlopen):
    """Download Natural Plan calendar scheduling into <store>/material/schedule-nosolver and split it.

    Writes source/ (the raw download), public/ (the sample listed in material.json, with an attribution
    notice), held-out/ (every other record) and split.json. The network is touched only here.
    """
    spec = json.loads(MATERIAL_JSON.read_text(encoding="utf-8"))
    root = Path(store) / "material" / "schedule-nosolver"
    request = urllib.request.Request(spec["source"]["data_url"], headers={"User-Agent": "metabench"})
    with opener(request, timeout=300) as response:
        data = response.read()
    records = json.loads(data.decode("utf-8"))
    public_ids = list(spec["public_records"])
    missing = [i for i in public_ids if i not in records]
    if missing:
        raise ValueError(f"public records missing from the download: {missing}")
    held_ids = [i for i in records if i not in set(public_ids)]
    unreadable = []
    for record_id, record in records.items():
        try:
            convert_natural_plan(record)
        except ValueError as exc:
            unreadable.append({"id": record_id, "error": str(exc)})

    def write(folder, name, content):
        (root / folder).mkdir(parents=True, exist_ok=True)
        (root / folder / name).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def slim(ids):
        return json.dumps({i: {k: records[i][k] for k in KEPT_FIELDS} for i in ids}, indent=1)

    write("source", SOURCE_FILE, data)
    write("public", SOURCE_FILE, slim(public_ids))
    write("public", "NOTICE.md", spec["attribution"] + "\n")
    write("held-out", SOURCE_FILE, slim(held_ids))
    write("", "split.json", json.dumps({"public": public_ids, "held_out": held_ids}, indent=1))
    return {"records": len(records), "public": len(public_ids), "held_out": len(held_ids), "unreadable": unreadable}
