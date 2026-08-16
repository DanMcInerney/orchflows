---
name: orch-spec
description: Turn a request plus evidence into a routing-stamped, decomposition-ready spec. Use before any delivery run.
role: none
---

Require: the request, and access to the workspace or evidence it
concerns.

Gather the facts a spec depends on through `orch-investigate` — one
bounded question: what exists, what constrains, what the request
actually touches. Settle the decisions only the user can make through
`orch-elicit`; synthesize settled decisions without re-interviewing.
When the request is itself a consequential decision, stop there: the
settled, approved spec is the deliverable.

Count the deliverable kinds the end state spans — this decision and
its evidence ride the Return. One kind → one pack-stamped spec. Two or
more → one spec per kind plus a composition instance at
`<state-root>/runs/<run>/composition.md`, orch-compose the executor that
runs it, chaining single-pack deliveries per
[contracts/composition.md](../../../contracts/composition.md), the cut
falling where the deliverable's kind changes, each successor's
`evidence` citing its predecessor's result identity — a successor spec
is written when that identity exists, not before.

Draft each spec per [contracts/work-item.md](../../../contracts/work-item.md#root-ticket),
holding its two hard lines — the objective is one observable end
state, never activities; a criterion no oracle can check is a spec
defect to fix here, not the decomposer's slack — with exact nouns and
verbs from [docs/vocabulary.md](../../../docs/vocabulary.md) and the
craft cell of the pack the stamp will name, so they read as the
deliverable's searchable names. Resolve every `exemplars` pointer to
an existing artifact and freeze its named imitation properties; an
unresolved pointer is a spec defect to fix here.

Stamp routing — exactly one pack per
[rules/topology.md](../../../rules/topology.md). Before Return, verify
the spec carries every field the stamped pack's `required_spec_fields`
cell demands — decomposition otherwise rejects it downstream, naming
the missing fields; catch that gap here, not there. Write the accepted
spec to `<state-root>/runs/<run>/spec.md`; the run itself — worklog, tickets,
terminal state — opens at delivery, not at spec time.

Never: stamp two packs in one spec (emit a composition instance
instead); leave an acceptance criterion oracle-less; restate standards
an exemplar's owner already states.

Return: the accepted spec path; when a composition instance was
emitted, its path — orch-compose the executor that runs it; the
kind-count decision and its evidence, assumptions, and evidence
consulted.
