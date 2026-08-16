---
name: orch-compose
description: Execute a composition's steps by edge, gate the whole at its done_check. Use whenever a named or runtime composition is the dispatched unit.
role: none
---

Require: a composition — named, or the runtime instance at
`<state-root>/runs/<run>/composition.md` — with its steps, edges, invariants,
and done_check; the request or evidence the composition concerns.

Validate the composition at load against
[contracts/composition.md](../../../contracts/composition.md)'s
admission sentence before executing a single step; a composition
failing it is a defect to fix at its source, never patched around
here.

Execute each edge by kind. `seq`: re-enter `orch-spec` with the
predecessor step's result identity carried as the successor spec's
evidence — access to that identity is the workspace this engine
supplies; this engine never drafts or edits a spec itself, only
triggers the re-entry. `par`: dispatch each branch as a fresh child
per [rules/delegation.md](../../../rules/delegation.md) with a complete
packet — objective, inputs,
authority, bounds, return contract, reply_to — and bring every
branch's return to its named join by way of `orch-integrate` before
any downstream step trusts it; branches hold disjoint write scopes
per [rules/topology.md](../../../rules/topology.md) §7. `loop`:
dispatch the body, its done-check, its bound, and the step's frozen
goal through `orch-loop` unchanged.

Bind every step to the `invariants` block as execution proceeds; a
step no invariant binds is the same defect the admission sentence
rejects, caught here if it slipped load.

At the composition's own close, dispatch `done_check` as one further
fresh child, carrying only the final envelope and the composition's
spec — never the internal steps' verdicts, never a step's own claimed
status. A `scheduled` entry re-evaluates `done_check` fresh on every
trigger firing, never reusing a prior run's verdict.

Never: write or edit a spec; let a par branch's return skip
`orch-integrate`; carry internal verdicts into the done_check context;
skip admission validation; treat a step's self-report as the
done_check's evidence; execute a step no invariant binds.

Return: status, result — the composition's terminal result identity,
verification — the done_check's verdict plus each step's per
[contracts/result.md](../../../contracts/result.md); then per-step
results by identity and the run or instance path.
