# Drift canary (non-normative example)

Detect behavior drift when a model, effort, or host binding changes —
before it surfaces as production friction.

The canary set: a small frozen fixture of golden work items with
known-good results and deterministic-leaning oracles, kept under
`.orch/canary/`, spanning the kernel boundaries — one delegation, one
integration rejection (out-of-scope result), one verification with a
deliberately failing criterion, one small tdd ticket, one judged
scoring with a known rubric anchor.

On any profiles.md change or announced model update: run the set
through `orch-task`, diff verdicts and score cards against the golden
results, and log every divergence as friction with category
`surprising-output` — feeding `orch-self-improve` the earliest possible
signal that a skill's wording lands differently on the new model.

Divergence is information, not failure: a better model may beat the
golden result. The canary flags the delta; a human reads it.
