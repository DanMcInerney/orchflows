"""Gates G1-G2 and metrics M1-M8 of a delivered benchmark, computed from the pool runs.

Pure functions over records: no process launching, no file I/O. Needs `benchkit` on `sys.path`. No
composite score; a metric that cannot be computed is `{"computed": false, "reason": ...}`, never a zero.

A run record is `{"summary": <summary.json>, "attempts": [...], "invocations": [...], "wall_seconds":
float, "replicates": [<summary.json>, ...]}`; only `summary` is required and a bare summary is accepted.
`member_runs` maps pool member ids to run records; the keys "@reference" and "@noop" hold the package's
own built-in runs. `order` is the pool's ORDER.json. A member's score is the benchmark's own aggregate,
`overall[metric]` (default mean_credit). Statistics come from `benchkit.stats` and `aggregate.paired`
(each delivered task is its own cluster, so builder-declared source groups cannot change the power to
detect a difference; anchors are excluded).

Scoring constants, echoed into report.json `conditions` by `conditions()`:
    ALPHA              0.05  kill and false-separation tests; a kill is a one-sided sign-flip p < ALPHA in
                             the constructed direction (oracle above defect)
    INTERVAL_LEVEL     0.90  bootstrap and Clopper-Pearson intervals; claims are checked against it
    BOOTSTRAP_DRAWS    1000  task-cluster bootstrap draws for the order-accuracy interval (it re-aggregates
                             with equal task weights)
    HACKABLE_FRACTION  0.5   a task is hackable when any floor or cheater earns full success on it, or
                             credit of at least this fraction of the oracle's, which must be positive
    NOOP_CREDIT_MAX    0.1   G2: highest mean credit a no-op may earn
    INFRASTRUCTURE_SHARE_MAX 0.05  G1: highest share of planned units lost to infrastructure errors
    VACUOUS_WIDTH      0.9   M9: an interval or target claim at least this wide is flagged vacuous
A designated contrast is resolved when its paired 95% interval excludes zero in the right direction and
reversed when it excludes zero the other way.
"""

import itertools
import math
import random
import statistics

from benchkit import aggregate, stats

ALPHA = 0.05
INTERVAL_LEVEL = 0.90
BOOTSTRAP_DRAWS = 1000
HACKABLE_FRACTION = 0.5
NOOP_CREDIT_MAX = 0.1
INFRASTRUCTURE_SHARE_MAX = 0.05
VACUOUS_WIDTH = 0.9
SCORE_METRIC = "mean_credit"
SEED = 0
GOOD_LABELS = ("valid", "correct-infeasible")
TRIVIAL = ("floor", "cheater")
ATTEMPTING = ("oracle", "defect", "ladder", "heuristic", "llm", "private", "other")
_EPS = 1e-9


def conditions() -> list[dict]:
    """The scoring constants as report `conditions` entries."""
    return [{"name": name, "value": value} for name, value in (
        ("alpha", ALPHA), ("interval_level", INTERVAL_LEVEL), ("bootstrap_draws", BOOTSTRAP_DRAWS),
        ("hackable_fraction", HACKABLE_FRACTION), ("noop_credit_max", NOOP_CREDIT_MAX),
        ("infrastructure_share_max", INFRASTRUCTURE_SHARE_MAX), ("vacuous_width", VACUOUS_WIDTH),
        ("score_metric", SCORE_METRIC), ("seed", SEED),
        ("kill", "one-sided sign-flip p < alpha, oracle above defect"),
        ("resolved", "paired 95% interval excludes 0 in the right direction"))]


def not_computed(reason: str, **extra) -> dict:
    return {"computed": False, "reason": reason, **extra}


def blocked(reason: str) -> dict:
    """Every metric undefined, for a build whose gates failed."""
    return {key: not_computed(reason) for key in (
        "M1_cheaters", "M2_order", "M3_kill", "M4_contrasts", "M5_reliability", "M6_verifier", "M7_task_profile",
        "M8_range", "speed")}


def summary_of(run: dict | None) -> dict | None:
    if not run:
        return None
    return run["summary"] if "summary" in run else run


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return math.fsum(values) / len(values) if values else None


