"""Writes the calendar-skill reference benchmark package: a hand-built, known-good delivery for the meta-task.

    python generate.py --instances offline|DIR --out PKG [--split development|held-out] [--limit N] [--seed S] [--only IDS]

`offline` uses the committed synthetic workspaces in offline-instances/. DIR holds workspace files (JSON with a
`workspace` key, as in offline-instances/) and/or Natural Plan's calendar_scheduling.json, whose records are turned
into workspaces with metabench; at most --limit convertible records are taken, chosen by --seed. The package gets
tasks/, admission/, suite.json, card.json, README.md, research/, rejections.jsonl and adapters/ (the stock agent
without and with the subject's skill, copied from meta-tasks/calendar-skill/subject), but no kit: assemble it by
copying scripts/benchkit and scripts/run.py of the Benchmaker skill into it. Verifiers and references are the files in
sources/task/; they are written from the public interface alone and import nothing from metabench.
"""
import argparse
import importlib.util
import json
import random
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"
BB = HERE.parents[1]
SUBJECT = BB / "meta-tasks" / "calendar-skill" / "subject"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


defects = load(SRC / "defects.py", "calendar_defects")
oracle = load(SRC / "task" / "solve.py", "reference_solve")
verifier = load(SRC / "task" / "verify.py", "reference_verify")

PHRASE = {"earliest": "at the earliest possible time", "latest": "at the latest possible time", "any": "at any time that works"}
ADAPTERS = {"haiku-low": {"model": "claude-haiku-4-5", "effort": "low", "skills": [], "safe_mode": False},
            "haiku-low-skill": {"model": "claude-haiku-4-5", "effort": "low", "skills": ["booking-rules"]}}
REPEATS, CONCURRENCY = 3, 6


# ---- instances -------------------------------------------------------------------------------------------------

def read_instances(source, limit, seed):
    """(docs, notes, offline): each doc is {id, family, source_group, title, difficulty, expert_minutes, workspace}."""
    if source == "offline":
        return [json.loads(f.read_text(encoding="utf-8")) for f in sorted((HERE / "offline-instances").glob("*.json"))], [], True
    folder, docs, notes = Path(source), [], []
    for f in sorted(folder.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "workspace" in data:
            docs.append(data)
        elif f.name == "calendar_scheduling.json":
            sys.path.insert(0, str(BB))
            from metabench.domains import calendar_material, scheduling_naturalplan as natural_plan
            instances = natural_plan.load_instances(f)
            order = sorted(instances)
            random.Random(seed).shuffle(order)
            for record_id in order:
                if len([d for d in docs if d["id"].startswith("np-")]) >= limit:
                    break
                number = record_id.rsplit("_", 1)[-1]
                try:
                    parts = calendar_material.from_schedule(instances[record_id], title=f"Natural Plan {number}")
                except ValueError as error:
                    notes.append({"candidate": f"np-{number}", "disposition": "rejected", "reason": f"no calendar form: {error}"})
                    continue
                people = len(parts["request"]["attendees"])
                docs.append({"id": f"np-{number}", "family": f"natural-plan-{people}-people", "source_group": f"natural-plan-{people}p",
                             "title": f"Natural Plan calendar scheduling {number}", "expert_minutes": 6,
                             "difficulty": "Natural Plan's calendar scheduling request reconstructed as calendar files under a buffer or room policy",
                             "workspace": {"request": parts["request"], "policy": parts["policy"], "calendars": parts["calendars"], "rooms": parts.get("rooms") or {}}})
            notes.append({"candidate": f.name, "disposition": "sampled", "reason": f"records chosen at random with seed {seed}"})
    if not docs:
        raise SystemExit(f"no workspaces found in {folder}")
    for number, doc in enumerate(docs):
        doc.setdefault("smoke", number == 0)
        doc.setdefault("quick", number % 4 == 0)
    return docs, notes, False


def render_policy(policy):
    """policy.md for a policy.json: the rules every booking follows, then one line per team rule."""
    lines = ["# Booking policy", "", "Every meeting is booked under these rules.", "", "## Always", "",
             "- Time is half-open: an entry from 10:00 to 10:30 occupies 10:00 up to, not including, 10:30, so a meeting may start exactly when an entry ends or end exactly when one starts.",
             "- Every attendee (`attendees` in `request.json`) must be inside their work hours, in their own `utc_offset`, for the whole meeting and must have no entry that overlaps it. Times are compared as instants whatever offset they are written in.",
             "- People in `optional` are invited but never restrict the time: ignore their work hours and entries.",
             "- The meeting lies inside the request's `window` and starts on its grid: `window.start` plus a whole number of `granularity_minutes` (it may end exactly at `window.end`). `preference` picks the earliest or latest valid start; `any` accepts every valid start.",
             "- When the folder has room files, book exactly one room that has no entry overlapping the meeting and whose `capacity` is at least the number of attendees. Without room files, book no room.",
             "- Never change or remove an existing entry or any other field of a file; a booking only adds entries.", "",
             "## Team rules", ""]
    for rule in policy["rules"]:
        if rule["type"] == "buffer_minutes":
            lines.append(f"- Keep at least {rule['minutes']} minutes between the new meeting and every other entry on each attendee's calendar, before and after.")
        elif rule["type"] == "focus_blocks":
            lines.append("- Focus blocks (entries of kind `focus`) are protected like meetings. " + (
                "A request with priority `urgent` may be booked over them: for an urgent request ignore every attendee's focus entries completely, so they neither overlap the meeting nor count for the buffer."
                if rule.get("urgent_may_override") else "No request, urgent or not, may be booked over them."))
        else:
            count = rule.get("min_attendees", 1)
            who = f"When {count} or more people attend, the" if count > 1 else "The"
            lines.append(f"- {who} room needs the `{rule['feature']}` feature.")
    if not policy["rules"]:
        lines.append("- None beyond the rules above.")
    return "\n".join(lines) + "\n"


def request_line(doc):
    r = doc["workspace"]["request"]
    names = ", ".join(r["attendees"][:-1]) + (" and " if len(r["attendees"]) > 1 else "") + r["attendees"][-1]
    extra = f" ({', '.join(r['optional'])} {'is' if len(r['optional']) == 1 else 'are'} invited but optional)" if r.get("optional") else ""
    urgent = " The request is urgent." if r.get("priority") == "urgent" else ""
    return (f"Book \"{r.get('title', 'Meeting')}\" for {names}{extra}: {r['duration_minutes']} minutes, {PHRASE[r['preference']]}, "
            f"between {r['window']['start']} and {r['window']['end']}.{urgent}")


def fill(text, **values):
    for key, value in values.items():
        text = text.replace(f"<<{key}>>", str(value))
    return text


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)


