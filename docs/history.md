# History

`history`, a subcommand of the [home CLI](home.md), reads Claude Code and Codex transcripts in place without changing them. `history <find|inspect|read> --help` lists flags. Native home: `CODEX_HOME` or `~/.codex`, `CLAUDE_CONFIG_DIR` or `~/.claude`, or `--native-home PATH`. Codex discovery reads the host's `state_*.sqlite` index and nothing else.

## Scope

| Request | Calls |
| --- | --- |
| This session | `inspect HOST SESSION_ID`, then `read` relevant agents |
| A period | `find codex --since A --until B`, and the same for `claude` |
| A project in a period | add `--project <recorded path fragment>` |

Take the current session ID from the host (Codex: `CODEX_THREAD_ID`); never assume the newest transcript. `--since` is inclusive, `--until` exclusive; bare `YYYY-MM-DD` is UTC midnight, timestamps need an offset. Repeat the same dates on every `read` page; drop them when earlier assignment context is needed. `--project` is a case-insensitive substring of the recorded cwd with slashes normalized, not a repository identity; worktrees and directory changes need their own fragments. `find` returns candidates whose index or endpoint bounds overlap the window, so a candidate may hold no events in it; missing metadata is `scope_unknown`. Query both hosts; no merged index exists. Follow every `next_cursor` with unchanged selectors until null.

## Reading

`inspect` returns the tree from ID down: per-agent event and tool counts, latest activity, errors, `calls_without_recorded_results`, gaps, and transcript path, line and event references; a wrapper call and its nested command activities are separate categories. Rerun to see newly spawned agents. `read` returns events in file order with previews; `has_more: false` is the current end and the cursor still reads later appends. Event IDs are `BYTE_OFFSET:INDEX`, local to one transcript; `--event` expands one field: `data` (tool input, message, command metadata), `presented_output` (tool response as recorded), `captured_output` (Codex command stdout), `stderr`, `sidecar` (one retained spill file inside the native home).

## Limits

Codex delegation message bodies are encrypted and reported `unavailable`; reasoning and system prompts are omitted. Captured output can exceed what the agent saw. Malformed records and incomplete tails appear as gaps. A call without a recorded result has an unknown outcome. Records are evidence of past activity, not current process state, workflow success or authorization to redo a write. Keep raw history local.
