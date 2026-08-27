# Result contract

The executor files work into its ticket's `## Result`, `## Verification`,
`## Feedback`, `## Risks`, and optional `## Handoff` sections as it is
produced. `Result` identifies the delivered artifact. `Verification` records
the methods the executor chose, their observations, the Goal portions they
cover, contradictions, and gaps. Code tests are one possible method, not a
ticket-authored criterion. Research, design, content, and specification work
use the artifact-appropriate evidence in
[verification.md](../rules/verification.md) §2. These records are append-only
after seal and do not change the semantic assignment digest. Every successful
section write adds exactly one canonical writer attribution, `### Written by <claimed_by>`,
and returns that identity. The required `--by` value matches `claimed_by` on the
currently claimed ticket; the command refuses absent or different identities
and never changes lifecycle state.

A read-only critique records findings in `## Feedback`; it never rewrites the
executor's Result or Verification. A verifier records its independent verdict
and evidence in `## Verification`.

The join reads the fixed candidate identity and its actual diff, checks the
returning name against the claim, adjudicates only material blockers against
Goal and Context, and records terminal status. Deterministic repository-global gates
run on the integrated tip. Suggested files are never an acceptance boundary.

A dispatch-v1 committed record stores the protocol command's success for
replay. It is not an executor Result, does not replace this section's writer,
and makes no exactly-once external-side-effect claim.

T0 supersession record sha256:9c4a109ca9158a60109f756f02e28673270cc741d8ad2e6a2fa06529841d5fdd: result section writes now require and return their current claim writer.
