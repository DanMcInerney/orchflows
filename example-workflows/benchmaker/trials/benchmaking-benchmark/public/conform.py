"""Conformance check for a delivered benchmark package: python conform.py <package> [--timeout SECONDS].

Standard library only, with no imports from the kit or from metabench: its shape checks are its own copy of what
benchkit/INTERFACE.md documents. It validates the package layout, `suite.json`, every `task.toml` and the card's
claims, runs `preflight`, a `smoke` run with an embedded no-op agent, a `full` run with `@reference`, and `grade`
on the reference run's captured workspaces, validates every record those commands wrote, and prints one JSON
report: {"package", "pass", "checks": [{"name", "passed", "detail"}], "commands": [...]}. Exit code 0 means pass.
It makes no model calls; it does not judge quality, only that the package runs and writes the documented shapes.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

STATUSES = ("completed", "refused", "cut-off", "agent-budget-exhausted", "infrastructure-error", "canceled",
            "interrupted", "not-launched")
SCORED = ("completed", "refused", "cut-off", "agent-budget-exhausted")
GRADINGS = ("scored", "indeterminate", "unscored")
SPLITS = ("development", "held-out")
ESTIMATES = ("measured", "author")
PRIMARY = ("full_success_rate", "mean_credit")
PROFILES = ("smoke", "quick", "full")
GAP_CATEGORIES = ("hackable-task", "unresolved-contrast", "inert-dimension", "verifier-false-reject",
                  "verifier-false-accept", "floor", "ceiling", "unprotected-boundary", "exposure", "missing-stage")
SUMMARY_KEYS = {
    "suite": ("name", "tasks"),
    "run": ("profile", "agent", "repeats", "jobs", "started", "finished", "wall_seconds", "attempt_seconds_sum",
            "achieved_overlap", "peak_concurrency", "deadline_reached", "observed_versions"),
    "counts": ("planned", "launched", "completed", "scored", "passed", "failed", "unscored", "canceled",
               "not_launched", "retries", "by_status"),
    "overall": ("full_success_rate", "mean_credit", "credit_bounds", "critical_failures", "scored_tasks",
                "missing_repeats", "anchors_excluded"),
    "cost": ("usd_known", "attempts_with_unknown_cost"),
    "time": ("setup_seconds", "execution_seconds", "grading_seconds", "total_seconds"),
}
TASK_KEYS = ("family", "source_group", "anchor", "planned", "scored", "full_success_rate", "mean_credit",
             "critical_failures", "statuses")
NOOP_AGENT = '''import argparse
import json

parser = argparse.ArgumentParser()
for name in ("workspace", "prompt-file", "transcript", "timeout"):
    parser.add_argument("--" + name, required=True)
parser.parse_args()
print(json.dumps({"status": "completed", "exit_code": 0, "seconds": 0.0, "model": None, "cost_usd": 0.0, "final": ""}))
'''


# ---- shapes -----------------------------------------------------------------------------------------

def number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def integer(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def text(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def unit(x) -> bool:
    return number(x) and 0 <= x <= 1


def need(problems, where, doc, key, test, expect, *, optional=False, nullable=False) -> bool:
    if key not in doc:
        if not optional:
            problems.append(f"{where}: missing {key!r}")
        return False
    if doc[key] is None and nullable:
        return True
    if not test(doc[key]):
        problems.append(f"{where}: {key!r} must be {expect}")
        return False
    return True


def suite_problems(doc, where="suite.json") -> list[str]:
    if not isinstance(doc, dict):
        return [f"{where}: must be a JSON object"]
    p = []
    need(p, where, doc, "name", text, "a non-empty string")
    need(p, where, doc, "repeats", lambda x: integer(x) and x >= 1, "an integer >= 1")
    need(p, where, doc, "concurrency", lambda x: integer(x) and x >= 1, "an integer >= 1")
    need(p, where, doc, "deadline_seconds", lambda x: number(x) and x > 0, "a positive number", optional=True, nullable=True)
    for key in ("attempt_seconds_estimate", "attempt_cost_estimate_usd", "grace_seconds"):
        need(p, where, doc, key, lambda x: number(x) and x >= 0, "a number >= 0", optional=True, nullable=True)
    need(p, where, doc, "transient_retry_budget", lambda x: integer(x) and x >= 0, "an integer >= 0", optional=True)
    need(p, where, doc, "launch_budget", lambda x: integer(x) and x >= 1, "an integer >= 1", optional=True, nullable=True)
    for key in ("provision", "observe"):
        value = doc.get(key, [])
        if not isinstance(value, list) or not all(isinstance(c, list) and c and all(text(a) for a in c) for c in value):
            p.append(f"{where}: {key!r} must be a list of commands, each a non-empty list of strings")
    if "metrics" in doc:
        if not isinstance(doc["metrics"], dict):
            p.append(f"{where}: 'metrics' must be an object")
        else:
            need(p, f"{where} metrics", doc["metrics"], "primary", lambda x: x in PRIMARY, f"one of {', '.join(PRIMARY)}")
    return p


def task_problems(doc, where="task.toml") -> list[str]:
    if not isinstance(doc, dict):
        return [f"{where}: must be a TOML table"]
    p = []
    meta = doc.get("metadata")
    if not isinstance(meta, dict):
        p.append(f"{where}: missing [metadata]")
    else:
        w = f"{where} [metadata]"
        need(p, w, meta, "family", text, "a non-empty string")
        need(p, w, meta, "source_group", text, "a non-empty string")
        need(p, w, meta, "split", lambda x: x in SPLITS, f"one of {', '.join(SPLITS)}")
        for key in ("anchor", "smoke", "quick"):
            need(p, w, meta, key, lambda x: isinstance(x, bool), "true or false", optional=True)
        need(p, w, meta, "weight", lambda x: number(x) and x >= 0, "a number >= 0", optional=True)
        need(p, w, meta, "difficulty", lambda x: text(x) or number(x), "a rationale string or a number", optional=True)
        need(p, w, meta, "expert_minutes", lambda x: number(x) and x > 0, "a positive number", optional=True)
        need(p, w, meta, "time_estimate", lambda x: x in ESTIMATES, f"one of {', '.join(ESTIMATES)}", optional=True)
    for table, required in (("agent", True), ("verifier", False)):
        section = doc.get(table)
        if section is None and not required:
            continue
        if not isinstance(section, dict):
            p.append(f"{where}: missing [{table}]")
        else:
            need(p, f"{where} [{table}]", section, "timeout_sec", lambda x: number(x) and x > 0, "a positive number",
                 optional=not required)
    return p


def _weighted(dimensions) -> str | None:
    """A violation message for the dimensions of a scored verifier result, or None."""
    weights, credits = [], []
    for name, dim in dimensions.items():
        if not isinstance(dim, dict):
            return f"dimension {name!r} is not an object"
        weight, credit, required = dim.get("weight"), dim.get("credit"), dim.get("required", True)
        if not number(weight) or weight < 0:
            return f"dimension {name!r} weight must be a nonnegative number"
        if credit is not None and not unit(credit):
            return f"dimension {name!r} credit {credit!r} outside [0, 1]"
        if not isinstance(required, bool):
            return f"dimension {name!r} required must be true or false"
        weights.append(weight)
        credits.append(credit)
    if abs(math.fsum(weights) - 1.0) > 1e-6:
        return f"dimension weights sum to {math.fsum(weights):.6g}, not 1"
    return None


def verifier_problems(raw, where="verifier result") -> list[str]:
    if not isinstance(raw, dict):
        return [f"{where}: must be a JSON object"]
    status = raw.get("grading_status")
    if status not in GRADINGS:
        return [f"{where}: 'grading_status' must be one of {', '.join(GRADINGS)}"]
    if status != "scored":
        return [] if text(raw.get("reason")) else [f"{where}: a {status} result needs a 'reason'"]
    full, failures, dimensions, credit = (raw.get("full_success"), raw.get("critical_failures") or [],
                                          raw.get("dimensions") or {}, raw.get("credit"))
    if not isinstance(full, bool):
        return [f"{where}: full_success must be true or false"]
    if not isinstance(failures, list):
        return [f"{where}: critical_failures must be a list"]
    if failures and full:
        return [f"{where}: critical failure with full_success true"]
    if not isinstance(dimensions, dict):
        return [f"{where}: dimensions must be an object"]
    if credit is not None and not unit(credit):
        return [f"{where}: credit {credit!r} outside [0, 1]"]
    if dimensions:
        message = _weighted(dimensions)
        if message:
            return [f"{where}: {message}"]
        derived = [d.get("credit") for d in dimensions.values()]
        if all(c is not None for c in derived):
            total = math.fsum(d["weight"] * d["credit"] for d in dimensions.values())
            if credit is not None and abs(credit - total) > 1e-3:
                return [f"{where}: credit {credit} disagrees with the weighted dimensions ({total:.6g})"]
        elif credit is not None and any(d.get("required", True) and d.get("credit") is None for d in dimensions.values()):
            return [f"{where}: credit given while a required dimension is unjudged"]
    return []


def attempt_problems(row, where="attempt") -> list[str]:
    if not isinstance(row, dict):
        return [f"{where}: must be a JSON object"]
    p = []
    need(p, where, row, "task", text, "a non-empty string")
    need(p, where, row, "repeat", lambda x: integer(x) and x >= 1, "an integer >= 1")
    need(p, where, row, "retry", lambda x: integer(x) and x >= 0, "an integer >= 0")
    need(p, where, row, "status", lambda x: x in STATUSES, "an execution status")
    need(p, where, row, "reason", lambda x: isinstance(x, str), "a string")
    need(p, where, row, "grading_status", lambda x: x in GRADINGS, f"one of {', '.join(GRADINGS)}")
    for key in ("started", "finished", "model", "workspace", "transcript"):
        need(p, where, row, key, lambda x: isinstance(x, str), "a string or null", optional=True, nullable=True)
    need(p, where, row, "seconds", lambda x: number(x) and x >= 0, "a number >= 0 or null", optional=True, nullable=True)
    need(p, where, row, "cost_usd", lambda x: number(x) and x >= 0, "a number >= 0 or null", optional=True, nullable=True)
    need(p, where, row, "exit_code", integer, "an integer or null", optional=True, nullable=True)
    need(p, where, row, "left_running", lambda x: isinstance(x, bool), "true or false", optional=True)
    need(p, where, row, "full_success", lambda x: isinstance(x, bool), "true, false or null", optional=True, nullable=True)
    need(p, where, row, "credit", unit, "a number in [0, 1] or null", optional=True, nullable=True)
    need(p, where, row, "dimensions", lambda x: isinstance(x, dict), "an object", optional=True)
    need(p, where, row, "critical_failures", lambda x: isinstance(x, list), "a list", optional=True)
    if not p and row["grading_status"] == "scored":
        if row["status"] not in SCORED:
            p.append(f"{where}: a {row['status']} attempt cannot be scored")
        if not isinstance(row.get("full_success"), bool):
            p.append(f"{where}: a scored attempt needs 'full_success'")
    return p


def _rates(problems, where, doc):
    for key in ("full_success_rate", "mean_credit"):
        if doc.get(key) is not None and not unit(doc[key]):
            problems.append(f"{where}: {key!r} must be in [0, 1] or null")


def summary_problems(doc, where="summary.json") -> list[str]:
    if not isinstance(doc, dict):
        return [f"{where}: must be a JSON object"]
    p = []
    for section, keys in SUMMARY_KEYS.items():
        body = doc.get(section)
        if not isinstance(body, dict):
            p.append(f"{where}: missing {section!r}")
            continue
        p += [f"{where} {section}: missing {key!r}" for key in keys if key not in body]
    for section in ("families", "tasks"):
        if not isinstance(doc.get(section), dict):
            p.append(f"{where}: missing {section!r}")
    if not isinstance(doc.get("exclusions"), list):
        p.append(f"{where}: missing 'exclusions'")
    if p:
        return p
    counts, run = doc["counts"], doc["run"]
    by_status = counts["by_status"]
    if not isinstance(by_status, dict) or set(by_status) != set(STATUSES):
        return [f"{where} counts: 'by_status' must count exactly {', '.join(STATUSES)}"]
    if counts["scored"] + counts["unscored"] != counts["planned"]:
        p.append(f"{where}: scored + unscored must equal planned")
    if counts["passed"] + counts["failed"] != counts["scored"]:
        p.append(f"{where}: passed + failed must equal scored")
    if sum(by_status.values()) != counts["planned"]:
        p.append(f"{where}: by_status must sum to planned")
    if counts["planned"] != doc["suite"]["tasks"] * run["repeats"]:
        p.append(f"{where}: planned must be tasks x repeats")
    if len(doc["tasks"]) != doc["suite"]["tasks"]:
        p.append(f"{where}: 'tasks' must list every suite task")
    _rates(p, f"{where} overall", doc["overall"])
    for family, body in doc["families"].items():
        _rates(p, f"{where} family {family}", body)
    for task, body in doc["tasks"].items():
        p += [f"{where} task {task}: missing {key!r}" for key in TASK_KEYS if not isinstance(body, dict) or key not in body]
        if isinstance(body, dict):
            _rates(p, f"{where} task {task}", body)
    return p


def _band(problems, where, claim):
    if need(problems, where, claim, "low", number, "a number") & need(problems, where, claim, "high", number, "a number"):
        if claim["low"] > claim["high"]:
            problems.append(f"{where}: 'low' exceeds 'high'")


def _claim(claim, conditions, where) -> list[str]:
    p, kind = [], claim.get("type")

    def system(key):
        need(p, where, claim, key, lambda x: x in conditions, "a system named in conditions")

    def metric():
        need(p, where, claim, "metric", text, "a metric name")

    if kind == "interval":
        metric()
        system("system")
        _band(p, where, claim)
        need(p, where, claim, "level", lambda x: number(x) and 0 < x < 1, "a number in (0, 1)")
    elif kind == "order":
        system("higher")
        system("lower")
        metric()
        need(p, where, claim, "resolved", lambda x: isinstance(x, bool), "true or false")
    elif kind == "rate":
        metric()
        bounds = [key for key in ("min", "max") if key in claim]
        if not bounds:
            p.append(f"{where}: a rate claim needs 'min' or 'max'")
        for key in bounds:
            need(p, where, claim, key, number, "a number")
        if len(bounds) == 2 and number(claim["min"]) and number(claim["max"]) and claim["min"] > claim["max"]:
            p.append(f"{where}: 'min' exceeds 'max'")
    elif kind == "noise":
        metric()
        system("system")
        need(p, where, claim, "sd_max", lambda x: number(x) and x >= 0, "a number >= 0")
    elif kind == "target":
        metric()
        system("system")
        _band(p, where, claim)
    elif kind == "cost":
        system("system")
        need(p, where, claim, "profile", lambda x: x in PROFILES, f"one of {', '.join(PROFILES)}")
        limits = [key for key in ("usd_max", "wall_seconds_max") if key in claim]
        if not limits:
            p.append(f"{where}: a cost claim needs 'usd_max' or 'wall_seconds_max'")
        for key in limits:
            need(p, where, claim, key, lambda x: number(x) and x >= 0, "a number >= 0")
    elif kind == "verdict":
        need(p, where, claim, "supports_claim", lambda x: isinstance(x, bool), "true or false")
        need(p, where, claim, "reason", text, "a non-empty string")
    elif kind == "gap":
        need(p, where, claim, "category", lambda x: x in GAP_CATEGORIES, f"one of {', '.join(GAP_CATEGORIES)}")
        need(p, where, claim, "text", text, "a non-empty string")
    else:
        p.append(f"{where}: 'type' must be interval, order, rate, noise, target, cost, verdict or gap")
    return p


def claims_problems(card, where="card.json") -> list[str]:
    if not isinstance(card, dict):
        return [f"{where}: must be a JSON object"]
    p = []
    conditions, claims = card.get("conditions"), card.get("claims")
    if not isinstance(conditions, dict):
        p.append(f"{where}: 'conditions' must be an object of named systems")
        conditions = {}
    for name, condition in conditions.items():
        if not isinstance(condition, dict) or not text(condition.get("agent")):
            p.append(f"{where} condition {name!r}: needs an 'agent' string")
    if not isinstance(claims, list):
        return p + [f"{where}: 'claims' must be a list"]
    seen = set()
    for index, claim in enumerate(claims, 1):
        label = f"{where} claim {index}"
        if not isinstance(claim, dict):
            p.append(f"{label}: must be an object")
            continue
        if not text(claim.get("id")):
            p.append(f"{label}: missing 'id'")
        elif claim["id"] in seen:
            p.append(f"{label}: duplicate id {claim['id']!r}")
        else:
            seen.add(claim["id"])
            label = f"{where} claim {claim['id']}"
        p += _claim(claim, conditions, label)
    return p


def read_jsonl(path: Path) -> tuple[list, list[str]]:
    rows, problems = [], []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return rows, [f"{Path(path).name}: {error}"]
    for number_, line in enumerate(lines, 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                problems.append(f"{Path(path).name}: line {number_} is not JSON")
    return rows, problems


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_problems(out) -> list[str]:
    """Every record in a run directory: run.json, attempts.jsonl, grades-*.jsonl and the summaries."""
    out, p = Path(out), []
    try:
        run = read_json(out / "run.json")
    except (OSError, ValueError) as error:
        p.append(f"run.json: {error}")
    else:
        if not isinstance(run, dict):
            p.append("run.json: must be a JSON object")
        else:
            p += [f"run.json: missing {key!r}" for key in ("profile", "agent", "repeats", "jobs", "tasks", "started") if key not in run]
    rows, bad = read_jsonl(out / "attempts.jsonl")
    p += bad
    for index, row in enumerate(rows, 1):
        p += attempt_problems(row, f"attempts.jsonl row {index}")
    for path in sorted(out.glob("summary*.json")):
        try:
            p += summary_problems(read_json(path), path.name)
        except (OSError, ValueError) as error:
            p.append(f"{path.name}: {error}")
    return p


# ---- running commands -------------------------------------------------------------------------------

def run_command(command, cwd, timeout, logs: Path, name: str) -> dict:
    """Run a command with output to files and its tree stopped at the timeout; returns its record."""
    logs.mkdir(parents=True, exist_ok=True)
    out, err = logs / f"{name}.out.txt", logs / f"{name}.err.txt"
    began, status, code = time.monotonic(), "completed", None
    with open(out, "wb") as stdout, open(err, "wb") as stderr:
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        try:
            child = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, **options)
        except OSError as error:
            return {"command": command, "exit_code": None, "status": "error", "seconds": 0.0, "reason": str(error)}
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            status = "timeout"
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(child.pid)], capture_output=True)
            else:
                os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    tail = err.read_text(encoding="utf-8", errors="replace").strip()[-300:]
    return {"command": command, "exit_code": code, "status": status, "seconds": round(time.monotonic() - began, 2),
            "reason": "" if status == "completed" and code == 0 else (f"timed out after {timeout:g} s" if status == "timeout" else tail)}


# ---- the checks -------------------------------------------------------------------------------------

class Report:
    def __init__(self, package: Path):
        self.package, self.checks, self.commands = package, [], []

    def check(self, name: str, problems, detail: str = "") -> bool:
        problems = [problems] if isinstance(problems, str) else list(problems)
        self.checks.append({"name": name, "passed": not problems, "detail": "; ".join(problems[:6]) if problems else detail})
        return not problems

    def command(self, record: dict) -> dict:
        self.commands.append({**record, "command": [str(part) for part in record["command"]]})
        return record

    def ok(self, name: str, record: dict) -> bool:
        return self.check(name, [] if record["exit_code"] == 0 and record["status"] == "completed" else
                          [f"exit code {record['exit_code']}, {record['status']}: {record['reason']}".rstrip(": ")],
                          f"exit 0 in {record['seconds']} s")

    def result(self) -> dict:
        return {"package": str(self.package), "pass": all(c["passed"] for c in self.checks), "checks": self.checks,
                "commands": self.commands}


def layout_problems(package: Path) -> list[str]:
    p = [f"missing {name}" for name in ("suite.json", "run.py", "card.json") if not (package / name).is_file()]
    tasks = package / "tasks"
    ids = sorted(d.name for d in tasks.iterdir() if d.is_dir()) if tasks.is_dir() else []
    if not ids:
        p.append("tasks/ holds no task directory")
    for name in ids:
        for relative in ("instruction.md", "task.toml", "solution/solve.py", "tests/verify.py"):
            if not (tasks / name / relative).is_file():
                p.append(f"tasks/{name}/{relative} is missing")
    return p


def package_shapes(package: Path) -> list[str]:
    p = []
    for name, check in (("suite.json", suite_problems), ("card.json", claims_problems)):
        try:
            p += check(read_json(package / name), name)
        except (OSError, ValueError) as error:
            p.append(f"{name}: {error}")
    for folder in sorted((package / "tasks").glob("*/task.toml")):
        try:
            p += task_problems(tomllib.loads(folder.read_text(encoding="utf-8")), f"tasks/{folder.parent.name}/task.toml")
        except (OSError, ValueError) as error:
            p.append(f"tasks/{folder.parent.name}/task.toml: {error}")
    return p


def grade_problems(rows: list, tree: dict) -> list[str]:
    """Shapes of the grade rows, and agreement with the grades the run itself recorded for the same workspaces."""
    p = []
    by_key = {(row.get("task"), row.get("submission")): row for row in rows if isinstance(row, dict)}
    for key, source in tree.items():
        row = by_key.get(key)
        if row is None:
            p.append(f"grade wrote no row for {key[0]}/{key[1]}")
            continue
        p += verifier_problems(row, f"grade row {key[0]}/{key[1]}")
        recorded = source
        for field in ("grading_status", "full_success"):
            if row.get(field) != recorded.get(field):
                p.append(f"grade row {key[0]}/{key[1]}: {field} {row.get(field)!r} differs from the run's {recorded.get(field)!r}")
        if number(row.get("credit")) and number(recorded.get("credit")) and abs(row["credit"] - recorded["credit"]) > 1e-6:
            p.append(f"grade row {key[0]}/{key[1]}: credit {row['credit']} differs from the run's {recorded['credit']}")
    return p


def grade_tree(out: Path, destination: Path) -> dict:
    """Copy each scored attempt's captured workspace to destination/<task>/<attempt>; maps (task, id) to its row."""
    rows, _ = read_jsonl(out / "attempts.jsonl")
    tree = {}
    for row in rows:
        if isinstance(row, dict) and row.get("workspace") and row.get("grading_status") == "scored":
            source = out / row["workspace"]
            if source.is_dir():
                name = f"a{row['repeat']}-{row['retry']}"
                shutil.copytree(source, destination / row["task"] / name)
                tree[(row["task"], name)] = row
    return tree


