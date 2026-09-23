---
name: gauntlet-loop
description: Drive an ambitious goal past a real-world quality bar by splitting it into pieces, each looped through a builder and a fresh, harsh, blind critic until ours reaches the bar or the caller stops.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) as the coordinator (the lead). Inputs: goal, optional bar or candidate references, workspace and output location, optional caller bounds (time, cost, rounds) and scoped settings. Treat the goal as the destination: choose the architecture, pieces and order, adding no scope the caller did not ask for.

## Set the bar

The bar is a named, inspectable thing that ours can sit beside and lose to: reference artifacts for subjective quality, or tests, measurements and reference implementations for engineering. Use a supplied bar. Otherwise find the concrete comparison that plays the role real Call of Duty screenshots played for [Claude of Duty](https://github.com/mshumer/Claude-of-Duty/blob/main/prompt.md); "better", "production-ready" or a self-written rubric is not a bar. The bar need not be reachable. Gather the reference material into the output location, record the bar with one sentence on why it fits, and continue without a permission round unless the caller asked to approve it.

Reaching the bar means beating a reference, or matching a threshold bar such as a test suite, a target or an explicit "as good as".

## Split the work

Divide the goal into the smallest pieces that can be improved and judged separately, each mapped to the part of the bar it must reach. A piece the bar does not cover, such as sound when the bar is screenshots, gets its own. Keep coupled parts together where judging them apart would mislead. Run independent pieces concurrently within host limits; give shared files one owner. Add, merge or split pieces as the artifact teaches you.

## Run each piece through the gauntlet

A round is one build and its judgment for one piece. Record it before the build starts; consumed rounds carry through smoothing, splits and merges. Caller round bounds apply per piece unless the caller says otherwise.

1. **Build.** A builder makes or revises the piece from the goal, its slice of the bar, the latest gap and applicable guidance, and may study the bar. Continue a builder across rounds or replace it as useful.
2. **Judge.** Freeze the piece and apply `shared:compare-candidates` to ours and its reference, with a comparer who has not judged this piece before. Supply the goal, bar, binding rules and the actual output to inspect: rendered, run, played or read. Never supply the builder's history, reasoning or summary. Blind the pair where possible, with anonymous labels and randomized order; for measurement bars the critic runs the measurement. Ask for the better side and the largest meaningful gap in the side not picked, or in each side on a tie.
3. **Close the gap or confirm.** When ours falls short, map the gap back to ours; the next round starts from it. When ours reaches the bar, confirm with another `shared:compare-candidates` call by a fresh critic, without the first verdict: reversed order for judged comparisons, a matched re-run for measurements. Disagreement is a loss.

There is no fixed number of rounds. A piece that stops improving changes approach and shows the stall on the progress page; stalling is not completion.

## Smooth between waves

When separately improved pieces start to clash, have one fresh maker, with the builders' guidance, inspect the whole result and reconcile conflicts without redesigning it. Pieces it changes lose their confirmations and re-enter the gauntlet.

## Show progress

Maintain a live progress page in the output location, HTML or Markdown, showing the bar and each piece evolving: renders, drafts, test results, verdicts, stalls and remaining gaps, in whatever form suits the work. Update it as work lands so the caller can watch without interrupting. It and the run records must let a later session resume without redoing judged rounds.

## Stop and return

Stop when every piece holds a confirmation for its current state, the caller stops the run, a caller bound is reached or every remaining piece is blocked. Missing rendering, inspection or independent review blocks the pieces that need it; builder claims never stand in for a critic's view of the output.

Return the artifact, the bar and why it was chosen, each piece's final verdict and largest remaining gap, rounds and observed cost, smoothing passes, the stop reason and the progress page. A run stopped while ours still falls short is an ordinary result; say where.
