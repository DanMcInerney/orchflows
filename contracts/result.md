# Result contract

The executor files work into its ticket's `## Result`, `## Verification`,
`## Feedback`, `## Risks`, and optional `## Handoff` sections as it is
produced. `Result` identifies the delivered artifact. `Verification` records
the methods the executor chose, their observations, the Goal portions they
cover, contradictions, and gaps. Code tests are one possible method, not a
ticket-authored criterion. Research, design, content, and specification work
use the artifact-appropriate evidence in
[verification.md](../rules/verification.md) §2. These records are append-only
after seal and do not change the semantic assignment digest.

A read-only critique records findings in `## Feedback`; it never rewrites the
executor's Result or Verification. A verifier records its independent verdict
and evidence in `## Verification`.

The join reads the fixed candidate identity and its actual diff, checks the
returning name against the claim, adjudicates only material blockers against
Goal and Context, and records terminal status. Deterministic repository-global gates
run on the integrated tip. Suggested files are never an acceptance boundary.
