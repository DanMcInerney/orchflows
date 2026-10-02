"""`verify`: meta-verify one delivered package against one pool and write report.json and report.md.

Intake, preflight, a run per pool member and per built-in agent, the domain checker's verdict on every captured final
workspace, the crosscheck (regrades, recomputed summaries, agreement with the checker) and the staging findings, the
labelled-submission check of the verifier (M6), then the measurement functions of M1b (gates, M1-M8, M9) and the
report. Every run is scored from the summary the crosscheck recomputed, never from the delivered `summary.json`. `killable` is decided here from the
captures: a defect that the domain checker never judged wrong on this package's tasks is equivalent and excluded
from the kill rate, and the pairs it anchors move to `unconfirmed`.
"""
from __future__ import annotations

import copy
import shutil
import traceback
from pathlib import Path

from . import crosscheck as crosscheck_mod
from . import delivered, execute, pool, registry, store
from .execute import Run

store.use_kit()
from . import claims, labeled, metrics, report  # noqa: E402

GOOD = ("valid", "correct-infeasible")
EVALUATOR_KINDS = ("ancestor-file", "verifier-file")   # evaluator-reserved names reached outside the workspace


def recognize_all(domain, tasks: dict[str, delivered.Task], root: Path) -> tuple[dict, dict]:
    """(instances by task, staged workspace by task) for every delivered task; None where not recognized."""
    instances, staged = {}, {}
    for name, task in tasks.items():
        workspace = root / name
        try:
            prompt = delivered.stage(task, workspace)
            instances[name] = domain.recognize(workspace, prompt)
        except Exception:  # noqa: BLE001 - a task the domain cannot read is a coverage miss, not a crash
            instances[name] = None
        staged[name] = workspace
    return instances, staged


def check_captures(run: Run, domain, meta: registry.MetaTask, order: dict, results: dict, tasks, instances) -> tuple[dict, list]:
    """The domain checker's verdict on each member's captured final workspaces, and the findings cheaters logged."""
    checked, findings = {}, []
    for member, result in sorted(results.items()):
        if member.startswith("@"):
            continue
        for row in execute.invocation_rows(run.invocations / f"{member}.jsonl"):
            capture = run.ledger / row["final_capture"] if row.get("final_capture") else None
            task = crosscheck_mod.task_of(run, row, tasks)
            findings += [{"member": member, "label": order["members"][member].get("label"), "invocation": row["invocation"],
                          "task": task, **f} for f in row.get("findings") or []]
            if capture is None or not capture.is_dir() or task is None:
                continue
            instance = instances.get(task)
            entry = {"label": None, "recognized": instance is not None, "reasons": [], "invocation": row["invocation"]}
            if instance is not None:
                try:
                    verdict = domain.check(instance, registry.collect(domain, capture, meta))
                    entry.update(label=verdict["label"], reasons=list(verdict.get("reasons") or []))
                except Exception:  # noqa: BLE001
                    entry.update(recognized=False, reasons=[traceback.format_exc()[-200:]])
            checked.setdefault(member, {}).setdefault(task, []).append(entry)
    return checked, findings


def killability(order: dict, checked: dict) -> dict:
    """{member: {"basis", "confirmed"}} for defect and private members, from the captured verdicts; harness-defect
    LLM members keep what `confirm` recorded. Diagnostic defects get no entry, so they are never must-kill."""
    killable = dict(order.get("killable") or {})
    for member, spec in order["members"].items():
        defect_like = (spec.get("kind") == "scripted" and spec.get("behavior") == "defect") or spec.get("kind") == "private"
        results = [r for rs in (checked.get(member) or {}).values() for r in rs if r["recognized"]]
        if defect_like and not spec.get("diagnostic") and results:
            killable[member] = {"basis": "checker", "confirmed": any(r["label"] not in GOOD for r in results)}
    return killable


def prune(order: dict, ran: set, killable: dict) -> dict:
    """The order for this run: pairs, contrasts and A/A pairs over members that ran; pairs anchored on an equivalent
    defect move to `unconfirmed`."""
    equivalent = {m for m, k in killable.items() if k.get("confirmed") is False}
    out = copy.deepcopy(order)
    out["killable"] = killable
    known, moved = [], list(order.get("unconfirmed") or [])
    for pair in order.get("known_pairs") or []:
        if pair["higher"] not in ran or pair["lower"] not in ran:
            continue
        (moved if pair["lower"] in equivalent or pair["higher"] in equivalent else known).append(pair)
    out["known_pairs"], out["unconfirmed"] = known, moved
    out["contrasts"] = [c for c in order.get("contrasts") or [] if c["higher"] in ran and c["lower"] in ran]
    out["aa_pairs"] = [p for p in order.get("aa_pairs") or [] if all(m in ran for m in p)]
    return out


def labeled_check(run: Run, domain, instances, staged, cap: float) -> dict:
    """M6: the verifier's acceptance of the domain's labelled outputs, graded by the delivered `run.py grade` (on a
    copy under a random name, so nothing it is handed says these are the labelled ones)."""
    if not hasattr(domain, "labeled"):
        return metrics.not_computed("the domain has no labelled outputs")
    inputs = run.root / "labeled" / "input"
    labels = labeled.build_submissions(domain, instances, inputs, workspaces=staged)
    if not any(labels["submissions"].values()):
        return labeled.score_labels([], labels)
    outcome, rows, _ = execute.run_grade(run, "labeled", lambda tree: shutil.copytree(inputs, tree, dirs_exist_ok=True), cap)
    if outcome.status != "completed" or outcome.exit_code != 0:
        return metrics.not_computed(f"run.py grade failed on the labelled submissions: {outcome.reason or outcome.exit_code}")
    return labeled.score_labels(rows, labels)


