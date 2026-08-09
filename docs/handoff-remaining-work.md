# Handoff — remaining work after the first measurement pass

Four of six items closed 2026-08-09; the two that remain are the
expensive ones. Every item routes to one owner per
[rules/improvement.md](../rules/improvement.md) §3. Reasoning lives with
its owner and is linked, never restated: principles in
[the redesign handoff](handoff-benchmaker-redesign.md), what the
no-sealing decision withdrew in
[the spec](benchmaker-redesign-spec.md) §0, refusals in
[DESIGN.md](../DESIGN.md) "Roads not taken".

Delete this file when its table is empty.

## Closed 2026-08-09

**1 — The manifest cannot prove it describes its own tree.** Settled by
`benchmarks/benchmaker/tools/component_identity.py`: the recompute
recipe is `seal_set.py`'s line format nested one level — a file
component's identity is the sha256 of its bytes, a directory
component's is the sha256 of its component lock relative to the
component root. The three directory components are re-derived, so
`benchmark_identity` moves when `cases/` moves and `--verify` says so.
22 tests, each mutating one thing. `protected_evidence` is exempt and
printed as exempt.

**2 — `case.toml`'s `bound` conflates two quantities.** Settled by
renaming it `exec_bound`, carrying the candidate-facing execution bound
alone; the `BC1`–`BC6` allocation stays in `evaluation-design.md` §8.
`validate_cases.py` refuses a `BC<n>` token in `exec_bound` and a tier
disagreeing with `size`. Fourteen frozen keys, still fourteen. The
2026-08-08 measurement record quotes the predecessor string and is not
rewritten: `validate_measures.py` strips the construction clause before
comparing, and a predecessor row naming the wrong tier still fails.

**3 — Seventeen tickets carry an unlawful `executor`.** Settled in
`scripts/tickets.py`, not `tools/validate.py` — the owner named in the
first draft of this file was wrong. `tools/validate.py` validates the
library and never reads `.orch/`; `scripts/tickets.py` is what reads a
ticket and hands it to a dispatcher, so refusing there is refusing at
the moment it matters. A ticket whose `executor` names an engine loads
with an error, never appears in `ready`, and cannot be claimed. The
engine list mirrors `skills/engines/` and a test holds the two in sync.

**4 — §10 step 2 cannot be cut as written.** Both owners named:
`scoring.md` is a package file, so the scoring law lives in `PROT`
§Scoring; `EVD` is `skills/workflows/orch-eval-design/SKILL.md`. Step 2
then landed — see [the spec](benchmaker-redesign-spec.md) §10 and §0b.

## Open

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

**7 — The sixteen cases case none of the manifest's new fields.**
Owner: [the spec](benchmaker-redesign-spec.md) §10 step 3.
`MAN` now requires eight pre-seal fields. The case set was cut against
the predecessor law, so a candidate that omits all eight still passes
every probe. Recorded as a manifest gap; closing it is a case-evidence
change, not a law change.

**8 — The law landed without the disjoint gate.**
Owner: `orch-build`'s `orch-critique` step.
The 2026-08-09 change was authored and verified by one context. The
four deterministic oracles are green, and the previous pass's own
finding is that green can be an artifact of unreachability. A
library-lens critique in a disjoint context is owed before this is
treated as reviewed.

## Recorded, not scheduled

Four suspected case defects await
[the spec](benchmaker-redesign-spec.md) §4.1's reference audit: the two
repaired at `e5bdb24` and the two repaired at 2026-08-09 (items 1 and 2
above) — in every case the audit confirms the repair rather than
trusting it. They are listed in the manifest's
`reference_audit.awaiting_confirmation`. The redesign handoff's own
[open state](handoff-benchmaker-redesign.md) is unchanged by this pass.

## What this pass established about method

The change set that the library-lens gate refused passed all four
oracles while it was wrong, because the new skill it added was bound by
nothing. Green was an artifact of unreachability. The gate also caught a
`rules/` amendment written to legalize the malformed tickets in item 3
rather than treat them as the defect.
[rules/verification.md](../rules/verification.md) §10 is why that gate
runs; this pass is its evidence.
