---
name: benchmaker
description: Build and qualify one runnable benchmark for any target with an observable outcome.
disable-model-invocation: true
---

Require: `target` and `outcome` — the identity and its intended observable
outcome, which stay opaque to every call — `sources` (the source policy),
`rigor` (the confidence each load-bearing claim must reach, stated as the
evidence that must exist for it), `pack` (the construction calls' stamp)
and `package` (where the benchmark is written). Construction craft that no
rule or contract owns is [the protocol](../references/benchmaker-protocol.md);
the manifest's field set is [its own](../references/benchmaker-manifest.md);
acquisition's lane cut is [the charter's](../references/benchmaker-research.md).

    tickets.py frame-open <run> --goal-file <benchmark-goal> --workflow benchmaker


Three making calls, each on the one before it. **Acquire**, `do` with
`--pack orch-research-pack`: one converged synthesis about `target` and its
class, frozen with its sources at one identity, carrying every artifact the
charter names. **Design**, `do --pack <pack>`: one evaluation frozen at one
package-owned identity — case specifications with their execution tiers and
anchors, measurable criteria and evidence classifications, scoring and
aggregation, intended coverage, expected execution cost. **Materialize**,
`do --pack <pack> --isolation required`: every specification the frozen
design names, materialized exactly into `package` as runnable cases, runner,
scoring data and provenance, each at a preserved identity.

Then three read-only calls, and independence is what the chain is for.
**Qualify**, `judge --pack <pack>` over the materialized artifact in a
delivery disjoint from every builder: oracle failability, coverage,
discrimination, reproducibility, redundancy, provenance and execution cost
each checked independently, a verdict per required criterion. **Audit**,
`judge` over the package and that qualification in a context disjoint from
both: every evidence-backed blocker under the pack's lens. **Measure**,
`judge`: the manifest recorded and the measurement pass beside it — what the
candidates scored over the candidate-accessible scope at the declared rungs,
on [§Measurement pass](../references/benchmaker-protocol.md#measurement-pass)'s
terms.

Never: mutate `target`; generate, rank, promote or activate a candidate;
select, add, remove, rewrite or substitute a case; let a candidate or search
context read, choose, retire or receive item-level feedback from protected
evidence; let unsupported semantics become invented target truth; move the
declared coverage floor with the target's execution cost; buy speed from the
coverage floor, the oracle or the horizon; or return a self-qualified
verdict where the builder-disjoint context is unreachable.

Return: `tickets.py frame-close <run> <frame> --done <check>` over the
recorded manifest and its measurement pass.
