---
name: investigate-incident
description: Investigate incidents and propose mitigations; execute only a specifically authorized operation.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and [run contract](../../references/run-contract.md). Inputs: service, signal/question, telemetry/runbooks and incident window. Use `orch-work`; add no source repair loop or automatic deployment.

Supply context, release history, access, known actions and exact authorization. Assign one execution owner per authorized external operation; other investigation remains read-only. Reconstruct timeline/impact, test causal hypotheses, answer incident questions and rank mitigations by expected effect, scope, risk and recovery checks. Distinguish correlation from cause and unavailable telemetry from normal signals.

Investigation grants no mitigation authority. A specifically authorized operation may execute once after checking current state/preconditions. Record intent first, reconcile uncertain outcomes before retrying, verify effects and report unresolved impact. Failure authorizes no substitute mitigation, broader rollback or code change. Later authorization starts a new bounded invocation from the checkpoint, accounting for prior actions.

Return timeline, impact, evidence, hypotheses, proposals and actual actions separately. If code work is justified, propose a software-factory brief; implementation needs a caller request. Incident-channel messages/paging require separate explicit authorization.