def pretty(value, depth=0):
    """JSON with one line per small object, so an entry or a work-hours entry is not spread over many lines."""
    flat = json.dumps(value)
    if not isinstance(value, (dict, list)) or len(flat) <= 100 or not any(isinstance(v, (dict, list)) for v in (value.values() if isinstance(value, dict) else value)):
        return flat
    pad, inner = " " * depth, " " * (depth + 1)
    if isinstance(value, dict):
        return "{\n" + ",\n".join(f"{inner}{json.dumps(k)}: {pretty(v, depth + 1)}" for k, v in value.items()) + "\n" + pad + "}"
    return "[\n" + ",\n".join(inner + pretty(v, depth + 1) for v in value) + "\n" + pad + "]"


def dump(doc):
    return pretty(doc) + "\n"


# ---- tasks and admission ---------------------------------------------------------------------------------------

def write_environment(root, ws):
    write(root / "request.json", dump(ws["request"]))
    write(root / "policy.json", dump(ws["policy"]))
    write(root / "policy.md", render_policy(ws["policy"]))
    for group in ("calendars", "rooms"):
        for name, doc in ws[group].items():
            write(root / group / f"{name}.json", dump(doc))


def write_task(out, doc, split):
    task = out / "tasks" / doc["id"]
    write(task / "instruction.md", fill((SRC / "task" / "instruction.md").read_text(encoding="utf-8"), TITLE=doc["title"], REQUEST=request_line(doc)))
    write(task / "task.toml", fill((SRC / "task" / "task.toml").read_text(encoding="utf-8"),
          FAMILY=json.dumps(doc["family"]), GROUP=json.dumps(doc["source_group"]), SPLIT=json.dumps(split),
          SMOKE=str(doc["smoke"]).lower(), QUICK=str(doc["quick"]).lower(), DIFFICULTY=json.dumps(doc["difficulty"]),
          MINUTES=doc["expert_minutes"]))
    write_environment(task / "environment", doc["workspace"])
    for folder, name in (("solution", "solve.py"), ("tests", "verify.py")):
        (task / folder).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SRC / "task" / name, task / folder / name)
    return task


