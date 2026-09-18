---
name: investigate-incident
description: Investigate a production incident, explain evidence and propose mitigations; apply a specific mitigation only when explicitly authorized.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and the [run contract](../../references/run-contract.md). Inputs are the affected service, incident signal or question, available telemetry/runbooks and an incident window. Use `orch-work` for investigation assignments; no source repair loop or automatic deployment follows.

Give each assignment the incident context, release history, telemetry access, known actions and the caller's exact authorization. Assign one execution owner for each authorized external operation; other investigation assignments remain read-only. Investigators reconstruct a timeline, assess impact, test causal hypotheses against evidence and propose ranked mitigations with expected effect, scope, risks and recovery checks. Distinguish a correlation from a demonstrated cause and unavailable telemetry from a normal signal. Answer the caller's incident questions from that evidence.

Investigation alone authorizes no production mitigation. When the caller explicitly names and authorizes an operation, its assigned owner may apply that operation once after verifying current state and its preconditions. Record the operation before execution; reconcile an uncertain result before any retry. Verify the effect, and return unresolved impact. Do not substitute another mitigation, broaden a rollback or modify code when the authorized action fails. A later authorization resumes from the checkpoint as a new bounded invocation, accounting for earlier actions.

Return the timeline, impact, evidence, hypotheses, proposed mitigations and actual actions separately. Produce a follow-up software-factory brief if a code change is justified; implementation requires a caller request. Communicating with an incident channel or paging someone requires explicit authorization, separate from answering in this task.
