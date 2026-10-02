"""Crosscheck: what the delivered runner reports against what its pool member actually did.

The shim logged every invocation (the workspace path it ran in, the prompt it received, a copy of its final
workspace). For each member run this joins those invocations to the runner's `attempts.jsonl` rows, compares the
counts per task and with `summary.json`, and regrades the captured final workspaces through the delivered
`run.py grade`, comparing the grades with the rows. A runner that drops attempts, invents them or reports credit
the verifier does not give is caught here, not trusted. The result feeds the report's `crosscheck` gate:
`{"pass", "count_mismatches": [...], "grade_mismatches": [...], "regraded": n, "members": {...}}`.
"""
from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import delivered, execute
from .execute import Run

SCORED = {"completed", "refused", "cut-off", "agent-budget-exhausted"}
TOLERANCE = 1e-6


def norm(path) -> str:
    return os.path.normcase(os.path.realpath(path)) if path else ""


def live_workspace(out: Path, row: dict) -> str | None:
    """The workspace path the runner staged for an attempt, from its solver.json."""
    solver = execute.read_json(Path(out) / "attempts" / str(row.get("task")) / f"{row.get('repeat')}-{row.get('retry')}" / "solver.json")
    return solver.get("live_workspace") if isinstance(solver, dict) else None


def launched(rows: list[dict]) -> list[dict]:
    """Attempt rows that reached the member: a status other than not-launched, with a workspace or exit code."""
    return [r for r in rows if r.get("status") != "not-launched" and (r.get("workspace") or r.get("exit_code") is not None)]


def final_units(rows: list[dict]) -> dict:
    """(task, repeat) -> the row of its highest retry."""
    finals: dict = {}
    for row in rows:
        key = (row.get("task"), row.get("repeat"))
        if key not in finals or (row.get("retry") or 0) >= (finals[key].get("retry") or 0):
            finals[key] = row
    return finals


def task_of(run: Run, invocation: dict, tasks: dict[str, delivered.Task]) -> str | None:
    """The delivered task whose instruction the member received, from the captured prompt and workspace."""
    prompt = run.root / invocation["prompt_capture"] if invocation.get("prompt_capture") else None
    capture = run.root / invocation["final_capture"] if invocation.get("final_capture") else None
    text = prompt.read_text(encoding="utf-8", errors="replace") if prompt and prompt.is_file() else ""
    return delivered.identify(tasks, text, capture if capture and capture.is_dir() else None)


def check_member(run: Run, member: str, out: Path, tasks: dict[str, delivered.Task], *, grade_cap: float) -> dict:
    """The crosscheck for one member's run; `count_mismatches` and `grade_mismatches` list what disagrees."""
    out = Path(out)
    rows = execute.read_rows(out / "attempts.jsonl")
    summary = execute.read_json(out / "summary.json") or {}
    invocations = execute.invocation_rows(run.invocations / f"{member}.jsonl")
    counts, grades = [], []
    if not rows:
        counts.append({"member": member, "kind": "attempts", "detail": "attempts.jsonl is missing or empty"})
    by_path = {norm(i.get("workspace")): i for i in invocations}
    pairs, loose_rows = [], []
    for row in launched(rows):
        invocation = by_path.pop(norm(live_workspace(out, row)), None)
        (pairs.append((row, invocation)) if invocation else loose_rows.append(row))
    loose = list(by_path.values())
    for row in list(loose_rows):       # no workspace to join on: match by the task the member was given
        match = next((i for i in loose if task_of(run, i, tasks) == row.get("task")), None)
        if match:
            loose.remove(match)
            loose_rows.remove(row)
            pairs.append((row, match))
    for row, invocation in pairs:
        seen = task_of(run, invocation, tasks)
        if seen is not None and seen != row.get("task"):
            counts.append({"member": member, "kind": "task-differs", "task": row.get("task"),
                           "detail": f"the member received the instruction of {seen}, the row says {row.get('task')}"})
    for row in loose_rows:
        counts.append({"member": member, "kind": "attempt-without-invocation", "task": row.get("task"),
                       "detail": f"repeat {row.get('repeat')} retry {row.get('retry')} has no member invocation"})
    for invocation in loose:
        counts.append({"member": member, "kind": "invocation-without-attempt", "task": task_of(run, invocation, tasks),
                       "detail": f"invocation {invocation.get('invocation')} has no attempts.jsonl row"})
    reported = (summary.get("counts") or {}).get("launched")
    if reported is not None and reported != len(invocations):
        counts.append({"member": member, "kind": "summary-launched", "summary": reported, "invocations": len(invocations),
                       "detail": f"summary.json reports {reported} launches, the member ran {len(invocations)} times"})
    scored = sum(r.get("grading_status") == "scored" and r.get("status") in SCORED for r in final_units(rows).values())
    reported = (summary.get("counts") or {}).get("scored")
    if reported is not None and reported != scored:
        counts.append({"member": member, "kind": "summary-scored", "summary": reported, "attempts": scored,
                       "detail": f"summary.json reports {reported} scored units, attempts.jsonl has {scored}"})
    return {"count_mismatches": counts, "grade_mismatches": grades,
            "regraded": _regrade(run, member, pairs, grades, grade_cap)}


