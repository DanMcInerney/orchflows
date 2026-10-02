"""M9: a quality card's typed claims scored against what the meta-verifier measured.

Every claim is checked against a measurement, never by reading prose. `measure` builds the `measured`
record from the pool runs and the M1-M8 results; `score_claims` compares it with the card's claims
(B.4 shapes: interval, order, rate, noise, target, cost, verdict, gap). Needs `benchkit` on `sys.path`.

A claim is contradicted when the measured interval and the claimed range are disjoint (interval, target),
a bound is violated (rate, noise, cost) or the order is resolved the other way. `direction` says where the
measurement lies relative to the claim: measured-above, measured-below or reversed. An interval claim whose
measurement lies above it is also listed as underclaimed. A claim with nothing to check is uncheckable,
which is separate from false; a claim the evidence neither confirms nor contradicts is inconclusive.
Interval claims get a Gneiting-Raftery interval score (lower is better); intervals and rates that cannot
exclude anything are listed as vacuous.

`measured`:
    systems  {card system name: None | {"member", "metrics": {metric: {"estimate", "low", "high"}},
              "noise": {metric: {"sd", "n"}}, "cost_usd", "cost_complete", "wall_seconds"}}
    rates    {metric: {"estimate", "low", "high"}}    trivial_credit, reference_pass_rate,
             verifier_false_accept, verifier_false_reject, hackable_task_ratio, defect_kill_rate
    orders   {claim id: {"outcome": higher|lower|unresolved, "mean_diff", "ci95"}}
    defects  {gap category: [evidence]} for the defects measured; `checked` lists the categories that
             were measurable in this run; `verdict` is {"supports_claim": bool | None}.
"""

import math
import statistics

from benchkit import aggregate, stats

from . import metrics as scoring

SCORES = ("full_success_rate", "mean_credit")
MEASURABLE = ("hackable-task", "unresolved-contrast", "verifier-false-reject", "verifier-false-accept", "floor",
              "ceiling", "unprotected-boundary")
CATEGORIES = MEASURABLE + ("inert-dimension", "exposure", "missing-stage")
_Z = statistics.NormalDist().inv_cdf(1 - (1 - scoring.INTERVAL_LEVEL) / 2)
_EPS = 1e-9


def systems(card: dict, order: dict) -> dict[str, str | None]:
    """Card system name -> pool member id: "@reference" or "@noop" for built-in agents, else the LLM
    member without a harness defect that has the condition's model and effort."""
    specs = (order or {}).get("members") or {}
    out = {}
    for name, cond in (card.get("conditions") or {}).items():
        agent = str((cond or {}).get("agent") or "")
        match = [] if agent.startswith("@") or not (cond or {}).get("model") else sorted(
            m for m, s in specs.items() if s.get("kind") == "llm" and not s.get("harness_defect")
            and s.get("model") == cond.get("model") and s.get("effort") == cond.get("effort"))
        out[name] = agent if agent.startswith("@") else (match[0] if match else None)
    return out


def _interval(summary: dict, metric: str) -> dict | None:
    """Estimate with the wider of the task-cluster and (for full success) unit-binomial 90% intervals."""
    estimate = scoring.score(summary, metric)
    if estimate is None:
        return None
    rows = {t: r for t, r in (summary.get("tasks") or {}).items() if not r.get("anchor") and scoring._num(r.get(metric))}
    clusters: dict[str, list[float]] = {}
    for task, row in rows.items():
        clusters.setdefault(row.get("source_group") or task, []).append(row[metric])
    low = high = estimate
    if len(clusters) >= 2:
        lo, hi = stats.wild_cluster_ci([scoring.mean(v) for v in clusters.values()], level=scoring.INTERVAL_LEVEL)
        low, high = min(low, lo), max(high, hi)
    n = sum(r.get("scored") or 0 for r in rows.values())
    if metric == "full_success_rate" and n:
        passed = round(sum(r[metric] * (r.get("scored") or 0) for r in rows.values()))
        lo, hi = stats.clopper_pearson(passed, n, scoring.INTERVAL_LEVEL)
        low, high = min(low, lo), max(high, hi)
    return {"estimate": estimate, "low": max(low, 0.0), "high": min(high, 1.0)}


