---
name: orch-fix
description: Take a failure to a proven, regression-guarded repair. Use for any bug or defect with an unknown or unverified cause.
role: none
---

Require: the observed failure and the workspace it lives in.

Prove the cause through `orch-diagnose`, naming the `orch-worker`
profile. Repair through `orch-repair`, naming the `orch-worker`
profile, the proven cause's defect set and the workspace as write
scope. Verify through `orch-verify` with, beside the original oracles,
one new regression check that fails on the old behavior and passes on
the new — a fix without a regression guard is `limited`, not
`complete`.

Never: repair an unproven cause; widen into adjacent cleanup; skip the
regression guard because the fix looks obvious.

Return: status, cause, reproduction, changed artifacts, and
verification including the regression guard.