def score(summary: dict | None, metric: str) -> float | None:
    value = ((summary or {}).get("overall") or {}).get(metric)
    return float(value) if _num(value) else None


def task_values(summary: dict | None, metric: str) -> dict[str, float]:
    """The metric per non-anchor task, where available."""
    return {task: float(row[metric]) for task, row in ((summary or {}).get("tasks") or {}).items()
            if not row.get("anchor") and _num(row.get(metric))}


def proportion(k: int, n: int) -> dict | None:
    """A rate with its 90% Clopper-Pearson interval, or None for an empty denominator."""
    if not n:
        return None
    low, high = stats.clopper_pearson(k, n, INTERVAL_LEVEL)
    return {"estimate": k / n, "low": low, "high": high, "k": k, "n": n}


def _ci(rate: dict | None) -> list[float] | None:
    return [rate["low"], rate["high"]] if rate else None


def role(spec: dict) -> str:
    """oracle|defect|ladder|heuristic|floor|cheater for scripted members; else llm, private or other."""
    return (spec.get("behavior") or "other") if spec.get("kind") == "scripted" else (spec.get("kind") or "other")


def resolution(paired: dict | None) -> str:
    """'higher', 'lower' or 'unresolved' from a paired comparison's 95% interval."""
    ci = (paired or {}).get("ci95")
    return "unresolved" if not ci else "higher" if ci[0] > 0 else "lower" if ci[1] < 0 else "unresolved"


class Pool:
    """The pool runs, ORDER.json and a memo of paired comparisons for one metrics() call."""

    def __init__(self, member_runs: dict, order: dict, metric: str):
        self.order = order or {}
        self.specs = self.order.get("members") or {}
        self.metric = metric
        self.runs = {m: r for m, r in member_runs.items() if not m.startswith("@")}
        self.builtin = {m: r for m, r in member_runs.items() if m.startswith("@")}
        self._paired: dict = {}

    def summary(self, member: str) -> dict | None:
        return summary_of(self.runs.get(member) or self.builtin.get(member))

    def score(self, member: str) -> float | None:
        return score(self.summary(member), self.metric)

    def values(self, member: str, metric: str | None = None) -> dict[str, float]:
        return task_values(self.summary(member), metric or self.metric)

    def role(self, member: str) -> str:
        return role(self.specs.get(member, {}))

    def ids(self, *roles: str) -> list[str]:
        return sorted(m for m in self.runs if self.summary(m) and self.role(m) in roles)

    def trivial(self) -> list[str]:
        return [*self.ids(*TRIVIAL), *(m for m in ("@noop",) if self.summary(m))]

    def paired(self, higher: str, lower: str, direction: str = "two-sided") -> dict | None:
        a, b = self.summary(higher), self.summary(lower)
        if not a or not b:
            return None
        if (higher, lower, direction) not in self._paired:
            tasks = {t: t for t in (*a.get("tasks", {}), *b.get("tasks", {}))}
            self._paired[higher, lower, direction] = aggregate.paired(
                a, b, metric=self.metric, clusters=tasks, direction=direction)
        return self._paired[higher, lower, direction]

    def known_pairs(self) -> list[tuple[str, str]]:
        return [(p["higher"], p["lower"]) for p in self.order.get("known_pairs") or []]


# ---- gates ----------------------------------------------------------------------------------------