def _defects(results: dict) -> tuple[dict, list]:
    """Measured defects by gap category, and the categories this run could measure."""
    def ok(m):
        return bool(m) and m.get("computed") is not False

    found, checked = {}, []
    m1, m3, m4, m6, m7, m8 = (results.get(k) or {} for k in (
        "M1_cheaters", "M3_kill", "M4_contrasts", "M6_verifier", "M7_task_profile", "M8_range"))
    if ok(m1):
        checked.append("hackable-task")
        if m1.get("hackable_tasks"):
            found["hackable-task"] = [f"hackable tasks: {', '.join(m1['hackable_tasks'])}"]
    if ok(m4):
        checked.append("unresolved-contrast")
        missed = [f"{d['higher']} over {d['lower']}" for d in m4.get("designated", []) if d["must_resolve"] and not d["resolved"]]
        if missed:
            found["unresolved-contrast"] = missed
    if ok(m6):
        for category, key, label in (("verifier-false-reject", "false_rejects", "valid outputs rejected"),
                                     ("verifier-false-accept", "false_accepts", "wrong outputs accepted")):
            checked.append(category)
            if m6.get(key):
                found[category] = [f"{len(m6[key])} {label}"]
    if isinstance(m7.get("floor_credit"), list):
        checked.append("floor")
        if m7["floor_credit"]:
            found["floor"] = [f"floor credit on {len(m7['floor_credit'])} tasks"]
    if ok(m8) and m8.get("ceiling_share") is not None:
        checked.append("ceiling")
        if m8["ceiling_share"] > 0:
            found["ceiling"] = [f"every LLM member at ceiling on {m8['ceiling_share']:.0%} of tasks"]
    if ok(m3):
        checked.append("unprotected-boundary")
        alive = [d["member"] for d in m3.get("detail", []) if not d["killed"]]
        if alive:
            found["unprotected-boundary"] = [f"defect not killed: {', '.join(alive)}"]
    return found, checked


def _rates(member_runs: dict, results: dict) -> dict:
    rates = {}
    m1, m3, m6 = (results.get(k) or {} for k in ("M1_cheaters", "M3_kill", "M6_verifier"))
    members = [m for c in (m1.get("credit_by_class") or {}).values() for m in c["members"]]
    scored = {m: scoring.score(scoring.summary_of(member_runs.get(m)), "mean_credit") for m in members}
    scored = {m: s for m, s in scored.items() if s is not None}
    if scored:
        rates["trivial_credit"] = _interval(scoring.summary_of(member_runs[max(scored, key=scored.get)]), "mean_credit")
    reference = scoring.summary_of(member_runs.get("@reference"))
    if reference and reference.get("tasks"):
        tasks = reference["tasks"].values()
        rates["reference_pass_rate"] = scoring.proportion(
            sum(bool(t.get("scored")) and (t.get("full_success_rate") or 0) >= 1 - _EPS for t in tasks), len(reference["tasks"]))
    if m6.get("computed") is not False and m6:
        rates["verifier_false_accept"] = scoring.proportion(len(m6.get("false_accepts") or []), m6.get("negatives") or 0)
        rates["verifier_false_reject"] = scoring.proportion(len(m6.get("false_rejects") or []), m6.get("positives") or 0)
    if m1.get("tasks"):
        rates["hackable_task_ratio"] = scoring.proportion(len(m1.get("hackable_tasks") or []), m1["tasks"])
    if m3.get("killable"):
        rates["defect_kill_rate"] = scoring.proportion(m3["killed"], m3["killable"])
    return {k: v for k, v in rates.items() if v}


def _cid(claim: dict, index: int) -> str:
    return str(claim.get("id") or f"claim-{index + 1}")


def measure(card: dict, order: dict, member_runs: dict, results: dict, *, verdict: bool | None = None) -> dict:
    """The `measured` record for `score_claims`.

    `member_runs` and `order` are as for `metrics.metrics` and `results` is its result. A system's
    noise is the standard deviation of its score across its member, replicate full runs and A/A partner.
    """
    names = systems(card, order)
    partner = {m: p for a, b in (order or {}).get("aa_pairs") or [] for m, p in ((a, b), (b, a))}
    measured_systems = {}
    for name, member in names.items():
        run = member_runs.get(member) if member else None
        summary = scoring.summary_of(run)
        if not summary:
            measured_systems[name] = None
            continue
        entry = {"member": member, "metrics": {}, "noise": {}}
        for metric in SCORES:
            if (interval := _interval(summary, metric)):
                entry["metrics"][metric] = interval
            values = [scoring.score(summary, metric)] + [scoring.score(s, metric) for s in run.get("replicates") or []]
            values.append(scoring.score(scoring.summary_of(member_runs.get(partner.get(member))), metric))
            values = [v for v in values if v is not None]
            if len(values) >= 2:
                entry["noise"][metric] = {"sd": statistics.stdev(values), "n": len(values)}
        cost = summary.get("cost") or {}
        entry.update({"cost_usd": cost.get("usd_known"), "cost_complete": cost.get("attempts_with_unknown_cost") == 0,
                      "wall_seconds": run.get("wall_seconds") or (summary.get("run") or {}).get("wall_seconds")})
        measured_systems[name] = entry
    orders = {}
    for index, claim in enumerate(card.get("claims") or []):
        if claim.get("type") != "order":
            continue
        a = scoring.summary_of(member_runs.get(names.get(claim.get("higher"))))
        b = scoring.summary_of(member_runs.get(names.get(claim.get("lower"))))
        if a and b:
            paired = aggregate.paired(a, b, metric=claim.get("metric", scoring.SCORE_METRIC))
            orders[_cid(claim, index)] = {"outcome": scoring.resolution(paired), "mean_diff": paired["mean_diff"], "ci95": paired["ci95"]}
    defects, checked = _defects(results)
    return {"systems": measured_systems, "rates": _rates(member_runs, results), "orders": orders,
            "defects": defects, "checked": checked, "verdict": {"supports_claim": verdict}}


