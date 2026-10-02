"""Writes the schedule-nosolver reference benchmark package: a hand-built, known-good delivery for the meta-task.

    python generate.py --instances offline|DIR --out PKG [--split development|held-out] [--limit N] [--seed S] [--only IDS]

`offline` uses the committed synthetic instances in offline-instances/. DIR holds instance files (JSON with an
`instance` key, as in offline-instances/) and/or Natural Plan's calendar_scheduling.json, which is converted with
metabench; at most --limit of a real file's records are taken, chosen by --seed. The package gets tasks/,
admission/, suite.json, card.json, README.md, research/, rejections.jsonl and adapters/, but no kit: assemble it by
copying scripts/benchkit and scripts/run.py of the Benchmaker skill into it. Verifiers and references are the files
in sources/task/; they are written from the public interface alone and import nothing from metabench.
"""
import argparse
import importlib.util
import json
import random
import secrets
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"
BB = HERE.parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


defects = load(SRC / "defects.py", "schedule_defects")
oracle = load(SRC / "task" / "solve.py", "reference_solve")
verifier = load(SRC / "task" / "verify.py", "reference_verify")

ADAPTERS = {"haiku-low": {"model": "claude-haiku-4-5", "effort": "low"}, "sonnet-low": {"model": "claude-sonnet-5-5", "effort": "low"}}
PHRASE = {"earliest": "at the earliest possible time", "latest": "at the latest possible time", "any": "at any time that works"}
REPEATS, CONCURRENCY = 3, 8


# ---- instances -------------------------------------------------------------------------------------------------

def read_instances(source, limit, seed):
    if source == "offline":
        files = sorted((HERE / "offline-instances").glob("*.json"))
        return [json.loads(f.read_text(encoding="utf-8")) for f in files], [], True
    folder, docs, notes = Path(source), [], []
    for f in sorted(folder.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "instance" in data:
            docs.append(data)
        elif f.name == "calendar_scheduling.json":
            sys.path.insert(0, str(BB))
            from metabench.domains import scheduling_naturalplan as natural_plan
            instances = natural_plan.load_instances(f)
            chosen = random.Random(seed).sample(sorted(instances), min(limit, len(instances)))
            notes.append({"candidate": f.name, "disposition": "sampled",
                          "reason": f"{len(chosen)} of {len(instances)} records chosen at random with seed {seed}"})
            for record_id in chosen:
                inst = instances[record_id]
                people = sum(p.get("required", True) for p in inst["participants"])
                docs.append({"id": "np-" + record_id.rsplit("_", 1)[-1], "family": f"natural-plan-{people}-people",
                             "source_group": f"natural-plan-{people}p", "title": f"Natural Plan calendar scheduling {record_id.rsplit('_', 1)[-1]}",
                             "difficulty": "Generated from Natural Plan's calendar scheduling templates: several calendars over a week, day-specific preferences",
                             "expert_minutes": 6, "instance": inst})
    if not docs:
        raise SystemExit(f"no instances found in {folder}")
    for number, doc in enumerate(docs):
        doc.setdefault("smoke", number == 0)
        doc.setdefault("quick", number % 4 == 0)
    return docs, notes, False


def pretty(value, depth=0):
    """JSON with one line per small object, so an interval or a work-hours entry is not spread over many lines."""
    flat = json.dumps(value)
    if not isinstance(value, (dict, list)) or len(flat) <= 100 or not any(isinstance(v, (dict, list)) for v in (value.values() if isinstance(value, dict) else value)):
        return flat
    pad, inner = " " * depth, " " * (depth + 1)
    if isinstance(value, dict):
        rows = [f"{inner}{json.dumps(k)}: {pretty(v, depth + 1)}" for k, v in value.items()]
        return "{\n" + ",\n".join(rows) + "\n" + pad + "}"
    return "[\n" + ",\n".join(inner + pretty(v, depth + 1) for v in value) + "\n" + pad + "]"


def request_line(doc):
    inst = doc["instance"]
    required = [p["id"] for p in inst["participants"] if p.get("required", True)]
    optional = [p["id"] for p in inst["participants"] if not p.get("required", True)]
    who = ", ".join(required[:-1]) + (" and " if len(required) > 1 else "") + required[-1]
    extra = f" ({', '.join(optional)} {'is' if len(optional) == 1 else 'are'} invited but optional)" if optional else ""
    return (f"Schedule a {inst['duration_minutes']}-minute meeting for {who}{extra}, {PHRASE[inst['preference']]}, "
            f"between {inst['window']['start']} and {inst['window']['end']}.")


def fill(text, **values):
    for key, value in values.items():
        text = text.replace(f"<<{key}>>", str(value))
    return text


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)


