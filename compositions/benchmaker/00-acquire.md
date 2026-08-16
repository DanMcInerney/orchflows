---
id: 00-acquire
executor: orch-decompose
pack: orch-research-pack
depends_on: []
write_scope: [{{package}}]
bound: <= 120 tool calls
excluded_actions:
  - let unsupported semantics become invented target truth
independence: gate
isolation: required
profile: orch-worker
---

## Objective

One converged synthesis about {{target}} and its class, frozen with its
sources at one result identity, carrying every artifact the research
charter names.

## Fixed inputs

- The question, stated as one: what must be true of {{target}} and its
  class for a benchmark of {{outcome}} to be built from evidence rather
  than from belief?
- {{target}} — the target identity, opaque: carried, never defined.
- {{outcome}} — the intended observable outcome, carried the same way.
- {{sources}} — the source policy, including judgment permission and
  any bar on a lane's sources.
- {{rigor}} — this run's value for the rigor bar orch-research-pack's
  signature requires of a spec.
- {{package}} — the evidence store root the frozen synthesis is written
  under.
- [the research charter](../references/benchmaker-research.md) — the
  lane cut, the synthesis artifacts, and the exhibited/protected rule
  this delivery is cut under.

## Completion test

- the terminal synthesis fixes construct definition, claim register, failure atlas, prior-art register, disagreement register, gaps and sourcing mode at one result identity | oracle: the charter's artifact list against the frozen synthesis | oracle_class: deterministic | provenance: pre-existing
- every claim maps to a case specification or a recorded gap | oracle: the claim register | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the frozen synthesis identity and its source
identities; verification; feedback; risks — gaps explicit; a
non-complete delivery returns partial evidence, never a closed-over gap

## Result

## Verification

## Feedback

[]

## Risks

[]