def _g1(execs: dict | None) -> dict:
    execs = execs or {}
    preflight = (execs.get("preflight") or {}).get("exit_code")
    members = execs.get("members") or {}
    failed, planned_total, infra_total = [], 0, 0
    for member, entry in sorted(members.items()):
        counts = (entry.get("summary") or {}).get("counts") or {}
        planned = entry.get("planned", counts.get("planned")) or 0
        infra = entry.get("infrastructure_errors", (counts.get("by_status") or {}).get("infrastructure-error")) or 0
        problem = None
        if entry.get("status", "completed") != "completed" or entry.get("exit_code") != 0:
            problem = entry.get("reason") or f"status {entry.get('status')}, exit {entry.get('exit_code')}"
        elif entry.get("schema_valid") is not True:
            problem = entry.get("reason") or "records failed schema validation"
        if problem:
            failed.append({"member": member, "reason": problem})
            planned = infra = planned or 1
        planned_total += planned
        infra_total += infra
    share = infra_total / planned_total if planned_total else None
    reasons = ([f"preflight exit {preflight}"] if preflight != 0 else []) + ([] if members else ["no member runs"])
    reasons += [f"{f['member']}: {f['reason']}" for f in failed]
    if share is not None and share > INFRASTRUCTURE_SHARE_MAX:
        reasons.append(f"infrastructure error share {share:.3f} above {INFRASTRUCTURE_SHARE_MAX}")
    valid = sum(entry.get("schema_valid") is True for entry in members.values())
    return {"pass": not reasons, "preflight_exit": preflight, "member_runs": len(members),
            "schema_valid_share": valid / len(members) if members else None,
            "infrastructure_error_share": share, "failed_runs": failed, "reasons": reasons}


def _g2(reference_run: dict | None, noop_run: dict | None) -> dict:
    reasons, rate, failed, noop_tasks, noop_credit = [], None, [], [], None
    reference, noop = summary_of(reference_run), summary_of(noop_run)
    if reference is None:
        reasons.append("reference run missing")
    else:
        tasks = reference.get("tasks") or {}
        failed = sorted(t for t, row in tasks.items() if not (row.get("scored") and (row.get("full_success_rate") or 0) >= 1 - _EPS))
        rate = (len(tasks) - len(failed)) / len(tasks) if tasks else None
        if rate != 1.0:
            reasons.append(f"reference solved {len(tasks) - len(failed)} of {len(tasks)} tasks")
    if noop is None:
        reasons.append("no-op run missing")
    else:
        noop_tasks = sorted(t for t, row in (noop.get("tasks") or {}).items() if (row.get("full_success_rate") or 0) > 0)
        overall = noop.get("overall") or {}
        noop_credit = overall.get("mean_credit")
        if noop_credit is None and overall.get("credit_bounds"):
            noop_credit = overall["credit_bounds"][0]
        if noop_tasks:
            reasons.append(f"no-op earned full success on {len(noop_tasks)} tasks")
        if noop_credit is None:
            reasons.append("no-op credit unavailable")
        elif noop_credit > NOOP_CREDIT_MAX:
            reasons.append(f"no-op mean credit {noop_credit:.3f} above {NOOP_CREDIT_MAX}")
    return {"pass": not reasons, "reference_pass_rate": rate, "reference_failed_tasks": failed,
            "noop_full_success_tasks": noop_tasks, "noop_mean_credit": noop_credit, "reasons": reasons}


def gates(execs: dict | None, reference_run: dict | None, noop_run: dict | None,
          crosscheck: dict | None, staging) -> dict:
    """G1 executability, G2 reference and floor, crosscheck and staging; each non-compensatory.

    `execs` is `{"preflight": {"exit_code"}, "members": {id: {"exit_code", "status" (the meta-verifier's
    capped run: completed|timeout|error|canceled), "schema_valid", "reason", "planned",
    "infrastructure_errors", "summary"}}}`; planned and infrastructure_errors default from `summary`. A
    run the meta-verifier killed or that crashed counts all its planned units as infrastructure errors.
    `crosscheck` is `{"count_mismatches": [...], "grade_mismatches": [...]}` and `staging` the findings
    cheaters logged (a list, or a dict holding `cheater_findings`). A check not run fails.
    """
    if crosscheck is None:
        cross = {"pass": False, "count_mismatches": [], "grade_mismatches": [], "reasons": ["crosscheck not run"]}
    else:
        counts, grades = list(crosscheck.get("count_mismatches") or []), list(crosscheck.get("grade_mismatches") or [])
        cross = {**crosscheck, "count_mismatches": counts, "grade_mismatches": grades, "pass": not (counts or grades)}
    if staging is None:
        stage = {"pass": False, "cheater_findings": [], "reasons": ["staging check not run"]}
    else:
        found = list(staging.get("cheater_findings") or []) if isinstance(staging, dict) else list(staging)
        stage = {"pass": not found, "cheater_findings": found}
    return {"G1_executability": _g1(execs), "G2_reference_and_floor": _g2(reference_run, noop_run),
            "crosscheck": cross, "staging": stage}


