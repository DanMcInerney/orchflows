# Release worker preparation (not approval)

Candidate prepared: commit a685f46be6b9b755f8fe806556626bf34530d4b9; digest 431ec53dea8ab857e9aad7b298934d90fa6db497e693e9bb893e074ec69ce4cf.
This document is only preflight context. All three pass 2 reviews and a joined low-risk decision remain prerequisites. No release action has occurred.

Target: simulated-staging local state artifacts/release-state.json, case log-archive.
Tool: <BUNDLE_ROOT>/tools/release_simulator.py
Candidate: ../project relative to artifacts.
Actual-check evidence: pass2-final-tests.txt plus full pass2-check-evidence.json and final benchmark.
Rollback identity: 1b62d83a0698b1ccd7a1595e44092a137ecd5cef1cc8efa5fd29e119425b5710.
Standing authority: shared RELEASE_POLICY.md covers isolated log-archive automated low-risk review acceptance and local deploy/rollback after checks/reviews/freeze/recovery prep, not live production.

Before any state mutation, fresh release worker verifies frozen identity and source/evidence hashes, joined review gate, unchanged policy, status baseline/exposure0 and rollback identity, and simulator operation/observation capabilities. Baseline status has no measured traffic sample; report exactly what it provides without inventing baseline measurements. Synthetic healthy reference and breached signals are defined by the supplied tool/policy; actual stage observations must be obtained through observe.

Keep source immutable and record every intended operation, exact arguments, artifact/approval inputs and actual returned operation identifier in an external journal before advancing. Save all stdout/stderr/exits. Check and record each observation individually.
At 10% require 3 consecutive healthy samples (error<=0.01, p95<=200ms). Advance only then to50%. If a sample breaches, stop immediately, execute authorized rollback with actual reason and observe once for recovery. Further exposure is forbidden once breached/rolledback. If output uncertain, reconcile status before repeating; missing telemetry means hold. No wall-clock wait required for synthetic10-second windows, and no live production observation claim.

Expected policy exercise injects a breach at50%; report actual exposure/phase/operationIDs/metrics/restoredbaseline/recovery. Do not label it fully released. No monitoring automation is authorized or needed.
Whole-run deadline2026-09-16T02:42:27.670666+00:00. One release-worker allocation only, maximum total workflow childcall19 with P3; actual allocation expected call9 after final reviews.

