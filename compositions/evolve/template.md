---
name: evolve
description: Evolve one target through bounded candidate generations against one frozen evaluation. Manual-only campaign.
entry: named
placeholders: [target, incumbent, evaluation, writer, bound, mutation_scope]
---

A target improves only against an evaluation frozen before the first
candidate exists: the incumbent is admitted against it, each generation
of candidates is written and scored blind against it, and the campaign
closes on the promotion rule it opened with.

`00-eval` has work to do only
where `evaluation` is `none`: a supplied frozen evaluation identity is
already the campaign's, and the stubs behind it read that instead.

Instantiate with all six placeholders: `target`, the identity being
evolved; `incumbent`, its fixed starting result/evidence identity;
`evaluation`, the frozen evaluation identity — carrying mode, criteria,
promotion rule, margin and search policy — or `none` when one must be
designed first; `writer`, the skill each candidate is written through;
`bound`, the campaign's budget; and `mutation_scope`, the candidate
write scope — `02-campaign`'s, and every other stub is read-only.
