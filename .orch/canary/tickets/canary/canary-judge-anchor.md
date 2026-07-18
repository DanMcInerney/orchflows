---
id: canary-judge-anchor
run: canary
status: ready
executor: orch-judge
depends_on: []
write_scope: .orch/canary/scratch/judge/scorecard.json
bound: 5 tool calls
---
## Objective
Score the prose sample below against the rubric; write one score card
to scorecard.json.
## Fixed inputs
Prose (10 lines, verbatim):
Oracle-based verification beats self-report because a model grading
its own work shares the same blind spots that produced the work.
An external oracle has no stake in the answer being right.
This is why every criterion here names an oracle, never a claim.
Self-report is fast, which is exactly why it is dangerous at scale.
A deterministic check is strongest: same input, same output, no drift.
Judged criteria are weaker: they still need a fresh, blind context.
Evidence criteria are the slowest but resolve real-world claims.
None of these classes should be blended into one fuzzy "looks good."
Keep them separate, and the loop policy for each stays legible.
Rubric (1-5 each): Clarity - one claim per sentence, no hedging; Evidence - claims backed by a mechanism/example, not asserted; Structure - piece builds in order toward one conclusion.
## Completion test
1. scorecard.json has one score 1-5 with quoted evidence per
   criterion. Oracle: orch-judge rubric scoring above. oracle_class:
   judged.
## Return fields
status, changed_artifacts, verification.
## Result
[]
## Verification
[]
## Feedback
[]
## Risks
[]
