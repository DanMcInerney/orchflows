---
id: 00-acquire
executor: orch-decompose
pack: orch-research-pack
depends_on: []
write_scope: [{{package}}]
bound: <= 120 tool calls
excluded_actions:
  - multiply the caller bound
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
- {{bound}} — the one caller bound. Every stage's own bound is an
  allocation from it: nonnegative, totalling no more than it, unused
  allocation carrying forward from a completed stage. A caller bound
  smaller than the stage bounds below is repartitioned before dispatch.
- [the research charter](../references/benchmaker-research.md) — the
  lane cut, the synthesis artifacts, and the exhibited/protected rule
  this delivery is cut under.

## Completion test

- the terminal synthesis fixes construct definition, claim register, failure atlas, prior-art register, disagreement register, gaps and sourcing mode at one result identity | oracle: the charter's artifact list against the frozen synthesis | oracle_class: deterministic | provenance: pre-existing
- every claim maps to a case specification or a recorded gap | oracle: the claim register | oracle_class: deterministic | provenance: pre-existing
- a non-complete delivery, decision gap, unresolved source or uncovered remainder is returned as partial evidence rather than closed over | oracle: the delivery's own verdicts and gap list | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the frozen synthesis identity and its source
identities; verification; feedback; risks — gaps explicit, and
otherwise filed as contracts/work-item.md requires

## Result

## Verification

## Feedback

[]

## Risks

[]
