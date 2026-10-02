"""Crosscheck: what the delivered runner reports against what its pool member actually did, and the scores recomputed.

The shim logged every invocation (the workspace path it ran in, the prompt it received, a copy of its final
workspace). For each member run this joins those invocations to the runner's `attempts.jsonl` rows, compares the
counts per task and with `summary.json`, and regrades the captured final workspaces through the delivered
`run.py grade` (in an arena that names no member and no label), comparing the grades with the rows. The scores
the metrics use are then recomputed with the trusted kit's `aggregate.summarize` from those rows, with the regraded
grades in place of the delivered ones, over the task list the trusted kit reads from the package; any difference from
the delivered `summary.json` is a mismatch. Finally the domain checker's own label of each captured workspace is
compared with the delivered `full_success`: a verifier that disagrees with the independent checker on most attempts
is a mismatch. A runner that drops attempts, invents them, reports credit the verifier does not give, aggregates
wrongly or fabricates consistently is caught here, not trusted. The built-in `@reference` and `@noop` runs are
regraded and recomputed from the workspaces the kit kept (they have no invocation log). The result feeds the
report's `crosscheck` gate: `{"pass", "count_mismatches": [...], "grade_mismatches": [...], "regraded": n,
"members": {...}, "summaries": {id or @name: recomputed summary}}`.
"""
from __future__ import annotations

import math
import os
import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import delivered, execute, store
from .execute import Run

store.use_kit()
from benchkit import aggregate, suite as kit_suite  # noqa: E402

SCORED = {"completed", "refused", "cut-off", "agent-budget-exhausted"}
TOLERANCE = 1e-6
ORACLE_DISAGREEMENT_MAX = 0.25   # the share of checker-labelled attempts the delivered full_success may contradict
ORACLE_MIN_COMPARED = 4
# `suboptimal` and `lenient` are left out: a package may legitimately draw its full-success line differently there (that is what
# credit and the verifier check measure); a verdict that contradicts a valid or an invalid label is the systematic kind.
DECISIVE = ("valid", "correct-infeasible", "invalid")
GOOD = ("valid", "correct-infeasible")
LISTED = 20


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


def row_key(row: dict) -> tuple:
    return row.get("task"), row.get("repeat"), row.get("retry") or 0


def task_of(run: Run, invocation: dict, tasks: dict[str, delivered.Task]) -> str | None:
    """The delivered task whose instruction the member received, from the captured prompt and workspace."""
    prompt = run.ledger / invocation["prompt_capture"] if invocation.get("prompt_capture") else None
    capture = run.ledger / invocation["final_capture"] if invocation.get("final_capture") else None
    text = prompt.read_text(encoding="utf-8", errors="replace") if prompt and prompt.is_file() else ""
    return delivered.identify(tasks, text, capture if capture and capture.is_dir() else None)


def _num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _differs(a, b) -> bool:
    if a is None or b is None:
        return a is not b
    return abs(a - b) > TOLERANCE


def _unscored(reason: str) -> dict:
    return aggregate.validate_grade(None, reason)


# ---- regrade -----------------------------------------------------------------------------------------

def regrade(run: Run, name: str, items: list[tuple[dict, Path]], grades: list, cap: float) -> tuple[dict, int]:
    """Regrade captured final workspaces with the delivered `run.py grade`. `items` are (attempt row, workspace).
    Disagreements with the rows are appended to `grades`. Returns ({row key: normalized regrade}, number regraded);
    a row the delivered grader did not answer for gets an unscored grade, so it cannot earn credit."""
    items = [(row, path) for row, path in items if row.get("task") and path.is_dir()]
    if not items:
        return {}, 0
    expected: dict = {}

    def build(tree: Path) -> dict:
        for row, path in items:
            submission = store.anon_id("s", [s for _, s in expected])
            shutil.copytree(path, tree / row["task"] / submission)
            expected[row["task"], submission] = row
        return expected

    outcome, result, expected = execute.run_grade(run, name, build, cap)
    if outcome.status != "completed" or outcome.exit_code != 0:
        grades.append({"member": name, "kind": "grade-failed", "detail": f"run.py grade: {outcome.reason or outcome.exit_code}"})
        return {row_key(row): _unscored("run.py grade failed") for row in expected.values()}, 0
    found = {(r.get("task"), r.get("submission")): r for r in result}
    out = {}
    for (task, submission), row in expected.items():
        new = found.get((task, submission))
        if new is None:
            grades.append({"member": name, "task": task, "kind": "grade-missing", "detail": f"grade wrote no row for {task}/{submission}"})
            out[row_key(row)] = _unscored("run.py grade wrote no row")
            continue
        out[row_key(row)] = aggregate.validate_grade(new)
        for field in ("grading_status", "full_success"):
            if new.get(field) != row.get(field):
                grades.append({"member": name, "task": task, "repeat": row.get("repeat"), "field": field,
                               "attempts": row.get(field), "regrade": new.get(field)})
        if _differs(new.get("credit"), row.get("credit")):
            grades.append({"member": name, "task": task, "repeat": row.get("repeat"), "field": "credit",
                           "attempts": row.get("credit"), "regrade": new.get("credit")})
        if len(new.get("critical_failures") or []) != len(row.get("critical_failures") or []):
            grades.append({"member": name, "task": task, "repeat": row.get("repeat"), "field": "critical_failures",
                           "attempts": row.get("critical_failures"), "regrade": new.get("critical_failures")})
    return out, len(expected)


