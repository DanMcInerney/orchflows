---
name: benchmaker
description: Build and qualify one runnable benchmark for any target with an observable outcome.
entry: named
---

Require: one complete
[delegation packet](../contracts/work-item.md#dispatch). Its `objective` names
the target identity and intended observable outcome; `inputs` name
fixed evidence identities, source identities, source policy, judgment
permission, and applicable pack craft, lens, and oracle references;
`authority` grants the benchmark write scope and excluded actions;
`bounds` carry one caller bound including expected execution cost;
`return_contract` names status, the benchmark's revision,
qualification, gaps, bounds spent, and changed artifacts; `reply_to`
names the literal return address.

Read the [internal-call carrier rule](references/benchmaker-protocol.md#internal-call-carriage)
and [manifest](references/benchmaker-manifest.md) once at open.
Partition the caller bound before work and preserve every fixed
identity.

Steps:
- acquire-spec — `orch-spec` under the carrier rule: freeze one
  evidence-acquisition spec from the request, workspace or evidence
  access, and one applicable pack per internal spec, lanes and
  synthesis artifacts per the
  [research charter](references/benchmaker-research.md). Skipped when
  a supplied qualified synthesis is reused.
- acquire — `orch-deliver` of that frozen routing-stamped spec. A
  non-complete delivery, decision gap, or uncovered remainder returns
  its partial evidence and stops design.
- design — `orch-eval-design` under the carrier rule. A missing field
  or gap that leaves the intended outcome or materialization
  unobservable returns partial evidence and stops; carry every other
  declared gap forward.
- materialize — the same Spec and Deliver owners under the carrier
  rule: materialize the selected case specifications exactly, one
  applicable pack per internal spec.
- qualify — the same Deliver owner under the carrier rule, in a
  disjoint independent delivery: qualify the assembled benchmark.
- audit-and-measure — the protocol's three stages in order, each in its
  own allocation: a reference audit in a context disjoint from every
  builder and from the qualifier, then the attack pass, then the
  measurement — whose cheap triage pass precedes the audit it targets
  and is the measurement's own first pass, not a fourth stage. Each
  repairs or declares a gap; none renders a verdict on the benchmark.
  Record the manifest after they close.

Edges: seq acquire-spec → acquire → design → materialize → qualify →
audit-and-measure, each join carried by frozen evidence identity — the
frozen synthesis identity is design's evidence, the design identity is
materialization's evidence, the assembled case set is qualify's
evidence, the qualified assembly is audit-and-measure's; when cases span
domains, materialization chains single-pack deliveries by the same rule.

Invariants:
- The declared coverage floor never moves with the target's execution
  cost. A cheap target's cases are all fast; an expensive target's
  suite ceiling rises and its cost is declared. Speed comes from the
  probe, never from the coverage floor, the oracle, or the horizon the
  outcome needs; difficulty comes from horizon, outcome specificity,
  and a stricter correct oracle, never from filtering on a candidate's
  scores.
- Qualify the assembled result at a fixed identity in a context
  independent of its builders; builders never qualify their own cases
  or authored oracles as sufficient evidence; discrimination is
  qualified over known-good and known-bad seeds that context
  supplies — UNVERIFIED and an explicit gap where none can exist.
- Record the qualified result in the package's
  [manifest](references/benchmaker-manifest.md), which owns its field
  set and how a component reference resolves. The benchmark's version
  is the git revision it sits at.
- Never: mutate the target; generate a candidate; compare candidates;
  promote or activate anything; call Evolve; let builders qualify their
  own work; multiply the caller bound.

Done check: the manifest's qualification verdict set covers every
component but its own — covered PASS on every required criterion, gaps
explicit (`[]` when none).

Return: status, result — the benchmark's revision, verification — the
qualification; then gaps (`[]` when none), bounds spent, and changed
artifacts; failure carries partial evidence in qualification and gaps,
and the closing result addresses `reply_to`.
