"""The meta-verification report: `assemble` builds report.json and `render` writes report.md. Pure.

report.md lists the gates first, then one row per metric with its interval, then the contradicted claims,
the measured gaps and the conditions. There is no composite score.
"""

import json

from . import metrics as scoring

GATES = ("G1_executability", "G2_reference_and_floor", "crosscheck", "staging")


def assemble(*, meta_task: str, build: str, arm: str, pool: str, gates: dict, metrics: dict, claims: dict | None = None,
             builder: dict | None = None, copied_reference_files=(), conditions=()) -> dict:
    """report.json from the parts. `claims` is `claims.score_claims`' result, filed as M9; the scoring
    constants are echoed into `conditions` ahead of the run's own."""
    out = {k: v for k, v in metrics.items() if k not in ("M9_claims", "speed", "builder")}
    out["M9_claims"] = claims or scoring.not_computed("no card claims scored")
    if "speed" in metrics:
        out["speed"] = metrics["speed"]
    out["builder"] = builder or {"seconds": None, "cost_usd": None, "out_of_workspace_reads": []}
    disclosed = set((claims or {}).get("disclosed_gaps") or [])
    gaps = [{"category": category, "evidence": evidence, "disclosed": category in disclosed}
            for category, evidence in ((claims or {}).get("measured_gaps") or {}).items()]
    return {"meta_task": meta_task, "build": build, "arm": arm, "pool": pool, "gates": gates, "metrics": out,
            "copied_reference_files": list(copied_reference_files), "conditions": scoring.conditions() + list(conditions),
            "gaps": gaps}


def _f(x, digits: int = 2) -> str:
    return "n/a" if x is None else f"{x:.{digits}f}"


def _ci(interval) -> str:
    return f" ({scoring.INTERVAL_LEVEL:.0%} interval {interval[0]:.2f} to {interval[1]:.2f})" if interval else ""


def _count(items) -> int:
    return len(items) if isinstance(items, list) else 0


def _cell(text) -> str:
    return str(text).replace("|", "/").replace("\n", " ")


def _gate_detail(name: str, gate: dict) -> str:
    if name == "G1_executability":
        text = (f"preflight exit {gate.get('preflight_exit')}; {gate.get('member_runs')} member runs; schema-valid share "
                f"{_f(gate.get('schema_valid_share'))}; infrastructure error share {_f(gate.get('infrastructure_error_share'), 3)}"
                + (f"; interrupted by the usage limit: {', '.join(gate['interrupted_runs'])}" if gate.get("interrupted_runs") else ""))
    elif name == "G2_reference_and_floor":
        text = (f"reference pass rate {_f(gate.get('reference_pass_rate'))}; no-op full success on "
                f"{_count(gate.get('noop_full_success_tasks'))} tasks; no-op mean credit {_f(gate.get('noop_mean_credit'))}")
    elif name == "crosscheck":
        text = f"{_count(gate.get('count_mismatches'))} count mismatches; {_count(gate.get('grade_mismatches'))} grade mismatches"
    else:
        text = f"{_count(gate.get('cheater_findings'))} cheater findings; {_count(gate.get('warnings'))} name-only warnings"
    reasons = gate.get("reasons") or []
    return text + (f". Failed: {'; '.join(map(str, reasons))}" if reasons else "")


def _m1(m: dict) -> str:
    classes = ", ".join(f"{k} {_f(v.get('mean_credit'))}" for k, v in (m.get("credit_by_class") or {}).items())
    return (f"hackable-task ratio {_f(m.get('hackable_task_ratio'))}{_ci(m.get('ci90'))} over {m.get('tasks')} tasks "
            f"({', '.join(m.get('hackable_tasks') or []) or 'none'}); credit by class: {classes}")


def _m2(m: dict) -> str:
    return (f"pair accuracy {_f(m.get('pair_accuracy'))}{_ci(m.get('ci90'))} over {m.get('pairs')} pairs; tau-b {_f(m.get('tau_b'))}; "
            f"null p {_f(m.get('null_p'), 4)}; {_count(m.get('contradicted'))} contradicted, {_count(m.get('unresolved'))} unresolved")


def _m3(m: dict) -> str:
    inert = [k for k, v in (m.get("exercised_share") or {}).items() if v == 0]
    origin = ", ".join(f"{k} {_f(v)}" for k, v in (m.get("by_origin") or {}).items())
    return (f"killed {m.get('killed')} of {m.get('killable')} killable defects, rate {_f(m.get('rate'))}{_ci(m.get('ci90'))}; by origin: {origin}"
            f"; never exercised: {', '.join(inert) or 'none'}")


def _m4(m: dict) -> str:
    return (f"must-resolve recall {_f(m.get('resolution_recall'))}{_ci(m.get('ci90'))}; A/A false separation "
            f"{_f(m.get('aa_false_separation'))} over {_count(m.get('aa_pairs'))} pairs; {_count(m.get('reversed'))} contrasts reversed")


def _m5(m: dict) -> str:
    return (f"test-retest tau-b {_f(m.get('test_retest_tau_b'))}; decision accuracy {_f(m.get('decision_accuracy'))}; "
            f"pooled run-to-run SD {_f(m.get('pooled_sd'), 3)}; SNR {_f(m.get('snr'))}")


