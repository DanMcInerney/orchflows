"""Run a bounded research plan through discovery, semantic choices and hydration.

This package-local command manages acquisition files only. It dispatches no
agents, judges no packets, and produces no synthesis. The workflow retains those
independent responsibilities. Completed/refused steps are immutable receipts.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import time

import acquire_plan
from acquire_checkpoint import (BoundedRead, CheckpointError, Store, atomic_json,
                                exclusive, package_identity, read_json)
from super_research import coverage, normalize, pacing, runner, schema, transport

PACKAGE = Path(__file__).resolve().parents[3]


def record_from(row):
    row = dict(row)
    row["engagement"] = tuple(schema.EngagementSnapshot(**item) for item in row["engagement"])
    row["attributes"] = tuple(tuple(item) for item in row["attributes"])
    row["loss"] = tuple(row["loss"])
    return schema.AcquisitionRecord(**row)


def joined(manifest, receipts, selected_records=None):
    records = tuple(record_from(row) for receipt in receipts for row in receipt["artifact"]["records"])
    results = tuple(schema.StepResult(**dict(row, loss=tuple(row["loss"]), warnings=tuple(row["warnings"])))
                    for receipt in receipts for row in receipt["artifact"]["steps"])
    typed = normalize.type_discovery_gaps(records, selected_records)
    return schema.AcquisitionArtifact(
        artifact_id=runner.artifact_id_for(manifest.manifest_id), manifest_id=manifest.manifest_id,
        mode="fused", as_of=manifest.as_of, records=typed, steps=results,
        edges=normalize.link_discovery_hydration(typed, selected_records), groups=normalize.group_records(typed),
        outcome=schema.reduce_outcomes(tuple(row.outcome for row in results)),
        loss=tuple(sorted({loss for row in results for loss in row.loss})))


def execute(plan, output, selection=None, *, opener=None, now=None, clock=time.monotonic,
            sleep=time.sleep, lanes=runner.MAX_CONCURRENT_LANES, after_checkpoint=None):
    started = clock()
    manifest = acquire_plan.validate(plan)
    output = Path(output).resolve()
    if output == PACKAGE or PACKAGE in output.parents:
        raise CheckpointError("evidence output must be outside the pinned package")
    identity = {"plan": acquire_plan.digest(plan), "package": package_identity(PACKAGE)}
    with exclusive(output):
        store = Store(output, identity, plan)
        before_requests = len(store.state["requests"])
        bounded = BoundedRead(store, transport.urlopen_read if opener is None else opener,
                              transport.utc_now_iso if now is None else now, clock, sleep)
        carrier = pacing.paced_carrier(transport.Transport(opener=bounded, now=now), clock, bounded.wait,
                                      state=bounded.pacing_state(), checkpoint=bounded.save_pacing)
        receipts = {}
        reused = []
        uncertain = []

        def run_one(step):
            step_identity = acquire_plan.digest(asdict(step))
            try:
                held = store.begin(step.step_id, step_identity)
            except CheckpointError as error:
                if "uncertain interrupted step" not in str(error):
                    raise
                uncertain.append(step.step_id)
                return
            if held is not None:
                receipts[step.step_id] = held
                reused.append(step.step_id)
                return
            step_started = clock()
            bounded.local.step_id = step.step_id
            single = replace(manifest, steps=(step,))
            run = runner.run_scheduled(single, carrier=carrier, clock=clock, lanes=1)
            if run.artifact.outcome == "refused" or set(run.artifact.loss) & {
                    "auth_required", "attestation_required", "rate_limited"}:
                bounded.decline_step(step.step_id)
            held = {"artifact": asdict(run.artifact), "ledger": [asdict(row) for row in run.ledger],
                    "manifest_advisories": [asdict(row) for row in coverage.review_manifest(single)],
                    "elapsed_seconds": clock() - step_started}
            store.finish(step.step_id, step_identity, held)
            receipts[step.step_id] = held
            if after_checkpoint is not None:
                after_checkpoint(step.step_id)

        def run_lane(steps):
            for step in steps:
                run_one(step)

        def run_stage(steps):
            groups = {}
            for step in steps:
                groups.setdefault(step.adapter_id, []).append(step)
            if lanes == 1 or len(groups) <= 1:
                run_lane(steps)
            else:
                with ThreadPoolExecutor(max_workers=min(lanes, runner.MAX_CONCURRENT_LANES, len(groups))) as pool:
                    futures = [pool.submit(run_lane, group) for group in groups.values()]
                    for future in futures:
                        future.result()

        run_stage(manifest.steps)
        discovery_receipts = [receipts[step.step_id] for step in manifest.steps if step.step_id in receipts]
        discovered = joined(manifest, discovery_receipts)
        batch = {"identity": identity, "candidates": acquire_plan.candidates(plan, discovered.records),
                 "steps": [asdict(row) for row in discovered.steps],
                 "advisories": [asdict(row) for row in coverage.review_artifact(discovered)],
                 "limits": plan["limits"], "uncertain_steps": list(uncertain)}
        candidate_id = acquire_plan.digest(batch)
        atomic_json(output / "candidates.json", dict(batch, candidate_id=candidate_id))
        phase = "selection_required"
        depth = ()
        if selection is None:
            selection = store.state["selection"]
        if selection is not None:
            depth = acquire_plan.selections(plan, discovered.records, selection, candidate_id)
            store.bind_selection(selection)
            atomic_json(output / "selection.json", selection)
            run_stage(depth)
            phase = "complete"
        elif not plan["depth"]:
            phase = "complete"
        ordered = tuple(manifest.steps) + tuple(depth)
        selected_records = {step.step_id: choice["record_id"] for step, choice in
                            zip(depth, selection["choices"] if selection is not None else ())
                            if step.selected_hits}
        artifact = joined(manifest, [receipts[step.step_id] for step in ordered if step.step_id in receipts],
                          selected_records)
        packet = asdict(artifact)
        atomic_json(output / "packet.json", packet)
        horizon_gaps = [row.record_id for row in artifact.records if row.observed_at > plan["as_of"]]
        gaps = ([{"code": "interrupted_step_uncertain", "step_id": name} for name in uncertain]
                + [{"code": "observation_after_as_of", "record_id": name} for name in horizon_gaps])
        if gaps:
            phase = "incomplete"
        elapsed = clock() - started
        with store.lock:
            store.state["spent_seconds"] = bounded.prior + clock() - bounded.started
            store.save()
        summary = {"identity": identity, "phase": phase, "candidate_id": candidate_id,
                   "packet_sha256": "sha256:" + hashlib.sha256((output / "packet.json").read_bytes()).hexdigest(),
                   "requests_total": len(store.state["requests"]),
                   "answered_requests": sum(row["state"] == "answered" for row in store.state["requests"]),
                   "uncertain_requests": sum(row["state"] != "answered" for row in store.state["requests"]),
                   "requests_this_invocation": len(store.state["requests"]) - before_requests,
                   "elapsed_seconds": elapsed, "active_acquisition_seconds": store.state["spent_seconds"],
                   "timing_complete": not uncertain and all(row["state"] == "answered" for row in store.state["requests"]),
                   "reused_steps": reused, "gaps": gaps,
                   "artifact_advisories": [asdict(row) for row in coverage.review_artifact(artifact)],
                   "limits": plan["limits"],
                   "measurement": "charged opener reservations, not redirect hops; uncertain reservations may not have reached I/O and interrupted intervals are unmeasured; measured execute wall time through summary assembly; no CLI startup/LLM/review time"}
        atomic_json(output / "summary.json", summary)
        return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--selection", type=Path)
    args = parser.parse_args(argv)
    try:
        result = execute(read_json(args.plan), args.output,
                         selection=read_json(args.selection) if args.selection else None)
    except (acquire_plan.PlanError, CheckpointError) as error:
        print(json.dumps({"error": type(error).__name__, "message": str(error)}))
        return 2
    print(json.dumps(result, indent=2))
    return 3 if result["phase"] == "incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
