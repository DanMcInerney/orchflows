# Delivery loop (non-normative example)

Converge a workspace through two delivery runs: deliver an original
spec, rebuild that spec from the first run's evidence, then deliver the
replacement once. `orch-goal` owns this fixed sequence; its second run
uses the replacement instead of replaying the original spec.

Freeze the original user request, original spec, and three-part bound
first. Delivery 1 runs the original spec even when it may already pass.
Its result, verification, uncovered remainder, feedback, failed
approaches, problems, and workarounds converge into the packet owned by
[orch-goal's second-pass design](../skills/workflows/orch-goal/references/second-pass.md).

Before delivery 2, orch-spec re-reads the exact original request, the
original spec, and that packet as evidence. It writes a new
`pattern: deliver` spec under a new run id and the reserved second-run
budget; orch-deliver runs the new spec once. The original spec remains
unchanged, discovered scope stays queued, and there is no third delivery.

Delivery 2's final verification and status close the goal. Delivery 1's
status cannot skip re-specification when its returned evidence can still
support it.
