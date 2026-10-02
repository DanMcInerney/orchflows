"""Records derived from a run's ledger: attempt rows, summaries, re-grading, grade-only and comparison.

The ledger is the only record of what ran. attempts.jsonl and summary.json are rebuilt from it, so a run that
stopped at any point still has both. A re-grade adds grades-<n>.jsonl without touching the ledger or the attempts.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import adapters, aggregate, shapes
from .schedule import Ledger
from .suite import Suite, task_meta

CONTROL = ("transient", "usage_limit")
GRADE_FIELDS = ("grading_status", "full_success", "credit", "credit_bounds", "dimensions", "critical_failures")


def iso(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    """Replace a file whole, so a reader never sees half of it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_name(path.name + ".part")
    scratch.write_text(text, encoding="utf-8")
    os.replace(scratch, path)


def write_json(path: Path, doc) -> None:
    write_text(path, json.dumps(doc, indent=2, allow_nan=False) + "\n")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def blank_row(task: str, repeat: int, retry: int) -> dict:
    return {"task": task, "repeat": repeat, "retry": retry, "status": "not-launched", "reason": "", "started": None,
            "finished": None, "seconds": None, "exit_code": None, "model": None, "cost_usd": None, "left_running": False,
            "grading_status": "unscored", "full_success": None, "credit": None, "credit_bounds": None, "dimensions": {},
            "critical_failures": [], "grade_reason": "", "grading_seconds": None, "workspace": None, "transcript": None}


def attempt_rows(records: list[dict]) -> list[dict]:
    """One row per launched attempt, and per refused unit, from the ledger: the last `finished` record for each
    (unit, retry) overlaid on a blank row."""
    planned = {row["key"]: (row["task"], row["repeat"]) for row in records if row["kind"] == "planned"}
    last = {}
    for row in records:
        if row["kind"] == "finished" and row["key"] in planned:
            last.pop((row["key"], row["retry"]), None)
            last[(row["key"], row["retry"])] = row
    rows = []
    for (key, retry), done in last.items():
        task, repeat = planned[key]
        row = blank_row(task, repeat, retry)
        row.update({name: value for name, value in (done.get("result") or {}).items() if name not in CONTROL})
        row.update(task=task, repeat=repeat, retry=retry, status=done["status"], reason=done.get("reason", ""))
        if row["grading_status"] != "scored" and not row["grade_reason"]:
            row["grade_reason"] = f"not graded: {row['status']}"
        rows.append(row)
    return sorted(rows, key=lambda row: (row["task"], row["repeat"], row["retry"]))


def grades_files(out: Path) -> list[tuple[int, Path]]:
    found = [(int(match.group(1)), path) for path in Path(out).glob("grades-*.jsonl")
             if (match := re.fullmatch(r"grades-(\d+)\.jsonl", path.name))]
    return sorted(found)


def overlay(rows: list[dict], grades: list[dict]) -> list[dict]:
    """The rows with the grading fields of a later re-grade, matched by task, repeat and retry."""
    newer = {(g["task"], g["repeat"], g["retry"]): g for g in grades}
    merged = []
    for row in rows:
        grade = newer.get((row["task"], row["repeat"], row["retry"]))
        if grade:
            row = {**row, **{name: grade.get(name) for name in GRADE_FIELDS}, "grade_reason": grade.get("reason", ""),
                   "grading_seconds": grade.get("seconds")}
        merged.append(row)
    return merged


def current_rows(out: Path, base: list[dict] | None = None) -> list[dict]:
    base = attempt_rows(Ledger(Path(out) / "ledger.jsonl").records()) if base is None else base
    files = grades_files(out)
    return overlay(base, shapes.read_jsonl(files[-1][1])[0]) if files else base


def read_run(out: Path) -> dict:
    return read_json(Path(out) / "run.json")


def run_summary_info(info: dict, suite: Suite, rows: list[dict]) -> dict:
    """The `run` argument of aggregate.summarize."""
    invocations = info.get("invocations", [])

    def total(key):
        return round(sum(i.get(key) or 0 for i in invocations), 3)

    return {"profile": info["profile"], "agent": info["agent"], "repeats": info["repeats"], "jobs": info["jobs"],
            "started": info["started"], "finished": info.get("finished"), "suite_name": suite.name,
            "deadline_reached": any(i.get("stopped") == "deadline" for i in invocations),
            "observed_versions": info["observed_versions"], "wall_seconds": total("wall_seconds"),
            "setup_seconds": total("setup_seconds"),
            "grading_seconds": round(sum(r["grading_seconds"] or 0 for r in rows), 3),
            "execution_seconds": round(sum(r["seconds"] or 0 for r in rows), 3)}


