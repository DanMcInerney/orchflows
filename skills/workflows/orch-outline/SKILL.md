---
name: orch-outline
description: Freeze and seal a semantic root when evidence, user decisions, kind boundaries, or successor planning are unresolved.
role: planner
---

Require: the request as Goal, workspace facts as Context, and the stamped
pack's craft (`packs.py cells <digest>`); intake reads `## Outline` and
`## Spec fields`.

Use research craft for one bounded question in Context's source policy. Ask
unresolved user decisions singly; record verbatim.

Semantic root policy:

- **Evidence identities**: Cite long evidence and exemplars by identity, never
  inline rationale.
- **Root contents**: Carry only settled observable behavior and boundaries an
  executor cannot infer.
- **Executor authority**: Leave files, schemas, tests, proof methods, and
  internal mechanics to the executor.
- **Seal blockers**: Vague quality adjectives settle nothing. Do not seal while
  a choice, contradiction, or impossible acceptance threshold remains.
- **Reference resolution**: Validate fixed identities and canonical-owner
  references before seal; locators must resolve.
- **Review eligibility**: Recommend one outside blocker-only review only when
  several independent semantic policies or cross-cutting contract surfaces
  require it.
- **Review finality**: A corrected root that already addresses a review never
  recommends another critique. Deterministic admission and downstream
  verification decide what follows.

Lifecycle:

One kind gets stamped root. For multiple, open; persist remainder
through `tickets.py run-state <first-run> --artifact
successors.md`; entries name kind, pack, run/root ids, and `planned` state.

A drained `orch-frontier` trigger grants no authority. Caller opens a
materialization run: ordinal-1 root, planner ticket bound
to this exact skill. Seal it; invoke `tickets.py dispatch` for the root and
launch the child from the `launch` object it returns; the child runs
`tickets.py dispatch-receive`.
Receiver identity, authority, and committed bytes must agree before its durable
accepted receipt permits successor materialization. Never send a follow-up
after the prior planner outcome closed.

Resolve the accepted predecessor `## Result` identity; semantic-root change is
unsupported without that accepted predecessor result identity. Once resolved,
fresh successor run: create root via `tickets.py new`; `root_generation`
ordinal `1`; make `## Context` cite it; preserve predecessor bytes. Never
create a second root in the same run.

Draft per [work-item.md](../../../contracts/work-item.md#roots-decomposition-and-integration)
in the craft's terms. Route per [topology](../../../rules/topology.md)
§2: bind one executor plus `orch-integrate` directly rather than
`orch-decompose`. Use it only for a [topology](../../../rules/topology.md) §5
graph, through `tickets.py new
<run> <root-id> --executor orch-decompose --pack <stamp> --independence gate …`.

Run `tickets.py stamp-generation`, `tickets.py draft-validate`, then
`tickets.py seal` with the validated `--cut-generation`; `assignment_seal`
fixes dispatch identity. After seal, replace `successors.md` through `tickets.py
run-state --artifact successors.md --replace`, moving `planned` to `opened` and
keeping the next entry `planned`; unmaterialized entries remain durable.

After the fresh planner outcome crosses `orch-integrate`, the outer coordinator
dispatches that sealed root by the chosen route and starts `orch-frontier`.

Never: stamp incompatible packs; prescribe implementation or tests in Goal;
restate owners or exemplar rationale.

Return: root id/path; durable `successors.md` identity (`[]` for one kind);
successor id/path and cited predecessor result identity; kind count,
assumptions, evidence, and consistency observations.
