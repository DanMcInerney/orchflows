# Orchflows: main versus the refactor

Compared on 2026-09-18 after fetching `origin/main`:

- **Main:** `16d2644ba25562d66af5648a7dfed8ebde1cfe90`, core 0.7.1.
- **Refactor baseline:** `3197adcd64f7adb42b34b0825047197931e634d5`, core 0.12.0, `codex/flat-workflow-composition`. The subsequent tests described below add one explicit blocked-review rule, released as core 0.12.1.

This comparison includes the complete difference from main, including work that preceded the final refactor commits. [Architecture](../docs/architecture.md) is the current contract; [final decisions](final-decisions.md) explains the settled choices.

## What the library is

Both versions start with two operations: ask a fresh native agent to make something (`orch-work`), or ask a fresh independent agent to review something without changing it (`orch-review`). Workflows combine those operations with ordinary instructions. Libraries package workflows, guidance and supporting files for reuse.

Neither version has its own agent runtime, scheduler or programming language. Codex, Claude Code or another supported host executes the agents. Reading another workflow applies a procedure; it does not itself start an agent. Composition and user-owned guidance already existed on main. The refactor makes their boundaries clearer and removes some prescribed staffing.

The intended division is now explicit: **the prompt supplies the particular task; the workflow supplies the process; guidance supplies standards, methods and taste.** Improving a model should often let you remove a corrective reminder from guidance while retaining real dependencies, independence requirements and stopping rules.

## What changed

| Area | Tip of main | Current branch |
| --- | --- | --- |
| Core entrypoints | Work, review, workflow authoring, dynamic fallback. | Work, review, workflow authoring, explicit review-and-one-revision. Still four entrypoints. |
| Unmatched requests | `orch-dynamic-workflow` was configured for automatic selection when no specific skill fit. | No Orchflows fallback or automatic router. The host handles the request normally. |
| Composition | Workflows could compose; several examples prescribed fresh agents for ordinary stages. | Arbitrarily nested procedures remain in one coordinator. Procedure depth adds no agent, review or budget. |
| Staffing | Design Loop required six fresh children per full cycle; Evolve required fresh challenger makers. | The coordinator chooses direct work, a suitable existing maker or a fresh maker for ordinary production. Explicit `orch-work` still means fresh. Required independent judgments remain. |
| Dispatch | The two primitives supplied delegation, with coordination rules distributed across workflows. | Core explicitly makes the top-level coordinator responsible for every launch and continuation. Children return results and requests; they do not delegate. |
| Review and repair | The dynamic workflow embedded one final review followed by one repair pass. Other workflows repeated similar instructions. | `orch-review-revise-once` is a reusable, explicitly selected process. Each workflow owns its review count. |
| Guidance | Instructions were described through Make and Review sections; resolved context generally passed through unchanged. | Common criteria apply to both roles, with optional role-specific sections. Each nested call receives applicable guidance; local additions stay out of sibling calls. |
| Model settings | Caller choices beat saved preferences; named assignments beat operation defaults. | Adds stage-level choices between assignment and operation defaults. Model and effort still resolve separately, with unspecified controls inherited from the host. |
| Resumption | Individual loops defined their own counting and checkpoints. | Core owns the common rule: record and count an attempt before work; failures and pauses consume it; resumption does not refund it. Loops still define their own state and limits. |
| Authoring | Build, trial and review, using the dynamic workflow. | Build, finish the trial and its judgments, then apply explicit review/revision. Packaging instructions now have their own document. |

## Dynamic workflows and routing, concretely

On main, the intended route was: **request → specific selected workflow, if applicable → otherwise dynamic workflow**. The dynamic workflow investigated, arranged work, joined the result, obtained one independent review, and allowed one repair pass. Automatic selection depended on the host honoring its discovery metadata; it was never a deterministic Python router.

Now there are three ordinary cases:

1. **“Fix this typo.”** The host handles it using its normal behavior. Orchflows adds no review promise to that request.
2. **“Use Design Loop for two cycles to improve this CLI.”** The named workflow supplies the stages, comparison and bounds. Within those stages, the coordinator chooses appropriate assignments and tools.
3. **“Review this draft using `orch-review-revise-once`, then run these checks.”** The coordinator gets one fresh independent review, makes at most one coordinated repair pass, and runs the required checks even if no repair was needed.

