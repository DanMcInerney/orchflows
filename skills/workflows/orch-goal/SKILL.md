---
name: orch-goal
description: Use for a mandatory two-run goal: deliver the original spec, rebuild it from first-run evidence, then deliver the new spec.
disable-model-invocation: true
role: none
---

Require: a frozen, routing-stamped [spec](../../../contracts/spec.md)
stamped `pattern: deliver` whose `evidence` names the original user
request by identity, and a goal bound reserving separate budgets for
delivery 1, re-specification, and delivery 2.

Run `orch-deliver` twice, naming the `orch-planner` profile per
[rules/roles.md](../../../rules/roles.md) §4. Delivery 1 runs the
original spec. Its status never omits delivery 2 when its contracted
Return and durable artifacts can support re-specification; otherwise
return its partial evidence under [rules/composition.md](../../../rules/composition.md)
rule 8.

Converge delivery 1 through the
[goal second-pass design](references/second-pass.md). Run `orch-spec`
with the same profile, supplying the exact original request as its
request and the original spec plus that packet as evidence. It writes a
fresh `pattern: deliver` spec with a new run id, the original pack, and
delivery 2's reserved bound. Delivery 2 runs that spec once; its final
verification and status close the goal.

Never: edit the original spec, omit delivery 2 because delivery 1
passed, widen the original request from discovered scope, or dispatch a
third delivery.

Return: status, original and replacement spec identities, both
deliveries' status, result identity, changed artifacts, and final
verification, the second-pass packet, queued scope, and bounds spent.
