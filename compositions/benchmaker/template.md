---
name: benchmaker
description: Build and qualify one runnable benchmark for any target with an observable outcome.
entry: named
placeholders: [target, outcome, sources, rigor, pack, package]
---

One benchmark for one opaque target: evidence is acquired and frozen,
an evaluation is designed from it, the design is materialized exactly,
the assembly is qualified by someone who did not build it, audited by
someone who did neither, and finally measured on
[the protocol](../references/benchmaker-protocol.md#measurement-pass)'s
terms.

Independence is what the chain is for: `03-qualify` runs in a delivery
disjoint from the builders, and `04-audit` in a context disjoint from
both.

Instantiate with `target` and `outcome` (the identity and the intended
observable outcome, which stay opaque to every stage), `sources` (the
source policy), `rigor` (the rigor bar acquisition's research pack
requires — the confidence each load-bearing claim must reach, stated as
the evidence that must exist for it), `pack` (the run's stamp) and
`package` (where the benchmark is written). Construction craft that no
stub, rule or contract owns is
[the protocol](../references/benchmaker-protocol.md); the manifest's
field set is [its own](../references/benchmaker-manifest.md) and
acquisition's lane cut is
[the charter's](../references/benchmaker-research.md).
