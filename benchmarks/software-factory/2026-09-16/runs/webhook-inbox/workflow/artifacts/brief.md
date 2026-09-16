# Webhook inbox delivery brief

Requested endpoint: working, validated Python standard-library webhook inbox and a checked patch plus human security-review release handoff. No live or simulated webhook release is authorized. Deadline: 2026-09-16T02:40:07.258925Z, from dispatch 2026-09-16T01:55:07.258925Z.

## Context and bounds

Project/candidate: <BUNDLE_ROOT>/runs/webhook-inbox/workflow/project

Run/evidence: <BUNDLE_ROOT>/runs/webhook-inbox/workflow/artifacts

Baseline commit: 30d2cde4c11a1912b47ca5256f6dd2a19419371e. Tracked files initially clean. Preserve intentionally untracked caller-note.txt (SHA256 1688056B517941C9189DC5C3D646E967D90F2D26DFC3532EB5764C755A80CD15). Baseline archive and smoke evidence are alongside this brief.

Use software-factory with P=3 candidate passes (initial included), maximum 19 child allocations, one fresh builder per pass and fresh applicable reviewers following passing checks. Model and effort unspecified and left unset. No release-worker allocation will be consumed because project policy forbids webhook release without human review. The existing project is the persistent candidate; only the active builder may change its source. Reviewers receive separate snapshots for test side effects.

Core root: <WORKFLOW_SOURCE@1a04d85254455012b9f73e2bced43218f9f755f5>

Library root: <WORKFLOW_SOURCE@1a04d85254455012b9f73e2bced43218f9f755f5>/example-workflows/software-factory

Resolved guidance, in order:

1. <WORKFLOW_SOURCE@1a04d85254455012b9f73e2bced43218f9f755f5>/guidance/code.md
2. <WORKFLOW_SOURCE@1a04d85254455012b9f73e2bced43218f9f755f5>/example-workflows/software-factory/guidance/software-delivery.md

Resolved primitives: core skills/orch-work/SKILL.md and skills/orch-review/SKILL.md. Missing core software-delivery is expected: the selected library owns that explicitly selected domain.

## Acceptance and checks

TASK.md is the full contract: exact public create_server/CLI behavior; HMAC-SHA256 authentication and timestamp boundaries; precise header/body validation and JSON errors; per-tenant authorization; SQLite durable raw bytes and event IDs; atomic idempotency under concurrency; insertion-sequence pagination; restart survival; no secrets in responses/logs; unknown tenants/paths; Python 3.11+ standard library only. The README's prompt.md reference is stale; TASK.md is present and authoritative.

Required checks before review: unchanged public `python -m unittest -v test_smoke`; `python -m unittest discover -v` including added behavior tests; `python -m py_compile inbox.py`; `python inbox.py --help`; whitespace check `git diff --check`. New tests should cover faults without write effects, retry/conflict concurrency, cross-tenant isolation, pagination boundaries, timestamp/body-size boundaries, persistence and factory/CLI startup. This is a local-only project: no required remote CI, publication, external service or benchmark performance target. Record raw command output outside source and tie it to a frozen candidate SHA256 manifest.

## Review and release

Applicable fresh lenses: correctness (all acceptance and failure behavior), data (schema, atomicity, durable bytes, pagination), security (headers, signatures, read authorization, tenant boundaries, SQL, leakage), infrastructure (local server lifecycle, resource handling, startup, operating/recovery documentation). Cloud omitted: no provider, cloud resource or external service is involved. Four independent reviews per checked candidate, at most five total children each pass.

Authentication/signature/tenant changes are high risk under project AGENTS.md; human security approval is mandatory for live release, even if automated reviews pass. Shared RELEASE_POLICY.md independently forbids webhook simulator deployment. Authorized simulator operation is read-only status; initial state is recorded. Deliver deployment/rollback preparation and open human decisions. Never claim deployment, production observation or approval.
