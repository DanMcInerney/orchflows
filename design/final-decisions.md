# Final design decisions

This resolves the review of commit `4a145ae5` on `codex/flat-workflow-composition`. The current [architecture](../docs/architecture.md) owns execution and product policy. The earlier [design](composable-workflows.md) and [validation record](refactor-validation.md) describe the earlier candidate; they are evidence, not competing contracts.

## Decision

Keep two native-agent primitives, arbitrary-depth composition in one coordinator, explicit workflow selection, scoped guidance and independent review where selected. Keep the tagline “Two primitives. Reusable workflows. Your own guidance.” The caller or host handles an unmatched task. Remove the catch-all workflow and compatibility aliases. No new execution runtime, mandatory conformance checker, syntax, or host-specific agent profile is part of this change.

These decisions are settled for this refactor. A different preference is not a defect. Reopen a decision for a concrete counterexample to a required behavior or an explicit user request; do not keep rewriting it to satisfy successive reviewers.

## Assessment of Fable's review

| Finding | Independent assessment and disposition |
| --- | --- |
| Contract split, shared criteria, scoped guidance, shorter entries | Correct benefits, with the already recorded qualifications. Moving text is not necessarily reducing required context. Bootstrap trials used intermediate snapshots, so they do not prove every final criterion reached every role. |
| Delete the shared revision alias | Correct under the user's no-compatibility direction. Removed it and changed live callers to core `orch-review-revise-once`. Shared now owns only comparison. |
| Drop the one-level composition limit | Correct concession. Both hosts executed the four-level historical composition. The simpler current fixture has three levels because the redundant alias is gone. Neither observation proves arbitrary depth is cost-free. |
| Policy and tagline changed inside a refactor | Correct. PRs [197](https://github.com/DanMcInerney/orchflows/pull/197) and [205](https://github.com/DanMcInerney/orchflows/pull/205) show deliberate opposite invocation choices. Attributing opt-in fallback to Fable's proposal was unsupported. That attribution is corrected. The contract now states the user's final no-fallback choice and the product identity. |
| Benchmaker lost Deliver | Correct and substantive. The step exists at `00edb062f` and `f45f9e61` and disappears in `b9675e5b`. The refactor and its review missed a pre-existing branch regression. Restored delivery of the package, commands, actual cost/timing, requested versus achieved stage, separate score denominators and validity gaps. Hash verification alone cannot detect a missing requirement. |
| Every trial overran | Incorrect. The Codex bootstrap completed in about 4m34s against “6 minutes if possible.” Several other runs overran and reported timing poorly. The narrower conclusion—written bounds are not reliable wall-clock enforcement—is correct. |
| Promote the local launcher to a run primitive | Useful prototype, not a finished portable primitive. It embeds this machine's executable and evidence paths, hard-codes permissions, copies a particular package set, and terminates through Windows `taskkill`. Successful tests of that helper do not establish a supported cross-host runner. Hard deadlines belong to the invoking host or an explicitly chosen supervisor. No `orchflows run` command is added. |
| A checker needs no semantic events | Partly correct. Parentage and tool counts can be extracted mechanically; native `history inspect` already exposes them. My earlier objection was too broad. But a tool timestamp alone does not identify a candidate repair: the same shell or Python tool can read files, edit evidence or mutate the candidate. Start records count attempts; they do not identify all review gates, release stages or arbitrary stage starts. Ephemeral and encrypted traces leave gaps. A universal PASS would need trustworthy additional mappings or events. No mandatory checker or new event protocol is added. |
| Corrections have no labeled home | Correct. The premature-authoring-review reminder now lives in the Corrections section of `guidance/orchflows.md`. Required review-before-repair ordering stays in the process: it is a dependency, not a temporary model weakness. The catch-all child-exclusion sentence disappears with that workflow. |
| Ship Claude restricted subagent types | A valid optional host technique, not a demonstrated requirement. Claude supports tool allowlists and denies; omitting Agent blocks that tool. The negative trial restricted a top-level session, not two installed reusable profiles. Shell/MCP access also means that one denied tool is not proof against every delegation route. We retain portable primitive contracts and do not add partially enforcing host profiles. [Claude tool controls](https://code.claude.com/docs/en/sub-agents#restrict-which-subagents-can-be-spawned). |
| Centralize attempt starts and deduplicate contexts | Accepted. Core owns the shared counting/resumption rule; each loop defines its own iteration and state. Context files retain package-specific requirements and a core reference, while repeated scope/staffing explanations are removed. A reference to the contract is not itself a duplicate implementation. |
| Collapse Design Loop because it is eight files | Rejected. Its stages are public reusable components with distinct inputs and results. File count alone is not a defect, and collapsing them would reduce the composition the user wants. No actual missing dependency or broken stage was identified. |
| Remove design status and correct shared README | Accepted. The design identifies the candidate it describes instead of carrying a live implementation status. Shared documentation distinguishes historical alias-based trials from the current direct-core fixture. |

The independent review therefore contained real missed defects, sound optional ideas, and unsupported generalizations. It was useful; it does not establish that all seven proposed additions are necessary.

## Code and interface cleanup

- Deleted `orch-dynamic-workflow` and its metadata, plugin prompt references and fallback opt-in instructions. Core has four entrypoints: two primitives, workflow authoring and bounded review/revision.
- Deleted `shared:review-revise-once`; live examples and fixtures call the core owner directly. Resolving the removed name is an error.
- Removed `setup --skip-host-config` and its Python parameter. Omitting `--concurrency` already preserves settings; the old option is rejected by the CLI.
- Kimi configuration writes only the documented `[background] max_running_tasks`. A competing `[task] max_running_tasks` is rejected before any write instead of synchronizing two paths. Unrelated settings are preserved. The supported key is documented in [Kimi configuration](https://moonshotai.github.io/kimi-code/en/configuration/config-files#background).
- Removed RSS/Atom's implicit bare-channel-ID-to-URL conversion. Callers supply an HTTPS feed URL; bare IDs are refused without transport. Explicit YouTube feed URLs retain their own route budget. Updated the retained test callers to use URLs.
- Export preserves the source's explicitly optional behavior; it cannot invent a substitute to hide a missing required integration.

The source audit searched maintained core scripts, skills, guidance, host setup paths and example-library runtime scripts, then inspected the matched code and its callers and ran affected tests. It found no additional deliberate legacy alias or silent fallback path in those runtime sources. Supported host discovery, current shared plugin formats, RSS versus Atom parsing, configured defaults, and failure-safe restoration of the user's files remain real behavior. They are not obsolete compatibility implementations. Current test-suite aggregators remain necessary for discovery; their misleading “compatibility” labels were corrected. Historical trial records are preserved as historical evidence, not loaded as runtime instructions.

Only packages with changed interfaces or behavior get new versions: core 0.12.0, shared 0.5.0, research-acquire 0.5.0, Benchmaker 0.4.3, Design Loop/Evolve 0.3.2 and Export Workflow 0.3.2. Editorial deduplication does not bump every other library.

## Closure and verification

The acceptance bar is preservation of the chosen process, one owner per operation, explicit missing-capability reporting, removal of the identified compatibility paths, and passing affected checks. It is not “no reviewer can suggest a different design.” No new agent-review chain is required to settle these edits.

Verification after the final edits: The earlier native trials retain their original snapshot and coverage limits; they are not relabeled as executions of this cleanup. No full game, new benchmark measurement, native registration or broad cross-host conformance claim is made.

| Check | Result |
| --- | --- |
| Core `python -m unittest discover -s tests` | 126 run: 125 passed, one platform skip. Includes isolated installation, resolution failure for both removed workflow names, removed-flag rejection, and configuration preservation. |
| Research acquisition `python -m unittest discover -s tests -t .` with the skill scripts on `PYTHONPATH` | 575 passed. Includes explicit feed URL reads and no-transport refusal of bare IDs; test HTTP response fixtures emitted ResourceWarnings. |
| Package and Markdown checks | All 12 four-manifest package identities agree; all 30 shipped skills have matching names and manual invocation metadata; 134 changed-document local links and 25 heading targets resolve. |
| Whitespace and retained callers | `git diff --check` passed; no maintained runtime caller uses either removed workflow name or the removed setup option. Historical evidence and the tests of rejection retain those names intentionally. |

The feed suite initially exposed callers still supplying the removed bare-ID input; those callers were updated to explicit URLs and the complete suite passed. No alternate parsing path was restored to satisfy old inputs. The Benchmaker delivery step was compared directly with the historical source, and the restored content preserves its original delivery requirements.
