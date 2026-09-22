# Software delivery

## Make

Define observable acceptance and required checks before implementation; never weaken failures into passes. Bind builds, CI and performance results to the candidate. For performance-sensitive changes, compare equivalent baseline/candidate workloads and conditions, separating regressions from noise.

Verify the delivered artifact, not only the workspace. A complete patch must reconstruct the candidate from its recorded clean baseline, including additions/deletions. Export bytes without shell text conversion; check/apply the actual saved patch in isolation and compare file set/content under project Git attributes. Record patch hash, baseline, candidate and reconstruction. Tracked-only diffs and `git diff --check` prove no complete handoff. For commits/other artifacts, verify the exact delivered object against the candidate.

Prepare rollback/signals while building. Prefer existing rollout/telemetry; create a dashboard only for a specific visibility gap, defining queries/thresholds before external creation.

Deduplicate production signals by service, release, symptom and overlapping window. Preserve evidence/affected users; repeated alerts prove neither distinct incidents nor regression. Separate facts, causal hypotheses and actions. Performance follow-ups need measurable regression, reproduction/comparison plan and acceptance.

## Review

Judge requested behavior in actual project context; specialist labels alone prove no expertise. Apply relevant lenses:

| Lens | Context/checks |
| --- | --- |
| Correctness | Acceptance, callers, tests, failure behavior; requested and preserved behavior |
| Data | Schemas, migrations, retention, consumers; integrity, compatibility, backfills, reversibility |
| Infrastructure | Topology, CI, deployment/recovery; availability, rollout ordering, rollback |
| Cloud | Resources, IAM, quotas, scaling, cost; actual environment/permission boundaries |
| Security | Trust, authentication/authorization, secrets, dependencies; changed inputs/access paths |

Report actionable locations, consequences and evidence, missing context and lens-specific risk. Make no repairs; missing evidence is not a clean review. Correctness also inspects delivered identity/reconstruction: broken required handoffs block readiness despite passing workspace tests.

Low risk requires bounded impact, understood behavior, passing checks, complete applicable reviews without blocking findings, supported recovery and no material uncertainty. Authorization/secrets changes, destructive data operations, public contracts and broad infrastructure require human review unless specific established policy covers the exact case. Disagreement/uncertainty also takes that path; small diffs alone are not low risk.
