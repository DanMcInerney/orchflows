---
name: orch-spec
description: Turn a request plus evidence into a routing-stamped, decomposition-ready root ticket. Use before any delivery run.
role: none
---

Require: the request as the packet's `objective`; the workspace or
evidence it concerns as its `inputs`.

Gather the facts the frozen statement depends on through
`orch-investigate` — one bounded question: what exists, what
constrains, what the request actually touches. Settle decisions only the
user can make with the user, one question at a time, each answer
recorded verbatim, without re-interviewing a settled one.

Count the deliverable kinds the end state spans. One kind → one
pack-stamped root ticket. Two or more → one root ticket per kind, cut
where the deliverable's kind changes, each successor `depends_on` its
predecessor and names, among its own `## Fixed inputs`, the
predecessor's result by that root's id — resolved when it completes.

Draft each per
[contracts/work-item.md](../../../contracts/work-item.md#root-ticket),
with exact nouns and verbs from
[docs/vocabulary.md](../../../docs/vocabulary.md) and the craft cell of
the pack the stamp will name, so they read as the deliverable's
searchable names.

Stamp routing — exactly one pack per
[rules/topology.md](../../../rules/topology.md). Write it through
`tickets.py new <run> <root-id> --executor orch-decompose --pack <the
stamp> …`.

Never: stamp two packs in one root ticket; leave an acceptance criterion
oracle-less; restate standards an exemplar's owner already states.

Return: the accepted root ticket's id and path, plus each further root
ticket and its edge where the end state spans more than one kind; the
kind-count decision and its evidence, assumptions, evidence consulted.
