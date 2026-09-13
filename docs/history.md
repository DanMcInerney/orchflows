# History

The [home CLI](home.md)'s `history` command reads native transcripts without changing them or resuming agents. `HOST` is `codex` or `claude`; each command accepts `--native-home PATH` and `--help`.

Native home: `CODEX_HOME` → `~/.codex`; `CLAUDE_CONFIG_DIR` → `~/.claude`. An explicit `--native-home` wins. Codex discovery requires `state_*.sqlite`; it has no transcript-scan fallback.

## Scope

| Request | Calls |
| --- | --- |
| This session | `history inspect HOST SESSION_ID`, then `history read HOST AGENT_ID` |
| A period | `history find codex --since A --until B`, then repeat for `claude` |
| A project in a period | add `--project <recorded path fragment>` |

Take the session ID from the host (Codex: `CODEX_THREAD_ID`), never the newest transcript. `--since` is inclusive; `--until` exclusive. Dates are UTC midnight; timestamps require an offset. Repeat dates on every `read` page; start a separate read without dates for earlier assignment context.

`--project` matches a case-insensitive recorded-cwd substring with normalized slashes, not repository identity. Include worktree/directory variants. `find` returns overlapping index or endpoint bounds; candidates may contain no matching events. Missing scope metadata is `scope_unknown`.

Page with `--after NEXT_CURSOR`, preserving selectors. Stop `find`/`inspect` at `next_cursor: null`; stop `read` at `has_more: false`. A read cursor remains valid for later appends. Changed/truncated sources invalidate it; restart that read.

## Reading

`inspect` returns the descendant tree: per-agent counts, latest activity, errors, unmatched calls, gaps and source references. Wrapper calls and nested command activities are separate categories. Rerun to discover new children.

`read` returns file-order previews. Expand a field with `history read HOST ID --event BYTE_OFFSET:INDEX --field FIELD`; event IDs are transcript-local. Fields: `data` (input/message/metadata), `presented_output` (recorded tool response), `captured_output` (Codex stdout), `stderr`, `sidecar` (one available native-home spill file). Continue expansion with `--offset NEXT_OFFSET` until `next_offset: null`. `--event` cannot combine with dates or `--after`.

## Limits

Codex delegation message bodies are encrypted and reported `unavailable`; reasoning and system prompts are omitted. Captured output can exceed what the agent saw. Malformed records and incomplete tails appear as gaps. A call without a recorded result has an unknown outcome. Records are evidence of past activity, not current process state, workflow success or authorization to redo a write. Keep raw history local.
