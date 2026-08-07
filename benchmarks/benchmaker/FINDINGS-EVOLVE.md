# Evolve campaign findings — benchmaker vs. B(0), no promotion

Campaign 20260806T235733Z-evolve-benchmaker (runtime records under
the main checkout's `.orch/runs/`, this file the durable summary).
Frozen benchmark: the twelve-case set @ 966d8de sealed as
`sha256:fb7cd69d…f42b9d15`; incumbent evidence: B(0) sealed as
`sha256:683e7ba0…36b3b9f5`. Constants (chosen with the owner):
promotion = Pareto + net ≥ 3 over the incumbent's 27
(net = bad seeds caught − false-positive case events), 3 candidates
× 3 lanes, staged evaluation (six-case screen, full twelve for
finalists), two-generation bound, overfit wall (candidate text names
no case specifics). Candidate evaluation: one fresh-context
benchmaker execution per (candidate, case), seed-scored by the
frozen B(0) scorer; refusal and contradiction judged from the
produced package, never the seed matrix.

## Outcome

No promotion; incumbent retained. The closing judge's score card
satisfies criteria (a) no metric regression, (b) clean sweeps, and
(c) lawfulness — and fails (d): net 27 < 30. Six candidates over two
generations were all lawfully killed:

| gen | candidate | thrust | outcome |
| --- | --- | --- | --- |
| 1 | c1 | license exhaustion bound at input-carriage | best of campaign: full suite 30/32, 1 FP event, net 29 — killed by margin (−1) and one clean-sweep regression |
| 1 | c2 | evidence-silence + variant tolerance | screen pass net 9; killed by margin ceiling (its own B2 trap reproduced on its home case) |
| 1 | c3 | minimal three-sentence integration | killed at screen: verbatim-only casing regressed sparse-evidence to 0/3 |
| 2 | d1 | c1 + all three gen-2 laws | killed: one variance miss + law-crowding collapse to 0/3 |
| 2 | d2 | c1 + minimal two-law delta | screen pass net 10; killed by margin ceiling 29 |
| 2 | d3 | c1 + anchor + executed-variant laws | killed at screen: sparse 0/3; capacity FP recurred |

The frozen rule did its job: every candidate that beat the incumbent
on aggregates had lost something the incumbent discriminated. c1's
full-suite evidence (B2 and B4 fixed, half of B1, one FP family
halved) is admitted and sealed; adopting its text is a delivery
decision outside campaign law, and any adopted successor starts a
new campaign under a re-qualified benchmark.

## Findings

**E1 — gap-declaration is a lawful exit from exhaustion.** Every
protocol variant that stated coverage law at design-acceptance or
qualification saw builders satisfy it by declaring gaps instead of
materializing cases (sparse-evidence: five of six builds at or below
the incumbent's 1/3). Tightening the clause to
impossible-within-bound did not change single-run behavior. Coverage
law binds only where it forces enumeration into the design packet's
inputs before case authoring — and even there inconsistently (E5).

**E2 — laws crowd.** The candidate carrying the most law produced
the worst under-generation of the campaign: its builder satisfied
the cheap, checklist-shaped anchor law (one oracle per exhibited
pair) and shipped nothing beyond the exhibits while reporting zero
gaps. A cheap-to-satisfy law displaces an expensive open-ended one;
remedies must compose into one obligation, not stack.

**E3 — the exhibited↔licensed form gap defeats protocol text.**
Seven builds across four protocol variants each produced a
workflow-parser brittle at a different guessed spelling; all seven
scored the identical 3/3 + 2 FP. Even the executed-fixture law
(self-run must run every exhibited form) failed, because the case's
good implementations use forms the evidence licenses but never
exhibits — the trap this case plants. This edge belongs to the
benchmark, not to any one-context protocol remedy; candidate
generations should stop targeting it and evaluation should treat it
as a constant.

**E4 — exhibited anchors carry unique discrimination.** The one
clean-sweep regression of the campaign came from a builder judging
an exhibited input/output trace "an implementation artifact" and
dropping it; that trace anchored the only oracle catching the
restream seed. Where the anchor law was honored, the trace's oracle
reappeared. An exhibited concrete artifact is licensed oracle
material; excluding it needs an impossibility reason.

**E5 — single-run scores are noisy at the kill margin.** Repeat
builds of the same (protocol, case) moved ±1-2 seeds: the tombstone
seed was caught or missed across runs of near-identical protocols;
the invented `capacity` attribute FP struck two of six rate-limiter
builds — a convergent attractor the case design deliberately baits.
At one build per cell, candidate scores conflate protocol quality
with builder-run luck, and the Pareto rule converts one unlucky
seed into a kill. The bench-stack port should score the median of n
independent builds per cell.

**E6 — exhaustion generativeness tracked the builder model.** Only
the strongest-model builder composed witnesses across quantifier
ranges beyond the exhibits (2/3 on sparse-evidence); every other
build stopped at or near the exhibited pairs regardless of protocol
text. B1's remedy is bounded by builder generativeness, not by law
alone.

## Campaign-harness notes

- The digest-last interface rule held: the B(0) unverified-digest
  defect did not recur in thirty gen-1/gen-2 packages.
- All protected-evidence walls held across 36 builder executions;
  builders relayed friction they could not log rather than breach
  write scope (one wrote into the qualifying context's results
  directory once — packet wording now forbids it explicitly).
- Refusal and contradiction lawfulness were preserved by every
  candidate in every build: the campaign's regressions were all on
  the discrimination axis, never on lawfulness.

## Next steps, in order

1. Owner decision on c1's text (delivery outside campaign law;
   adoption re-qualifies the benchmark and arms a new campaign).
2. Settlement round harness (unchanged from FINDINGS-B0; still the
   gate on contradictory-evidence discrimination).
3. bench-stack port carrying: median-of-n scoring (E5),
   contradiction-register scoring, held-out seed storage, scorer
   fixture.
4. Thirteenth case: multi-candidate ranking.
