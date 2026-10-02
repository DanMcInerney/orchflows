"""Grade validation, per-task metrics, run summaries and paired comparisons. Standard library only.

Execution status, grading status and task success stay separate. A unit is one
task repeat; its final attempt (highest retry) decides its outcome, so quality
counts use planned units while `launched` counts every attempt including
retries.
"""

import math
from datetime import datetime

from . import stats

SCORED = {"completed", "refused", "cut-off", "agent-budget-exhausted"}
UNSCORED = {"infrastructure-error", "canceled", "interrupted", "not-launched"}
STATUS_ORDER = ("completed", "refused", "cut-off", "agent-budget-exhausted",
                "infrastructure-error", "canceled", "interrupted", "not-launched")
_GRADING_STATUSES = ("scored", "indeterminate", "unscored")
_WEIGHT_TOLERANCE = 1e-6
_CREDIT_TOLERANCE = 1e-3


class _Violation(Exception):
    pass


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _unit(x) -> bool:
    return _num(x) and 0.0 <= x <= 1.0


def _why(head: str, text) -> str:
    return f"{head}: {text}" if text else head


def _grade(status: str, reason: str, **fields) -> dict:
    grade = {"grading_status": status, "full_success": None, "credit": None, "credit_bounds": None,
             "dimensions": {}, "critical_failures": [], "reason": reason}
    grade.update(fields)
    return grade


def _weighted(dimensions: dict) -> tuple[float | None, float, float]:
    """(credit, lower, upper) from `{name: {credit, weight, required}}`.

    Weights must be nonnegative and sum to 1, credits in [0, 1] or None
    (unjudged). An unjudged required dimension (`required` defaults to true)
    makes the credit None, with bounds that fill it with 0 and 1. An unjudged
    optional dimension earns 0 in credit and both bounds.
    """
    weights, lower, upper, unjudged_required = [], [], [], False
    for name, dim in dimensions.items():
        if not isinstance(dim, dict):
            raise _Violation(f"dimension {name!r} is not an object")
        weight, credit, required = dim.get("weight"), dim.get("credit"), dim.get("required", True)
        if not _num(weight) or weight < 0:
            raise _Violation(f"dimension {name!r} weight must be a nonnegative number")
        if credit is not None and not _unit(credit):
            raise _Violation(f"dimension {name!r} credit {credit!r} outside [0, 1]")
        if not isinstance(required, bool):
            raise _Violation(f"dimension {name!r} required must be true or false")
        weights.append(weight)
        if credit is None:
            unjudged_required = unjudged_required or required
            lower.append(0.0)
            upper.append(1.0 if required else 0.0)
        else:
            lower.append(credit)
            upper.append(credit)
    if abs(math.fsum(weights) - 1.0) > _WEIGHT_TOLERANCE:
        raise _Violation(f"dimension weights sum to {math.fsum(weights):.6g}, not 1")
    low = math.fsum(w * c for w, c in zip(weights, lower))
    high = math.fsum(w * c for w, c in zip(weights, upper))
    return (None if unjudged_required else low), low, high


def _bounds(value) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(_unit(v) for v in value) and value[0] <= value[1]:
        return [float(value[0]), float(value[1])]
    return None


def _scored_grade(raw: dict, reason: str) -> dict:
    full = raw.get("full_success")
    if not isinstance(full, bool):
        raise _Violation("full_success must be true or false")
    failures = raw.get("critical_failures") or []
    if not isinstance(failures, list):
        raise _Violation("critical_failures must be a list")
    if failures and full:
        raise _Violation("critical failure with full_success true")
    dimensions = raw.get("dimensions") or {}
    if not isinstance(dimensions, dict):
        raise _Violation("dimensions must be an object")
    credit = raw.get("credit")
    if credit is not None and not _unit(credit):
        raise _Violation(f"credit {credit!r} outside [0, 1]")
    if dimensions:
        derived, low, high = _weighted(dimensions)
        if derived is None and credit is not None:
            raise _Violation("credit given while a required dimension is unjudged")
        if derived is not None and credit is not None and abs(credit - derived) > _CREDIT_TOLERANCE:
            raise _Violation(f"credit {credit} disagrees with the weighted dimensions ({derived:.6g})")
        credit, bounds = derived, [low, high]
    elif credit is None:
        bounds = _bounds(raw.get("credit_bounds")) or [0.0, 1.0]
    else:
        bounds = [float(credit), float(credit)]
    return _grade("scored", reason, full_success=full, credit=None if credit is None else float(credit),
                  credit_bounds=bounds, dimensions=dimensions, critical_failures=failures)