def gates_pass(result: dict) -> bool:
    return all((result.get(key) or {}).get("pass") is True
               for key in ("G1_executability", "G2_reference_and_floor", "crosscheck", "staging"))


# ---- M1 cheaters, M2 order ------------------------------------------------------------------------

def _m1(pool: Pool) -> dict:
    members = pool.trivial()
    if not members:
        return not_computed("no floor or cheater members")
    oracle = (pool.ids("oracle") or [None])[0]
    base = pool.summary(oracle) if oracle else pool.summary("@reference")
    base_credit, base_overall = task_values(base, "mean_credit"), score(base, "mean_credit")
    classes: dict[str, list[str]] = {}
    for member in members:
        spec = pool.specs.get(member, {})
        classes.setdefault(spec.get("name") or spec.get("behavior") or member, []).append(member)
    by_class = {}
    for name, ids in sorted(classes.items()):
        credit = mean(score(pool.summary(m), "mean_credit") for m in ids)
        by_class[name] = {"role": role(pool.specs[ids[0]]) if ids[0] in pool.specs else "floor", "members": ids,
                          "mean_credit": credit,
                          "full_success_rate": mean(score(pool.summary(m), "full_success_rate") for m in ids),
                          "relative_to_oracle": credit / base_overall if credit is not None and base_overall else None}
    universe, hackable = set(), {}
    for member in members:
        full, credit = pool.values(member, "full_success_rate"), pool.values(member, "mean_credit")
        universe |= set(full) | set(credit)
        for task in set(full) | set(credit):
            reference = base_credit.get(task, 0)
            earns = reference > _EPS and credit.get(task, 0) > _EPS and credit[task] >= HACKABLE_FRACTION * reference - _EPS
            if full.get(task, 0) > _EPS or earns:
                hackable.setdefault(task, []).append(member)
    ratio = proportion(len(hackable), len(universe))
    return {"credit_by_class": by_class, "hackable_task_ratio": ratio["estimate"] if ratio else None, "ci90": _ci(ratio),
            "hackable_tasks": sorted(hackable), "hackable_by": {t: sorted(m) for t, m in sorted(hackable.items())},
            "tasks": len(universe), "oracle": oracle}


def tau_b_known(scores: dict[str, float], pairs: list[tuple[str, str]]) -> float | None:
    """Kendall's tau-b over the known (higher, lower) pairs: (C - D) / sqrt(K (K - ties)).

    It equals `stats.kendall_tau_b` against the reference order when the known pairs order every pair of
    members. None when every known pair is tied in the scores.
    """
    concordant = discordant = ties = 0
    for higher, lower in pairs:
        diff = scores[higher] - scores[lower]
        ties += diff == 0
        concordant += diff > 0
        discordant += diff < 0
    denominator = math.sqrt(len(pairs) * (len(pairs) - ties))
    return (concordant - discordant) / denominator if denominator else None


def _quantile(sorted_values: list[float], q: float) -> float:
    return sorted_values[min(max(math.ceil(q * len(sorted_values) - 1e-9) - 1, 0), len(sorted_values) - 1)]


def _accuracy_interval(pool: Pool, pairs: list[tuple[str, str]], seed: int) -> list[float] | None:
    involved = sorted({m for pair in pairs for m in pair})
    values = {m: pool.values(m) for m in involved}
    groups: dict[str, list[str]] = {}
    for task in sorted(set().union(*values.values())):
        groups.setdefault(task, []).append(task)
    if not groups:
        return None
    rng, names, draws = random.Random(seed), list(groups), []
    for _ in range(BOOTSTRAP_DRAWS):
        tasks = [t for g in (rng.choice(names) for _ in names) for t in groups[g]]
        accuracy = stats.pair_accuracy({m: mean(values[m][t] for t in tasks if t in values[m]) for m in involved}, pairs)
        if not math.isnan(accuracy):
            draws.append(accuracy)
    draws.sort()
    tail = (1 - INTERVAL_LEVEL) / 2
    return [_quantile(draws, tail), _quantile(draws, 1 - tail)] if draws else None


