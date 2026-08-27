---
name: orch-spec
description: Freeze and seal a semantic root when evidence, user decisions, kind boundaries, or successor planning are unresolved.
role: planner
---

Require: the request as Goal and relevant workspace facts as Context.

Gather the facts the frozen statement depends on through
`orch-investigate`, carrying one question, the fixed evidence sources or
source policy from Context, and a bound: what exists, what constrains, what
the request actually touches. Settle decisions only the
user can make with the user, one question at a time, each answer
recorded verbatim, without re-interviewing a settled one.

Count the deliverable kinds the end state spans. One kind → one
pack-stamped root ticket. Two or more → open only the first kind's root
now, and first persist the ordered remainder through `tickets.py run-state
<first-run> --artifact successors.md`: kind, pack, proposed successor run and
root ids, and state `planned` for each entry. This skill is that artifact's
sole writer and materialization owner. When a drained `orch-frontier` returns
its successor trigger under [work-item.md](../../../contracts/work-item.md#roots-decomposition-and-integration),
resolve the predecessor's accepted result identity;
once resolved, open the next entry's successor run and root, cite that identity among the
successor root's own `## Context`, then replace `successors.md` with that
entry `opened` and the next entry still `planned`. A kind boundary never
creates a second root in the same run, and an unmaterialized entry is durable
state, never a promise left only in this Return.

Draft each per
[contracts/work-item.md](../../../contracts/work-item.md#roots-decomposition-and-integration),
with exact nouns and verbs from
[docs/vocabulary.md](../../../docs/vocabulary.md) and the craft cell of
the pack the stamp will name, so they read as the deliverable's
searchable names.

Stamp routing per [rules/topology.md](../../../rules/topology.md) 5a.
Write it through
`tickets.py new <run> <root-id> --executor orch-decompose --pack <the
stamp> --independence gate …`.

When one executor plus the mandatory `orch-integrate` join owns the whole
outcome, bind that executor in the root itself rather than `orch-decompose`.

For every new root, open the generation lifecycle through
`tickets.py stamp-generation <run> <root-id>`, which derives `root_generation`
as `root:<root-id>:<ordinal>:sha256:<digest>`. Finish its `draft`, validate
that snapshot through `tickets.py draft-validate <run> <root-id>`, then
compare-and-swap the recorded receipt to `sealed` through `tickets.py seal
<run> <root-id> --cut-generation <validated cut_generation>`. Only that
validated digest is sealed and eligible for dispatch; its
`assignment_seal` records that exact assignment digest. A semantic-root change
uses the planned successor run once its accepted predecessor result identity
resolves; cite it in root Context. A later cut may evolve members only under
unchanged root semantics. An unsupported in-run amendment is a successor
trigger, never a predecessor-ticket rewrite.

Never: stamp a pack the cut cannot share; prescribe implementation or tests in
Goal; restate standards an exemplar's owner already states.

Return: the accepted root ticket's id and path, the durable `successors.md`
identity (`[]` for one kind), and, after each predecessor resolves, the
successor root's id, path, and cited predecessor result identity; the
kind-count decision and its evidence, assumptions, evidence consulted, and
consistency observations against the settled decisions and repository facts.
