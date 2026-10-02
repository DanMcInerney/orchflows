"""Write the logtriage-llm reference package: a known-good benchmark for CI-failure triage, in the kit's format.

    python generate.py --instances offline|DIR --out PACKAGE [--tasks N] [--per-repo K] [--seed S]
                       [--split development|held-out] [--date YYYY-MM-DD]

`--instances offline` reads the committed synthetic logs in `offline-instances/`; a directory reads LogChunks-layout
material (`build-failure-reason/<language>/<owner@repo>.xml` and `logs/`), such as the `public/` or `held-out/` folder
the metabench material step writes. Every candidate goes through an admission screen; admitted candidates are
selected (all of them offline, a seeded stratified draw otherwise) and written as tasks. Everything except the
kit (`run.py`, `benchkit/`) is written; the kit is copied in separately. Nothing here imports the meta-verifier.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from string import Template

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lc          # noqa: E402
import outcomes    # noqa: E402

SOURCES = HERE / "sources"
OFFLINE = HERE / "offline-instances"
SUBJECT = HERE.parents[1] / "meta-tasks" / "logtriage-llm" / "subject" / "agent"
AGENT_FILES = ("run_agent.py", "prompt.md", "README.md", "config.json")
MAX_OCCURRENCES = 5
OWNED = ("tasks", "admission", "adapters", "research")
PUBLIC_DEFAULT_TASKS = 24


def load_verifier():
    spec = importlib.util.spec_from_file_location("logtriage_verify", SOURCES / "verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- screen and selection

def screen(entry: dict, args) -> dict:
    """The entry with `lines` and `spans`, or with `reject`: the reason it cannot be a task."""
    def reject(reason):
        return {**entry, "reject": reason}

    text, why = lc.read_log(entry["path"])
    if text is None:
        return reject(why)
    size = entry["path"].stat().st_size
    lines = lc.split_lines(text)
    n = len(lines)
    if size > args.max_bytes or n > args.max_lines:
        return reject(f"{n} lines and {size} bytes exceed the limits of {args.max_lines} lines and {args.max_bytes} bytes")
    spans = lc.chunk_spans(lines, entry["chunk"])
    if not spans:
        return reject(f"the label text is not found in the log, or holds fewer than {lc.MIN_KEY} letters and digits")
    if len(spans) > MAX_OCCURRENCES:
        return reject(f"ambiguous: the marked text occurs {len(spans)} times, more than {MAX_OCCURRENCES}")
    for name, span in (("a range of the whole log", (1, n)), ("a range of the whole log minus its first line", (2, n)),
                       ("a range of the whole log minus its last line", (1, n - 1)), ("the instruction's example range", outcomes.EXAMPLE)):
        if 1 <= span[0] <= span[1] <= n and outcomes.expected_grade(*span, spans, n)[1] > 0:
            return reject(f"trivial: {name} earns credit ({n} lines, marked failure {spans[0][1] - spans[0][0] + 1} lines)")
    if outcomes.expected_grade(*outcomes.heuristics(lines)["tail_50"], spans, n)[0]:
        return reject("trivial: the last 50 lines already count as correct")
    return {**entry, "lines": lines, "spans": spans, "bytes": size, "reject": None}


def select(admitted: list[dict], args, *, limit: int | None) -> list[dict]:
    admitted = sorted(admitted, key=lambda e: e["log"])
    if limit is None:
        return admitted
    rng = random.Random(args.seed)
    groups: dict[str, list[dict]] = {}
    for entry in admitted:
        groups.setdefault(entry["group"], []).append(entry)
    order = list(groups)
    rng.shuffle(order)
    for items in groups.values():
        rng.shuffle(items)
    chosen = []
    for rank in range(args.per_repo):
        for group in order:
            if len(chosen) < limit and rank < len(groups[group]):
                chosen.append(groups[group][rank])
    return sorted(chosen, key=lambda e: e["log"])


def flags(tasks: list[dict]) -> None:
    """quick: the first task of each source group (at most 8); smoke: two of those with different families."""
    seen, quick = set(), []
    for task in tasks:
        if task["group"] not in seen and len(quick) < 8:
            seen.add(task["group"])
            quick.append(task)
    smoke = []
    for task in quick:
        if len(smoke) < 2 and task["family"] not in {t["family"] for t in smoke}:
            smoke.append(task)
    smoke += [t for t in quick if t not in smoke][:2 - len(smoke)]
    for task in tasks:
        task["quick"], task["smoke"] = task in quick, task in smoke


# ---------------------------------------------------------------- one task

def toml_str(value) -> str:
    return json.dumps(" ".join(str(value).split()), ensure_ascii=False)


def difficulty(item: dict, meta: dict) -> str:
    if meta.get("difficulty"):
        return meta["difficulty"]
    n, (s, e) = len(item["lines"]), item["spans"][0]
    text = f"Real Travis CI log of {n} lines; the marked failure is {e - s + 1} line(s) at {s}-{e}, {n - e} lines before the end."
    first = outcomes.heuristics(item["lines"])["grep_first_error"]
    if outcomes.expected_grade(*first, item["spans"], n)[1] == 0:
        text += " The first line matching error, fail or exception lies outside the failure."
    return text


def write_task(pkg: Path, tid: str, item: dict, meta: dict, synthetic: bool, split: str) -> None:
    task = pkg / "tasks" / tid
    for sub in ("environment", "solution", "tests"):
        (task / sub).mkdir(parents=True)
    shutil.copyfile(item["path"], task / "environment" / "build.log")
    shutil.copyfile(SOURCES / "instruction.md", task / "instruction.md")
    shutil.copyfile(SOURCES / "solve.py", task / "solution" / "solve.py")
    shutil.copyfile(SOURCES / "verify.py", task / "tests" / "verify.py")
    expected = {"spans": [list(span) for span in item["spans"]], "chunk": item["chunk"], "source_log": item["log"]}
    (task / "tests" / "expected.json").write_text(json.dumps(expected, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    minutes = meta.get("expert_minutes") or max(1, round(1 + len(item["lines"]) / 800))
    provenance = "synthetic (invented repository and log in the byte format of Travis logs)" if synthetic else \
        "real Travis CI log from LogChunks (Brandt, Panichella, Beller 2020), CC BY 4.0"
    (task / "task.toml").write_text(
        "[metadata]\n"
        f"family = {toml_str(item['family'])}\nsource_group = {toml_str(item['group'])}\nsplit = {toml_str(split)}\nanchor = false\n"
        f"smoke = {str(item['smoke']).lower()}\nquick = {str(item['quick']).lower()}\n"
        f"difficulty = {toml_str(difficulty(item, meta))}\nexpert_minutes = {minutes}\ntime_estimate = \"author\"\n"
        f"language = {toml_str(item['language'])}\nprovenance = {toml_str(provenance)}\nsource_log = {toml_str(item['log'])}\n\n"
        f"[agent]\ntimeout_sec = {120 if item['bytes'] <= 150_000 else 180}\n\n[verifier]\ntimeout_sec = 30\n", encoding="utf-8", newline="\n")


def run_verifier(task: Path, workspace: Path) -> dict:
    result = workspace.parent / f"{workspace.name}-result.json"
    done = subprocess.run([sys.executable, str(task / "tests" / "verify.py"), "--task", str(task), "--workspace", str(workspace), "--result", str(result)],
                          cwd=task, capture_output=True, text=True, timeout=60)
    if done.returncode:
        raise SystemExit(f"{task.name}: verifier failed: {done.stderr.strip()[-400:]}")
    return json.loads(result.read_text(encoding="utf-8"))


def reference_evidence(task: Path) -> tuple[dict, dict]:
    """Grades of the reference solution and of a solver that delivers nothing, each in a staged copy of the workspace."""
    with tempfile.TemporaryDirectory(prefix="logtriage-gen-") as tmp:
        ref, empty = Path(tmp) / "ref", Path(tmp) / "empty"
        shutil.copytree(task / "environment", ref)
        shutil.copytree(task / "environment", empty)
        done = subprocess.run([sys.executable, str(task / "solution" / "solve.py"), "--workspace", str(ref)], cwd=ref, capture_output=True, text=True, timeout=60)
        if done.returncode:
            raise SystemExit(f"{task.name}: reference failed: {done.stderr.strip()[-400:]}")
        return run_verifier(task, ref), run_verifier(task, empty)


def write_admission(pkg: Path, tid: str, item: dict, synthetic: bool, verifier, date: str) -> dict:
    task, folder = pkg / "tasks" / tid, pkg / "admission" / tid
    expected = json.loads((task / "tests" / "expected.json").read_text(encoding="utf-8"))
    n = len(item["lines"])
    rows = outcomes.labeled_outcomes(item["lines"], item["spans"], "The build failed; see the selected lines.")
    labels, problems = {}, []
    for number, row in enumerate(rows, 1):
        name = f"s{number:02d}-{row['kind']}"
        target = folder / "labeled" / name
        target.mkdir(parents=True)
        raw = row["files"].get("triage.json")
        if raw is not None:
            (target / "triage.json").write_bytes(raw)
        got = verifier.grade(expected, n, raw)
        if got["full_success"] != row["accept"] or abs(got["credit"] - row["credit"]) > 1e-6:
            problems.append(f"{name}: verifier gave full_success {got['full_success']} credit {got['credit']:.4f}, rule says {row['accept']} {row['credit']:.4f}")
        labels[name] = {"kind": row["kind"], "label": "valid" if row["accept"] else "invalid", "accept": row["accept"], "credit": row["credit"]}
    if problems:
        raise SystemExit(f"{tid}: verifier and documented rule disagree:\n  " + "\n  ".join(problems))
    (folder / "labels.json").write_text(json.dumps(labels, indent=1) + "\n", encoding="utf-8", newline="\n")
    ref, empty = reference_evidence(task)
    idle = [labels[k] for k in labels if labels[k]["kind"] in ("missing-file", "empty-file", "whole-log", "whole-log-minus-first-line",
                                                               "whole-log-minus-last-line", "instruction-example")]
    if not ref["full_success"] or ref["credit"] != 1.0 or empty["credit"] != 0.0 or any(x["credit"] or x["accept"] for x in idle):
        raise SystemExit(f"{tid}: reference or trivial attempts are not graded as required: {ref['credit']} {empty['credit']}")
    valid = sum(x["accept"] for x in labels.values())
    done = lambda outcome, evidence: {"outcome": outcome, "evidence": evidence, "date": date}
    pending = lambda why: done("not-run", why)
    heur = {name: {"range": list(span), "full_success": outcomes.expected_grade(*span, item["spans"], n)[0],
                   "credit": outcomes.expected_grade(*span, item["spans"], n)[1]} for name, span in outcomes.heuristics(item["lines"]).items()}
    admission = {"task": tid, "source_log": item["log"], "disposition": "draft: admission incomplete", "criteria": {
        "realistic": done("synthetic" if synthetic else "real", "an invented log in the byte format of real Travis logs; no fresh reviewer compared it with the catalog" if synthetic
                          else "a real Travis CI log with a human-marked failure chunk (LogChunks)"),
        "solvable": done("pass", f"solution/solve.py run in a staged workspace is graded full success, credit {ref['credit']}"),
        "unearned_by_inaction": done("pass", "a missing file, an empty file, the whole log, the whole log minus an edge and the instruction's example range each earn credit 0; "
                                             f"@noop-style delivery graded credit {empty['credit']}"),
        "specified": pending("no fresh auditor solved from the public material"),
        "fairly_graded": done("pass", f"{len(labels)} labeled outcomes ({valid} accepted by the rule, {len(labels) - valid} not) graded by verify.py agree with the rule restated over sets"),
        "shortcut_resistant": pending("no adversary attempted the task"),
        "calibrated": pending("no calibration system attempted the task"),
        "hard_for_the_right_reason": pending("no failure transcripts exist; the known-order check has not run")},
        "scripted_baselines": heur, "labeled_outcomes": len(labels)}
    (folder / "admission.json").write_text(json.dumps(admission, indent=1) + "\n", encoding="utf-8", newline="\n")
    return admission


# ---------------------------------------------------------------- package-level files

def table(header: list[str], rows: list[list]) -> str:
    cell = lambda value: str(value).replace("|", "\\|")
    return "\n".join(["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"] +
                     ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows])


def baselines(tasks: list[dict]) -> tuple[str, dict]:
    names = {"tail_50": "last 50 lines", "grep_first_error": "5 lines around the first error-like line", "grep_last_error": "5 lines around the last error-like line"}
    stats = {key: [outcomes.expected_grade(*outcomes.heuristics(t["lines"])[key], t["spans"], len(t["lines"])) for t in tasks] for key in names}
    shifted = []
    for t in tasks:
        s, e = t["spans"][0]
        n = len(t["lines"])
        span = (e + 1, min(n, e + (e - s + 1))) if e < n else (max(1, s - (e - s + 1)), s - 1)
        shifted.append(outcomes.expected_grade(*span, t["spans"], n))
    stats["shifted"], names["shifted"] = shifted, "the marked range moved past its own length"
    stats["whole_log"] = [outcomes.expected_grade(1, len(t["lines"]), t["spans"], len(t["lines"])) for t in tasks]
    names["whole_log"] = "the whole log"
    count = len(tasks)
    rows = [[names[k], f"{sum(f for f, _ in v)} of {count}", f"{sum(c for _, c in v) / count:.3f}", f"{sum(1 for f, _ in v if not f)} of {count}"] for k, v in stats.items()]
    summary = {k: {"full_success_tasks": sum(f for f, _ in v), "mean_credit": round(sum(c for _, c in v) / count, 4), "wrong_tasks": sum(1 for f, _ in v if not f)} for k, v in stats.items()}
    rng, draws = random.Random(0), 60
    guesses = []
    for t in tasks:
        n = len(t["lines"])
        got = [outcomes.expected_grade(*sorted((rng.randint(1, n), rng.randint(1, n))), t["spans"], n) for _ in range(draws)]
        guesses.append((sum(f for f, _ in got) / draws, sum(c for _, c in got) / draws))
    rate, credit = sum(f for f, _ in guesses) / count, sum(c for _, c in guesses) / count
    rows.append(["a random valid range", f"{rate:.1%} of {draws * count} draws", f"{credit:.3f}", "n/a"])
    summary["random_range"] = {"full_success_share": round(rate, 4), "mean_credit": round(credit, 4), "draws": draws * count}
    return table(["Script", "Full success", "Mean credit", "Wrong on"], rows), summary


def write_files(pkg: Path, tasks: list[dict], metas: dict, rejections: list[dict], kind: str, date: str, split: str) -> None:
    count, groups = len(tasks), sorted({t["group"] for t in tasks})
    synthetic = sum(1 for t in tasks if metas.get(t["log"]))
    base_table, base_stats = baselines(tasks)
    exposure = ("The logs are invented, so no model has seen them, but they imitate public Travis logs and tool output that models have seen; no reviewer compared them with real logs."
                if synthetic == count else
                "LogChunks has been public since 2020: models may have seen these logs and labels, so scores on them can overstate performance on unseen logs.")
    rows = [[t["id"], t["group"], t["language"], t["family"], len(t["lines"]), f"{t['spans'][0][1] - t['spans'][0][0] + 1} at {t['spans'][0][0]}",
             difficulty(t, metas.get(t["log"], {}))] for t in tasks]
    tasks_table = table(["Task", "Source group", "Language", "Family", "Lines", "Marked lines", "Why it is hard"], rows)
    source = ("The logs are synthetic: invented repositories and logs written to imitate real Travis CI logs (format, tools, failure patterns), labelled the way LogChunks labels real ones. "
              "They exist so the package can be built and checked offline; `generate.py --instances <dir>` builds the same package from real LogChunks logs."
              if synthetic == count else
              "The logs are real Travis CI logs from LogChunks (Brandt, Panichella, Beller 2020, https://doi.org/10.5281/zenodo.3632351, CC BY 4.0), unchanged, with the marked failure text located in each.")
    suite = json.loads((SOURCES / "suite.json").read_text(encoding="utf-8"))
    suite.update(name=f"logtriage-{kind}", launch_budget=suite["repeats"] * count + 12)
    (pkg / "suite.json").write_text(json.dumps(suite, indent=1) + "\n", encoding="utf-8", newline="\n")
    card = json.loads((SOURCES / "card.json").read_text(encoding="utf-8"))
    card = {"name": f"logtriage-{kind}", **card}
    card["realism"] = {"real": count - synthetic, "reconstructed": 0, "synthetic": synthetic,
                       "review": "none: no fresh reviewer has judged the synthetic logs against the research catalog" if synthetic else "not applicable: real logs"}
    families: dict[str, int] = {}
    for t in tasks:
        families[t["family"]] = families.get(t["family"], 0) + 1
    card["coverage"] = {"tasks": count, "source_groups": len(groups), "languages": sorted({t["language"] for t in tasks}), "families": families, "split": split,
                        "expert_minutes": "author estimates in task.toml"}
    card["scripted_baselines"] = {"note": "computed from the labels with the documented rule; no model", **base_stats}
    card["claims"] = card["claims"] + [{"id": "g3", "type": "gap", "category": "exposure", "text": exposure}]
    (pkg / "card.json").write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    fill = dict(name=f"logtriage-{kind}", n_tasks=count, n_groups=len(groups), source_paragraph=source, launch_budget=suite["launch_budget"],
                families_table=tasks_table, baselines_table=base_table, exposure_note=exposure)
    (pkg / "README.md").write_text(Template((SOURCES / "README.md").read_text(encoding="utf-8")).safe_substitute(fill), encoding="utf-8", newline="\n")
    (pkg / "research").mkdir(parents=True, exist_ok=True)
    coverage = "## Coverage\n\nTasks in this build and the scenario each samples.\n\n" + tasks_table
    (pkg / "research" / "catalog.md").write_text(Template((SOURCES / "research" / "catalog.md").read_text(encoding="utf-8")).safe_substitute(coverage=coverage),
                                                 encoding="utf-8", newline="\n")
    with (pkg / "rejections.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for row in rejections:
            out.write(json.dumps({**row, "date": date}, ensure_ascii=False) + "\n")
    for name, config in (("haiku-low", None), ("sonnet-low", {"model": "claude-sonnet-5-5", "effort": "low"})):
        target = pkg / "adapters" / name
        target.mkdir(parents=True)
        for file in AGENT_FILES:
            if not (SUBJECT / file).is_file():
                raise SystemExit(f"the supplied agent is missing: {SUBJECT / file}")
            shutil.copyfile(SUBJECT / file, target / file)
        if config:
            (target / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instances", required=True, help="offline, or a directory in the LogChunks layout")
    parser.add_argument("--out", required=True)
    parser.add_argument("--tasks", type=int, help=f"tasks to draw (offline: all admitted; otherwise {PUBLIC_DEFAULT_TASKS})")
    parser.add_argument("--per-repo", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--split", choices=("development", "held-out"), default="development")
    parser.add_argument("--max-bytes", type=int, default=400_000)
    parser.add_argument("--max-lines", type=int, default=15_000)
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args(argv)
    offline = args.instances == "offline"
    root = lc.find_root(OFFLINE if offline else Path(args.instances))
    metas = json.loads((root / "instances.json").read_text(encoding="utf-8")) if (root / "instances.json").is_file() else {}
    screened = [screen(entry, args) for entry in lc.load_entries(root)]
    admitted = [s for s in screened if not s["reject"]]
    for item in admitted:
        meta = metas.get(item["log"], {})
        item["family"] = meta.get("family") or lc.guess_family(item["chunk"])
    chosen = select(admitted, args, limit=args.tasks if args.tasks else (None if offline else PUBLIC_DEFAULT_TASKS))
    if not chosen:
        raise SystemExit("no candidate passed the admission screen")
    flags(chosen)
    pkg = Path(args.out)
    pkg.mkdir(parents=True, exist_ok=True)
    for name in OWNED:
        shutil.rmtree(pkg / name, ignore_errors=True)
    verifier = load_verifier()
    chosen_logs = {t["log"] for t in chosen}
    rejections = []
    for index, item in enumerate(chosen, 1):
        item["id"] = f"t{index:02d}"
    ids = {t["log"]: t["id"] for t in chosen}
    for s in screened:
        disposition = "rejected" if s["reject"] else "admitted" if s["log"] in chosen_logs else "not-selected"
        rejections.append({"candidate": s["log"], "source_group": s["group"], "disposition": disposition, "task": ids.get(s["log"]),
                           "reason": s["reject"] or ("passed the admission screen" if disposition == "admitted" else "passed the screen; the stratified draw did not select it")})
    split = args.split
    for item in chosen:
        meta = metas.get(item["log"], {})
        write_task(pkg, item["id"], item, meta, bool(meta), split)
        write_admission(pkg, item["id"], item, bool(meta), verifier, args.date)
    write_files(pkg, chosen, metas, rejections, "offline" if offline else f"{split}", args.date, split)
    print(f"wrote {len(chosen)} tasks ({len(admitted)} admitted of {len(screened)} candidates) to {pkg}")


if __name__ == "__main__":
    main()
