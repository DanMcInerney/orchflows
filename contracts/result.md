# Result contract

The executor files work into its ticket's `## Result`, `## Verification`,
`## Feedback`, `## Risks`, and optional `## Handoff` sections as it is
produced. These records are append-only after seal and do not change the
semantic assignment digest.

The join reads the fixed candidate identity and its actual diff, checks the
returning name against the claim, adjudicates blockers against Goal and
Context, and records terminal status. Deterministic repository-global gates
run on the integrated tip. Suggested files are never an acceptance boundary.