def _pair_row(higher: str, lower: str, paired: dict | None) -> dict:
    return {"higher": higher, "lower": lower, "mean_diff": (paired or {}).get("mean_diff"), "ci95": (paired or {}).get("ci95")}


def _m2(pool: Pool, seed: int) -> dict:
    known = pool.known_pairs()
    scores = {m: pool.score(m) for m in pool.runs}
    scorable = [(h, l) for h, l in known if scores.get(h) is not None and scores.get(l) is not None]
    if not scorable:
        return not_computed("no known pair has scores for both members", known_pairs=len(known))
    accuracy = stats.pair_accuracy(scores, scorable)
    contradicted, unresolved = [], []
    for higher, lower in scorable:
        paired = pool.paired(higher, lower)
        outcome = resolution(paired)
        if outcome != "higher":
            (contradicted if outcome == "lower" else unresolved).append(_pair_row(higher, lower, paired))
    return {"metric": pool.metric, "pairs": len(scorable), "pair_accuracy": accuracy,
            "ci90": _accuracy_interval(pool, scorable, seed), "tau_b": tau_b_known(scores, scorable),
            "null_p": stats.order_null_p(sorted({m for p in scorable for m in p}), scorable, accuracy),
            "ties": sum(scores[h] == scores[l] for h, l in scorable), "contradicted": contradicted,
            "unresolved": unresolved, "unscorable": [list(p) for p in known if p not in scorable],
            "unconfirmed_excluded": len(pool.order.get("unconfirmed") or [])}


# ---- M3 kill, M4 contrasts ------------------------------------------------------------------------

def _exercised(captures: dict | None, member: str) -> float | None:
    results = [r for rs in ((captures or {}).get(member) or {}).values() for r in rs if r.get("recognized", True)]
    return sum(r.get("label") not in GOOD_LABELS for r in results) / len(results) if results else None


def _m3(pool: Pool, captures: dict | None) -> dict:
    killable = pool.order.get("killable") or {}
    defects = sorted(m for m in pool.runs
                     if pool.role(m) == "defect" or m in killable or (pool.specs.get(m) or {}).get("harness_defect"))
    if not defects:
        return not_computed("no defect members in the pool")
    counted = [m for m in defects if (killable.get(m) or {}).get("confirmed") is True]
    equivalent = [m for m in defects if (killable.get(m) or {}).get("confirmed") is False]
    unconfirmed = [m for m in defects if m not in counted and m not in equivalent]
    if not counted:
        return not_computed("no confirmed killable defects", excluded_equivalent=equivalent, excluded_unconfirmed=unconfirmed)
    oracle = (pool.ids("oracle") or [None])[0]
    detail = []
    for member in counted:
        higher = oracle or next((h for h, l in pool.known_pairs() if l == member), None)
        one, two = pool.paired(higher, member, "greater"), pool.paired(higher, member)
        p = (one or {}).get("sign_flip_p")
        detail.append({"member": member, "against": higher, "killed": p is not None and p < ALPHA, "p": p,
                       "ci95": (two or {}).get("ci95"), "mean_diff": (two or {}).get("mean_diff"),
                       "origin": (pool.specs.get(member) or {}).get("origin") or "unknown"})
    killed = [d["member"] for d in detail if d["killed"]]
    by_origin = {o: sum(d["killed"] for d in detail if d["origin"] == o) / sum(d["origin"] == o for d in detail)
                 for o in sorted({d["origin"] for d in detail})}
    rate = proportion(len(killed), len(counted))
    return {"killable": len(counted), "killed": len(killed), "rate": rate["estimate"], "ci90": _ci(rate),
            "killed_members": killed, "excluded_equivalent": equivalent, "excluded_unconfirmed": unconfirmed,
            "by_origin": by_origin, "exercised_share": {m: _exercised(captures, m) for m in counted}, "detail": detail}


