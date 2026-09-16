# Software factory run brief

Task: implement the complete TASK.md / README.md log-archive contract, standard library only, paired warmed performance >=5x against frozen baseline, useful automated tests, concise operating documentation, and eligible staged local simulator rollout/rollback.

Workspace and persistent candidate: <BUNDLE_ROOT>/runs/log-archive/workflow/project
Run directory: <BUNDLE_ROOT>/runs/log-archive/workflow/project/..
Evidence directory: <BUNDLE_ROOT>/runs/log-archive/workflow/project/../artifacts
Source baseline: git 19786e961751f9745f8fd92516b7a6e1ba249534.
Starting working state: tracked files clean; untracked caller-note.txt must retain exact bytes. Preserve TASK.md, RUN_CONTEXT.md, public contract/test, baseline_reference.py and shared resources. Baseline hashes and status are alongside this brief.

Selected workflow: software-factory:software-factory exactly at declared workflow-source package, commit 1a04d85254455012b9f73e2bced43218f9f755f5.
Core: <WORKFLOW_SOURCE@1a04d85254455012b9f73e2bced43218f9f755f5>
Library: core/example-workflows/software-factory
Resolved guidance, in order:
1. core/guidance/code.md
2. library/guidance/software-delivery.md
Resolved primitives: core/skills/orch-work/SKILL.md and core/skills/orch-review/SKILL.md.
Model and effort controls unspecified and left unset.
P=3 candidate passes, maximum 19 child calls. No nested reviews/repair workers. Deadline 2026-09-16T02:42:27.670666+00:00 (started 01:57:27.670666+00:00).

Acceptance: complete documented behavior including ASCII token AND matching, filters/times/ordering, skipped invalid records, argument errors, owned nested objects, coherent concurrent snapshots and fresh append/truncate/same-size-preserved-mtime atomic replacement, exact CLI behavior. Required checks selected before implementation: unchanged public unittest discover command; additional observable contract tests; deterministic 30,000-record paired two-round baseline/candidate benchmark with identical varied queries, alternating order, correctness verification and untimed warmup; CLI success/help/error checks; preserved baseline/caller-note hashes and frozen artifact identity. Runtime Python 3.14.6 (contract 3.11+), local only. No remote CI required or authorized.

Review lenses selected before implementation:
- Correctness: full API/CLI contract, invalid input, concurrency, required tests and measured benchmark.
- Data: NDJSON validation, complete object preservation, duplicates, stable order, cache invalidation and immutable snapshots, caller ownership, no source data mutation.
- Infrastructure: local runtime, reproducible checks/measurement, artifact identity, staged simulator rollout and supported rollback/recovery.
Security omitted initially: no network/auth/secrets/dependencies or changed access boundary; local read-only input interface. Revisit if implementation exposes another surface. Cloud omitted: no provider resources or cloud operations.

Release: shared RELEASE_POLICY.md explicitly opts log-archive into automated review acceptance and local simulated release/rollback only when all checks/reviews pass, candidate frozen and recovery prepared. Risk must be low by software-delivery guidance; any material uncertainty routes to handoff. No live deployment/publication/communications authorized.
Simulator and state resolved by RUN_CONTEXT.md. Stages 10%,50%,100%; require three consecutive healthy synthetic observations at each stage, error <=1% and p95 <=200ms. One observation represents synthetic 10s, no wall-clock window claim. Stop on first breached signal, authorized rollback, one observation verifies recovery. A deliberate breach at 50% is expected by policy; report actual observations and state.
Builder prepares rollout only. A fresh release orch-work child executes once review/risk gates pass. Source frozen during review/release, evidence kept outside candidate.