def write_outputs(out: Path, suite: Suite, info: dict) -> dict:
    """Rebuild attempts.jsonl and summary.json from the ledger and the latest re-grade; returns the summary."""
    out = Path(out)
    base = attempt_rows(Ledger(out / "ledger.jsonl").records())
    write_text(out / "attempts.jsonl", "".join(json.dumps(row) + "\n" for row in base))
    rows = current_rows(out, base)
    tasks = [suite.tasks[name] for name in info["tasks"]]
    summary = aggregate.summarize(rows, task_meta(tasks), run_summary_info(info, suite, rows))
    files = grades_files(out)
    if files:
        summary["rescore"] = {"grades": files[-1][1].name}
    write_json(out / "summary.json", summary)
    return summary


def _grade_row(grade: dict) -> dict:
    return {**{name: grade[name] for name in GRADE_FIELDS}, "reason": grade["reason"], "seconds": grade["seconds"]}


def _regrade(task, workspace: Path, log_dir: Path) -> dict:
    if task is None:
        return {**aggregate.validate_grade(None, "task is not in the package"), "seconds": 0.0, "exit_code": None}
    if not Path(workspace).is_dir():
        return {**aggregate.validate_grade(None, "the captured workspace is missing"), "seconds": 0.0, "exit_code": None}
    return adapters.grade_copy(task, workspace, log_dir)


def rescore(out: Path, suite: Suite, jobs: int | None = None) -> dict:
    """Grade every scored attempt's captured workspace again with the package's current verifiers.

    Writes grades-<n>.jsonl and refreshes summary.json (the one it replaces is kept as summary-<n-1>.json);
    the ledger and attempts.jsonl are untouched, so nothing is relaunched.
    """
    out = Path(out)
    info = read_run(out)
    rows = [row for row in attempt_rows(Ledger(out / "ledger.jsonl").records())
            if row["status"] in aggregate.SCORED and row["workspace"]]
    number = (grades_files(out)[-1][0] if grades_files(out) else 0) + 1

    def one(row):
        log = out / f"rescore-{number}" / row["task"] / f"{row['repeat']}-{row['retry']}"
        grade = _regrade(suite.tasks.get(row["task"]), out / row["workspace"], log)
        return {"task": row["task"], "repeat": row["repeat"], "retry": row["retry"],
                "previous": {name: row[name] for name in ("grading_status", "full_success", "credit")},
                **_grade_row(grade)}

    with ThreadPoolExecutor(max_workers=max(1, jobs or info["jobs"])) as pool:
        graded = list(pool.map(one, rows))
    write_text(out / f"grades-{number}.jsonl", "".join(json.dumps(row) + "\n" for row in graded))
    if (out / "summary.json").is_file():
        write_text(out / f"summary-{number - 1}.json", (out / "summary.json").read_text(encoding="utf-8"))
    summary = write_outputs(out, suite, info)
    write_json(out / f"summary-{number}.json", summary)
    return summary


def grade_tree(suite: Suite, source: Path, jobs: int = 4) -> list[dict]:
    """One row per `source/<task-id>/<submission-id>/` final workspace; the workspaces are not modified."""
    source = Path(source)
    found = [(task.name, sub.name, sub) for task in sorted(source.iterdir()) if task.is_dir() and not task.name.startswith(".")
             for sub in sorted(task.iterdir()) if sub.is_dir() and not sub.name.startswith(".")]

    def one(item):
        name, submission, path = item
        with tempfile.TemporaryDirectory(prefix="benchkit-grade-") as scratch:
            grade = _regrade(suite.tasks.get(name), path, Path(scratch) / "log")
        return {"task": name, "submission": submission, **_grade_row(grade)}

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        return list(pool.map(one, found))


def _describe(path: Path, summary: dict, metric: str) -> dict:
    run = summary["run"]
    return {"output": str(path), "agent": run["agent"], "profile": run["profile"], "repeats": run["repeats"],
            "overall": summary["overall"].get(metric)}


def compare(a: Path, b: Path, metric: str = "full_success_rate") -> dict:
    """Paired per-task differences a - b between two runs, with the runs' identities and any mismatch."""
    summaries = []
    for path in (a, b):
        try:
            summaries.append(read_json(Path(path) / "summary.json"))
        except (OSError, ValueError) as error:
            raise ValueError(f"{path}: no readable summary.json ({error})") from None
    first, second = summaries
    result = aggregate.paired(first, second, metric=metric, clusters={})
    warnings = [f"{key} differs: {first[section][key]!r} vs {second[section][key]!r}"
                for section, key in (("suite", "name"), ("run", "profile"), ("run", "repeats"))
                if first[section][key] != second[section][key]]
    return {"metric": metric, "a": _describe(a, first, metric), "b": _describe(b, second, metric), "warnings": warnings, **result}