# ---- tasks and admission ---------------------------------------------------------------------------------------

def write_task(out, doc, split):
    task = out / "tasks" / doc["id"]
    inst = doc["instance"]
    write(task / "instruction.md", fill((SRC / "task" / "instruction.md").read_text(encoding="utf-8"),
                                        TITLE=doc["title"], REQUEST=request_line(doc)))
    write(task / "task.toml", fill((SRC / "task" / "task.toml").read_text(encoding="utf-8"),
          FAMILY=json.dumps(doc["family"]), GROUP=json.dumps(doc["source_group"]), SPLIT=json.dumps(split),
          SMOKE=str(doc["smoke"]).lower(), QUICK=str(doc["quick"]).lower(), DIFFICULTY=json.dumps(doc["difficulty"]),
          MINUTES=doc["expert_minutes"]))
    write(task / "environment" / "input.json", pretty(inst) + "\n")
    for folder, name in (("solution", "solve.py"), ("tests", "verify.py")):
        (task / folder).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SRC / "task" / name, task / folder / name)
    return task


def grade(inst, raw):
    """The verifier's (full_success, credit) for the bytes of an output.json."""
    valid, optimal, _ = verifier.grade(verifier.Request(inst), raw)
    credit = verifier.WEIGHTS["valid"] * valid + verifier.WEIGHTS["optimal"] * optimal
    return bool(valid and optimal), credit


def admit(out, doc, task):
    """admission/<id>/: labelled outputs as final workspaces, labels.json and the evidence record."""
    inst, root = doc["instance"], out / "admission" / doc["id"]
    found = oracle.valid_starts(inst)
    items = defects.labeled(oracle, inst)
    labels, agree = {}, {"valid": [0, 0], "suboptimal": [0, 0], "invalid": [0, 0]}
    for number, (kind, label, raw) in enumerate(items, 1):
        sub = f"{number:02d}-{kind.replace(':', '-')}"
        write(root / "labeled" / sub / "input.json", (task / "environment" / "input.json").read_bytes())
        write(root / "labeled" / sub / "output.json", raw)
        labels[sub] = {"label": label, "kind": kind}
        full, _ = grade(inst, raw)
        agree[label][0] += full == (label == "valid")
        agree[label][1] += 1
    mismatched = {k: v for k, v in agree.items() if v[0] != v[1]}
    if mismatched:
        raise SystemExit(f"{doc['id']}: the verifier disagrees with the reference's labels: {mismatched}")
    write(root / "labels.json", json.dumps(labels, indent=1) + "\n")
    reference = oracle.solve(inst)
    full, credit = grade(inst, json.dumps(reference).encode())
    if not full:
        raise SystemExit(f"{doc['id']}: the reference does not pass its own verifier")
    rooms, grid = len(inst.get("rooms", [])), defects_grid(inst)
    chance = lambda picks: sum((len(r) / rooms if rooms else 1) for _, r in picks) / grid  # noqa: E731
    best = {"earliest": found[:1], "latest": found[-1:]}.get(inst["preference"], found)
    weights = verifier.WEIGHTS
    expected = weights["valid"] * chance(found) + weights["optimal"] * chance(best)
    exercised = {name: defects.exercised(oracle, inst, name, range(3)) for name in defects.DEFECTS}
    evidence = {"task": doc["id"], "valid_starts": len(found), "grid_starts": grid, "random_valid_probability": round(chance(found), 4),
                "random_expected_credit": round(expected, 4),
                "noop_credit": grade(inst, b"")[1], "empty_output_credit": grade(inst, b"{}")[1],
                "labeled": {k: v[1] for k, v in agree.items()}, "defects_exercised": {k: round(v, 2) for k, v in exercised.items()},
                "criteria": {"realistic": "reconstructed or synthetic: authored from the interface and the Natural Plan scenario style; no logged requests",
                             "solvable": "pass: solution/solve.py output graded full success by tests/verify.py",
                             "unearned-by-inaction": "pass: no output and an empty object earn credit 0; a random well-formed slot is valid with the probability above",
                             "fairly-graded": "pass: every labelled output (valid variants, valid-not-optimal and invalid) graded as labelled; labels come from the reference, not the verifier",
                             "specified": "not run: no fresh auditor in a zero-cost build",
                             "shortcut-resistant": "not run: no adversary in a zero-cost build; solver workspaces hold input.json only",
                             "calibrated": "not run: no calibration system was attempted",
                             "hard-for-the-right-reason": "not run: no failure transcripts"},
                "disposition": "draft", "reason": "criteria 4 and 6 to 8 need model runs"}
    write(root / "admission.json", json.dumps(evidence, indent=1) + "\n")
    return evidence


