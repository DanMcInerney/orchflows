# History

The [home CLI](home.md)'s `history` reads native transcripts without changing them or resuming agents. `HOST`: `codex` or `claude`. Every command accepts `--native-home PATH` and `--help`.

Antigravity, Kimi Code, Grok Build and ZCode have no transcript adapters; use native session/export tools and report unavailable history as a gap. Claude Code with Z.ai uses `claude`.

Antigravity's `/resume` and `/agents` inspect sessions and children. Documented CLI transcripts: `~/.gemini/antigravity-cli/brain/<conversationId>/.system_generated/logs/transcript.jsonl`; desktop: `~/.gemini/antigravity/brain/`. These paths establish neither an Orchflows adapter nor a stable schema. [Sessions](https://www.agy.dev/docs/cli/commands/resume/), [transcript paths](https://antigravity.google/docs/hooks).

Native home: explicit `--native-home`, then `CODEX_HOME` → `~/.codex` or `CLAUDE_CONFIG_DIR` → `~/.claude`. Codex requires `state_*.sqlite`; no transcript-scan fallback.

## Scope

| Request | Calls |
| --- | --- |
| This session | `history inspect HOST SESSION_ID`, then `history read HOST AGENT_ID` |
| A period | `history find codex --since A --until B`, then repeat for `claude` |
| A project in a period | add `--project <recorded path fragment>` |

Use the host's session ID (Codex: `CODEX_THREAD_ID`), never the newest transcript. `--since` is inclusive; `--until` exclusive. Dates mean UTC midnight; timestamps require offsets. Repeat dates on every `read` page; read separately without dates for earlier assignment context.

`--project` matches case-insensitive recorded-cwd substrings with normalized slashes, not repository identity; include worktree/directory variants. `find` returns overlapping index or endpoint bounds that may contain no matching events. Missing scope metadata is `scope_unknown`.

Page with `--after NEXT_CURSOR`, preserving selectors. Stop `find`/`inspect` at `next_cursor: null`, `read` at `has_more: false`. Appends preserve read cursors; changed/truncated sources invalidate them and require restarting the read.

## Reading

`inspect` returns a descendant tree with per-agent counts, latest activity, errors, unmatched calls, gaps and source references. Wrapper calls and nested commands are separate categories. Agents also report observed `models` and `efforts`; children report `launch_context` (`fresh`, `inherited` or `unknown`) with the records behind it, and `unlinked_spawns` lists spawn calls no recorded child could be tied to. Rerun for new children.

Per-agent `models` and `efforts` tally what records say ran: Claude assistant `message.model` and `effort`, Codex `turn_context` `model` and `effort`. A value a record omits counts as `unknown`. Requested settings and subagent metadata are requests, not evidence of what ran.

`read` previews events in file order. Expand with `history read HOST ID --event BYTE_OFFSET:INDEX --field FIELD`; event IDs are transcript-local. Fields: `data` (input/message/metadata), `presented_output` (recorded tool response), `captured_output` (Codex stdout), `stderr`, `sidecar` (one available native-home spill file). Continue with `--offset NEXT_OFFSET` until `next_offset: null`. `--event` cannot combine with dates or `--after`.

## Limits

Codex delegation bodies are encrypted and reported `unavailable`; reasoning and system prompts are omitted. Captured output may exceed what agents saw. Malformed records and incomplete tails are gaps; calls without recorded results have unknown outcomes. Records establish past activity, not current state, workflow success or permission to repeat writes. Keep raw history local.
