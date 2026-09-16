# Software delivery

## Make

Define acceptance through observable behavior. Select required checks before implementing; do not weaken a failing check to obtain a passing result. Tie builds, CI results and performance measurements to the actual candidate. For a performance-sensitive change, compare the baseline and candidate under equivalent workloads and conditions; separate regressions from measurement noise.

Prepare rollback and deployment signals while building the change. Prefer the project's existing rollout and telemetry mechanisms. A new dashboard is useful only when it resolves a specific visibility gap; define its queries and thresholds before creating it in an external system.

Deduplicate production signals by service, release, symptom and overlapping time window. Preserve underlying evidence and affected users; repeated alerts alone do not establish multiple incidents or a regression. Separate observed facts, causal hypotheses and proposed actions. Follow-up performance work needs a measurable regression, reproduction or comparison plan and acceptance criteria.

## Review

Assess the candidate against the requested behavior and real project context. A specialist label alone is not evidence of expertise. Use these lenses where applicable:

| Lens | Context and questions |
| --- | --- |
| Correctness | Acceptance criteria, callers, tests and failure behavior; does the change meet the request and preserve required behavior? |
| Data | Schemas, migrations, retention and consumers; are integrity, compatibility, backfills and reversibility accounted for? |
| Infrastructure | Runtime topology, CI, deployment and recovery; are availability, rollout ordering and rollback assumptions supported? |
| Cloud | Provider resources, IAM, quotas, scaling and cost; do the actual environment and permission boundaries support the change? |
| Security | Trust boundaries, authentication, authorization, secrets and dependencies; can changed inputs or access paths violate the project's security requirements? |

Each reviewer reports actionable findings with location, consequence and evidence; explicitly names missing context; and assesses risk within the assigned lens. Reviewers do not repair the candidate. Missing evidence is not a clean review.

A low-risk decision requires all of: bounded impact, understood behavior, passing required checks, complete applicable reviews without unresolved blocking findings, a supported recovery path and no material uncertainty. Changes to authorization, secrets, destructive data operations, public contracts or broad infrastructure require human review unless a specific established project policy covers the exact case. Disagreement or uncertainty takes the human-review path. Size of the diff alone does not establish low risk.

Human review can address judgment and risk; it does not turn failed checks or missing required evidence into success. Automatic review acceptance requires explicit project opt-in for the affected area. Release authority remains a separate requirement, even when automated review is accepted.
