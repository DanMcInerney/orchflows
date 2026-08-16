---
name: drift-canary
description: Detect behavior drift when a model, effort, or host binding changes — before it surfaces as production friction.
entry: scheduled
---

Require: the canary set — a small frozen fixture of golden work items
with known-good results and deterministic-leaning oracles under
`.orch/canary/`, spanning the kernel boundaries: one delegation, one
integration rejection (out-of-scope result), one verification with a
deliberately failing criterion, one small tdd ticket, one judged
scoring with a known rubric anchor. Trigger: any profiles.md change or
announced model update.

Steps:
- run — `orch-frontier` over a directory holding each canary item as its
  own one-ticket run.
- diff — `orch-verify` over the run's results, `golden.json` the oracle
  every verdict and score card is read against; log every divergence as
  friction, category `surprising-output` — feeding `orch-self-improve`
  the earliest signal that a skill's wording lands differently on the
  new model.

Edges: seq run → diff — run's result identities are diff's evidence.

Invariants — Never: edit a golden result inside a canary run; treat
divergence as failure — a better model may beat the golden result; the
canary flags the delta, a human reads it.

Done check: every canary item ran and every divergence is logged as
friction.

Return: status, result — the divergence log, verification —
`orch-verify`'s verdicts against `golden.json`; then divergences by
item.