# ---- claim checks ---------------------------------------------------------------------------------

def _unchecked(reason: str) -> dict:
    return {"status": "uncheckable", "reason": reason}


def _range_result(claimed: list, found: dict, *, level: float | None = None) -> dict:
    low, high = claimed
    estimate = found["estimate"]
    result = {"status": "consistent", "claimed": claimed, "measured": [found["low"], found["high"]], "estimate": estimate}
    if found["high"] < low - _EPS:
        result.update(status="contradicted", direction="measured-below")
    elif found["low"] > high + _EPS:
        result.update(status="contradicted", direction="measured-above")
    if level is not None:
        alpha = 1 - level
        result["interval_score"] = (high - low) + 2 / alpha * (max(low - estimate, 0) + max(estimate - high, 0))
    return result


def _system_metric(measured: dict, claim: dict) -> tuple[dict | None, str]:
    entry = (measured.get("systems") or {}).get(claim.get("system"))
    if not entry:
        return None, f"system {claim.get('system')!r} was not measured"
    found = (entry.get("metrics") or {}).get(claim.get("metric"))
    return found, "" if found else f"{claim.get('metric')!r} was not measured for {claim.get('system')!r}"


def _interval_claim(claim: dict, measured: dict, _cid: str = "") -> dict:
    found, why = _system_metric(measured, claim)
    if found is None:
        return _unchecked(why)
    result = _range_result([claim["low"], claim["high"]], found, level=claim.get("level", scoring.INTERVAL_LEVEL))
    result["width"] = claim["high"] - claim["low"]
    return result


def _target_claim(claim: dict, measured: dict, _cid: str = "") -> dict:
    found, why = _system_metric(measured, claim)
    return _unchecked(why) if found is None else _range_result([claim["low"], claim["high"]], found)


def _rate_claim(claim: dict, measured: dict, _cid: str = "") -> dict:
    found = (measured.get("rates") or {}).get(claim.get("metric"))
    if not found:
        return _unchecked(f"rate {claim.get('metric')!r} was not measured")
    result = {"status": "consistent", "claimed": [claim.get("min"), claim.get("max")], "measured": [found["low"], found["high"]],
              "estimate": found["estimate"]}
    if claim.get("max") is not None and found["low"] > claim["max"] + _EPS:
        result.update(status="contradicted", direction="measured-above")
    elif claim.get("min") is not None and found["high"] < claim["min"] - _EPS:
        result.update(status="contradicted", direction="measured-below")
    return result


def _noise_claim(claim: dict, measured: dict, _cid: str = "") -> dict:
    entry = (measured.get("systems") or {}).get(claim.get("system"))
    noise = ((entry or {}).get("noise") or {}).get(claim.get("metric"))
    if not noise:
        return _unchecked("no repeated run or A/A partner measured the system's noise")
    sd, count = noise["sd"], noise["n"]
    lower = sd - _Z * sd / math.sqrt(2 * (count - 1))
    status = "contradicted" if lower > claim["sd_max"] else "inconclusive" if sd > claim["sd_max"] else "consistent"
    return {"status": status, "claimed": [None, claim["sd_max"]], "measured": [lower, sd], "estimate": sd,
            **({"direction": "measured-above"} if status == "contradicted" else {})}


def _cost_claim(claim: dict, measured: dict, _cid: str = "") -> dict:
    entry = (measured.get("systems") or {}).get(claim.get("system"))
    if not entry:
        return _unchecked(f"system {claim.get('system')!r} was not measured")
    if claim.get("profile", "full") != "full":
        return _unchecked("only the full profile is measured")
    over, open_ = [], False
    for key, value in (("usd_max", entry.get("cost_usd")), ("wall_seconds_max", entry.get("wall_seconds"))):
        if claim.get(key) is None:
            continue
        if value is None:
            open_ = True
        elif value > claim[key]:
            over.append(f"{key.removesuffix('_max')} {value:.4g} above {claim[key]}")
        elif key == "usd_max" and not entry.get("cost_complete"):
            open_ = True
    if over:
        return {"status": "contradicted", "direction": "measured-above", "reason": "; ".join(over)}
    if open_:
        return {"status": "inconclusive", "reason": "some cost or time was not measured"}
    return {"status": "consistent"}


