---
name: export-workflow
description: Export an Orchflows workflow as a standalone native skill with a portability report and bounded trial.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) and [export contract](references/export-contract.md) to create a skill requiring no installed Orchflows.

Resolve the source path or library/skill identity and dependencies as source material; discovery does not execute the source task. Use caller host or current host, preserving selected library order. Resolve missing identity/scope before dependent conversion.

Write in the caller's context to its destination or `exports/<skill-name>/`. Preserve source files; choose an unused destination unless updating was requested. Default to the source name without leading `orch-`. Exporting does not install/register.

Inventory reachable workflows, guidance, references, scripts/assets and host requirements. Preserve supported behavior and record changes, omissions and unresolved capabilities. Runtime inputs stay configurable; export-time dependency choices must not hard-code the trial task. Missing dependencies block dependent conversion; unresolved required behavior makes the result incomplete.

Check metadata, links, imports and resource paths outside the source tree. Verify both invocation settings under core `docs/hosts.md`, preserving caller opt-ins and otherwise manual-only defaults.

Run one bounded representative trial under core `docs/hosts.md#workflow-trials` in an unrelated disposable workspace. The fresh top-level session receives only the relocated export, ordinary synthetic inputs and declared prerequisites, without source/authoring history; its guidance comes from the export. Simulate external effects, keep references read-only and record fixtures, interventions and unexercised integrations. Keep outputs/report outside the installable folder. Unavailable safe execution is a validation gap, not authority for live trials.

After the trial and its required judgments complete, apply `orchflows:orch-review-revise-once` to the stable export, source, requirements, author guidance and trial evidence. Scope repairs to export/portability checks. If repairs change trial behavior, repeat affected trial once under the same contract. Missing prerequisites block dependent trials, not gap disclosure.

Deliver folder and sibling report: source revision plus local changes or hashes; libraries/guidance order; host; bundled dependencies; external tools; behavior changes; original review/delivered revision; checks/trial limits. Source updates require re-export. Claim native availability only after separate verified registration.
