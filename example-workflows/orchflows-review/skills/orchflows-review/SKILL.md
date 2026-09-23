---
name: orchflows-review
description: Review Orchflows against its purpose and design principles (architecture, workflow design, wording and bugs) and apply reviewed improvements on unmerged branches.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Inputs:
- **Scope:** defaults to the Orchflows checkout in the current workspace, with its example libraries, plus the user-authored libraries in the resolved home. Home copies of example libraries are reviewed only for drift from the checkout.
- **Optional:** focus, occasion (such as a new model or host release), sources, decisions on earlier findings, scoped settings and bounds.
- **Output location:** defaults to `artifacts/orchflows-review/` in the home.

Report-only requests stop after the reviewed findings.

## Understand

Record each repository's revision as the baseline and work from it. Report uncommitted changes and keep them out of branches. Review libraries without version control read-only. Use this run's workflow and guidance as loaded at start, even when the run changes them.

Keep a brief in the output location across runs. It holds:
- the library's purpose, design principles and deliberate policy, drawn from its design, architecture and READMEs;
- each earlier finding with its fate.

Refresh the brief from current source, then reconcile earlier findings:
- merged findings are accepted;
- findings the user declined, in the request or in notes in the brief, keep their reasons;
- the rest stay open.

When the occasion calls for it, research what changed and what it means for the library, with dated sources.

## Review

The coordinator runs the deterministic checks, and a baseline E2E pass over the cases in scope on each available host. Meanwhile, through `orchflows:orch-work`, review in coherent assignments with the brief, any research, and check and E2E results as they become available. Together they cover:
- **Architecture:** whether primitives, composition, contracts and ownership serve the purpose with the least mechanism, and what to simplify, merge or remove.
- **Workflow design:** whether each workflow's stages, gates, handoffs, independence and bounds achieve its result at a cost it earns.
- **Wording:** what could be shorter or clearer, what should be owned once, and what is stale.
- **Bugs:** found by running as well as by reading. Reviewers may run tests and probe edge inputs; they leave E2E runs to the coordinator.

Cite files, lines and run evidence.

## Findings

Join the reviews, checks and E2E results into one list ranked by value to the purpose. Each finding names its evidence, change, owner files, policy impact and how it will be verified. Leave out declined findings unless their evidence changed, and say what changed.

Apply `shared:review-revise-once` to the list with the brief and evidence. Record every listed and dropped finding in the brief.

## Apply and verify

Apply the list on a candidate branch in a writable, isolated worktree of each affected repository, one owner per area, through `orchflows:orch-work` as settings permit. Leave manifest versions unchanged.

Run the deterministic checks. On each host, the coordinator runs the E2E cases the changes affect on a fresh baseline alongside the candidate, from one harness (`--package-root`) at the same settings. Revert a change when the evidence shows it regresses, and report changes left untested. Trials used as evidence stay at baseline; changes to them are separate items.

Apply `shared:review-revise-once` to the stable diffs. Repairs stay within the reviewed list, and the affected checks and E2E cases are required checks. Record each finding's fate in the brief.

Return unmerged branches and a report:
- revisions;
- findings applied, reverted, deferred and dropped, each with evidence;
- checks and E2E results per host, with the revision each result ran on;
- the original review, separate from the delivered revision;
- gaps.

Merging and pushing belong to the user.
