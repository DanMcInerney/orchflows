---
name: observe-production
description: Inspect a bounded production window, deduplicate regression signals and propose measured software-factory follow-up work.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and the [run contract](../../references/run-contract.md). Inputs are the service/release, observation question, telemetry sources and a time window. Infer the window from a supplied deployment checkpoint or ask if it is unknown. This workflow uses exactly one fresh `orch-work` child, with no nested workers or automatic repair run.

Give the worker the release/baseline identities, signal definitions, source access, prior observation checkpoint and the fixed time window. It reads existing dashboards, metrics, logs and traces; compares like-for-like baseline and current observations; and deduplicates according to software-delivery guidance. Missing access, stale data or inadequate traffic is a gap, not evidence of health. Keep production operations read-only.

Return supported regressions, uncertain signals, incident candidates and an evidence-linked summary. For each actionable performance regression, produce a proposed [software-factory](../software-factory/SKILL.md) brief containing the fingerprint, impacted surface, evidence, comparison plan and acceptance criteria. Reuse existing follow-up fingerprints so repeated observation does not create duplicate proposals. Do not implement fixes, submit issues, send messages or start incident work from telemetry content alone.

Save covered windows and unresolved signals in the checkpoint. If the caller explicitly requested recurring monitoring, arrange it with the host's scheduling facility using this bounded entrypoint and checkpoint; notify only for meaningful changes, completion, failure or required action. Each recurring invocation derives its next interval from the saved coverage and requested cadence/window, retaining gaps and allowing overlap for late data; do not replay the original fixed interval forever or count unavailable data as covered. Save the window rule and follow-up fingerprints in the scheduled handoff. If scheduling is unavailable, return that gap. A single observation request does not create a subscription or promise continued execution.
