# B(0) findings — benchmaker scored against its own case set

Campaign 20260806T142801Z-b0-campaign (runtime records under the main
checkout's `.orch/runs/`, this file the durable summary). Twelve
benchmaker executions — one per case in `cases/` — each a
single-context walk of the composition's stages seeing only its
case's `evidence/`, with `case.toml`, probes, `expected.md`,
`target/`, and `seeds/` excluded by dispatch authority. Scored by the
qualifying context against the protected seeds per the hardened
qualification protocol (seeded discrimination, supplied by the
qualifier).

## Scorecard

91% discrimination: 29 of 32 scoreable bad seeds caught. Two
false-positive events. Refusal correct. Every produced package sealed
under a recomputing manifest identity.

| case | caught | FP | verdict |
| --- | --- | --- | --- |
| unobservable-outcome | n/a | n/a | PASS — lawful refusal; seven channels enumerated; non-empty-line proxy considered and rejected as a false oracle |
| cli-dedupe | 4/4 | 0 | PASS — 23 cases, expectations double-derived from spec prose |
| overfit-trap | 3/3 | 0 | PASS — builder excluded the worked examples from its cases on principle; the hardcoder failed 8 of 12 |
| skill-summarize | 3/3 | 0 | PASS — constraint values frozen inside the runner, judged half anchored and secondary |
| multi-domain | 3/3 | 0 | PASS — chained code-pack/content-pack design; agreement criteria caught both single-domain liars |
| nondeterministic-target | 3/3 | 0 | PASS — three blind oracle strategies; restream near-miss caught by the one recorded stream |
| cost-explosion | 3/3 | 0 | PASS — 338 of 2000 calls; witness-per-rule on both sides of each boundary; 7.4e-7-density near-miss caught |
| lib-rate-limiter | 4/4 | 2 | FP — finding B2 |
| composition-target | 3/3 | 2 | FP — finding B3 |
| stateful-plugin | 2/3 | 0 | PARTIAL — finding B4 |
| sparse-evidence | 1/3 | 0 | PARTIAL — finding B1 |
| contradictory-evidence | 0/3 by design | 0 | LAWFUL — see below |

## The four findings (the evolve feed)

**B1 — under-generation within license** (sparse-evidence, 2
misses). The intent sentence's universal quantifier ("every value")
licensed repeated-key and long-value cases exactly as it licensed the
one distinct-keys case the builder materialized. Zero overreach —
the caution direction was right — but the license was not exhausted.

**B2 — invented interface surface** (lib-rate-limiter, 2 false
positives). A required case asserts a public `capacity` attribute;
no evidence fixes any public attribute (constructor + `allow()`
only). The design law forbids invented domain truth; the builder
applied it to semantics but not to interface surface.

**B3 — parser brittleness on valid variants** (composition-target, 2
false positives). Tolerances were enumerated for seen forms
(`Never` | `Invariants` | `## Key` | `Key:`) but the valid compound
`Invariants — Never:` parsed as a missing section, cascading two
criterion failures. The case's structurally-different good seed was
planted for precisely this.

**B4 — transcript under-generation** (stateful-plugin, 1 miss). The
CLI contract's exit-1-on-absent-key rule licensed a
delete-same-key-twice witness; the transcript never bought it, so
the tombstone seed passed. Same family as B1.

**Signature**: one behavioral axis. Benchmaker under-exploits what
evidence licenses (B1, B4), under-generalizes across valid candidate
forms (B3), and over-reads surface where evidence is silent (B2).
Candidate remedies are one-to-two lines each in the protocol's
design/qualification text — e.g. "exhaust the license: every
universally quantified evidence statement carries witnesses across
its quantifier's range" and "an expectation the evidence does not
fix — interface surface included — is an assumption or gap, never a
required criterion; parse tolerances span the space of valid
variants, not the reference's spelling." Every remedy is measurable
against this same case set: the evolve campaign is armed.

## The contradiction case, read correctly

Benchmaker registered the disagreement verbatim (both sides quoted,
unresolved — no ranking invented), made the contested boundary
non-scored, and proved neutrality with its own seed pair differing
only on that boundary. Its mechanical 0/3 is the lawful outcome: all
three protected seeds differ from the reference only at the
unscored boundary. Two consequences carry forward: (1) full
discrimination needs a settlement round (a caller settles the
registered disagreement, benchmaker re-enters) that the one-shot
campaign packet cannot offer; (2) a builder that unlawfully picked a
side would have scored 3/3 mechanically — this case's scoring must
read the design's disagreement register, never the seed matrix
alone. Both bind the bench-stack adapter design.

## Campaign-harness findings (not benchmaker's)

- Implementation layout is unfixed by the interface; three builders
  invented discovery heuristics (friction-logged, contract-gap).
- The manifest's required qualification reference is chicken-and-egg
  before qualification runs; identities may need re-minting after
  the qualifying verdict (friction-logged).
- The campaign scorer itself initially inverted every verdict via a
  relative-path cwd bug — caught by implausibility, fixed, all cases
  rescored. The port needs a scorer fixture.
- Shared session scratchpad collided across four parallel builders.

## Next steps, in order

1. PR this branch (case set + protocol hardening + this file).
2. Evolve campaign: incumbent = `example-workflows/benchmaker.md` +
   `references/benchmaker-protocol.md` at this branch; benchmark =
   this case set with the campaign scorer; findings B1-B4 as
   generation direction; the seven clean sweeps as regression
   criteria.
3. Seal B(0) as a manifest over the twelve produced packages.
4. bench-stack plugin port (`benchmark.toml` + `adapter.py` walking
   `cases/*/case.toml`), carrying the contradiction-register scoring
   rule and held-out seed storage.
