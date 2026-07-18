# Role profiles

The starting agent is the orchestrator; only children use profiles. This
file solely owns default model mappings and the child-naming algorithm.

| Profile | Role | Codex | Claude Code |
| --- | --- | --- | --- |
| `orch-planner` | planner | agent_type `orch_planner`, model `gpt-5.6-sol`, model_reasoning_effort `ultra` | model `claude-fable-5`, effort `high` |
| `orch-worker` | worker | agent_type `orch_worker`, model `gpt-5.6-sol`, model_reasoning_effort `high`, service_tier `fast` | model `claude-sonnet-5`, effort `xhigh` |

Use native invocation fields when available; a prompt-only request is
requested, not verified. An unsupported or blocked model binding stops
the dispatch — never substitute; a missing effort control alone is
requested in the prompt and noted unverified, never a stop.

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

On Claude Code, a named child's return travels only by explicit
SendMessage to the spawner; plain final text is undelivered. The
durable artifact remains the return per
[rules/delegation.md](../../../../rules/delegation.md) §10.