def paid(summary: dict | None, task: str | None) -> bool:
    """Did the member earn any credit on the task (overall, when the finding names no task)?"""
    row = ((summary or {}).get("tasks") or {}).get(task) if task else (summary or {}).get("overall")
    return any(isinstance(row.get(key), (int, float)) and row[key] > 0 for key in ("mean_credit", "full_success_rate")) if row else False


def staging(findings: list[dict], member_runs: dict) -> dict:
    """The staging gate's input. A finding fails the gate when the cheater was paid for it (credit on that task), when
    its bytes are one of the oracle's output files, or when it reached evaluator-reserved names outside the workspace.
    A file that merely has an answer-like name is a warning: M1 already measures what such files are worth by credit."""
    failing, warnings = [], []
    for finding in findings:
        pays = paid((member_runs.get(finding["member"]) or {}).get("summary"), finding.get("task"))
        leaked = pays or finding.get("matches_answer") is True or finding.get("kind") in EVALUATOR_KINDS
        (failing if leaked else warnings).append({**finding, "paid": pays})
    return {"cheater_findings": failing, "warnings": warnings}


def verify(meta_task: str, package: Path, root: Path, *, pool_id: str | None = None, jobs: int = 3, llm: bool = False,
           out_root: Path | None = None, run_id: str | None = None, build: str = "reference", arm: str = "reference",
           cap: float | None = None) -> dict:
    """Meta-verify `package`; returns the report (also written as report.json and report.md under the run)."""
    st = store.Store(root)
    out_root = Path(out_root) if out_root else store.default_out_root()
    store.apart(st.root, out_root, labels=["the output root"])
    meta = registry.get(meta_task)
    domain = registry.load_domain(meta)
    registry.configure(domain, st.root)
    pool_id, pool_dir = st.find_pool(meta_task, pool_id)
    order = pool.read_order(st, meta_task, pool_id)
    run_id = run_id or store.anon_id("r")
    run = Run(run_id, st.run(run_id), out_root / run_id)
    copied = execute.intake(run, package, meta.reference)
    seconds = execute.cap_seconds(run.package, cap)
    preflight = execute.preflight(run)
    members = pool.members_of(order, llm=llm)
    results = execute.run_all(run, pool_dir, order, members, jobs=jobs, cap=seconds)
    tasks = delivered.tasks(run.intake)
    instances, staged = recognize_all(domain, tasks, run.root / "stage")
    checked, findings = check_captures(run, domain, meta, order, results, tasks, instances)
    interrupted = sorted(n for n, r in results.items() if r["exec"].get("interrupted"))
    cross = crosscheck_mod.crosscheck(run, {n: r for n, r in results.items() if n not in interrupted}, tasks,
                                      grade_cap=seconds, jobs=jobs, checked=checked)
    summaries = cross.pop("summaries")
    ran = set(members) - set(interrupted)
    order_run = prune(order, ran, killability(order, checked))
    m6 = labeled_check(run, domain, instances, staged, seconds)
    member_runs = {name: {**result["run"], "delivered_summary": result["run"]["summary"], "summary": summaries.get(name)}
                   for name, result in results.items() if name not in interrupted}
    execs = {"preflight": {"exit_code": preflight["exit_code"]},
             "members": {n: {**r["exec"], "summary": summaries.get(n)} for n, r in results.items()}}
    gate_results = metrics.gates(execs, member_runs.get("@reference"), member_runs.get("@noop"), cross,
                                 staging(findings, member_runs))
    scored = metrics.metrics(member_runs, order_run, m6, checked)
    card = execute.read_json(run.package / "card.json")
    card_claims = None
    if isinstance(card, dict):
        measured = claims.measure(card, order_run, member_runs, scored)
        card_claims = claims.score_claims(card, measured)
    extra = [{"name": "jobs", "value": jobs}, {"name": "llm_members", "value": llm},
             {"name": "members_run", "value": len(members)}, {"name": "preflight", "value": preflight},
             {"name": "package_cap_seconds", "value": seconds}, {"name": "interrupted_by_usage_limit", "value": interrupted},
             {"name": "scored_from", "value": "summaries recomputed by the crosscheck from the attempt rows and regrades"}]
    result = report.assemble(meta_task=meta_task, build=build, arm=arm, pool=pool_id, gates=gate_results,
                             metrics=scored, claims=card_claims, copied_reference_files=copied, conditions=extra)
    store.write_json(run.root / "report.json", result)
    (run.root / "report.md").write_text(report.render(result), encoding="utf-8")
    store.write_json(run.root / "run.json", {"run": run_id, "meta_task": meta_task, "pool": pool_id, "package": str(package),
                                             "out": str(run.out_root), "jobs": jobs, "llm": llm})
    shutil.rmtree(run.runtime, ignore_errors=True)
    shutil.rmtree(run.arenas, ignore_errors=True)
    return result
