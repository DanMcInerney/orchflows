---
name: benchmaker
description: Build and qualify one runnable benchmark for any target with an observable outcome.
entry: named
placeholders: [target, outcome, sources, rigor, bound, pack, package]
---

One benchmark for one opaque target: evidence is acquired and frozen,
an evaluation is designed from it, the design is materialized exactly,
the assembly is qualified by someone who did not build it, audited by
someone who did neither, and finally measured on
[the protocol](../references/benchmaker-protocol.md#measurement-pass)'s
terms.

Six stubs, one chain: `00-acquire` → `01-design` → `02-materialize` →
`03-qualify` → `04-audit` → `05-measure`. `05-measure` is terminal, so
its completion test is this template's done check — the manifest's
qualification verdict set covering every component but its own.
Independence is what the chain is for: `03-qualify` runs in a delivery
disjoint from the builders, and `04-audit` in a context disjoint from
both. A run that cannot reach those contexts returns `blocked` naming
the authority it lacks, never a self-qualified verdict set.

Instantiate with `target` and `outcome` (the identity and the intended
observable outcome, which stay opaque to every stage), `sources` (the
source policy), `rigor` (the rigor bar acquisition's research pack
requires — the confidence each load-bearing claim must reach, stated as
the evidence that must exist for it), `bound` (the one caller bound the
stage allocations
partition), `pack` (the run's stamp, which `02-materialize`'s cut
re-stamps per case kind where a case's domain differs) and `package`
(where the benchmark is written). The run's bound is `00-acquire`'s
`bound`, the one caller bound every stage's own allocation is
partitioned from. Construction craft that no stub, rule
or contract owns is
[the protocol](../references/benchmaker-protocol.md); the manifest's
field set is [its own](../references/benchmaker-manifest.md) and
acquisition's lane cut is
[the charter's](../references/benchmaker-research.md). Each stub is a
ticket per [contracts/work-item.md](../../contracts/work-item.md)
missing only what instantiation adds.
