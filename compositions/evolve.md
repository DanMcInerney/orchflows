# Evolve (non-normative example)

Best verified candidate from variation under selection — seeded with
one artifact to improve or several to choose among, textual or
behavioral. Run inputs: the seed(s), the goal, the generation width,
the judge count, the target or margin, and the bound.

Open with `orch-bench`: frozen criteria, weights, aggregation, loss
check, task set, and the generation brief, grounded in the matching
pack's craft and oracle references. Score the seed(s) first through
`orch-panel`; the best becomes the incumbent, and its score card seeds
the brief.

Run `orch-loop` with body — one generation: dispatch N generation
lanes from the brief in parallel through `orch-delegate`, each variant
attacking a different weakest criterion of the incumbent's score card
while holding the brief's constraints verbatim — directed variation,
never N random rewrites; every lane result crosses `orch-integrate`. A
behavioral candidate — a skill, a prompt — first runs the
bench's task set in an isolated workspace, `orch-task` per item; the
panel scores its outputs, never its text. `orch-panel` scores
incumbent and variants together with the run's judge count, lanes
blind to provenance and to iteration history. A variant replaces the
incumbent only by a declared margin with a clean loss check — a tie
keeps the incumbent. Graft the runners-up's best-scored elements into
the next brief. Packet: the incumbent's identity and score card, the
grafted elements, and the disagreement register.

Between generations only, `orch-bench` revise mode may rewrite
criteria the panel's disagreement register or a dead score spread
indicts; retained candidates re-score under the new version.

Done-check: a fresh `orch-judge` pass over the final incumbent alone
against the declared target score or margin, frozen before iteration
1 — never the promoting generation's panel score. Bound caps
generations; two iterations without margin improvement exit stalled
with the incumbent. The final verdict is judged-class and says so: the
loop optimizes the bench's letter, so the loss check and a human read
of the winner guard against having optimized the wrong thing.