def _regrade(run: Run, member: str, pairs, grades: list, cap: float) -> int:
    """Regrade the shim's captured final workspaces with the delivered `run.py grade`; append disagreements."""
    shutil.rmtree(run.root / "grades" / member, ignore_errors=True)
    tree, expected = run.root / "grades" / member / "input", {}
    for row, invocation in pairs:
        capture = run.root / invocation["final_capture"] if invocation.get("final_capture") else None
        if row.get("status") not in SCORED or not row.get("task") or capture is None or not capture.is_dir():
            continue
        submission = invocation["invocation"][:8]
        shutil.copytree(capture, tree / row["task"] / submission)
        expected[row["task"], submission] = row
    if not expected:
        return 0
    outcome, result = execute.run_grade(run, member, tree, run.root / "grades" / member / "grades.jsonl", cap)
    if outcome.status != "completed" or outcome.exit_code != 0:
        grades.append({"member": member, "kind": "grade-failed", "detail": f"run.py grade: {outcome.reason or outcome.exit_code}"})
        return 0
    found = {(r.get("task"), r.get("submission")): r for r in result}
    for (task, submission), row in expected.items():
        new = found.get((task, submission))
        if new is None:
            grades.append({"member": member, "task": task, "kind": "grade-missing", "detail": f"grade wrote no row for {task}/{submission}"})
            continue
        for field in ("grading_status", "full_success"):
            if new.get(field) != row.get(field):
                grades.append({"member": member, "task": task, "repeat": row.get("repeat"), "field": field,
                               "attempts": row.get(field), "regrade": new.get(field)})
        if _differs(new.get("credit"), row.get("credit")):
            grades.append({"member": member, "task": task, "repeat": row.get("repeat"), "field": "credit",
                           "attempts": row.get("credit"), "regrade": new.get("credit")})
        if len(new.get("critical_failures") or []) != len(row.get("critical_failures") or []):
            grades.append({"member": member, "task": task, "repeat": row.get("repeat"), "field": "critical_failures",
                           "attempts": row.get("critical_failures"), "regrade": new.get("critical_failures")})
    return len(expected)


def _differs(a, b) -> bool:
    if a is None or b is None:
        return a is not b
    return abs(a - b) > TOLERANCE


def crosscheck(run: Run, results: dict, tasks: dict[str, delivered.Task], *, grade_cap: float, jobs: int = 3) -> dict:
    """The gate's input over every member run (not the built-ins, which have no invocation log)."""
    members = sorted(m for m in results if not m.startswith("@"))
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        found = list(pool.map(lambda m: check_member(run, m, results[m]["out"], tasks, grade_cap=grade_cap), members))
    counts = [item for one in found for item in one["count_mismatches"]]
    grades = [item for one in found for item in one["grade_mismatches"]]
    return {"pass": not (counts or grades), "count_mismatches": counts, "grade_mismatches": grades,
            "regraded": sum(one["regraded"] for one in found),
            "members": {m: {"count_mismatches": len(one["count_mismatches"]), "grade_mismatches": len(one["grade_mismatches"]),
                            "regraded": one["regraded"]} for m, one in zip(members, found)}}
