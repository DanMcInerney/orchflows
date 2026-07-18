---
name: orch-evolve
description: Bounded generations of judged parallel candidates against a frozen bench, toward a declared target. Manual-only evolve pattern.
disable-model-invocation: true
role: none
---

Require: the incumbent artifact by identity; the goal as stated; a
done-check independent of the bound — a target score or a stated
margin over the incumbent, that decision settled through
`orch-elicit` when undeclared; a generation width; and a bound. When
the artifact's class matches a pack, its craft, lens, and oracle
references bind generation and judging; nothing here invents domain
best practice.

Freeze the bench through `orch-bench` (design mode). Run `orch-loop`
with: body — one generation: dispatch one lane per variant in
parallel through orch-delegate, every result crossing orch-integrate,
the incumbent as fixed input, the generation brief's dimensions to
vary and constraints to hold verbatim, and its executor binding, then
orch-panel judges the fixed set, incumbent
plus every variant, against the frozen bench; a winning variant
promotes as the new incumbent, every non-winner a killed approach
carrying the panel's evidence; between generations only, on panel
disagreement or a criterion with no score spread, re-run `orch-bench`
(revise mode) and re-score the incumbent under the versioned bench
before the next generation counts as progress. Done-check — the
declared target or margin, judged through a fresh `orch-judge` pass
over the final incumbent alone, never the promoting generation's panel
score. Packet — the incumbent's identity and score card, grafted
runner-up elements, and the disagreement register. Bound — the
generation cap. Terminal states — complete, stalled, limited — follow
[rules/loops.md](../../../rules/loops.md).

Never: compare candidates across generations without the frozen bench;
promote a variant the loss check contradicts.

Return: the final incumbent's identity and closing score card,
generation count, bench version history, the promotion/kill log, and
bounds spent.
