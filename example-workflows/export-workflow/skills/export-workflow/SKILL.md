---
name: export-workflow
description: Export an Orchflows workflow and its selected dependencies as a standalone native skill, with a portability report and bounded trial.
disable-model-invocation: true
---

Create a skill folder that works without Orchflows installed. Establish [library context](../../references/library-context.md) once. The exported skill follows the [export contract](references/export-contract.md).

Resolve the source workflow by supplied path or library and skill name. Read it and its dependencies as source material; do not execute its task during discovery. Use the caller's target host, else the current host, and selected libraries in their supplied order. Establish any missing source identity or scope needed to resolve dependencies before exporting.

Use the requested destination, else `exports/<skill-name>/` in the caller's workspace. Keep the source untouched; choose an unused destination if one already exists unless updating that export was requested. Use the source name without a leading `orch-` unless the caller names the export. Exporting does not install or register it.

Inventory reachable composed workflows, guidance, references, scripts, assets and host requirements. Apply the export contract, preserving supported behavior and recording every changed, omitted or unresolved capability. Keep the source's runtime inputs configurable; export-time choices select dependencies, not a hard-coded trial task. Report a missing dependency as a gap and stop dependent conversion; label any deliverable with unresolved required behavior incomplete.

Write the export in the caller's context. Check metadata, relative links, script imports and resource paths from outside the source tree. Verify both host invocation settings from the resolved core's `docs/hosts.md`, preserving explicit caller opt-ins and otherwise using manual-only defaults.

Try the exported skill on one bounded representative request in a disposable, unrelated workspace, following core `docs/hosts.md#workflow-trials`. Give the fresh top-level session only the exported folder, ordinary inputs and declared external dependencies, without the source or authoring conversation. Its guidance comes only from the export. Keep outputs and the export report outside the installable folder. Record preparation, interventions and behavior not exercised; unavailable capabilities limit the claim.

After the trial finishes, apply core's standard review and repair to the export against the source, selected guidance and trial evidence. If repairs affect trial behavior, repeat the affected trial once under the same trial contract. Missing prerequisites block dependent trials, not disclosure of the gap.

Deliver the skill folder and a sibling export report naming the source revision with local changes identified, or content hashes; selected libraries and guidance order; target host; bundled dependencies; required external tools; behavior changes; checks and trial limits. Explain that source updates require re-export. Claim availability by name only after separate, verified host registration.