def _m6(m: dict) -> str:
    return (f"TPR {_f(m.get('tpr'))}{_ci(m.get('tpr_ci90'))}, TNR {_f(m.get('tnr'))}{_ci(m.get('tnr_ci90'))}; oracle coverage "
            f"{_f(m.get('oracle_coverage'))} ({m.get('tasks_covered')} of {m.get('tasks_total')} tasks); "
            f"{_count(m.get('false_rejects'))} false rejects, {_count(m.get('false_accepts'))} false accepts")


def _m7(m: dict) -> str:
    parts = [f"{k} {_count(m[k]) if isinstance(m.get(k), list) else 'n/a'}" for k in ("reference_fail", "floor_credit", "flat", "inverted")]
    return f"informative share {_f(m.get('informative_share'))} of {m.get('tasks')} tasks; flagged: {', '.join(parts)}"


def _m8(m: dict) -> str:
    return (f"LLM scores {_f(m.get('min'))} to {_f(m.get('max'))}; floor share {_f(m.get('floor_share'))}; "
            f"ceiling share {_f(m.get('ceiling_share'))}; weakest {m.get('weakest')}, strongest {m.get('strongest')}")


def _m9(m: dict) -> str:
    return (f"{m.get('checkable')} of {m.get('claims')} claims checkable; contradicted {_count(m.get('contradicted'))} "
            f"(rate {_f(m.get('contradiction_rate'))}); underclaimed {_count(m.get('underclaimed'))}; uncheckable "
            f"{_count(m.get('uncheckable'))}; vacuous {_count(m.get('vacuous'))}; gap recall {_f(m.get('gap_recall'))}; "
            f"gap precision {_f(m.get('gap_precision'))}; verdict agreement {m.get('verdict_agreement')}")


def _speed(m: dict) -> str:
    compared = m.get('compared_members')
    scope = (f" over {compared} members whose agent is most of each attempt ({m.get('not_compared_members')} not "
             f"compared)" if compared is not None else "")
    return (f"overlap reported {_f(m.get('achieved_overlap_reported'), 1)}, measured "
            f"{_f(m.get('achieved_overlap_measured'), 1)}{scope}, declared concurrency {m.get('declared_concurrency')}")


def _builder(m: dict) -> str:
    return (f"build seconds {_f(m.get('seconds'), 0)}; cost {_f(m.get('cost_usd'))}; "
            f"{_count(m.get('out_of_workspace_reads'))} out-of-workspace reads")


_METRICS = {"M1_cheaters": _m1, "M2_order": _m2, "M3_kill": _m3, "M4_contrasts": _m4, "M5_reliability": _m5,
            "M6_verifier": _m6, "M7_task_profile": _m7, "M8_range": _m8, "M9_claims": _m9, "speed": _speed, "builder": _builder}


def _metric_row(name: str, value) -> str:
    if isinstance(value, dict) and value.get("computed") is False:
        return f"not computed: {value.get('reason')}"
    fmt = _METRICS.get(name)
    return fmt(value) if fmt else json.dumps(value, sort_keys=True, default=str)[:300]


def _condition(item) -> str:
    return f"- {item['name']}: {item['value']}" if isinstance(item, dict) and "name" in item else f"- {item}"


def render(report: dict) -> str:
    """report.md: gates first, then one row per metric, the contradicted claims, the gaps and the conditions."""
    gates, metrics = report.get("gates") or {}, report.get("metrics") or {}
    lines = [f"# Meta-verification: {report.get('meta_task')}", "",
             f"Build {report.get('build')}, arm {report.get('arm')}, pool {report.get('pool')}.", "", "## Gates", "",
             "| Gate | Result | Detail |", "| --- | --- | --- |"]
    for name in GATES:
        gate = gates.get(name) or {}
        lines.append(f"| {name} | {'pass' if gate.get('pass') is True else 'FAIL'} | {_cell(_gate_detail(name, gate))} |")
    if not all((gates.get(name) or {}).get("pass") is True for name in GATES):
        lines += ["", "A failed gate is reported, not averaged away; metrics computed below a failed gate are unreliable."]
    lines += ["", "## Metrics", "", "| Metric | Result |", "| --- | --- |"]
    lines += [f"| {name} | {_cell(_metric_row(name, value))} |" for name, value in metrics.items()]
    claims = metrics.get("M9_claims") or {}
    lines += ["", "## Contradicted claims", ""]
    lines += [f"- {c.get('id')} ({c.get('type')}): {c.get('direction')}; claimed {c.get('claimed')}, measured {c.get('measured')}"
              + (f" ({c['reason']})" if c.get("reason") else "") for c in claims.get("contradicted") or []] or ["None."]
    lines += ["", "## Gaps", ""]
    lines += [f"- {g.get('category')}: {'; '.join(map(str, g.get('evidence') or []))} "
              f"({'disclosed' if g.get('disclosed') else 'not disclosed'})" for g in report.get("gaps") or []] or ["None measured."]
    if report.get("copied_reference_files"):
        lines += ["", "## Files copied from the reference packages", ""] + [f"- {f}" for f in report["copied_reference_files"]]
    conditions = report.get("conditions") or []
    if isinstance(conditions, dict):
        conditions = [{"name": k, "value": v} for k, v in conditions.items()]
    lines += ["", "## Conditions", ""] + [_condition(c) for c in conditions]
    return "\n".join(lines) + "\n"
