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
Verify cheap claims; mark the rest assumptions.

Draft the spec per [contracts/spec.md](../../../contracts/spec.md),
holding its two hard lines: the objective is one observable end state,
never activities, and a criterion no oracle can check is a spec defect
to fix here, not the decomposer's slack. The spec's exact nouns and
verbs come from [docs/vocabulary.md](../../../docs/vocabulary.md) and
the craft cell of the pack the stamp will name — they become the
deliverable's searchable names.

Stamp routing — pattern by shape of done and exactly one pack per
[rules/topology.md](../../../rules/topology.md) — and carry the
stamped pack's required fields. Write the accepted spec to
`.orch/runs/<run>/spec-<pattern>.md`; the run itself — worklog,
tickets, terminal state — opens at delivery, not at spec time.

Never: stamp two packs (chain two specs instead); leave an acceptance
criterion oracle-less; restate standards an exemplar's owner already
states.

Return: the accepted spec path, decisions, assumptions, and evidence
consulted.