def grade_dir(orig, workspace):
    valid, optimal, reported, critical, _ = verifier.grade(orig, workspace)
    credit = sum(verifier.WEIGHTS[k] * v for k, v in (("valid", valid), ("optimal", optimal), ("reported", reported)))
    return bool(valid and optimal and reported and not critical), credit


def chance(docs):
    """(probability that a uniformly random start and room make a valid booking, that they make the best one)."""
    instance = oracle.instance_of(docs)
    found = oracle.valid_starts(instance)
    m = oracle.read(instance)
    grid = int((m["hi"] - m["lo"] - m["duration"]) / m["step"]) + 1
    rooms = len(docs["rooms"])
    share = lambda picks: sum((len(r) / rooms if rooms else 1) for _, r in picks) / grid  # noqa: E731
    best = {"earliest": found[:1], "latest": found[-1:]}.get(docs["request"]["preference"], found)
    return share(found), share(best), len(found), grid


def admit(out, doc, task):
    """admission/<id>/: labelled final workspaces, labels.json and the evidence record."""
    ws, root, env = doc["workspace"], out / "admission" / doc["id"], task / "environment"
    orig = verifier.Original(env)
    items = defects.labeled(oracle, ws)
    labels, agree = {}, {"valid": [0, 0], "suboptimal": [0, 0], "invalid": [0, 0]}
    for number, (kind, label, files) in enumerate(items, 1):
        sub = f"{number:02d}-{kind.replace(':', '-')}"
        target = root / "labeled" / sub
        shutil.copytree(env, target)
        for path in list(target.glob("calendars/*.json")) + list(target.glob("rooms/*.json")) + [target / "result.json"]:
            path.unlink(missing_ok=True)
        for rel, data in files.items():
            write(target / rel, data)
        labels[sub] = {"label": label, "kind": kind}
        full, _ = grade_dir(orig, target)
        agree[label][0] += full == (label == "valid")
        agree[label][1] += 1
    mismatched = {k: v for k, v in agree.items() if v[0] != v[1]}
    if mismatched:
        raise SystemExit(f"{doc['id']}: the verifier disagrees with the reference's labels: {mismatched}")
    write(root / "labels.json", json.dumps(labels, indent=1) + "\n")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(env, Path(tmp) / "w")
        subprocess.run([sys.executable, str(SRC / "task" / "solve.py"), "--workspace", str(Path(tmp) / "w")], check=True, capture_output=True)
        reference_full, _ = grade_dir(orig, Path(tmp) / "w")
        shutil.rmtree(Path(tmp) / "w")
        shutil.copytree(env, Path(tmp) / "w")
        noop = grade_dir(orig, Path(tmp) / "w")[1]
        write(Path(tmp) / "w" / "result.json", "{}")
        empty = grade_dir(orig, Path(tmp) / "w")[1]
    if not reference_full:
        raise SystemExit(f"{doc['id']}: the reference does not pass its own verifier")
    p_valid, p_best, found, grid = chance(ws)
    exercised = {name: defects.exercised(oracle, ws, name, range(2)) for name in defects.DEFECTS}
    weights = verifier.WEIGHTS
    evidence = {"task": doc["id"], "valid_starts": found, "grid_starts": grid, "random_valid_probability": round(p_valid, 4),
                "random_expected_credit": round((weights["valid"] + weights["reported"]) * p_valid + weights["optimal"] * p_best, 4),
                "noop_credit": noop, "empty_result_credit": empty,
                "labeled": {k: v[1] for k, v in agree.items()}, "defects_exercised": {k: round(v, 2) for k, v in exercised.items()},
                "criteria": {"realistic": "reconstructed or synthetic: authored from the interface and the Natural Plan scenario style; the team policy is the team's own and invented for this benchmark",
                             "solvable": "pass: solution/solve.py edits the files and writes result.json, graded full success by tests/verify.py",
                             "unearned-by-inaction": "pass: leaving the workspace alone and an empty result.json earn credit 0; a random well-formed booking is valid with the probability above",
                             "fairly-graded": "pass: every labelled workspace (valid variants, valid-not-optimal, invalid, damaged files) graded as labelled; labels come from the reference, not the verifier",
                             "specified": "not run: no fresh auditor in a zero-cost build",
                             "shortcut-resistant": "not run: no adversary in a zero-cost build; solver workspaces hold the public files only",
                             "calibrated": "not run: no calibration system was attempted",
                             "hard-for-the-right-reason": "not run: no failure transcripts"},
                "disposition": "draft", "reason": "criteria 4 and 6 to 8 need model runs"}
    write(root / "admission.json", json.dumps(evidence, indent=1) + "\n")
    return evidence