def _m4(pool: Pool) -> dict:
    contrasts, aa_pairs = pool.order.get("contrasts") or [], pool.order.get("aa_pairs") or []
    if not contrasts and not aa_pairs:
        return not_computed("no designated contrasts or A/A pairs")
    designated = []
    for c in contrasts:
        paired = pool.paired(c["higher"], c["lower"])
        outcome = resolution(paired) if paired else "unavailable"
        designated.append({**_pair_row(c["higher"], c["lower"], paired), "must_resolve": bool(c.get("must_resolve")),
                           "resolved": outcome == "higher", "reversed": outcome == "lower"})
    must = [d for d in designated if d["must_resolve"]]
    recall = proportion(sum(d["resolved"] for d in must), len(must))
    aa = []
    for a, b in aa_pairs:
        p = (pool.paired(a, b) or {}).get("sign_flip_p")
        if p is not None:
            aa.append({"pair": [a, b], "p": p, "separated": p < ALPHA})
    return {"designated": designated, "resolution_recall": recall["estimate"] if recall else None, "ci90": _ci(recall),
            "reversed": [[d["higher"], d["lower"]] for d in designated if d["reversed"]], "aa_pairs": aa,
            "aa_false_separation": sum(a["separated"] for a in aa) / len(aa) if aa else None}


# ---- M5 reliability, M6 verifier, M7 task profile, M8 range, speed --------------------------------

def _m5(pool: Pool) -> dict:
    series = {}
    for member, run in pool.runs.items():
        values = [pool.score(member)] + [score(s, pool.metric) for s in run.get("replicates") or []]
        if len(values) >= 2 and None not in values:
            series[member] = values
    if len(series) < 2:
        return not_computed("single full run per member")
    ids = sorted(series)
    first, second = [series[m][0] for m in ids], [series[m][1] for m in ids]
    sign = lambda x, y: (x > y) - (x < y)  # noqa: E731
    pairs = list(itertools.combinations(range(len(ids)), 2))
    agree = sum(sign(first[i], first[j]) == sign(second[i], second[j]) for i, j in pairs)
    sds = {m: statistics.stdev(series[m]) for m in ids}
    pooled = math.sqrt(math.fsum(v * v for v in sds.values()) / len(sds))
    means = [statistics.fmean(series[m]) for m in ids]
    tau = stats.kendall_tau_b(first, second)
    return {"members": len(ids), "test_retest_tau_b": None if math.isnan(tau) else tau, "decision_accuracy": agree / len(pairs),
            "noise_sd": sds, "pooled_sd": pooled, "snr": (max(means) - min(means)) / pooled if pooled > 0 else None}


def _m6(labels_m6: dict | None) -> dict:
    return labels_m6 or not_computed("no labelled-submission scoring supplied")


def _m7(pool: Pool) -> dict:
    out = {"reference_fail": not_computed("no @reference run"), "floor_credit": not_computed("no floor, cheater or @noop run"),
           "flat": not_computed("fewer than two attempting members"), "inverted": not_computed("no known pairs")}
    if pool.summary("@reference"):
        out["reference_fail"] = sorted(t for t, v in task_values(pool.summary("@reference"), "full_success_rate").items() if v < 1 - _EPS)
    trivial = pool.trivial()
    if trivial:
        earned: dict[str, dict] = {}
        for member in trivial:
            full = pool.values(member, "full_success_rate")
            for task, credit in pool.values(member, "mean_credit").items():
                if credit > _EPS or full.get(task, 0) > _EPS:
                    row = earned.setdefault(task, {"task": task, "members": [], "max_credit": 0.0})
                    row["members"].append(member)
                    row["max_credit"] = max(row["max_credit"], credit)
        out["floor_credit"] = [earned[t] for t in sorted(earned)]
    attempting = {m: pool.values(m) for m in pool.ids(*ATTEMPTING)}
    if len(attempting) >= 2:
        out["flat"] = sorted(t for t in set().union(*attempting.values())
                             if len(vs := [v[t] for v in attempting.values() if t in v]) >= 2 and max(vs) - min(vs) <= _EPS)
    everyone = {m: pool.values(m) for m in pool.runs}
    if pool.known_pairs():
        margin = {}
        for a, b in pool.order.get("aa_pairs") or []:
            for task in set(everyone.get(a, {})) & set(everyone.get(b, {})):
                margin[task] = max(margin.get(task, 0.0), abs(everyone[a][task] - everyone[b][task]))
        inverted: dict[str, list] = {}
        for higher, lower in pool.known_pairs():
            for task in set(everyone.get(higher, {})) & set(everyone.get(lower, {})):
                if everyone[lower][task] - everyone[higher][task] > margin.get(task, 0.0) + _EPS:
                    inverted.setdefault(task, []).append([higher, lower])
        out["inverted"] = [{"task": t, "pairs": inverted[t]} for t in sorted(inverted)]
    tasks = set().union(*everyone.values()) if everyone else set()
    flags = [i["task"] if isinstance(i, dict) else i for v in out.values() if isinstance(v, list) for i in v]
    out["informative_share"] = len(tasks - set(flags)) / len(tasks) if tasks else None
    out["flags_used"] = [k for k, v in out.items() if isinstance(v, list)]
    out["tasks"] = len(tasks)
    return out


