---
name: design-loop
description: Develop a project endgoal through N bounded cycles of brainstorm and research, design, implementation, comparison testing and analysis.
disable-model-invocation: true
---

Use the request and [shared handoff contract](../../references/design-loop-contract.md). Inputs are an endgoal, starting workspace or artifacts, output directory and optional N, criteria, constraints, domains and scoped model/effort choices. Reuse resolved context and extend it for newly introduced work. This skill coordinates in the caller through the component workflows below.

## Bounds

`N` is the maximum number of attempted cycles in this run, including the first PoC and failed cycles; default to 3 and state it. Require a positive integer. Apply core's iteration bounds to cycle attempts; brainstorming is the first work of a cycle. Run through N unless the caller stops, a stated resource bound is reached, required capability or authorization is missing, or the caller explicitly chose stop-on-goal. Reaching the goal alone does not shorten the requested run; remaining cycles may improve robustness or confirm that no justified change is available.

The orchestrator chooses assignments for each stage under core execution rules. Stages preserve their dependencies and independent testing; caller resource limits still apply.

## Run

1. Establish or resume the checkpoint, state the resolved N and bounds, and preserve the initial accepted baseline. Each cycle starts from the last accepted state. The first cycle scopes the smallest working PoC; later cycles use the accumulated decisions and observations, including failed candidates.
2. Record the start of a new attempt, or resume the active one. Apply [brainstorm-research](../brainstorm-research/SKILL.md) with the request, baseline and prior observations. Pass its result to [design-increment](../design-increment/SKILL.md).
3. Create an isolated candidate from the baseline and invoke [implement-increment](../implement-increment/SKILL.md) with the design. Freeze its returned state and pass the baseline, candidate and evaluation plan to [test-increment](../test-increment/SKILL.md).
4. Invoke [analyze-iteration](../analyze-iteration/SKILL.md) with all cycle evidence, including any failures or gaps. Check its recommendation, record adopt/retain and the exact accepted state, and pass its observations into the next cycle. Checkpoint each returned stage. Apply the failure/resumption rules below if a stage cannot complete.
5. Stop at the resolved bound or a declared early-stop condition and return the result below. Further work requires a new or extended caller request.

Composition: `brainstorm-research → design-increment → implement-increment → test-increment → analyze-iteration`. The first component calls two leaves; testing supplies one independent comparison round. No additional final review or repair loop is part of this workflow.

## Failure and resumption

On a failed stage, retain its evidence and mark dependent stages unexecuted. If available, run the scheduled analysis on the partial handoff; otherwise record the missing analysis and retain the baseline. A completed failed attempt still counts. Continue only if another bounded cycle can make progress; a persistent capability or authorization block ends the run with an explicit gap. Corrections are proposed in a later cycle, within N.

If design finds no justified change, mark implementation and testing inapplicable, analyze that evidence, and record retain. The attempt still counts and the normal early-stop rules apply.

To resume, read the checkpoint and attempt-start records and verify the recorded state/artifact identities and remaining bounds. Reconcile starts or completed work not yet reflected in the checkpoint; a stale checkpoint does not erase an attempt. Continue the first unfinished stage of that same attempt, reusing valid completed work. Recover completed work or rejoin live assignments before replacing lost work. If inputs changed, mark affected downstream evidence stale and report that the caller must supply a new or extended run to repeat completed stages. Resuming does not silently increase N or reset caller constraints.

## Return

Return the exact final accepted state and how to use it, the initial-to-final change and evidence summary, completed/attempted counts, decisions, remaining gaps and checkpoint path. Keep retained candidates available as evidence. If the caller requested integration into an existing checkout, verify it still matches the preserved starting state before applying the chosen changes; report a conflict rather than overwrite newer work.