# ---- recomputed summary -------------------------------------------------------------------------------

def _compare(path: str, given, fresh, found: list) -> None:
    if isinstance(fresh, dict):
        for key, value in fresh.items():
            _compare(f"{path}.{key}", given.get(key) if isinstance(given, dict) else None, value, found)
    elif isinstance(fresh, list):
        if all(_num(v) for v in fresh):
            if not (isinstance(given, list) and len(given) == len(fresh) and not any(_differs(a, b) for a, b in zip(given, fresh))):
                found.append({"where": path, "summary": given, "recomputed": fresh})
    elif _num(fresh):
        if not _num(given) or _differs(given, fresh):
            found.append({"where": path, "summary": given, "recomputed": fresh})
    elif fresh is None and given is not None:
        found.append({"where": path, "summary": given, "recomputed": None})


def differences(given: dict, fresh: dict) -> list[dict]:
    """The scored sections of a delivered summary that differ from the recomputed one (`launched` and `scored` have
    their own checks against the invocations)."""
    found: list = []
    counts = {k: v for k, v in (fresh.get("counts") or {}).items() if k not in ("launched", "scored")}
    for path, value in (("counts", counts), ("overall", fresh.get("overall")), ("tasks", fresh.get("tasks"))):
        _compare(path, (given or {}).get(path), value, found)
    return found


def recompute(run: Run, member: str, rows: list[dict], grades: dict, given: dict | None) -> tuple[dict | None, list[dict]]:
    """The summary the metrics score from: the trusted kit's `summarize` over the crosschecked rows, with `grades` (the
    regrades) in place of the delivered grades and any unverifiable scored row unscored. Also the mismatches against
    the delivered summary."""
    try:
        suite = kit_suite.load(run.intake)
        chosen = kit_suite.select(suite, "full")
        info = {**((given or {}).get("run") or {}), "profile": "full", "repeats": kit_suite.repeats_for(suite, "full"),
                "suite_name": suite.name}
        fixed = []
        for row in rows:
            row = dict(row)
            grade = grades.get(row_key(row)) or (_unscored("the grade could not be verified") if row.get("status") in SCORED else None)
            if grade:
                row.update({name: grade[name] for name in ("grading_status", "full_success", "credit", "credit_bounds",
                                                           "dimensions", "critical_failures")}, grade_reason=grade["reason"])
            fixed.append(row)
        fresh = aggregate.summarize(fixed, kit_suite.task_meta(chosen), info)
    except Exception as error:  # noqa: BLE001 - a package the trusted kit cannot read is reported, not scored
        detail = f"{type(error).__name__}: {error}"[:300]
        return None, [{"member": member, "kind": "summary-uncomputable", "detail": f"the scores cannot be recomputed: {detail}"}]
    found = differences(given, fresh) if given else [{"where": "summary", "summary": None, "recomputed": "present"}]
    shown = [{"member": member, "kind": "summary-differs", **item,
              "detail": f"{item['where']}: summary.json says {item['summary']!r}, the attempts give {item['recomputed']!r}"}
             for item in found[:LISTED]]
    if len(found) > LISTED:
        shown.append({"member": member, "kind": "summary-differs", "detail": f"and {len(found) - LISTED} more differences"})
    return fresh, shown


# ---- independent oracle ------------------------------------------------------------------------------

