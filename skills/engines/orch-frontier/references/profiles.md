# Role profiles

The starting agent is the orchestrator; only children use profiles. This
file owns the host bindings: model mappings, child naming,
dispatch-surface mechanics, and lane watching.

| Profile | Role | Codex | Claude Code |
| --- | --- | --- | --- |
| `orch-planner` | planner | agent_type `orch_planner`, model `gpt-5.6-sol`, model_reasoning_effort `ultra` | model `claude-opus-5`, effort `max` |
| `orch-worker` | worker | agent_type `orch_worker`, model `gpt-5.6-sol`, model_reasoning_effort `high`, service_tier `fast` | model `claude-opus-5`, effort `high` |

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

On Claude Code only a child the orchestrator itself dispatched can
spawn children; a grandchild cannot. So a stub whose executor must
itself dispatch — an engine stub, or a blind scoring lane that spawns
the children applying each candidate — is run by the engine at depth
one, or inline in the engine's own context.

On Codex, `agent_type` selects the installed profile; `task_name` only
labels the child. A spawn surface that omits `agent_type` cannot apply a
profile and stops the dispatch. Codex V2 profile selection uses a
non-full-history fork (`fork_turns="none"` or a positive turn count).

Child names are unique within a run; a resumed child keeps its name.

## Watching a lane (Claude Code)

Wake and completion notifications are lossy here
(anthropics/claude-code#39632), so a caller arms its own re-check of a
lane's durable run state at dispatch — through the host's scheduler
where it has one, at a stated cadence never coarser than the lane's
bound read as a duration; else the caller's own re-check on each
notification and at its next turn, never a wait loop, which the host
block bars in a worktree-isolated session. Each reading is judged by
[rules/delegation.md](../../../../rules/delegation.md) §11: an idle
notification or an unanswered nudge decides nothing. A launched
external process is delegation.md §11's: hold the turn until its
outcome lands in durable state, or record it at launch.

On Claude Code, a named child's return travels only by explicit
SendMessage to the spawner; plain final text is undelivered. `reply_to`
per
[contracts/work-item.md](../../../../contracts/work-item.md#dispatch);
a child that will itself dispatch is told its own assigned name, since
that name is its children's `reply_to`.
