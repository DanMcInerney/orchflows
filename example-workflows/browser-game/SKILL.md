---
name: browser-game
description: Turn an incomplete browser-game brief into evidence-bound checkpoints and pack-stamped successor delivery.
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

Require: one incomplete product request as `brief`, and `workspace`, the
git-backed product repository — the only invocation inputs. Missing fields
never become defaults: an empirical gap becomes a declared experiment, a
`kind: user-only` gap one verbatim question for the root to relay, and
neither blocks the other.

    tickets.py frame-open <run> --goal-file <program-goal> --workflow browser-game


<!-- BGW-TRACE[implementation:program-record|PJ-03,PJ-07] -->
<!-- BGW-TRACE[implementation:question-authority|PJ-06,PJ-09,PJ-10] -->
<!-- BGW-TRACE[implementation:decision-safety|PJ-22] -->
**Record**, `do --pack orch-content-pack --isolation required`: one
versioned program record in `workspace` for `brief`, conforming to its
[program-record schema](../references/browser-game-program-record.schema.json)
and [intake-authority policy](../references/browser-game-intake-policy.json).
Each Q-01–Q-12 field is recorded independently with its disposition,
authority kind, owner, rationale, evidence and revision; each omitted
material field carries a stable open-question or decision identity; a
settled decision keeps its revision and invalidation trigger.
`browser_game_validate.py` runs against it before filing.

<!-- BGW-TRACE[implementation:experiment-validity|PJ-16,PJ-17] -->
<!-- BGW-TRACE[implementation:conditional-fidelity|PJ-23] -->
<!-- BGW-TRACE[implementation:revalidation|PJ-25] -->
**Evidence**, `do --pack orch-research-pack` handed the record's artifact
line: one fixed evidence packet for the independently schedulable empirical
fields affecting the record's next transition. Each experiment matches its
source field's open `decision_id`, predeclares every required field and
settles only its matched cells. Negative, null and inconclusive results stay
visible; a control or experiment without the policy's complete recorded
trigger identity stays `inactive`.

<!-- BGW-TRACE[implementation:checkpoint-disposition|PJ-05] -->
<!-- BGW-TRACE[implementation:kind-separation|AUTH-05,PJ-18,PJ-19,PJ-28] -->
<!-- BGW-TRACE[implementation:evidence-identity|PJ-08,PJ-24] -->
**Checkpoint**, one `judge --pack orch-content-pack` over both artifact
lines: exactly one disposition — `advance`, `revise`, `experiment`,
`user-decision-required` or `stop` — bound to its governing requirement, the
fixed record revision and evidence identity. Its findings validate
against the
[checkpoint contract](../references/browser-game-checkpoint.schema.json).
Only where that disposition is lawful does one further
`do --pack orch-content-pack` materialize the
[pack-separated successor plan](../references/browser-game-program-record.schema.json#/$defs/successorPlanRevision),
each ordered entry preserving its artifact identity, artifact kind, matching
pack, run/root identities, dependencies and `planned`/`opened`
status.

Never: invent a stack, cohort, support promise, budget, fallback, provider
or release policy; settle a user-only field from evidence
or paraphrase its question before relay; represent absence as agreement or
overwrite a settled decision; infer `advance` from task completion; open a
successor whose kind, pack, predecessor identity, dependency or root identity
is unresolved; hide one artifact kind behind another's identity; or file
anything the instance validator rejects.

Return: `tickets.py frame-close <run> <frame> --done <check>` on the terminal
checkpoint — record and evidence identities, disposition, open question or
successor identities and the invalidation boundary, all observable without
historical input.