def validate_grade(raw: dict | None, reason: str = "") -> dict:
    """Normalize a verifier result into `{grading_status, full_success, credit, credit_bounds,
    dimensions, critical_failures, reason}`.

    - No result (None or not an object) is `unscored` with `reason`: the verifier
      crashed or produced nothing.
    - A scored result that breaks the contract is `indeterminate` with the
      violation as its reason: `full_success` not a boolean, a critical failure
      with `full_success` true, a credit or dimension credit outside [0, 1],
      dimension weights that are negative or do not sum to 1, a credit that
      disagrees with the weighted dimensions, or a credit given while a
      required dimension is unjudged.
    - Credit is the weighted dimension sum when dimensions exist, else the
      reported credit; `credit_bounds` is [credit, credit], or [0-filled,
      1-filled] when credit is None.

    Idempotent: a normalized grade validates to itself.
    """
    if not isinstance(raw, dict):
        return _grade("unscored", reason or "no verifier result")
    status, why = raw.get("grading_status"), str(raw.get("reason") or reason or "")
    if status in ("indeterminate", "unscored"):
        return _grade(status, why or f"verifier reported {status}")
    if status != "scored":
        return _grade("indeterminate", f"contract violation: grading_status {status!r}")
    try:
        return _scored_grade(raw, why)
    except _Violation as violation:
        return _grade("indeterminate", f"contract violation: {violation}")


def _row_credit(row: dict) -> tuple[float | None, float, float]:
    credit = row.get("credit")
    if _unit(credit):
        return float(credit), float(credit), float(credit)
    if row.get("dimensions"):
        try:
            return _weighted(row["dimensions"])
        except _Violation:
            pass
    low, high = _bounds(row.get("credit_bounds")) or (0.0, 1.0)
    return None, low, high


def _final_attempts(attempts: list[dict], planned_repeats: int) -> dict[int, dict]:
    finals: dict[int, dict] = {}
    for row in attempts:
        repeat = row.get("repeat")
        if not isinstance(repeat, int) or not 1 <= repeat <= planned_repeats:
            raise ValueError(f"attempt repeat {repeat!r} outside 1..{planned_repeats}")
        if row.get("status") not in STATUS_ORDER:
            raise ValueError(f"unknown execution status {row.get('status')!r}")
        current = finals.get(repeat)
        if current is None or row.get("retry", 0) >= current.get("retry", 0):
            finals[repeat] = row
    return finals


def task_metrics(attempts: list[dict], planned_repeats: int) -> dict:
    """Metrics for one task from its attempt rows (B.3 `attempts.jsonl` shape).

    Each repeat is judged by its final attempt. A repeat is scored when that
    attempt's status is in SCORED and its `grading_status` is `scored`; every
    other repeat, including one with no row, is unscored and listed in
    `excluded`. Rates and credit average the scored repeats; the scored count is
    the denominator, and `missing_repeats` is planned minus scored.

    Full success defeats on any critical failure, whatever `full_success` says.
    `mean_credit` is None when any scored repeat's credit is unavailable, with
    `credit_bounds` the mean of the per-repeat lower and upper bounds (None when
    nothing was scored). `critical_failures` counts scored repeats with at least
    one critical failure.

    Returns {planned, scored, passed, failed, missing_repeats, full_success_rate,
    mean_credit, credit_bounds, critical_failures, statuses, excluded}.
    """
    finals = _final_attempts(attempts, planned_repeats)
    statuses: dict[str, int] = {}
    excluded, credits = [], []
    passed = critical = 0
    for repeat in range(1, planned_repeats + 1):
        row = finals.get(repeat)
        if row is None:
            statuses["not-launched"] = statuses.get("not-launched", 0) + 1
            excluded.append({"repeat": repeat, "reason": "not-launched: no attempt record"})
            continue
        status = row["status"]
        statuses[status] = statuses.get(status, 0) + 1
        grading = row.get("grading_status")
        if status in SCORED and grading == "scored":
            failures = row.get("critical_failures") or []
            critical += bool(failures)
            passed += row.get("full_success") is True and not failures
            credits.append(_row_credit(row))
        elif status in SCORED:
            excluded.append({"repeat": repeat, "reason": _why(
                f"{status}, grading {grading or 'missing'}", row.get("grade_reason") or row.get("reason"))})
        else:
            excluded.append({"repeat": repeat, "reason": _why(status, row.get("reason"))})
    scored = len(credits)
    mean = math.fsum(c for c, _, _ in credits) / scored if scored and all(c is not None for c, _, _ in credits) else None
    bounds = [math.fsum(lo for _, lo, _ in credits) / scored, math.fsum(hi for _, _, hi in credits) / scored] if scored else None
    return {"planned": planned_repeats, "scored": scored, "passed": passed, "failed": scored - passed,
            "missing_repeats": planned_repeats - scored,
            "full_success_rate": passed / scored if scored else None,
            "mean_credit": mean, "credit_bounds": bounds, "critical_failures": critical,
            "statuses": statuses, "excluded": excluded}


