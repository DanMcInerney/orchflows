---
name: browser-game
description: Turn an incomplete browser-game brief into evidence-bound checkpoints and pack-stamped successor delivery.
disable-model-invocation: true
---

Require: one incomplete product request as `brief`, and `workspace`, its
git-backed repository — the only inputs. No missing field becomes a default:
an `empirical` gap is a declared experiment, a `kind: user-only` gap one
verbatim question the root relays, neither blocking the other.

    tickets.py frame-open <run> --goal-file <program-goal>
      --workflow browser-game

Re-read the frame's `## Report` and its children at every wave's head,
append the decision with `tickets.py result <run> <frame> --by <frame>`, and
relay every returned `artifact:` and `findings:` line verbatim.

**Record**, one versioned program record in `workspace`
(document-tree: no `--isolation`):

    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --goal-file <record-goal> --bound "<= 120 tool calls"
      --workspace <workspace>

Its goal: a record under the
[program-record schema](../references/browser-game-program-record.schema.json)
and [intake-authority policy](../references/browser-game-intake-policy.json)
— every Q-01–Q-12 field dispositioned independently, with its authority kind, owner,
rationale, evidence and revision; every omission carrying a stable
open-question or decision identity; every settled decision keeping its
invalidation trigger; the installed instance validator run before filing.

**Evidence**, handed the record's `artifact:` line:

    tickets.py do <run> --pack orch-research-pack --parent <frame>
      --goal-file <evidence-goal> --bound "<= 80 tool calls"

Its goal: one fixed evidence packet for the independently schedulable
`empirical` fields affecting the record's next transition, each experiment
matched to its `decision_id`. Negative and null results stay visible; an
experiment without its recorded trigger identity stays `inactive`.

**Checkpoint**, one judge over the fixed record revision:

    tickets.py judge <run> --pack orch-content-pack --parent <frame>
      --artifacts doc:<record-path>@sha256:<digest>
      --goal-file <checkpoint-goal> --bound "<= 60 tool calls"
      --workspace <workspace>

A judge reads one artifact kind, so its goal quotes the packet's
`artifact: evidence:<id>` line verbatim. Exactly one disposition —
`advance`, `revise`, `experiment`, `user-decision-required` or `stop` —
bound to its governing requirement, record revision and evidence
identity, validating against the
[checkpoint contract](../references/browser-game-checkpoint.schema.json).

**Successor plan**, only where that disposition is lawful:

    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --goal-file <successor-goal> --bound "<= 60 tool calls"
      --workspace <workspace>

Its goal: the
[pack-separated successor plan](../references/browser-game-program-record.schema.json#/$defs/successorPlanRevision),
each ordered entry preserving artifact identity, artifact kind, matching
pack, proposed run/root identities, dependencies and `planned`/`opened`
status.

Never: invent a stack, cohort, support promise, budget, fallback, provider or
release policy; settle a user-only field from evidence or paraphrase its
question; overwrite a settled decision; infer `advance` from completion; open
a successor whose kind, pack, predecessor, dependency or root is
unresolved; hide one artifact kind behind another's; or close over the making
calls without the checkpoint judge or an `unjudged: <reason>` journal line.

Return: `tickets.py frame-close <run> <frame> --done <check>`, done the
installed validator over record and checkpoint: record and evidence
identities, disposition, open questions, successors and invalidation
boundary, readable without historical input.

<!--
BGW-TRACE[implementation:closed-surface|PJ-20]
BGW-TRACE[implementation:program-record|PJ-03,PJ-07]
BGW-TRACE[implementation:question-authority|PJ-06,PJ-09,PJ-10]
BGW-TRACE[implementation:decision-safety|PJ-22]
BGW-TRACE[implementation:experiment-validity|PJ-16,PJ-17]
BGW-TRACE[implementation:conditional-fidelity|PJ-23]
BGW-TRACE[implementation:revalidation|PJ-25]
BGW-TRACE[implementation:checkpoint-disposition|PJ-05]
BGW-TRACE[implementation:kind-separation|AUTH-05,PJ-18,PJ-19,PJ-28]
BGW-TRACE[implementation:evidence-identity|PJ-08,PJ-24]
BGW-TRACE[help:traceability|PJ-21]
BGW-TRACE[help:program-record|PJ-03,PJ-07]
BGW-TRACE[help:question-authority|PJ-06,PJ-09,PJ-10]
BGW-TRACE[help:checkpoint-disposition|PJ-05]
BGW-TRACE[help:experiment-validity|PJ-16,PJ-17]
BGW-TRACE[help:kind-separation|AUTH-05,PJ-18,PJ-19,PJ-28]
BGW-TRACE[help:closed-surface|PJ-20]
BGW-TRACE[help:decision-safety|PJ-22]
BGW-TRACE[help:conditional-fidelity|PJ-23]
BGW-TRACE[help:evidence-identity|PJ-08,PJ-24]
BGW-TRACE[help:revalidation|PJ-25]
BGW-TRACE[help:migration|PJ-01,PJ-26,U-03]
BGW-TRACE[help:instance-validation|PJ-05,PJ-06,PJ-09,PJ-10,PJ-22,PJ-24,PJ-25,PJ-28]
-->