def oracle_agreement(member: str, pairs: list, checked: dict | None) -> tuple[dict, list[dict]]:
    """Compare the delivered `full_success` of each attempt with the domain checker's label of its captured workspace.
    Returns ({compared, disagreements, share}, count mismatches)."""
    entries = {e.get("invocation"): e for es in ((checked or {}).get(member) or {}).values() for e in es}
    compared, wrong = 0, []
    for row, invocation in pairs:
        entry = entries.get(invocation.get("invocation"))
        if not entry or not entry.get("recognized", True) or entry.get("label") not in DECISIVE or row.get("status") not in SCORED:
            continue
        accepted = row.get("grading_status") == "scored" and row.get("full_success") is True and not row.get("critical_failures")
        compared += 1
        if accepted != (entry["label"] in GOOD):
            wrong.append({"task": row.get("task"), "repeat": row.get("repeat"), "checker": entry["label"], "full_success": row.get("full_success")})
    share = len(wrong) / compared if compared else None
    found = []
    if compared >= ORACLE_MIN_COMPARED and share > ORACLE_DISAGREEMENT_MAX:
        found.append({"member": member, "kind": "oracle-disagreement", "compared": compared, "disagreements": len(wrong),
                      "detail": f"the delivered full_success contradicts the independent checker on {len(wrong)} of {compared} attempts"})
    return {"compared": compared, "disagreements": wrong[:LISTED], "share": share}, found


# ---- one member, one built-in -----------------------------------------------------------------------

def check_member(run: Run, member: str, out: Path, tasks: dict[str, delivered.Task], *, grade_cap: float, checked: dict | None = None) -> dict:
    """The crosscheck for one member's run; `count_mismatches` and `grade_mismatches` list what disagrees and
    `summary` is the recomputed summary (None when it cannot be computed)."""
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
    items = [(row, run.ledger / invocation["final_capture"]) for row, invocation in pairs
             if row.get("status") in SCORED and invocation.get("final_capture")]
    regrades, regraded = regrade(run, member, items, grades, grade_cap)
    skipped = {id(r) for r in loose_rows}
    fresh, differing = recompute(run, member, [r for r in rows if id(r) not in skipped], regrades, summary)
    counts += differing
    agreement, found = oracle_agreement(member, pairs, checked)
    counts += found
    return {"count_mismatches": counts, "grade_mismatches": grades, "regraded": regraded, "summary": fresh, "oracle": agreement}


def check_builtin(run: Run, name: str, out: Path, *, grade_cap: float) -> dict:
    """The same regrade and recomputation for `@reference` or `@noop`, from the workspaces the kit kept."""
    out = Path(out)
    rows = execute.read_rows(out / "attempts.jsonl")
    summary = execute.read_json(out / "summary.json") or {}
    counts, grades = [], []
    items = [(row, out / row["workspace"]) for row in rows if row.get("status") in SCORED and row.get("workspace")]
    regrades, regraded = regrade(run, name, items, grades, grade_cap)
    fresh, differing = recompute(run, name, rows, regrades, summary)
    return {"count_mismatches": counts + differing, "grade_mismatches": grades, "regraded": regraded, "summary": fresh, "oracle": None}


def crosscheck(run: Run, results: dict, tasks: dict[str, delivered.Task], *, grade_cap: float, jobs: int = 3,
               checked: dict | None = None) -> dict:
    """The gate's input over every run: members against their invocation logs, built-ins from the kit's own records.
    `summaries` holds each run's recomputed summary, the one the metrics score from."""
    names = sorted(results, key=lambda n: (n.startswith("@"), n))

    def one(name):
        try:
            if name.startswith("@"):
                return check_builtin(run, name, results[name]["out"], grade_cap=grade_cap)
            return check_member(run, name, results[name]["out"], tasks, grade_cap=grade_cap, checked=checked)
        except Exception:  # noqa: BLE001 - one run's crash must not hide the others
            return {"count_mismatches": [{"member": name, "kind": "crosscheck-error", "detail": traceback.format_exc()[-300:]}],
                    "grade_mismatches": [], "regraded": 0, "summary": None, "oracle": None}

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        found = list(pool.map(one, names))
    counts = [item for one in found for item in one["count_mismatches"]]
    grades = [item for one in found for item in one["grade_mismatches"]]
    return {"pass": not (counts or grades), "count_mismatches": counts, "grade_mismatches": grades,
            "regraded": sum(one["regraded"] for one in found),
            "members": {m: {"count_mismatches": len(one["count_mismatches"]), "grade_mismatches": len(one["grade_mismatches"]),
                            "regraded": one["regraded"], "oracle": one["oracle"]} for m, one in zip(names, found)},
            "summaries": {m: one["summary"] for m, one in zip(names, found)}}