def _resolve_weights(tasks: dict[str, dict], weights: dict | None) -> dict[str, float] | None:
    if weights is None:
        declared = {t: meta["weight"] for t, meta in tasks.items() if meta.get("weight") is not None}
        if not declared:
            return None
        if len(declared) != len(tasks):
            raise ValueError(f"weight declared for only {len(declared)} of {len(tasks)} tasks")
        weights = declared
    if set(weights) != set(tasks):
        raise ValueError("weights must name exactly the suite's tasks")
    if not all(_num(w) and w >= 0 for w in weights.values()) or abs(math.fsum(weights.values()) - 1.0) > _WEIGHT_TOLERANCE:
        raise ValueError("task weights must be nonnegative and sum to 1")
    return dict(weights)


def _rollup(task_ids: list[str], metrics: dict[str, dict], tasks: dict[str, dict], weights: dict | None) -> dict:
    """Headline metrics over non-anchor tasks; each task's repeat-averaged value is weighted.

    Weights apply to tasks with at least one scored repeat, renormalized over
    them (equal weights when none are declared). `mean_credit` is None when any
    included task's is, with `credit_bounds` the weighted bounds.
    """
    members = [t for t in task_ids if not tasks[t].get("anchor")]
    included = [t for t in members if metrics[t]["scored"]]
    share = {t: (weights[t] if weights else 1.0) for t in included}
    total = math.fsum(share.values())

    def weighted(pick):
        return math.fsum(share[t] * pick(metrics[t]) for t in included) / total if included and total > 0 else None

    credit_known = all(metrics[t]["mean_credit"] is not None for t in included)
    return {"full_success_rate": weighted(lambda m: m["full_success_rate"]),
            "mean_credit": weighted(lambda m: m["mean_credit"]) if credit_known else None,
            "credit_bounds": [weighted(lambda m: m["credit_bounds"][0]), weighted(lambda m: m["credit_bounds"][1])]
            if included and total > 0 else None,
            "critical_failures": sum(metrics[t]["critical_failures"] for t in members),
            "scored_tasks": len(included),
            "missing_repeats": sum(metrics[t]["missing_repeats"] for t in members),
            "anchors_excluded": len(task_ids) - len(members)}


def _moment(text) -> datetime | None:
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def _peak_concurrency(rows: list[dict]) -> int | None:
    events = []
    for row in rows:
        start, end = _moment(row.get("started")), _moment(row.get("finished"))
        if start and end:
            events += [(start, 1), (end, -1)]
    peak = running = 0
    for _, step in sorted(events, key=lambda e: (e[0], e[1])):
        running += step
        peak = max(peak, running)
    return peak if events else None


def _wall_seconds(run: dict, rows: list[dict]) -> float | None:
    if _num(run.get("wall_seconds")):
        return float(run["wall_seconds"])
    begin, end = _moment(run.get("started")), _moment(run.get("finished"))
    if not (begin and end):
        starts = [m for m in (_moment(r.get("started")) for r in rows) if m]
        ends = [m for m in (_moment(r.get("finished")) for r in rows) if m]
        begin, end = (min(starts), max(ends)) if starts and ends else (None, None)
    return round((end - begin).total_seconds(), 3) if begin and end else None