def _m8(pool: Pool) -> dict:
    ids = pool.ids("llm")
    if not ids:
        return not_computed("no LLM members")
    scores = {m: pool.score(m) for m in ids if pool.score(m) is not None}
    values = {m: pool.values(m) for m in ids}
    tasks = sorted(set.intersection(*[set(v) for v in values.values()]))
    open_scores = {m: s for m, s in scores.items() if _EPS < s < 1 - _EPS}
    share = lambda hit: sum(all(hit(values[m][t]) for m in ids) for t in tasks) / len(tasks) if tasks else None  # noqa: E731
    return {"members": scores, "min": min(scores.values(), default=None), "max": max(scores.values(), default=None),
            "range": max(scores.values()) - min(scores.values()) if scores else None,
            "floor_share": share(lambda v: v <= _EPS), "ceiling_share": share(lambda v: v >= 1 - _EPS),
            "weakest": min(open_scores, key=open_scores.get) if open_scores else None,
            "strongest": max(open_scores, key=open_scores.get) if open_scores else None, "tasks": len(tasks)}


def _speed(pool: Pool) -> dict:
    walls, reported, measured, jobs = {}, {}, {}, []
    for member, run in {**pool.runs, **pool.builtin}.items():
        info = (summary_of(run) or {}).get("run") or {}
        wall = run.get("wall_seconds") if _num(run.get("wall_seconds")) else info.get("wall_seconds")
        walls[member] = wall
        if _num(info.get("achieved_overlap")):
            reported[member] = float(info["achieved_overlap"])
        seconds = [r["seconds"] for r in run.get("invocations") or [] if _num(r.get("seconds"))]
        if seconds and _num(wall) and wall > 0:
            measured[member] = math.fsum(seconds) / wall
        jobs += [info["jobs"]] if _num(info.get("jobs")) else []
    return {"full_wall_seconds": walls, "achieved_overlap_reported": mean(reported.values()),
            "achieved_overlap_measured": mean(measured.values()), "declared_concurrency": max(jobs, default=None),
            "overlap_by_member": {m: {"reported": reported.get(m), "measured": measured.get(m)} for m in walls
                                  if m in reported or m in measured}}


def metrics(member_runs: dict[str, dict], order: dict, labels_m6: dict | None, captures_checked: dict | None, *,
            metric: str = SCORE_METRIC, seed: int = SEED) -> dict:
    """M1-M8 and speed for the pool.

    `labels_m6` is `labeled.score_labels`' result. `captures_checked` maps member id -> task ->
    [`{"label", "recognized", "reasons"}`], the domain checker's verdict on each captured final
    workspace; M3's `exercised_share` is the share of those whose label is not valid or
    correct-infeasible. Returns the report's `metrics` entries except M9 and `builder`.
    """
    pool = Pool(member_runs, order, metric)
    return {"M1_cheaters": _m1(pool), "M2_order": _m2(pool, seed), "M3_kill": _m3(pool, captures_checked),
            "M4_contrasts": _m4(pool), "M5_reliability": _m5(pool), "M6_verifier": _m6(labels_m6),
            "M7_task_profile": _m7(pool), "M8_range": _m8(pool), "speed": _speed(pool)}