Dynamic planning therefore still happens **inside an explicitly selected process**, or through the host's ordinary reasoning. A user can also request an ad hoc composition of the primitives. There is no longer a built-in named catch-all that silently gives every task the same lifecycle.

Workflow composition is direct. A personal `launch-pack` can call `research-brief`, which calls core review/revision, then use the returned brief in a campaign step. One coordinator follows those procedures and owns any actual children. The brief's neutral-writing guidance and the campaign's promotional guidance can differ without changing either reusable component.

Selection, lookup and dispatch are different things. Native skill metadata exposes names for invocation; the home CLI resolves installed package and skill paths; the coordinator follows the selected procedure and dispatches agents. The CLI does not choose or execute a workflow. All current shipped skills request manual invocation. Hosts that cannot enforce that policy must report the limitation.

## Review, scope and failure behavior

A reviewer inspects a stable candidate. Required judgments must finish before repair. The delivered revision is identified separately from the reviewed version: passing review of an earlier draft does not certify later edits. The reusable review/revision process adds neither another review nor a release step.

Guidance scope controls which preferences apply, rather than making files secret. A reviewer may read another step's guidance as evidence without adopting it. Caller constraints, authorization and workflow requirements still take priority over a local preference.

Missing required review, a missing dependency or an unsupported requested control remains an explicit gap. Unrelated useful work can continue; dependent work cannot invent a replacement. Removed names fail instead of resolving through aliases.

## Effects on the bundled libraries and existing users

Design Loop retains eight reusable stages and its independent comparison, but drops the mandatory six-agent staffing plan. Shared now contains `compare-candidates`; bounded review/revision has one core owner. Evolve keeps calibrated evaluation, independent judgment, confirmation and promotion rules, with harness experiments and state details in references and methods in guidance. The game workflow retains its two review gates. Benchmaker retains its pilot, separate review and delivery requirements; its target-agent dispatch now belongs to the coordinator.

These are selective reductions in repeated orchestration and prescribed staffing. Moving a paragraph into a required reference does not eliminate the reading or reasoning it requires. There is no matched evidence yet that the refactor is generally faster or produces better results than main.

Existing callers of `orch-dynamic-workflow` must choose the process they actually want. The intermediate branch's `shared:review-revise-once` alias is also gone; it did not exist on this main baseline. Setup's obsolete `--skip-host-config` option is removed: omit `--concurrency` to preserve settings. Kimi uses its supported background-task key and rejects a conflicting obsolete override. Research feed acquisition requires an explicit HTTPS feed URL instead of expanding a bare channel ID.

Core setup still manages the installed core, while user libraries remain user-owned. No new runtime, mandatory checker, automatic migration or host-specific agent profile is introduced.

## What is established, and what still needs testing

The final cleanup passed 125 core tests with one platform skip, plus 575 research-acquisition tests. Earlier native trials exercised composition on Codex and Claude, independent review, a missing-review failure, Evolve promotion and interrupted Design Loop resumption. Those trials also exposed real mistakes, including premature authoring review and an unsupported output claim. Their snapshots and limits are recorded in [the validation record](refactor-validation.md) and [shared trials](../example-workflows/shared/trials/README.md).

After writing this comparison, the [new end-to-end tests](../tests/e2e/README.md) exercised actual main-to-current installation, native manual selection, nested guidance scope, required checks on a no-repair result, and unavailable independent review. The last case caught an agent repairing despite a missing reviewer. One explicit blocked-branch sentence fixed the observed failure on the same input: preserve the candidate; a request to repair within the workflow does not waive review. This clarifies the existing dependency and changes no architecture decision.

The completed native composition retained one coordinator, used one independent reviewer, preserved the correct invoice, ran the required check and kept internal versus public guidance separate. The ordinary request invoked no skill or reviewer. These are small Claude Code observations, not proof of general routing reliability or a final-build Codex result. Fast deterministic installation tests and small native tasks provide different evidence; neither substitutes for the other.
