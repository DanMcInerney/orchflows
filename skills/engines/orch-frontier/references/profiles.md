# Role profiles

The starting agent is the orchestrator; only children use profiles. This
file owns the host bindings: model mappings, child naming,
dispatch-surface mechanics, and lane watching.

| Profile | Role | Codex | Claude Code |
| --- | --- | --- | --- |
| `orch-planner` | planner | agent_type `orch_planner`, fork_turns `none`, model `gpt-5.6-sol`, model_reasoning_effort `ultra` | model `claude-opus-5`, effort `max` |
| `orch-worker` | worker | agent_type `orch_worker`, fork_turns `none`, model `gpt-5.6-sol`, model_reasoning_effort `high`, service_tier `fast` | model `claude-opus-5`, effort `high` |

Use native invocation fields when available; a prompt-only request is
requested, not verified. An unsupported or blocked model binding stops
the dispatch — never substitute; a missing effort control alone is
requested in the prompt and noted unverified, never a stop.

A host with no native isolation field cannot establish an isolated
workspace at dispatch: the request rides the prompt, is graded
requested, not verified, and is never recorded as established. Like a
missing effort control it is no stop on its own — what an unisolated
child then shares with its siblings is the caller's to weigh before
dispatching them.

On Claude Code a role-bearing skill adapter declares `context: fork`
and `agent: orch-planner` or `agent: orch-worker`; those native fields
establish the matching role child before its exact named body runs.

On Codex, `agent_type` selects the installed profile; `task_name` only
labels the child. Root explicitly dispatches the exact named skill and
complete packet to that matching role child. Missing or mismatched
`agent_type` refuses execution; a role child runs its primary skill
directly. Codex V2 profile selection uses a non-full-history fork
(`fork_turns="none"` or a positive turn count). These are contractual
instructions, not a claimed automatic binding or hard root guard.

Child names are unique within a run; a resumed child keeps its name.

## Watching a lane (Claude Code)

Wake and completion notifications are lossy here
(anthropics/claude-code#39632), so a caller arms its own re-check of a
lane's durable run state at dispatch — through the host's scheduler
where it has one, at a stated cadence never coarser than the lane's
bound read as a duration; else the caller's own re-check on each
notification and at its next turn, never a wait loop, which the host
block bars in a worktree-isolated session. Each re-check reads
`tickets.py bound-check <run>`, whose exit status alone says whether any
live claim is past its bound. Each reading is judged by
[rules/delegation.md](../../../../rules/delegation.md) §11: an idle
notification or an unanswered nudge decides nothing. A launched
external process is delegation.md §11's: hold the turn until its
outcome lands in durable state, or record it at launch.

On Claude Code, a named child's return travels only by explicit
SendMessage to the spawner; plain final text is undelivered. A child that
will itself dispatch is told its own assigned name so its children can
address their returns.

## Running the terminal required checks (Claude Code)

The standards owner's required checks run in the engine's own context —
no lane, no child — one command per call, the turn held until each exit
status lands, by the §11 reading above: a launched process whose outcome
never reaches durable state graded the result not at all. Run the suite once
after ticket-local or run-gate acceptance closes. A host whose accepted
terminal identity is a worktree branch runs it there; the revision recorded
beside its verdict is the accepted terminal identity's revision.