def defects_grid(inst):
    m = oracle.read(inst)
    return int((m["hi"] - m["lo"] - m["duration"]) / m["step"]) + 1


# ---- the rest of the package -----------------------------------------------------------------------------------

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
    feasible = [e for e in evidence if e["valid_starts"]]
    card["coverage"] = {"tasks": tasks, "families": {f: sum(d["family"] == f for d in docs) for f in families},
                        "source_groups": {g: sum(d["source_group"] == g for d in docs) for g in groups},
                        "infeasible_tasks": tasks - len(feasible), "split": split,
                        "defects_exercised_on_tasks": {name: sum(e["defects_exercised"][name] >= 0.5 for e in evidence) for name in defects.DEFECTS},
                        "expected_credit_of_a_random_well_formed_slot": round(expected, 4)}
    write(out / "card.json", json.dumps(card, indent=1) + "\n")
    readme = fill((SRC / "README.md").read_text(encoding="utf-8"), TASKS=tasks, FAMILIES=len(families), GROUPS=len(groups), SPLIT=split,
                  RANDOM=f"{expected:.3f}")
    write(out / "README.md", readme)
    shutil.copytree(SRC / "research", out / "research")
    rows = (SRC / "rejections.jsonl").read_text(encoding="utf-8") if offline else ""
    write(out / "rejections.jsonl", rows + "".join(json.dumps(n) + "\n" for n in notes))
    for name, config in ADAPTERS.items():
        write(out / "adapters" / name / "config.json", json.dumps(config, indent=1) + "\n")
        shutil.copyfile(SRC / "adapters" / "run_agent.py", out / "adapters" / name / "run_agent.py")
        write(out / "adapters" / name / "README.md", f"Stock scheduling assistant: one Claude call with no tools, `{config['model']}` at `{config['effort']}` effort. Settings are in `config.json`; `python run_agent.py --print-command ...` shows the call without making it.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instances", required=True, help="offline, or a folder of instance files")
    parser.add_argument("--out", required=True)
    parser.add_argument("--split", choices=("development", "held-out"), default="development")
    parser.add_argument("--limit", type=int, default=24)
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
    evidence = []
    for doc in docs:
        task = write_task(out, doc, args.split)
        evidence.append(admit(out, doc, task))
    write_package(out, docs, evidence, notes, args.split, offline)
    print(f"wrote {len(docs)} tasks to {out}")


if __name__ == "__main__":
    main()