def conform(package: Path, timeout: float = 900.0) -> dict:
    package = Path(package).resolve()
    report = Report(package)
    if not report.check("layout", layout_problems(package), "suite.json, run.py, card.json and tasks/ with their files"):
        return report.result()
    report.check("package shapes", package_shapes(package), "suite.json, every task.toml and the card's claims are valid")
    with tempfile.TemporaryDirectory(prefix="conform-") as scratch:
        scratch = Path(scratch)
        logs, py = scratch / "logs", sys.executable
        agent = scratch / "noop-agent"
        agent.mkdir()
        (agent / "run_agent.py").write_text(NOOP_AGENT, encoding="utf-8")
        steps = (("preflight", ["preflight"], None), ("smoke with a no-op agent", ["smoke", "--agent", str(agent), "--output",
                                                                                  str(scratch / "noop")], scratch / "noop"),
                 ("full with @reference", ["full", "--agent", "@reference", "--output", str(scratch / "reference")],
                  scratch / "reference"))
        for name, arguments, out in steps:
            record = report.command(run_command([py, "run.py", *arguments], package, timeout, logs, name.split()[0]))
            if report.ok(name, record) and out is not None:
                report.check(f"{name}: records", run_problems(out), "run.json, attempts.jsonl and summaries are valid")
        reference = scratch / "reference"
        if (reference / "attempts.jsonl").is_file():
            tree = grade_tree(reference, scratch / "grade-in")
            record = report.command(run_command([py, "run.py", "grade", "--input", str(scratch / "grade-in"), "--output",
                                                 str(scratch / "grades.jsonl")], package, timeout, logs, "grade"))
            if report.ok("grade on the reference outputs", record):
                rows, bad = read_jsonl(scratch / "grades.jsonl")
                report.check("grade rows", bad + ([] if tree else ["the reference run left nothing to grade"])
                             + grade_problems(rows, tree), f"{len(rows)} rows agree with the run's own grades")
    return report.result()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", help="the delivered package directory (holds run.py)")
    parser.add_argument("--timeout", type=float, default=900.0, help="seconds allowed for each command")
    args = parser.parse_args(argv)
    result = conform(Path(args.package), args.timeout)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
