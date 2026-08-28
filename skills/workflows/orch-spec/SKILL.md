---
name: orch-spec
description: Freeze and seal a semantic root when evidence, user decisions, kind boundaries, or successor planning are unresolved.
role: planner
---

Require: the request as Goal and relevant workspace facts as Context.

Use `orch-investigate` for one bounded question against Context's source
policy. Ask unresolved user decisions one at a time; record verbatim without
re-interviewing settled ones.

Semantic root policy:

- **Evidence identities**: Cite long evidence and exemplars by identity, never
  inline rationale.
- **Root contents**: Carry only settled observable behavior and authority,
  precedence, lifecycle, persistence, trust, compatibility, or non-goal
  boundaries an executor cannot infer.
- **Executor authority**: Leave files, functions, schemas, commands, tests,
  proof methods, and internal mechanics to the executor.
- **Seal blockers**: Vague quality adjectives settle nothing. Do not seal while
  a choice, contradiction, or impossible acceptance threshold remains.
- **Reference resolution**: Validate fixed identities and canonical-owner
  references before seal; locators must resolve.
- **Review eligibility**: Recommend one outside blocker-only review only when
  the root spans several independent semantic policies or cross-cutting
  authority, lifecycle, or contract surfaces.
- **Review finality**: A corrected root that already addresses a review never
  recommends another critique. Deterministic admission and downstream
  verification decide what follows.

Lifecycle:

Count deliverable kinds. One gets a pack-stamped root. For multiple,
open first and persist the ordered remainder through `tickets.py run-state
<first-run> --artifact successors.md`; each entry names kind, pack,
successor run and root ids, and state `planned`. This skill is the
`successors.md` sole writer and materialization owner. When a drained
`orch-frontier` returns its successor trigger under
[work-item.md](../../../contracts/work-item.md#roots-decomposition-and-integration),
resolve the accepted predecessor result identity; open the next successor run
and root, cite the resolved identity in `## Context`, then replace
`successors.md` with that entry `opened` and the next `planned`. Never create a
second root in the same run; an unmaterialized entry remains durable.

Draft per [work-item.md](../../../contracts/work-item.md#roots-decomposition-and-integration)
using vocabulary and pack craft. Route per
[topology.md](../../../rules/topology.md) 5a. When one executor plus the
mandatory `orch-integrate` join owns the outcome, bind it directly rather than
`orch-decompose`; otherwise write the decomposed root through `tickets.py new
<run> <root-id> --executor orch-decompose --pack <stamp> --independence gate …`.

For each root, run `tickets.py stamp-generation`, finish and validate `draft`
with `tickets.py draft-validate`, then seal its receipt by compare-and-swap via
`tickets.py seal --cut-generation <validated cut_generation>`.
`assignment_seal` fixes the digest for dispatch. A semantic-root change is
unsupported in this physical run: after the accepted predecessor result
identity resolves, open a successor run, cite it in Context, preserve
predecessor bytes, and never mint another root ordinal.

Never: stamp a pack the cut cannot share; prescribe implementation or tests in
Goal; restate canonical-owner standards or exemplar rationale.

Return: the accepted root ticket's id and path, the durable `successors.md`
identity (`[]` for one kind), and, after each predecessor resolves, the
successor root's id, path, and cited predecessor result identity; the
kind-count decision, assumptions, evidence consulted, and
consistency observations against the settled decisions and repository facts.
