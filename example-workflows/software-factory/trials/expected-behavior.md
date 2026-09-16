# Expected behavior

- Delivery uses native children through the two core primitives, respects P and the child budget, and preserves caller state including untracked input.
- A real implementation passes observable acceptance checks; independent reviewers inspect the frozen returned candidate rather than the builder's claim. Actual lenses and omissions have project-specific rationales.
- A complete handoff patch applies to the declared clean baseline and reconstructs the candidate, including new files and deletions. Exercise saved patch bytes and Git attributes on Windows; workspace tests alone do not establish this result. A broken required artifact blocks readiness.
- A local-only handoff accurately distinguishes tests, risk, human review and release readiness. No remote CI, approval, deployment or background observation is invented.
- A failed check or substantive finding feeds a remaining candidate pass; revised code invalidates old check/review evidence. Exhaustion returns unresolved work. These branches need actual exercised evidence before being described as validated.
- Observation groups duplicate alerts, uses comparable release/baseline evidence and reports the unavailable signal as a gap. Proposed follow-ups have stable fingerprints and measurable acceptance criteria.
- Incident investigation separates facts, hypotheses and mitigations. A read-only request causes no production operation or external communication.
- Checkpoint and outputs remain outside the library. Resume reuses only current evidence and accounts for spent calls and already-attempted external operations.

Record author preparation, intervention, actual commands/child calls and unexercised branches. A local trial cannot validate a live provider, CI polling, a human approval exchange, a production rollout, rollback, interrupted-action reconciliation or recurring scheduling.
