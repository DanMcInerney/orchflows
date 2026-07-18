# Skill tournament (non-normative example)

Evolve applied to the library itself: competing variants of one skill
run the same work and are judged by the same oracles. The standing
method-test harness — how an empirical question about a skill's wording
gets settled by evidence instead of taste.

Fix the fixture first: a frozen set of work items with known oracles —
`orch-fixture` harvests them from real completed runs. `orch-build`
writes the variants, each differing in only the wording under test.
Per variant: an isolated workspace with the variant installed, the
fixture run through `orch-task`, results scored — deterministic
fixtures by their oracles, judged fixtures through `orch-panel` blind
to which variant produced what. The winner replaces the incumbent
through `orch-build` like any change.

One variable per tournament: variants differ in the one wording under
test, or the result attributes nothing.
