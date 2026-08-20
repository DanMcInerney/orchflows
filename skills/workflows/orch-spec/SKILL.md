---
name: orch-spec
description: Turn a request plus evidence into a routing-stamped, decomposition-ready root ticket. Use before any delivery run.
role: planner
---

Require: the request as the packet's `objective`; the workspace or
evidence it concerns as its `inputs`.

Gather the facts the frozen statement depends on through
`orch-investigate` — one bounded question: what exists, what
constrains, what the request actually touches. Settle decisions only the
user can make with the user, one question at a time, each answer
recorded verbatim, without re-interviewing a settled one.

Count the deliverable kinds the end state spans. One kind → one
pack-stamped root ticket. Two or more → open only the first kind's root
now, and first persist the ordered remainder through `tickets.py run-state
<first-run> --artifact successors.md`: kind, pack, proposed successor run and
root ids, and state `planned` for each entry. This skill is that artifact's
sole writer and materialization owner. When a drained `orch-frontier` returns
its successor trigger under [work-item.md](../../../contracts/work-item.md#root-ticket),
resolve the predecessor's accepted result identity;
once resolved, open the next entry's successor run and root, cite that identity among the
successor root's own `## Fixed inputs`, then replace `successors.md` with that
entry `opened` and the next entry still `planned`. A kind boundary never
creates a second root in the same run, and an unmaterialized entry is durable
state, never a promise left only in this Return.

Draft each per
[contracts/work-item.md](../../../contracts/work-item.md#root-ticket),
with exact nouns and verbs from
[docs/vocabulary.md](../../../docs/vocabulary.md) and the craft cell of
the pack the stamp will name, so they read as the deliverable's
searchable names.

Stamp routing — exactly one pack per
[rules/topology.md](../../../rules/topology.md). Write it through
`tickets.py new <run> <root-id> --executor orch-decompose --pack <the
stamp> --independence gate …`; the root's `checked_by` is its cut-reader
bookkeeping, never its final acceptance path.

Never: stamp two packs in one root ticket; leave an acceptance criterion
oracle-less; restate standards an exemplar's owner already states.

Return: the accepted root ticket's id and path, the durable `successors.md`
identity (`[]` for one kind), and, after each predecessor resolves, the
successor root's id, path, and cited predecessor result identity; the
kind-count decision and its evidence, assumptions, evidence consulted.
