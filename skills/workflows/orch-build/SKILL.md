---
name: orch-build
description: Materialize or change one library or scoped custom item through the admission tests. Use for any new or amended skill, pack, or contract.
role: worker
---

Require: the item's intended contract — what it requires, returns, and
never does — its target tier, and its scope per
[references/scopes.md](references/scopes.md).

Route first: a request the existing machinery already expresses — a
stamped spec, an existing skill or composition — returns that routing,
never a new item.

Apply [rules/composition.md](../../../rules/composition.md) §6 and
[rules/token-economy.md](../../../rules/token-economy.md) §6 before
writing; a custom workflow starts per
[references/scopes.md](references/scopes.md). Admission is
tools/validate.py and the tests, and for a template also
`tickets.py instantiate`.

Gate the result's artifact identity through `orch-critique` with
[references/library-lens.md](references/library-lens.md), in a context
independent of this one; verify with the validator and tests as
oracles where the scope provides them.

Never: touch a
T0 contract outside a supersession change; land at canonical scope what
the request placed at user or project scope; give a custom item the
`orch-` prefix, which is reserved for canonical skills.

Return: the item and adapter paths, admission evidence, boundary
findings, and oracle output — or the existing routing when no item is
minted.
