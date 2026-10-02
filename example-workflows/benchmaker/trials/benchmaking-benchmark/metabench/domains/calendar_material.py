"""Material for calendar-skill: Natural Plan requests turned into calendar workspaces, and the material fetch.

The scheduling material (Natural Plan calendar scheduling, code Apache-2.0, data CC BY 4.0) supplies realistic
requests and verified answers; the workspace layout and the booking policy are the team's own.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from . import scheduling_naturalplan as _np

MATERIAL_JSON = Path(__file__).resolve().parents[2] / "meta-tasks" / "calendar-skill" / "material.json"


def _policy_rules(constraints, required):
    """Policy rules for a scheduling instance's constraints; ValueError for one a calendar policy cannot express."""
    rules = []
    buffers = [c for c in constraints if c["type"] == "buffer_minutes"]
    if buffers:
        if len(buffers) != len(required) or {c["participant"] for c in buffers} != set(required) or len({c["minutes"] for c in buffers}) != 1:
            raise ValueError("buffer_minutes must apply to every required participant alike")
        rules.append({"type": "buffer_minutes", "minutes": buffers[0]["minutes"]})
    for constraint in constraints:
        if constraint["type"] == "room_feature":
            rules.append({"type": "room_feature", "min_attendees": 1, "feature": constraint["feature"]})
        elif constraint["type"] != "buffer_minutes":
            raise ValueError(f"constraint {constraint['type']} has no form in a calendar policy")
    return rules


def from_schedule(instance, policy=None, *, title="Meeting", priority="normal"):
    """build_workspace keywords for a scheduling instance: its busy intervals become calendar entries.

    Only constraints a calendar policy can express survive: a `buffer_minutes` that is the same for every required
    participant, and `room_feature`. Anything else, such as a day-specific preference, raises ValueError. `policy`
    adds rules, such as `focus_blocks`, that the instance cannot carry."""
    required = [p["id"] for p in instance["participants"] if p.get("required", True)]
    rules = _policy_rules(instance.get("constraints", []), required) + list((policy or {}).get("rules", []))

    def events(owner):
        return [{"id": f"{owner['id']}-{n}", "title": "Busy", "kind": "meeting", **busy} for n, busy in enumerate(owner.get("busy", []), 1)]

    return {
        "request": {"title": title, "attendees": required,
                    "optional": [p["id"] for p in instance["participants"] if not p.get("required", True)],
                    "duration_minutes": instance["duration_minutes"], "granularity_minutes": instance.get("granularity_minutes", 15),
                    "window": instance["window"], "preference": instance["preference"], "priority": priority},
        "policy": {**(policy or {}), "rules": rules},
        "calendars": {p["id"]: {"utc_offset": p["utc_offset"], "work_hours": p["work_hours"], "events": events(p)}
                      for p in instance["participants"]},
        "rooms": {r["id"]: {"capacity": r["capacity"], "features": r.get("features", []), "events": events(r)}
                  for r in instance.get("rooms", [])}}


def fetch_material(store, opener=urllib.request.urlopen):
    """Natural Plan calendar scheduling for calendar-skill under <store>/material/calendar-skill.

    Writes public/ (the sample listed in material.json, with an attribution notice), held-out/ (every other
    record) and split.json. The raw download of schedule-nosolver is reused when it is in the store; otherwise
    the file is downloaded here. The network is touched only here."""
    spec = json.loads(MATERIAL_JSON.read_text(encoding="utf-8"))
    store = Path(store)
    shared = store / "material" / "schedule-nosolver" / "source" / _np.SOURCE_FILE
    if shared.is_file():
        data = shared.read_bytes()
    else:
        request = urllib.request.Request(spec["source"]["data_url"], headers={"User-Agent": "metabench"})
        with opener(request, timeout=300) as response:
            data = response.read()
    records = json.loads(data.decode("utf-8"))
    public = list(spec["public_records"])
    missing = [i for i in public if i not in records]
    if missing:
        raise ValueError(f"public records missing from the download: {missing}")
    held_out = [i for i in records if i not in set(public)]
    root = store / "material" / "calendar-skill"

    def write(folder, name, text):
        (root / folder).mkdir(parents=True, exist_ok=True)
        (root / folder / name).write_text(text, encoding="utf-8", newline="\n")

    def slim(ids):
        return json.dumps({i: {k: records[i][k] for k in _np.KEPT_FIELDS} for i in ids}, indent=1)

    write("public", _np.SOURCE_FILE, slim(public))
    write("public", "NOTICE.md", spec["attribution"] + "\n")
    write("held-out", _np.SOURCE_FILE, slim(held_out))
    write("", "split.json", json.dumps({"public": public, "held_out": held_out}, indent=1))
    return {"records": len(records), "public": len(public), "held_out": len(held_out)}