def summarize(attempts: list[dict], tasks: dict[str, dict], run: dict, *, weights: dict | None = None) -> dict:
    """The `summary.json` document (B.3) from attempt rows.

    `tasks` maps each task planned in this run to its metadata (`family`,
    `source_group`, `anchor`, optional `weight`); an attempt for any other task
    raises ValueError. `run` supplies `profile`, `agent`, `repeats` (else the
    highest repeat seen), `jobs`, `started`, `finished`, `suite_name`,
    `deadline_reached`, `observed_versions` and, when the scheduler measured
    them, `wall_seconds`, `peak_concurrency`, `setup_seconds`, `grading_seconds`
    and `execution_seconds`. Wall time, peak concurrency and attempt-seconds
    otherwise come from the rows; anything unknowable stays None.

    Counts: `planned` is tasks x repeats; `launched` and `retries` count every
    attempt row that ran; `completed`, `scored`, `passed`, `failed`,
    `unscored` (planned - scored, so canceled, interrupted and not-launched
    units are in it), `canceled`, `not_launched` and `by_status` count units by
    their final attempt. `overall` and `families` exclude anchor tasks
    (`anchors_excluded`), which stay in `tasks`; see `task_metrics` and
    `_rollup` for averaging and weights. `weights` (or each task's `weight`
    when all declare one) must be nonnegative and sum to 1.
    """
    weights = _resolve_weights(tasks, weights)
    seen = [row["repeat"] for row in attempts if isinstance(row.get("repeat"), int)]
    repeats = run.get("repeats") or max(seen, default=0)
    if repeats < 1:
        raise ValueError("run['repeats'] is missing and there are no attempts to infer it from")
    by_task: dict[str, list[dict]] = {t: [] for t in tasks}
    for row in attempts:
        if row.get("task") not in by_task:
            raise ValueError(f"attempt for task {row.get('task')!r}, which is not in this run's tasks")
        by_task[row["task"]].append(row)
    metrics = {t: task_metrics(rows, repeats) for t, rows in by_task.items()}

    by_status = {status: sum(m["statuses"].get(status, 0) for m in metrics.values()) for status in STATUS_ORDER}
    ran = [row for row in attempts if row.get("status") != "not-launched"]
    seconds = math.fsum(row["seconds"] for row in ran if _num(row.get("seconds")))
    known_cost = [row["cost_usd"] for row in ran if _num(row.get("cost_usd"))]
    scored = sum(m["scored"] for m in metrics.values())
    wall = _wall_seconds(run, attempts)
    setup, grading, execution = run.get("setup_seconds"), run.get("grading_seconds"), run.get("execution_seconds")
    if execution is None and None not in (wall, setup, grading):
        execution = round(wall - setup - grading, 3)

    families: dict[str, list[str]] = {}
    for task in tasks:
        families.setdefault(str(tasks[task].get("family") or "unknown"), []).append(task)
    return {
        "suite": {"name": run.get("suite_name"), "tasks": len(tasks)},
        "run": {"profile": run.get("profile"), "agent": run.get("agent"), "repeats": repeats, "jobs": run.get("jobs"),
                "started": run.get("started"), "finished": run.get("finished"), "wall_seconds": wall,
                "attempt_seconds_sum": round(seconds, 3),
                "achieved_overlap": round(seconds / wall, 3) if wall else None,
                "peak_concurrency": run.get("peak_concurrency") or _peak_concurrency(ran),
                "deadline_reached": bool(run.get("deadline_reached", False)),
                "observed_versions": dict(run.get("observed_versions") or {})},
        "counts": {"planned": len(tasks) * repeats, "launched": len(ran), "completed": by_status["completed"],
                   "scored": scored, "passed": sum(m["passed"] for m in metrics.values()),
                   "failed": sum(m["failed"] for m in metrics.values()), "unscored": len(tasks) * repeats - scored,
                   "canceled": by_status["canceled"], "not_launched": by_status["not-launched"],
                   "retries": sum(1 for row in ran if row.get("retry", 0) > 0), "by_status": by_status},
        "overall": _rollup(list(tasks), metrics, tasks, weights),
        "families": {family: _rollup(ids, metrics, tasks, weights) for family, ids in families.items()},
        "tasks": {t: {"family": str(tasks[t].get("family") or "unknown"),
                      "source_group": tasks[t].get("source_group") or t, "anchor": bool(tasks[t].get("anchor")),
                      "planned": m["planned"], "scored": m["scored"], "full_success_rate": m["full_success_rate"],
                      "mean_credit": m["mean_credit"], "critical_failures": m["critical_failures"],
                      "statuses": m["statuses"]} for t, m in metrics.items()},
        "cost": {"usd_known": round(math.fsum(known_cost), 6),
                 "attempts_with_unknown_cost": len(ran) - len(known_cost)},
        "time": {"setup_seconds": setup, "execution_seconds": execution, "grading_seconds": grading,
                 "total_seconds": wall},
        "exclusions": [{"task": t, **item} for t, m in metrics.items() for item in m["excluded"]],
    }


