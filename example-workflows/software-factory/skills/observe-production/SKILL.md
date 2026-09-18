---
name: observe-production
description: Inspect a bounded production window, deduplicate regressions and propose measured follow-up work.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and [run contract](../../references/run-contract.md). Inputs: service/release, question, telemetry and time window. Infer the window from a deployment checkpoint or ask if unknown. Use `orch-work`; no automatic repair follows.

Supply release/baseline identities, signal definitions, access, prior checkpoint and fixed window. Assign read-only inspection of existing dashboards/metrics/logs/traces, like-for-like comparison and deduplication under delivery guidance. Missing access, stale data and insufficient traffic are gaps, not health.

Return supported regressions, uncertainty, incident candidates and linked evidence. For each actionable performance regression, propose a [software-factory](../software-factory/SKILL.md) brief: stable fingerprint, affected surface, evidence, comparison plan and acceptance. Reuse fingerprints to avoid duplicates. Telemetry alone authorizes no fixes, issue submission, messages or incident work.

Checkpoint covered windows and unresolved signals. Only on an explicit recurring request, schedule this bounded entrypoint/checkpoint through the host; notify on meaningful change, completion, failure or required action. Derive each next interval from saved coverage and requested cadence/window, retaining gaps and allowing late-data overlap. Never endlessly replay the initial interval or mark missing data covered. Save the window rule/fingerprints in the scheduled handoff. Report unavailable scheduling; one observation creates no subscription.