# ---- the rest of the package -----------------------------------------------------------------------------------

def write_adapters(out):
    for name, config in ADAPTERS.items():
        agent = out / "adapters" / name
        write(agent / "config.json", json.dumps(config, indent=1) + "\n")
        shutil.copyfile(SUBJECT / "agent" / "run_agent.py", agent / "run_agent.py")
        text = "Stock calendar-operations agent: one Claude session with Read, Write, Edit, Bash, Glob and Grep"
        text += ", the `booking-rules` skill loaded as a plugin from `booking-rules/`." if config["skills"] else ", no skill. It runs with the same settings isolation as the skill arm, so the two differ only in the skill."
        write(agent / "README.md", text + f" Model `{config['model']}` at `{config['effort']}` effort; `config.json` holds the settings and `python run_agent.py --print-command ...` shows the call without making it.\n")
        if config["skills"]:
            shutil.copytree(SUBJECT / "booking-rules", agent / "booking-rules", ignore=shutil.ignore_patterns("__pycache__"))


def write_package(out, docs, evidence, notes, split, offline):
    tasks, families, groups = len(docs), sorted({d["family"] for d in docs}), sorted({d["source_group"] for d in docs})
    suite = json.loads((SRC / "suite.json").read_text(encoding="utf-8"))
    suite.update(repeats=REPEATS, concurrency=CONCURRENCY, launch_budget=tasks * REPEATS + 8)
    write(out / "suite.json", json.dumps(suite, indent=1) + "\n")
    card = json.loads((SRC / "card.json").read_text(encoding="utf-8"))
    expected = sum(e["random_expected_credit"] for e in evidence) / tasks
    for claim in card["claims"]:
        if claim.get("metric") == "trivial_credit":
            claim["max"] = max(claim["max"], round(2 * expected + 0.005, 2))
    card["coverage"] = {"tasks": tasks, "families": {f: sum(d["family"] == f for d in docs) for f in families},
                        "source_groups": {g: sum(d["source_group"] == g for d in docs) for g in groups},
                        "infeasible_tasks": sum(not e["valid_starts"] for e in evidence), "split": split,
                        "defects_exercised_on_tasks": {name: sum(e["defects_exercised"][name] >= 0.5 for e in evidence) for name in defects.DEFECTS},
                        "expected_credit_of_a_random_well_formed_booking": round(expected, 4)}
    write(out / "card.json", json.dumps(card, indent=1) + "\n")
    write(out / "README.md", fill((SRC / "README.md").read_text(encoding="utf-8"), TASKS=tasks, FAMILIES=len(families), GROUPS=len(groups),
                                  SPLIT=split, RANDOM=f"{expected:.3f}"))
    shutil.copytree(SRC / "research", out / "research")
    rows = (SRC / "rejections.jsonl").read_text(encoding="utf-8") if offline else ""
    write(out / "rejections.jsonl", rows + "".join(json.dumps(n) + "\n" for n in notes))
    write_adapters(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instances", required=True, help="offline, or a folder of workspace files")
    parser.add_argument("--out", required=True)
    parser.add_argument("--split", choices=("development", "held-out"), default="development")
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--only", default=None, help="comma-separated task ids to keep")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty")
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    docs, notes, offline = read_instances(args.instances, args.limit, seed)
    if args.only:
        docs = [d for d in docs if d["id"] in args.only.split(",")]
        if not docs:
            raise SystemExit(f"no task matches --only {args.only}")
    evidence = [admit(out, doc, write_task(out, doc, args.split)) for doc in docs]
    write_package(out, docs, evidence, notes, args.split, offline)
    print(f"wrote {len(docs)} tasks to {out}")


if __name__ == "__main__":
    main()
