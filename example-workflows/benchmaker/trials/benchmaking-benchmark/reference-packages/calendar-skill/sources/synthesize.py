"""Writes ../offline-instances/*.json and rejections.jsonl: python synthesize.py

Each slot in slots.py describes one task of the offline package. For every slot the script tries seeds until a
candidate passes the admission filters, and logs every try: the request must be feasible (or deliberately infeasible),
only a handful of the grid's starts may be valid so a guess at a slot almost never works, and the defects the slot
targets must actually go wrong on it, and an assistant that ignores the policy (the earliest free slot) must earn nothing.
The reference solution, not the verifier, is the oracle. Deterministic: seeds
are slot ids plus a counter.
"""
import copy
import importlib.util
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_workspaces as bw  # noqa: E402
import defects  # noqa: E402
from slots import SLOTS  # noqa: E402

bc = bw.bc
spec_ = importlib.util.spec_from_file_location("solve", HERE / "task" / "solve.py")
solve = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(solve)

FIRST = bc.MONDAY.date()
MAX_FRACTION = 0.015
EXERCISED = 0.5
VIDEO = "video"


def request_of(spec, tz):
    begin = bc.local(FIRST, spec.get("from", "00:00"), tz)
    out = {"title": spec["title"], "attendees": spec["ids"]}
    if spec.get("optional"):
        out["optional"] = spec["optional"]
    out.update(duration_minutes=spec["dur"], granularity_minutes=spec.get("gran", 15),
               window={"start": bc.stamp(begin), "end": bc.stamp(begin + timedelta(days=spec["days"], minutes=spec.get("extra", 0)))},
               preference=spec["pref"], priority=spec.get("priority", "normal"))
    return out


def starts_of(docs):
    return [s for s, _ in solve.valid_starts(solve.instance_of(docs))]


def finalize(docs):
    """Order every file's entries by start and number them in that order."""
    for group, folder in (("calendars", docs["calendars"]), ("rooms", docs["rooms"])):
        for name, doc in folder.items():
            doc["events"].sort(key=lambda e: datetime.fromisoformat(e["start"]))
            for n, e in enumerate(doc["events"], 1):
                e["id"] = f"{name}-{n:03d}"


def kill_rooms(docs, starts):
    r = docs["request"]
    for s in starts:
        for rid, room in docs["rooms"].items():
            if VIDEO in room["features"] and room["capacity"] >= len(r["attendees"]):
                begin = s - timedelta(minutes=15)
                room["events"].append({"id": f"{rid}-x{len(room['events'])}", "title": "Board meeting", "kind": "meeting",
                                       "start": bc.stamp(begin), "end": bc.stamp(begin + timedelta(minutes=r["duration_minutes"] + 30))})


def make(rng, spec):
    """(docs, [reasons it fails]) for one candidate."""
    tz = bc.zone(bc.person(spec.get("window_of", spec["ids"][0]))["utc_offset"])
    docs = bw.workspace(rng, spec, FIRST, tz, request_of(spec, tz))
    if spec.get("base"):
        blank = copy.deepcopy(docs)
        for folder in ("calendars", "rooms"):
            for doc in blank[folder].values():
                doc["events"] = []
        count = len(starts_of(blank))
        lo, hi = spec["base"]
        if not lo <= count <= hi:
            return docs, [f"the people's work hours leave {count} shared starts before any entry; wanted {lo} to {hi}, so the overlap is not the intended kind"]
    cap = min(max(1, int(MAX_FRACTION * bw.grid_size(docs))), spec.get("cap", 99))
    kind, rules = spec.get("kind"), docs["policy"]["rules"]
    buffer = next((r for r in rules if r["type"] == "buffer_minutes"), None)
    if kind == "buffer":
        docs["policy"]["rules"] = [r for r in rules if r["type"] != "buffer_minutes"]
    if not starts_of(docs):
        return docs, ["the calendars and policy leave no valid start, so the request would be infeasible by accident"]
    starts = bw.squeeze(rng, solve, docs, 3 if kind else cap)
    if kind == "buffer":
        docs["policy"]["rules"] = rules
    elif kind == "rooms":
        kill_rooms(docs, starts)
    if kind:
        left = len(starts_of(docs))
        return docs, [] if left == 0 else [f"the blocker left {left} valid starts, so the request is not infeasible"]
    if not 1 <= len(starts) <= cap:
        return docs, [f"too guessable: {len(starts)} valid starts remain after adding meetings, above the cap of {cap} (1.5% of the grid)"]
    return docs, []


def exercise(docs):
    return {name: defects.exercised(solve, docs, name, range(3)) for name in defects.DEFECTS}


def run(write=True, limit=600):
    out = HERE.parent / "offline-instances"
    out.mkdir(exist_ok=True)
    log, chosen = [], {}
    for spec in SLOTS:
        for n in range(limit):
            rng = random.Random(f"{spec['id']}:{n}")
            docs, problems = make(rng, spec)
            row = {"candidate": f"{spec['id']}#{n}", "family": spec["family"], "source_group": spec["group"]}
            if not problems:
                finalize(docs)
                seen = exercise(docs)
                problems = [f"the {d} defect is not exercised (wrong on {seen[d]:.0%} of draws), so the task would not detect it"
                            for d in spec.get("must", ()) if seen[d] < EXERCISED]
                if not problems and defects.pays_blind(solve, docs):
                    problems = ["the earliest slot free of every entry, with the policy ignored, already earns credit, so a content-blind assistant would pass"]
            if problems:
                log.append({**row, "disposition": "rejected", "reason": "; ".join(problems)})
                continue
            found = starts_of(docs)
            log.append({**row, "disposition": "admitted",
                        "reason": f"{len(found)} valid starts of {bw.grid_size(docs)}" if found else "no valid start, as designed"})
            chosen[spec["id"]] = (spec, docs)
            break
        else:
            print("no candidate for", spec["id"], file=sys.stderr)
    if write:
        for old in out.glob("*.json"):
            old.unlink()
        for slot_id, (spec, docs) in chosen.items():
            doc = {"id": slot_id, "family": spec["family"], "source_group": spec["group"], "title": spec["title"],
                   "difficulty": spec["why"], "expert_minutes": spec["minutes"], "smoke": spec.get("smoke", False),
                   "quick": spec.get("quick", False), "workspace": docs}
            (out / f"{slot_id}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        log += [{"candidate": c, "family": "-", "source_group": "-", "disposition": d, "reason": r} for c, d, r in MANUAL]
        (HERE / "rejections.jsonl").write_text("".join(json.dumps(r) + "\n" for r in log), encoding="utf-8")
    return chosen, log


MANUAL = [
    ("a hand-edited policy.md", "rejected", "The interface says policy.md is rendered from policy.json and never edited; generate.py renders it, so the two cannot disagree"),
    ("policy rules beyond buffer, focus blocks and room features", "rejected", "The interface fixes three rule types; a fourth would need an interface change and a new checker rule"),
    ("a skill-friendly task set (only rules the helper covers)", "rejected", "It would hide where a skill does not help; room-feature and urgent-focus tasks are included on purpose"),
    ("anchor tasks: one attendee, empty calendar", "rejected", "A random well-formed booking is valid on most of them, so guessing floors would earn credit; no anchors are admitted"),
    ("credit for result.json alone", "rejected", "A result that no file backs would earn credit; valid is judged from the files and reported from their agreement with result.json"),
]


if __name__ == "__main__":
    chosen, log = run()
    print(len(chosen), "workspaces;", sum(r["disposition"] == "rejected" for r in log), "rejected candidates")
