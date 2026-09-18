---
name: design-loop
description: Develop a project endgoal through N bounded cycles of brainstorm and research, design, implementation, comparison testing and analysis.
disable-model-invocation: true
---

Use the [handoff contract](../../references/design-loop-contract.md). Inputs: endgoal, starting workspace/artifacts, output directory and optional N, criteria, constraints, domains and scoped model/effort choices. Coordinate in the caller; reuse context and extend it for new work.

## Bounds

`N` caps attempted cycles, including the first PoC and failures. Require a positive integer; default to 3 and state it. Apply core's iteration bounds; brainstorming is a cycle's first work. Run through N unless the caller stops, a resource bound is reached, required capability or authorization is missing, or explicit stop-on-goal applies. Goal attainment alone does not shorten the run.

Choose stage assignments under core execution rules, preserving dependencies, independent testing and caller limits.

## Run

1. Establish or resume the checkpoint, state N and bounds, and preserve the initial baseline. Start each cycle from the last accepted state. Target the smallest working PoC first; later cycles use accumulated decisions and observations, including failures.
2. Record a new attempt before work, or resume the active one. Apply [brainstorm-research](../brainstorm-research/SKILL.md) with request, baseline and observations, then [design-increment](../design-increment/SKILL.md) to its result.
3. Create an isolated baseline copy; apply [implement-increment](../implement-increment/SKILL.md) with the design. Freeze the returned candidate; pass it, the baseline and evaluation plan to [test-increment](../test-increment/SKILL.md).
4. Apply [analyze-iteration](../analyze-iteration/SKILL.md) to all cycle evidence, including failures/gaps. Check its recommendation; record adopt/retain, exact accepted state and next-cycle observations. Checkpoint each returned stage; use the rules below for incomplete stages.
5. Stop at the bound or declared early-stop condition. Further work requires a new or extended caller request.

Brainstorm-research calls two leaves; testing supplies one independent comparison round. There is no additional final review or repair loop.

## Failure and resumption

On failure, retain evidence and mark dependent stages unexecuted. Run scheduled analysis on the partial handoff if possible; otherwise record missing analysis and retain the baseline. Failed attempts count. Continue only if another bounded cycle can progress; persistent capability/authorization blocks end the run with a gap. Corrections belong to later cycles within N.

For no justified change, mark implementation/testing inapplicable, analyze the evidence and record retain. The attempt counts; normal early-stop rules apply.

To resume, read checkpoint and attempt-start records; verify state/artifact identities and remaining bounds. Reconcile uncheckpointed starts or completed work; stale checkpoints erase no attempts. Continue the same attempt's first unfinished stage, reusing valid work. Recover completed work or rejoin live assignments before replacements. Changed inputs make affected downstream evidence stale; repeating completed stages requires a new or extended caller run. Never reset N or caller constraints on resume.

## Return

Return exact accepted state, usage, initial-to-final changes/evidence, completed/attempted counts, decisions, gaps and checkpoint path. Keep retained candidates as evidence. For requested integration, verify the checkout still matches its preserved starting state; report conflicts instead of overwriting newer work.
