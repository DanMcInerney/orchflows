# Handoff — unfinished work after the law landing

State at `35d1266` (PR #30), as amended by run
`20260809T021408Z-benchmaker-unseal`. Every item routes to one owner per
[rules/improvement.md](../rules/improvement.md) §3. Reasoning lives with
its owner and is linked, never restated: principles in
[the redesign handoff](handoff-benchmaker-redesign.md), what each
revision withdrew and what it added in
[the spec](benchmaker-redesign-spec.md) §0, §0b and §0c, refusals in
[DESIGN.md](../DESIGN.md) "Roads not taken". Four items closed on
2026-08-09 and three more closed with the seal removal (§0c); git
history owns them. Item 1 of those three closes at that run's disjoint
library-lens gate, which had not run when this line was written — a
gate finding beyond one correction pass re-opens it with the finding's
owner, per [rules/topology.md](../rules/topology.md) §5.

Delete this file when its table is empty.

## Redesign, resumable

**3 — Thirteen cases unmeasured.**
Owner: [the spec](benchmaker-redesign-spec.md) §4.3.
Tickets `T04`–`T16` are cut and resumable. Re-running them without
§4.3's dispatch-authority declaration — now law in
`benchmaker-protocol.md` §Audit and measurement — reproduces the
confound the existing three rows carry.
Cost, measured: 211,834 tokens per case at two rungs.

**4 — Nothing measured the judged class or a rerun spread.**
Owner: the same.
Neither three-trial case ran, so `resolution` rests on the one-case
floor and the suite's weakest oracle class is unexercised. Both figures
are recorded as absent, not as zero: the rerun spread in the manifest's
`resolution`, the judged class in the measurement record the manifest's
`measurement` locator names.

## Recorded, not scheduled

The suspected case defects listed in `awaiting_confirmation`, in the
reference audit record the manifest's `reference_audit` locator names,
await [the spec](benchmaker-redesign-spec.md) §4.1's reference audit. In
every case the audit confirms the repair rather than trusting it.

Spec §10 steps 3 and 4 — the audit and measurement stages run for real,
then anchors as their references arrive — and §11's standing gaps (G1
WMT/MQM judge certification, G2 client-rendered leaderboards, RF-18..21
still self-verified) are unchanged by this pass.
