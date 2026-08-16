# Role profiles

The starting agent is the orchestrator; only children use profiles. This
file solely owns default model mappings and the child-naming algorithm.

| Profile | Role | Codex | Claude Code |
| --- | --- | --- | --- |
| `orch-planner` | planner | agent_type `orch_planner`, model `gpt-5.6-sol`, model_reasoning_effort `ultra` | model `claude-opus-5`, effort `max` |
| `orch-worker` | worker | agent_type `orch_worker`, model `gpt-5.6-sol`, model_reasoning_effort `high`, service_tier `fast` | model `claude-opus-5`, effort `high` |

One machine runs different bindings by editing its own rendered role
agent. The installer asks before replacing one it did not last write, and
keeping it is the default; nothing else has to change.

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

On Codex, `agent_type` selects the installed profile; `task_name` only
labels the child. A spawn surface that omits `agent_type` cannot apply a
profile and stops the dispatch. Codex V2 profile selection uses a
non-full-history fork (`fork_turns="none"` or a positive turn count).

Child naming: normalize base name, model, and effort — lowercase ASCII,
each maximal run outside `[a-z0-9]` becomes `_` on Codex or `-` on
Claude, trim separators, `default` for omitted effort — and join the
three tokens with the host separator. On collision, append the host
separator plus the first available positive integer. A resumed child
keeps its name.

## Watching a lane (Claude Code)

Wake and completion notifications are lossy here
(anthropics/claude-code#39632), so a caller arms its own re-check of a
lane's durable run state at dispatch — through the host's scheduler, or
a bounded wait loop where it has none — and states that cadence when
arming, never coarser than the lane's bound read as a duration. Each
reading is judged by
[rules/delegation.md](../../../../rules/delegation.md) §11: an idle
notification or an unanswered nudge decides nothing. A dispatch that
launches an external process whose outcome its return depends on either
holds its turn until that outcome lands in durable state, or records the
process and its expected artifact in the run's notes
(`tickets.py run-state --note`) at launch, as helper lanes are recorded,
so the re-check covers it.

On Claude Code, a named child's return travels only by explicit
SendMessage to the spawner; plain final text is undelivered. The
spawner's own name — or `main` when the spawner is the top-level
orchestrator — travels down as the packet's `reply_to`
([contracts/work-item.md](../../../../contracts/work-item.md#dispatch)),
fixed once at dispatch; a child never infers it, since nothing in a
child's own context names who dispatched it. The durable artifact
remains the return per
[rules/delegation.md](../../../../rules/delegation.md) §10.
