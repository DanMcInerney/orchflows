"""`confirm`: run a pool on the private slice and settle what construction cannot.

Members run on the slice package through the same executor as `verify`; the domain checker, not the package's
verifier, scores every captured workspace (valid 1, suboptimal 0.5, anything else 0). Unconfirmed pairs (the LLM
hypotheses) are promoted to `known_pairs` when the higher member beats the lower one-sided at ALPHA; harness-defect
LLM members get `killable` (confirmed when the checker judged them wrong somewhere and they differ from their
unmodified twin, equivalent when never wrong); a known pair the slice resolves the other way is demoted to
`unconfirmed`. Everything is written to `confirmations.json` beside ORDER.json, and ORDER.json is updated in place.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import delivered, execute, pool, registry, store, verify
from .execute import Run

store.use_kit()
from benchkit import aggregate  # noqa: E402

from .metrics import ALPHA  # noqa: E402

CREDIT = {"valid": 1.0, "correct-infeasible": 1.0, "suboptimal": 0.5}


def task_scores(checked: dict, member: str) -> dict:
    """{task: {"mean_credit", "full_success_rate", "anchor"}} from a member's checker verdicts."""
    scores = {}
    for task, results in (checked.get(member) or {}).items():
        values = [CREDIT.get(r["label"], 0.0) if r["recognized"] else 0.0 for r in results]
        scores[task] = {"mean_credit": sum(values) / len(values), "anchor": False,
                        "full_success_rate": sum(v == 1.0 for v in values) / len(values)}
    return scores


def compare(checked: dict, higher: str, lower: str) -> dict | None:
    a, b = task_scores(checked, higher), task_scores(checked, lower)
    if not a or not b:
        return None
    clusters = {task: task for task in {*a, *b}}
    one = aggregate.paired(a, b, metric="mean_credit", clusters=clusters, direction="greater")
    two = aggregate.paired(a, b, metric="mean_credit", clusters=clusters)
    return {"p_greater": one["sign_flip_p"], "mean_diff": two["mean_diff"], "ci95": two["ci95"], "tasks": two["common"]}


def exercised(checked: dict, member: str) -> float | None:
    results = [r for rs in (checked.get(member) or {}).values() for r in rs if r["recognized"]]
    return sum(r["label"] not in verify.GOOD for r in results) / len(results) if results else None


def twin(order: dict, member: str) -> str | None:
    """The same LLM member without its harness defect."""
    spec = order["members"][member]
    same = [m for m, s in order["members"].items() if s.get("kind") == "llm" and not s.get("harness_defect")
            and (s.get("model"), s.get("effort"), s.get("mode")) == (spec.get("model"), spec.get("effort"), spec.get("mode"))]
    return sorted(same)[0] if same else None


def _wins(found: dict | None) -> bool:
    return bool(found) and (found["mean_diff"] or 0) > 0 and found["p_greater"] is not None and found["p_greater"] < ALPHA


def _loses(found: dict | None) -> bool:
    return bool(found) and (found["mean_diff"] or 0) < 0 and found["p_greater"] is not None and found["p_greater"] > 1 - ALPHA


def confirm(meta_task: str, root: Path, *, pool_id: str | None = None, slice_id: str | None = None, llm: bool = False,
            jobs: int = 3, out_root: Path | None = None, cap: float | None = None) -> dict:
    """Run the pool on the slice and update ORDER.json; returns the confirmations record."""
    st = store.Store(root)
    out_root = Path(out_root) if out_root else store.default_out_root()
    store.apart(st.root, out_root, labels=["the output root"])
    meta = registry.get(meta_task)
    domain = registry.load_domain(meta)
    registry.configure(domain, st.root)
    pool_id, pool_dir = st.find_pool(meta_task, pool_id)
    slice_id = slice_id or (st.slices(meta_task) or [None])[-1]
    if slice_id is None:
        raise store.StoreError(f"no slice for {meta_task}; run `slice build --meta-task {meta_task}`")
    order = pool.read_order(st, meta_task, pool_id)
    run_id = store.anon_id("c")
    run = Run(run_id, st.run(run_id), out_root / run_id)
    execute.intake(run, st.slice(meta_task, slice_id) / "package", None)
    members = pool.members_of(order, llm=llm)
    results = execute.run_all(run, pool_dir, order, members, jobs=jobs, cap=execute.cap_seconds(run.package, cap), builtins=())
    tasks = delivered.tasks(run.intake)
    instances, _ = verify.recognize_all(domain, tasks, run.root / "stage")
    checked, _ = verify.check_captures(run, domain, meta, order, results, tasks, instances)
    ran, evidence, known, unconfirmed = set(members), {"pairs": [], "killable": {}}, [], []
    for pair in order["known_pairs"]:
        found = compare(checked, pair["higher"], pair["lower"]) if {pair["higher"], pair["lower"]} <= ran else None
        if _loses(found):
            unconfirmed.append(pair)
            evidence["pairs"].append({**pair, "outcome": "demoted", **found})
        else:
            known.append(pair)
    for pair in order["unconfirmed"]:
        found = compare(checked, pair["higher"], pair["lower"]) if {pair["higher"], pair["lower"]} <= ran else None
        known.append({**pair, "basis": "slice"}) if _wins(found) else unconfirmed.append(pair)
        evidence["pairs"].append({**pair, "outcome": "confirmed" if _wins(found) else "unconfirmed", **(found or {})})
    killable = dict(order.get("killable") or {})
    for member in members:
        spec = order["members"][member]
        if spec.get("kind") != "llm" or not spec.get("harness_defect"):
            continue
        share, base = exercised(checked, member), twin(order, member)
        found = compare(checked, base, member) if base else None
        if share == 0:
            killable[member] = {"basis": "slice", "confirmed": False, "exercised_share": share}
        elif share and _wins(found):
            killable[member] = {"basis": "slice", "confirmed": True, "exercised_share": share, "p": found["p_greater"]}
        evidence["killable"][member] = {"exercised_share": share, **(found or {})}
    store.write_json(pool_dir / "ORDER.json", {**order, "known_pairs": known, "unconfirmed": unconfirmed, "killable": killable})
    result = {"meta_task": meta_task, "pool": pool_id, "slice": slice_id, "run": run_id, "llm": llm,
              "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "members_run": len(members), **evidence}
    store.write_json(pool_dir / "confirmations.json", result)
    shutil.rmtree(run.runtime, ignore_errors=True)
    shutil.rmtree(run.arenas, ignore_errors=True)
    return result
