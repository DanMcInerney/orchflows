"""Shape checks for the records the kit reads and writes. Each returns a list of problems; empty means valid.

INTERFACE.md documents every shape; the examples there are validated by the tests, so the two cannot drift.
Unknown extra keys are always allowed.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from . import aggregate
from .schedule import Ledger, LedgerError

STATUSES = tuple(aggregate.STATUS_ORDER)
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


def number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def integer(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def text(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def unit(x) -> bool:
    return number(x) and 0 <= x <= 1


def _check(problems, where, doc, key, test, expect, *, optional=False, nullable=False) -> bool:
    """Record a problem unless `doc[key]` passes `test`; a missing key is fine when optional, None when nullable."""
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


def _commands(problems, where, doc, key):
    value = doc.get(key, [])
    if not isinstance(value, list) or not all(isinstance(c, list) and c and all(text(a) for a in c) for c in value):
        problems.append(f"{where}: {key!r} must be a list of commands, each a non-empty list of strings")


def suite_problems(doc, where="suite.json") -> list[str]:
    if not isinstance(doc, dict):
        return [f"{where}: must be a JSON object"]
    p = []
    _check(p, where, doc, "name", text, "a non-empty string")
    _check(p, where, doc, "repeats", lambda x: integer(x) and x >= 1, "an integer >= 1")
    _check(p, where, doc, "concurrency", lambda x: integer(x) and x >= 1, "an integer >= 1")
    _check(p, where, doc, "deadline_seconds", lambda x: number(x) and x > 0, "a positive number", optional=True, nullable=True)
    for key in ("attempt_seconds_estimate", "attempt_cost_estimate_usd", "grace_seconds"):
        _check(p, where, doc, key, lambda x: number(x) and x >= 0, "a number >= 0", optional=True, nullable=True)
    _check(p, where, doc, "transient_retry_budget", lambda x: integer(x) and x >= 0, "an integer >= 0", optional=True)
    _check(p, where, doc, "launch_budget", lambda x: integer(x) and x >= 1, "an integer >= 1", optional=True, nullable=True)
    _commands(p, where, doc, "provision")
    _commands(p, where, doc, "observe")
    if "metrics" in doc:
        metrics = doc["metrics"]
        if not isinstance(metrics, dict):
            p.append(f"{where}: 'metrics' must be an object")
        else:
            _check(p, f"{where} metrics", metrics, "primary", lambda x: x in PRIMARY, f"one of {', '.join(PRIMARY)}")
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
        _check(p, w, meta, "family", text, "a non-empty string")
        _check(p, w, meta, "source_group", text, "a non-empty string")
        _check(p, w, meta, "split", lambda x: x in SPLITS, f"one of {', '.join(SPLITS)}")
        for key in ("anchor", "smoke", "quick"):
            _check(p, w, meta, key, lambda x: isinstance(x, bool), "true or false", optional=True)
        _check(p, w, meta, "weight", lambda x: number(x) and x >= 0, "a number >= 0", optional=True)
        _check(p, w, meta, "difficulty", lambda x: text(x) or number(x), "a rationale string or a number", optional=True)
        _check(p, w, meta, "expert_minutes", lambda x: number(x) and x > 0, "a positive number", optional=True)
        _check(p, w, meta, "time_estimate", lambda x: x in ESTIMATES, f"one of {', '.join(ESTIMATES)}", optional=True)
    for table, required in (("agent", True), ("verifier", False)):
        section = doc.get(table)
        if section is None and not required:
            continue
        if not isinstance(section, dict):
            p.append(f"{where}: missing [{table}]")
        else:
            _check(p, f"{where} [{table}]", section, "timeout_sec", lambda x: number(x) and x > 0, "a positive number",
                   optional=not required)
    return p


def weights_problems(weights: dict[str, float | None]) -> list[str]:
    """Task weights are all declared or none; nonnegative; summing to 1."""
    declared = {task: w for task, w in weights.items() if w is not None}
    if not declared:
        return []
    if len(declared) != len(weights):
        return [f"weight declared for only {len(declared)} of {len(weights)} tasks"]
    if abs(math.fsum(declared.values()) - 1.0) > 1e-6:
        return [f"task weights sum to {math.fsum(declared.values()):.6g}, not 1"]
    return []


def verifier_problems(raw, where="verifier result") -> list[str]:
    if not isinstance(raw, dict):
        return [f"{where}: must be a JSON object"]
    status = raw.get("grading_status")
    if status not in GRADINGS:
        return [f"{where}: 'grading_status' must be one of {', '.join(GRADINGS)}"]
    if status != "scored":
        return [] if text(raw.get("reason")) else [f"{where}: a {status} result needs a 'reason'"]
    grade = aggregate.validate_grade(raw)
    return [f"{where}: {grade['reason']}"] if grade["grading_status"] != "scored" else []


def attempt_problems(row, where="attempt") -> list[str]:
    if not isinstance(row, dict):
        return [f"{where}: must be a JSON object"]
    p = []
    _check(p, where, row, "task", text, "a non-empty string")
    _check(p, where, row, "repeat", lambda x: integer(x) and x >= 1, "an integer >= 1")
    _check(p, where, row, "retry", lambda x: integer(x) and x >= 0, "an integer >= 0")
    _check(p, where, row, "status", lambda x: x in STATUSES, "an execution status")
    _check(p, where, row, "reason", lambda x: isinstance(x, str), "a string")
    _check(p, where, row, "grading_status", lambda x: x in GRADINGS, f"one of {', '.join(GRADINGS)}")
    for key in ("started", "finished", "model", "workspace", "transcript"):
        _check(p, where, row, key, lambda x: isinstance(x, str), "a string or null", optional=True, nullable=True)
    _check(p, where, row, "seconds", lambda x: number(x) and x >= 0, "a number >= 0 or null", optional=True, nullable=True)
    _check(p, where, row, "cost_usd", lambda x: number(x) and x >= 0, "a number >= 0 or null", optional=True, nullable=True)
    _check(p, where, row, "exit_code", integer, "an integer or null", optional=True, nullable=True)
    _check(p, where, row, "left_running", lambda x: isinstance(x, bool), "true or false", optional=True)
    _check(p, where, row, "full_success", lambda x: isinstance(x, bool), "true, false or null", optional=True, nullable=True)
    _check(p, where, row, "credit", unit, "a number in [0, 1] or null", optional=True, nullable=True)
    _check(p, where, row, "dimensions", lambda x: isinstance(x, dict), "an object", optional=True)
    _check(p, where, row, "critical_failures", lambda x: isinstance(x, list), "a list", optional=True)
    if not p and row["grading_status"] == "scored":
        if row["status"] not in aggregate.SCORED:
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
    if _check(problems, where, claim, "low", number, "a number") & _check(problems, where, claim, "high", number, "a number"):
        if claim["low"] > claim["high"]:
            problems.append(f"{where}: 'low' exceeds 'high'")


def _claim(claim, conditions, where) -> list[str]:
    p = []
    kind = claim.get("type")

    def system(key):
        _check(p, where, claim, key, lambda x: x in conditions, "a system named in conditions")

    def metric():
        _check(p, where, claim, "metric", text, "a metric name")

    if kind == "interval":
        metric()
        system("system")
        _band(p, where, claim)
        _check(p, where, claim, "level", lambda x: number(x) and 0 < x < 1, "a number in (0, 1)")
    elif kind == "order":
        system("higher")
        system("lower")
        metric()
        _check(p, where, claim, "resolved", lambda x: isinstance(x, bool), "true or false")
    elif kind == "rate":
        metric()
        bounds = [key for key in ("min", "max") if key in claim]
        if not bounds:
            p.append(f"{where}: a rate claim needs 'min' or 'max'")
        for key in bounds:
            _check(p, where, claim, key, number, "a number")
        if len(bounds) == 2 and number(claim["min"]) and number(claim["max"]) and claim["min"] > claim["max"]:
            p.append(f"{where}: 'min' exceeds 'max'")
    elif kind == "noise":
        metric()
        system("system")
        _check(p, where, claim, "sd_max", lambda x: number(x) and x >= 0, "a number >= 0")
    elif kind == "target":
        metric()
        system("system")
        _band(p, where, claim)
    elif kind == "cost":
        system("system")
        _check(p, where, claim, "profile", lambda x: x in PROFILES, f"one of {', '.join(PROFILES)}")
        limits = [key for key in ("usd_max", "wall_seconds_max") if key in claim]
        if not limits:
            p.append(f"{where}: a cost claim needs 'usd_max' or 'wall_seconds_max'")
        for key in limits:
            _check(p, where, claim, key, lambda x: number(x) and x >= 0, "a number >= 0")
    elif kind == "verdict":
        _check(p, where, claim, "supports_claim", lambda x: isinstance(x, bool), "true or false")
        _check(p, where, claim, "reason", text, "a non-empty string")
    elif kind == "gap":
        _check(p, where, claim, "category", lambda x: x in GAP_CATEGORIES, f"one of {', '.join(GAP_CATEGORIES)}")
        _check(p, where, claim, "text", text, "a non-empty string")
    else:
        p.append(f"{where}: 'type' must be interval, order, rate, noise, target, cost, verdict or gap")
    return p


def claims_problems(card, where="card.json") -> list[str]:
    """`conditions` (named systems) and `claims` (typed, each citing only systems named there)."""
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
    for number_, claim in enumerate(claims, 1):
        label = f"{where} claim {number_}"
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
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            problems.append(f"{Path(path).name}: line {number_} is not JSON")
    return rows, problems


def run_problems(out: Path) -> list[str]:
    """Every record in a run directory: run.json, ledger, attempts, grades and summaries."""
    out, p = Path(out), []

    def load(name):
        try:
            return json.loads((out / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            p.append(f"{name}: {error}")

    run = load("run.json")
    if isinstance(run, dict):
        for key in ("profile", "agent", "repeats", "jobs", "tasks", "observed_versions", "started"):
            if key not in run:
                p.append(f"run.json: missing {key!r}")
    elif run is not None:
        p.append("run.json: must be a JSON object")
    try:
        Ledger(out / "ledger.jsonl").records()
    except LedgerError as error:
        p.append(str(error))
    rows, bad = read_jsonl(out / "attempts.jsonl")
    p += bad
    for number_, row in enumerate(rows, 1):
        p += attempt_problems(row, f"attempts.jsonl row {number_}")
    for path in sorted(out.glob("grades-*.jsonl")):
        grades, bad = read_jsonl(path)
        p += bad
        for number_, row in enumerate(grades, 1):
            if not isinstance(row, dict) or row.get("grading_status") not in GRADINGS:
                p.append(f"{path.name} row {number_}: 'grading_status' must be one of {', '.join(GRADINGS)}")
    for path in sorted(out.glob("summary*.json")):
        summary = load(path.name)
        if summary is not None:
            p += summary_problems(summary, path.name)
    return p
