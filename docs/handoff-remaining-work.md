# Handoff — remaining work after the first measurement pass

State at `e5bdb24`. Every item routes to one owner per
[rules/improvement.md](../rules/improvement.md) §3. Reasoning lives with
its owner and is linked, never restated: principles in
[the redesign handoff](handoff-benchmaker-redesign.md), what the
no-sealing decision withdrew in
[the spec](benchmaker-redesign-spec.md) §0, refusals in
[DESIGN.md](../DESIGN.md) "Roads not taken".

Delete this file when its table is empty.

## Blocking anything that touches the manifest

**1 — The manifest cannot prove it describes its own tree.**
Owner: `benchmarks/benchmaker/tools/`.
`benchmark_identity` recomputes from the manifest payload, proving the
JSON is self-consistent. `benchmark.lock` proves the tree matches its
own recipe. Nothing binds the two, and the manifest's directory-component
identities (`cases/`, `provenance/`, `qualification/`) reproduce under no
recipe tried, including over pre-edit bytes. A `cases/` change does not
move `benchmark_identity` and nothing detects it.
Settled by: a component recompute tool, so the manifest's own claim that
consumers "resolve the locator and verify that digest before use" is
executable. Every field the redesign adds inherits this hole until then.

## Correctness

**2 — `case.toml`'s `bound` conflates two quantities.**
Owner: the case schema, `benchmarks/benchmaker/tools/validate_cases.py`.
`BC1`–`BC6` are the construction run's six builder contexts
(`evaluation-design.md` §8), so "one BC1 share" tells a candidate how the
case was authored. Only "probe within <tier>" is candidate-facing, and
only it was measurable in the pass.
Settled by: separating construction allocation from execution bound — a
change to the fourteen frozen keys, not a definition that can be added.

**3 — Seventeen tickets carry an unlawful `executor`.**
Owner: `tools/validate.py`.
`.orch/tickets/20260808T061035Z-…/` holds 17 tickets with
`executor: orch-task`, which
[contracts/work-item.md](../contracts/work-item.md) forbids and
[rules/composition.md](../rules/composition.md) §3 makes a call cycle —
`orch-task` is the engine that dispatches a ticket's executor. Inert now;
the cut was the defect.
Settled by: a validator check that a ticket's `executor` names no engine.
A recording item names `orch-verify`, `orch-judge` or `orch-investigate`,
or the decomposition returns a decision gap.

## Redesign, resumable

**4 — §10 step 2 cannot be cut as written.**
Owner: [the spec](benchmaker-redesign-spec.md) §10.
Two of its four law surfaces do not resolve: `EVD` names nothing in
`compositions/references/`, and `scoring.md` is a package file inside the
case set, not law.
Settled by: naming both owners.

**5 — Thirteen cases unmeasured.**
Owner: [the spec](benchmaker-redesign-spec.md) §4.3.
Tickets `T04`–`T16` are cut and resumable. Re-running them without
§4.3's dispatch-authority declaration reproduces the confound the
existing three rows carry.
Cost, measured: 211,834 tokens per case at two rungs.

**6 — Nothing measured the judged class or a rerun spread.**
Owner: the same.
Neither three-trial case ran, so `resolution` rests on the one-case floor
and the suite's weakest oracle class is unexercised.

## Recorded, not scheduled

Four suspected case defects await
[the spec](benchmaker-redesign-spec.md) §4.1's reference audit: the two
repaired at `e5bdb24` (which the audit should confirm rather than trust),
item 2, and item 1. The redesign handoff's own
[open state](handoff-benchmaker-redesign.md) is unchanged by this pass.

## What this pass established about method

The change set that the library-lens gate refused passed all four
oracles while it was wrong, because the new skill it added was bound by
nothing. Green was an artifact of unreachability. The gate also caught a
`rules/` amendment written to legalize the malformed tickets in item 3
rather than treat them as the defect.
[rules/verification.md](../rules/verification.md) §10 is why that gate
runs; this pass is its evidence.