def _order_claim(claim: dict, measured: dict, cid: str) -> dict:
    found = (measured.get("orders") or {}).get(cid)
    if not found:
        return _unchecked("one of the systems was not measured")
    if found["outcome"] == "lower":
        return {"status": "contradicted", "direction": "reversed", "measured": found["ci95"], "estimate": found["mean_diff"]}
    if found["outcome"] == "unresolved" and claim.get("resolved"):
        return {"status": "inconclusive", "reason": "the measured order is not resolved", "measured": found["ci95"]}
    return {"status": "consistent", "measured": found["ci95"], "estimate": found["mean_diff"]}


_CHECKS = {"interval": _interval_claim, "target": _target_claim, "rate": _rate_claim, "noise": _noise_claim,
           "cost": _cost_claim, "order": _order_claim}


def _vacuous(claim: dict) -> bool:
    kind = claim.get("type")
    if kind in ("interval", "target"):
        return claim["high"] - claim["low"] >= scoring.VACUOUS_WIDTH - _EPS
    if kind == "rate":
        return (claim.get("max") is not None and claim["max"] >= 1) or (claim.get("min") is not None and claim["min"] <= 0)
    return False


def score_claims(card: dict, measured: dict) -> dict:
    """M9: contradicted, underclaimed, inconclusive, uncheckable and vacuous claims, interval scores, gap
    recall and precision, and agreement of the card's verdict with the measured one."""
    claims = card.get("claims") or []
    if not claims:
        return scoring.not_computed("card has no claims")
    results, gaps, verdicts = {}, [], []
    for index, claim in enumerate(claims):
        cid, kind = _cid(claim, index), claim.get("type")
        if kind == "gap":
            gaps.append(claim)
        elif kind == "verdict":
            verdicts.append(claim)
        else:
            check = _CHECKS.get(kind)
            try:
                result = check(claim, measured, cid) if check else _unchecked(f"unknown claim type {kind!r}")
            except (KeyError, TypeError, ValueError) as error:
                result = _unchecked(f"malformed claim: {error!r}")
            results[cid] = {**result, "id": cid, "type": kind, "vacuous": _safe_vacuous(claim)}
    checkable = [r for r in results.values() if r["status"] != "uncheckable"]
    contradicted = [{k: r.get(k) for k in ("id", "type", "direction", "claimed", "measured", "estimate", "reason")}
                    for r in results.values() if r["status"] == "contradicted"]
    underclaimed = [r["id"] for r in results.values() if r["type"] == "interval" and r.get("direction") == "measured-above"]
    found, checked = measured.get("defects") or {}, set(measured.get("checked") or [])
    disclosed = {g.get("category") for g in gaps if g.get("category") in CATEGORIES}
    confirmable = disclosed & checked & set(MEASURABLE)
    agreement = None
    seen = (measured.get("verdict") or {}).get("supports_claim")
    if verdicts and seen is not None:
        agreement = all(bool(v.get("supports_claim")) == seen for v in verdicts)
    if not checkable and not gaps and not verdicts:
        return scoring.not_computed("no checkable claims", uncheckable=[{"id": r["id"], "reason": r["reason"]} for r in results.values()],
                                    vacuous=[r["id"] for r in results.values() if r["vacuous"]])
    return {"claims": len(claims), "checkable": len(checkable), "contradicted": contradicted, "underclaimed": underclaimed,
            "inconclusive": [r["id"] for r in results.values() if r["status"] == "inconclusive"],
            "uncheckable": [{"id": r["id"], "reason": r["reason"]} for r in results.values() if r["status"] == "uncheckable"]
            + [{"id": _cid(g, i), "reason": f"unknown gap category {g.get('category')!r}"}
               for i, g in enumerate(claims) if g.get("type") == "gap" and g.get("category") not in CATEGORIES],
            "vacuous": [r["id"] for r in results.values() if r["vacuous"]],
            "contradiction_rate": len(contradicted) / len(checkable) if checkable else None,
            "underclaim_rate": len(underclaimed) / len(checkable) if checkable else None,
            "interval_scores": {r["id"]: {"score": r["interval_score"], "width": r["width"]}
                                for r in results.values() if "interval_score" in r},
            "gap_recall": len(set(found) & disclosed) / len(found) if found else None,
            "gap_precision": len(confirmable & set(found)) / len(confirmable) if confirmable else None,
            "disclosed_gaps": sorted(disclosed), "measured_gaps": found, "verdict_agreement": agreement}


def _safe_vacuous(claim: dict) -> bool:
    try:
        return _vacuous(claim)
    except (KeyError, TypeError):
        return False
