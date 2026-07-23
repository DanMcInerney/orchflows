---
name: orch-benchmaker
description: Build and qualify one immutable runnable benchmark for any target with an observable outcome.
role: none
---

Require: one complete
[delegation packet](../../../contracts/delegation.md). Its `objective`
names the target identity and intended observable outcome; `inputs`
name fixed evidence identities, source identities, source policy,
judgment permission, and applicable pack craft, lens, and oracle
references; `authority` grants the benchmark write scope and excluded
actions; `bounds` carry one caller bound including expected execution
cost; `return_contract` names status, benchmark identity,
qualification, gaps, bounds spent, and changed artifacts; `reply_to`
names the literal return address.

Read the [internal-call carrier rule](references/protocol.md#internal-call-carriage) and
[manifest](references/manifest.md) once at open. Partition the caller
bound before work and preserve every fixed identity.

Reuse a supplied qualified synthesis. Otherwise freeze an
evidence-acquisition spec through `orch-spec` under that rule, with the request,
workspace or evidence access, and one applicable pack per internal
spec; deliver it through `orch-deliver` as a frozen routing-stamped
spec. A non-complete delivery, decision gap, or uncovered remainder
returns its partial evidence and stops design.

Invoke `orch-eval-design` under that rule. A missing field or gap that
leaves the intended outcome or
materialization unobservable returns partial evidence and stops; carry every
other declared gap forward.

Materialize the selected case specifications exactly through the same
Spec and Deliver owners under that rule, chaining single-pack deliveries by frozen
evidence identity. In a disjoint independent delivery, qualify the
assembled benchmark before sealing its identity and manifest.

Never: mutate the target; generate a candidate; compare candidates;
promote or activate anything; revise a benchmark in place; call Evolve;
let builders qualify their own work; multiply the caller bound.

Return: status, benchmark identity, qualification, gaps (`[]` when
none), bounds spent, and changed artifacts; failure carries partial
evidence in qualification and gaps, and the closing result addresses
`reply_to`.
