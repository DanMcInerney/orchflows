---
name: brief-intake
description: Turn an incomplete browser-game brief into evidence-bound checkpoints and standard-stamped successor delivery.
disable-model-invocation: true
---

<!-- BGW-TRACE[help:traceability|PJ-21] -->
<!-- BGW-TRACE[help:program-record|PJ-03,PJ-07] -->
<!-- BGW-TRACE[help:question-authority|PJ-06,PJ-09,PJ-10] -->
<!-- BGW-TRACE[help:checkpoint-disposition|PJ-05] -->
<!-- BGW-TRACE[help:experiment-validity|PJ-16,PJ-17] -->
<!-- BGW-TRACE[help:kind-separation|AUTH-05,PJ-18,PJ-19,PJ-28] -->
<!-- BGW-TRACE[help:closed-surface|PJ-20] -->
<!-- BGW-TRACE[help:decision-safety|PJ-22] -->
<!-- BGW-TRACE[help:conditional-fidelity|PJ-23] -->
<!-- BGW-TRACE[help:evidence-identity|PJ-08,PJ-24] -->
<!-- BGW-TRACE[help:revalidation|PJ-25] -->
<!-- BGW-TRACE[help:migration|PJ-01,PJ-26,U-03] -->
<!-- BGW-TRACE[help:instance-validation|PJ-05,PJ-06,PJ-09,PJ-10,PJ-22,PJ-24,PJ-25,PJ-28] -->
<!-- BGW-TRACE[implementation:closed-surface|PJ-20] -->

Require: incomplete product `brief`, git-backed `workspace`, and caller-opened
`intake-frame` under 3d-browser-game.
Three.js and Blender are fixed. Empirical gaps become declared experiments;
`kind: user-only` gaps become verbatim questions for root. Neither blocks the other.

Run calls in `intake-frame`; discovery alone closes it.

<!-- BGW-TRACE[implementation:program-record|PJ-03,PJ-07] -->
<!-- BGW-TRACE[implementation:question-authority|PJ-06,PJ-09,PJ-10] -->
<!-- BGW-TRACE[implementation:decision-safety|PJ-22] -->
**Record**, `do --standard orch-content --isolation required`:
versioned program record in `workspace` for `brief`, conforming to the
[program-record schema](../../references/browser-game-program-record.schema.json)
and [intake-authority policy](../../references/browser-game-intake-policy.json).
Record each Q-01–Q-12 field's disposition, authority kind, owner, rationale,
evidence and revision independently; omitted material fields carry stable
open-question/decision identities; settled decisions retain revision and
invalidation trigger.
Before pricing dependent production/play review, record task-critical vision,
listening and ordinary-input decision capabilities. Observe representative
interaction at required cadence, binding input/context identities and limits.
Tool presence or fixed scripts cannot prove adaptive play. Unavailable
capabilities remain empirical gaps until capability changes.
`browser_game_validate.py` runs against it before filing.

<!-- BGW-TRACE[implementation:experiment-validity|PJ-16,PJ-17] -->
<!-- BGW-TRACE[implementation:conditional-fidelity|PJ-23] -->
<!-- BGW-TRACE[implementation:revalidation|PJ-25] -->
**Evidence**, `do --standard orch-research` handed the record's artifact
line: a fixed evidence packet for independently schedulable empirical fields
affecting the next transition. Each experiment matches its source field's open
`decision_id`, predeclares required fields and settles only matched cells.
Negative, null and inconclusive results stay visible; controls/experiments
without the policy's complete recorded trigger identity stay `inactive`.

<!-- BGW-TRACE[implementation:checkpoint-disposition|PJ-05] -->
<!-- BGW-TRACE[implementation:kind-separation|AUTH-05,PJ-18,PJ-19,PJ-28] -->
<!-- BGW-TRACE[implementation:evidence-identity|PJ-08,PJ-24] -->
**Checkpoint**, one `judge --standard orch-content` over both artifact
lines: compare direction/evidence with the original brief and settled subject
facts, including visual relationships and actual interaction. Technical
reachability cannot establish intuitiveness or fun; preserve capability gaps
without lowering acceptance. Return exactly one disposition — `advance`, `revise`, `experiment`,
`user-decision-required` or `stop` — bound to its governing requirement, the
fixed record revision and evidence identity. Its findings validate
against the
[checkpoint contract](../../references/browser-game-checkpoint.schema.json).
Only a lawful disposition permits
`do --standard orch-content` to materialize the
[standard-separated successor plan](../../references/browser-game-program-record.schema.json#/$defs/successorPlanRevision),
each ordered entry preserving its artifact identity, artifact kind, matching
standard, run/root identities, dependencies and `planned`/`opened`
status.

Never: invent a stack, cohort, support promise, budget, fallback, provider
or release policy; settle a user-only field from evidence
or paraphrase its question before relay; represent absence as agreement or
overwrite a settled decision; infer `advance` from task completion; open a
successor with unresolved kind, standard, predecessor identity, dependency or root identity; hide one artifact kind behind another's
identity; or file
anything the instance validator rejects.

Return: the terminal checkpoint for the caller's `intake-frame`, with
record/evidence identities, disposition, open-question/successor
identities and invalidation boundary, observable without historical input.
