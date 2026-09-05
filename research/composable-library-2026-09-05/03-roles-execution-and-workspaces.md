# 3. Roles, execution, and workspaces

Status: proposed. Implement after stage 2 is accepted and installed.

## Dependencies

Stage 2's composable workflow package and the existing dispatch-v1, result, work-item, workspace, role, and host contracts. The implementation must preserve rules/roles.md, contracts/dispatch.md, contracts/result.md, and the source-identity handoff.

## Goal

A workflow can bind orch-planner or orch-worker to a host-supported model profile independently of whether a ticket makes or judges, and can group multiple compatible steps in one ordinary assignment when retaining context is useful. Every dispatched child has an exact launch binding, a durable result, an owned workspace, and an explicit independence boundary; unsupported transitions refuse rather than downgrade silently.

## Current-code evidence

rules/roles.md already defines planner and worker as capability classes, resolves explicit profiles before applied-skill defaults, and requires host-owned model bindings. hosts/claude.json, hosts/codex.json, and hosts/grok.json carry native launch records and role profiles. tickets_dispatch_launch.py resolves those records, while tickets_dispatch_launch_lines.py builds the prompt. tickets_mint.py exposes --profile on issue/dispatch plumbing but its do and judge usage does not currently accept it; the kernel manifests themselves currently bind orch-do to worker and orch-judge to planner, so the kernel role/mismatch law still couples operation to profile. The current Codex record carries service_tier, yet the live session's spawn API may not accept that field; native versus requested capability must be tested by the adapter. Workspace establishment/retirement and the result Report/outcome protocol already provide durable ownership and recovery.

## Bounded changes and causal owners

1. Decouple kernel operation from authority. Update orch-do and orch-judge and rules/roles.md so a role profile is an explicit ticket or caller binding, while operation defaults are only preferences. A planner profile may make/do and a worker profile may judge; the resolved launch profile must match the actual child. Preserve the current cheap worker preference for do and planner preference for judge when no profile is supplied, but neither preference is an authority check and no skill can change a running model.
2. Add the smallest callable-surface support for an optional proposed --profile on do and judge, pinning the selected profile at issue and resolving it through the active host record. An explicit profile wins; a missing profile keeps the operation preference for compatibility. A role requirement that the host cannot satisfy refuses rather than downgrading.
3. Make the dispatch adapter's capability result explicit: native fields are those the host record and probe can accept; requested fields are carried in the prompt and marked unverified. The launch record remains the canonical identity, and the emitted launch is still invoked verbatim. Add matrix checks for detected Claude, Codex, and Grok records; do not claim an unavailable host. The Codex probe must decide whether service_tier is legal before including it.
4. Use one ordinary assignment for grouped execution. Its Goal names one coherent artifact and its Details contain the workflow prose plus the union of applicable standards; the existing stamp mechanism pins all applicable standards at issue, and each inline do/judge call names only the subset of those standards that applies at that call in ordinary prose. The group has one dispatch, one resolved profile, one explicitly owned workspace, and one durable return, and it runs sequentially in one child context without a child spawn per inline step. If a step changes authority, isolation, or independence, the caller opens a separate ordinary ticket. No steps file, mini-DSL, or user-facing step/result taxonomy is introduced.
5. Update the kernel's single-kind restrictions only for explicitly grouped local work: a grouped assignment may make and locally inspect compatible artifacts in sequence, but the final independent review remains a separate ordinary judge ticket. A local self-review never becomes independent acceptance.
6. Tighten durable result/workspace checks at seams: a result names the attempt and writer; an artifact identity is printed verbatim; land reads the candidate's actual target and runs the done probe; a failed/unknown outcome retains partial evidence; no concurrent unowned writer is admitted. Large files use an existing or explicitly named artifact store.
7. Add checks for profile-at-mint, planner-do and worker-judge acceptance, operation/profile preference separation, role mismatch/refusal, native/requested field classification, grouped sequential execution with per-call standard subsets and no extra spawn, independent final review, stale result protection, crash recovery, and unchanged legacy invocation.

## Exclusions

Do not add a persona hierarchy, model names to skill prose, a runtime model switch, a new execution daemon, an always-on planner, or a requirement that every request outline, decompose, or review. Do not make one worktree per logical step when one explicit owner can safely retain it. Do not weaken independence because a grouped child also reviewed its own work. Do not require external tool purchases.

## Practical dogfood exercise

Recreate a disposable browser-game-qa fixture in a fresh scratch game from the accepted stage 2 source, recording the fixture's absolute source path and full source identity before use; do not rely on deleted scratch inputs. Bind a worker profile to build work and a planner profile to a do ticket that makes a design correction; then bind a worker profile to the independent final judge. Put two compatible steps with different narrowings in one ordinary assignment's prose, retain one workspace, and prove that the child runs them sequentially without a per-step spawn. Then hand the committed tip to a fresh judge with a different profile. Simulate a lost launch and a missing browser: replay the dispatch or return partial evidence, and verify the candidate and frame can resume without duplicate writes.

## Acceptance evidence

The stage records failing then passing readings for kernel/profile independence, planner-do and worker-judge acceptance, explicit profile precedence, role mismatch, unsupported native field, grouped execution, and independent review. It records each child name, launch identity, workspace path, artifact line, result record, and outside done probe. Host matrix checks pass for every detected host; absent hosts are named as gaps. Required focused checks, the stage dogfood, and the root's full gate establish the git candidate. A judge reads the grouped result and workspace seam rather than trusting the worker's status.

## Migration, compatibility, and recovery

Omitting --profile preserves current role resolution. Existing launch records remain readable; new capability metadata is additive and unknown fields refuse loudly at the adapter boundary. Grouped work is opt-in and does not merge prior ticket histories. If a profile or host adapter proves wrong, retire the affected attempt, restore the predecessor source, and replay from the durable ticket with a corrected host binding. Never reinstall beneath a live child; the accepted-source handoff in the index is the cutover boundary.
