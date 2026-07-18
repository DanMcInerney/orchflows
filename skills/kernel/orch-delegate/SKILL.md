---
name: orch-delegate
description: Dispatch one task to the cheapest capable rung of the ladder with a complete delegation packet. Use for every child spawn.
role: none
---

Require: a complete [delegation packet](../../../contracts/delegation.md) —
objective, inputs, authority (a subset of your own), bounds, return
contract — supplied directly, or by reference to a ticket path. Refuse
a dispatch missing any part; name the missing part.

Resolve the role per [rules/roles.md](../../../rules/roles.md) §4.

Choose the cheapest capable rung of the ladder per
[rules/delegation.md](../../../rules/delegation.md) §2, bindings per
[references/profiles.md](references/profiles.md).

Spawn one fresh child carrying the packet verbatim. Select the profile's
native agent type and compatible fork mode per the profiles reference;
the child task name never selects the profile. Name the child by normalized
base-model-effort per that reference.

Never: widen scope; dispatch two objectives in one packet; let a child
re-dispatch its primary work; substitute a blocked profile silently.

Return: executor, child name, profile, and the child's contracted result
verbatim.
