---
name: fix
description: Take a failure to a proven, regression-guarded repair. Use for any bug or defect with an unknown or unverified cause.
entry: routed
---

Require: the observed failure and the workspace it lives in.

Steps:
- diagnose — `orch-diagnose`, profile `orch-worker`.
- repair — `orch-repair`, profile `orch-worker`; bound to the proven
  cause's defect set and the workspace as write scope.
- verify — `orch-verify` with, beside the original oracles, the
  regression guard the done check names.

Edges: seq diagnose → repair → verify — repair takes diagnose's proven
cause as evidence; verify takes repair's changed artifacts.

Invariants — Never: repair an unproven cause; widen into adjacent
cleanup; skip the regression guard because the fix looks obvious.

Done check: verify's verdicts over the original oracles plus one new
regression check that fails on the old behavior and passes on the new
— a fix without a regression guard is `limited`, not `complete`.

Return: status, result — the changed artifacts, verification including
the regression guard; then cause and reproduction.