def paired(a: dict, b: dict, *, metric: str, clusters: dict[str, str] | None = None, exclude_anchors: bool = True,
           direction: str = "two-sided") -> dict:
    """Per-task paired differences a - b of a `tasks` metric, with cluster-level inference.

    `a` and `b` are summaries (or their `tasks` maps). `metric` is a per-task
    value such as `full_success_rate` or `mean_credit`. A task is `common`
    when both sides have the metric available; a task available on one side
    only is in `only_a` or `only_b`. A task flagged `anchor` in either summary
    is left out and listed in `anchors_excluded` unless `exclude_anchors` is
    false. `ties` counts tasks with no difference.

    Tasks fall in clusters by `clusters[task]`, else the task's `source_group`,
    else the task id. The estimate is the mean of the per-task differences
    (`mean_diff`). Inference treats each cluster as one observation: cluster g
    contributes G * (sum of its task differences) / N, so the contributions
    average to `mean_diff` and a cluster's weight follows its size. `sign_flip_p`
    is the sign-flip randomization p-value of those contributions
    (`direction` "two-sided", or "greater" for a > b, or "less") and `ci95` is
    their wild cluster Rademacher percentile interval (None below two
    clusters). `clusters` in the result maps each cluster to its mean
    difference; `method` states the exact or sampled procedures used.
    """
    alternative = stats.check_alternative(direction)
    tasks_a = a["tasks"] if "tasks" in a and "suite" in a else a
    tasks_b = b["tasks"] if "tasks" in b and "suite" in b else b
    clusters = clusters or {}
    per_task: dict[str, float] = {}
    only_a, only_b, anchors = [], [], []
    for task in sorted(set(tasks_a) | set(tasks_b)):
        entry_a, entry_b = tasks_a.get(task, {}), tasks_b.get(task, {})
        if exclude_anchors and (entry_a.get("anchor") or entry_b.get("anchor")):
            anchors.append(task)
            continue
        value_a, value_b = entry_a.get(metric), entry_b.get(metric)
        if _num(value_a) and _num(value_b):
            per_task[task] = value_a - value_b
        elif _num(value_a):
            only_a.append(task)
        elif _num(value_b):
            only_b.append(task)

    groups: dict[str, list[float]] = {}
    for task, diff in per_task.items():
        entry = tasks_a.get(task) or tasks_b[task]
        groups.setdefault(clusters.get(task) or entry.get("source_group") or task, []).append(diff)
    n, g = len(per_task), len(groups)
    contributions = [g * math.fsum(diffs) / n for diffs in groups.values()] if n else []
    p = stats.sign_flip_p(contributions, alternative=alternative) if n else None
    ci = stats.wild_cluster_ci(contributions, level=0.95) if g >= 2 else None
    return {"common": n, "only_a": only_a, "only_b": only_b, "anchors_excluded": anchors,
            "ties": sum(1 for d in per_task.values() if abs(d) < 1e-12),
            "mean_diff": math.fsum(per_task.values()) / n if n else None,
            "per_task": per_task,
            "clusters": {name: math.fsum(diffs) / len(diffs) for name, diffs in groups.items()},
            "sign_flip_p": p, "ci95": list(ci) if ci else None,
            "method": {"estimate": "mean of per-task differences (a - b)", "clusters": g, "direction": alternative,
                       "p": None if not n else "exact sign-flip" if g <= stats.SIGN_FLIP_EXACT_MAX
                       else "sampled sign-flip",
                       "ci95": None if ci is None else "exact wild cluster Rademacher" if g <= stats.WILD_EXACT_MAX
                       else "sampled wild cluster Rademacher"}}
