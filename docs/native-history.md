# Read native agent history

The core installs `scripts/native_logs.py` with the existing CLI. Use the home
Python runtime from any project; the reader needs only the standard library.
It does not write native logs, create a database, change settings or resume work.

```powershell
$orchflowsRoot = Join-Path $env:USERPROFILE '.orchflows'
$orchflowsPython = Join-Path $orchflowsRoot '.local/runtime/Scripts/python.exe'
$orchflowsCli = Join-Path $orchflowsRoot '.local/packages/orchflows-light/scripts/orchflows.py'
& $orchflowsPython $orchflowsCli history inspect codex SESSION_ID
& $orchflowsPython $orchflowsCli history read claude AGENT_ID --limit 30
```

Replace the uppercase IDs with native IDs. On macOS/Linux, use
`.local/runtime/bin/python`. Native locations default to `CODEX_HOME` or
`~/.codex`, and `CLAUDE_CONFIG_DIR` or `~/.claude`. `--native-home PATH` overrides
them. Orchflows' `--home` does not redirect native history. The source CLI can
also inspect logs before an Orchflows home is installed.

## Choose a scope

An LLM translates the request into explicit selectors; the script does no
natural-language parsing:

| Request | Reader calls |
| --- | --- |
| This session | `inspect HOST SESSION_ID`, then `read` each relevant agent. |
| All history in a week | `find codex --since START --until END` and the same call for `claude`. |
| A project's history in a week | Add `--project bench-stack` or a recorded checkout path to each `find` call. |

For this Codex session, use `CODEX_THREAD_ID` when the host supplies it. Otherwise
obtain the actual native ID from the host or discovery results; never substitute
the most recently modified transcript for the current session.

```text
history find codex --since 2026-09-04T00:00:00-04:00 --until 2026-09-11T00:00:00-04:00
history find claude --since 2026-09-04 --until 2026-09-11 --project bench-stack
history read codex AGENT_ID --since 2026-09-04 --until 2026-09-11
```

Dates are inclusive at `--since` and exclusive at `--until`. Bare dates mean
midnight UTC; timestamps require an offset. The LLM chooses the intended rolling
week or calendar week and timezone. Repeat the same dates on each `read` page;
omit them deliberately when earlier assignment context is needed. Undated
events, including damaged records, remain visible with `timestamp_unavailable`.
Expanding an event uses its ID without date arguments.

`find` returns bounded pages of candidate sessions **and subagents**, their IDs,
parents, recorded working directories, source paths and date bounds. Follow
`next_cursor` with unchanged selectors until it is null. Inspect selected trees
and avoid reading the same agent twice. To cover both hosts, query each; no
merged index is maintained. Rerun discovery to include newly created logs.

Discovery uses the Codex index where available, otherwise opening metadata and
the last dated transcript record. A session whose bounds overlap a week may
have no events in that week; date-filtered `read` selects the actual events.
Project matching is a case-insensitive substring of the recorded working
directory, with slash normalization. It is not a repository/alias registry:
`benchstack` does not automatically mean `bench-stack`. Choose the matching
recorded paths, including worktrees; unrelated worktree folder names may need a
separate query. Sessions that changed directories can require broader discovery.
Missing metadata is returned as `scope_unknown`, not treated as a confirmed
match or silently excluded. Native index omissions, deleted logs and endpoint
metadata still limit completeness.

## Inspect a tree

`history inspect HOST ID` returns the parent and descendants with per-agent
event/tool counts, latest recorded activity, errors, calls without recorded
results, and evidence gaps. References include transcript path, line and event
ID. Counts describe recorded entries: a tool-call wrapper and its nested
command activities are separate categories, not independent calls to add up.

The default page has at most 30 agents; `--limit` accepts 1–100. Pass the returned
`next_cursor` to `--after` for another page. Rerun from the start to discover
new agents. Each selected transcript is streamed without a persistent cache.

Codex discovery reads the existing SQLite task/parent index, including archived
tasks. If it is absent or unreadable, the reader scans headers under `sessions/`
and `archived_sessions/`. Claude discovery uses project folders and neighboring
subagent metadata. Missing transcripts and discovery errors are reported.

## Read and expand

`history read HOST ID` returns one agent's events in file order. Large fields
contain text previews, character counts and a `truncated` indicator. Continue
with `--after CURSOR`. `has_more: false` marks the current end; the retained
cursor can read later appends. A changed anchor or truncated source is rejected.

These arguments follow the installed CLI path shown above:

```text
history read codex AGENT_ID --after CURSOR --limit 30
history read codex AGENT_ID --event EVENT_ID --field captured_output --offset 0 --chars 12000
history read claude AGENT_ID --event EVENT_ID --field data
history read claude AGENT_ID --event EVENT_ID --field sidecar --offset 12000 --chars 12000
```

Event IDs are `BYTE_OFFSET:INDEX`, local to a transcript. Expansion returns text
and `next_offset` for character pagination. `--chars` accepts 1–50,000. Fields:

- `data`: tool input, message, command metadata or host activity data.
- `captured_output`: captured Codex command output, when present.
- `presented_output`: recorded tool response or formatted command output.
- `stderr`: separately recorded command error output.
- `sidecar`: one explicitly referenced, retained native output file.

Assignments generally use `data`; tool results use `presented_output`. Only
explicit spill markers inside the selected native home are followed. Missing
files and outside references remain explicit. For an event with multiple
sidecars, inspect its returned paths directly rather than choosing one silently.

## Evidence limits

Sampled Claude assignments are readable. Sampled Codex delegation wrappers are
readable but their message fields are encrypted; the reader marks these as
unavailable. Model reasoning and system/developer message bodies are omitted.
Context records identify available fields without reproducing hidden context.

Captured output can exceed what the agent was shown. Some records are already
truncated, and referenced images/artifacts may no longer exist. Unknown records
remain identifiable. Malformed middle records and incomplete final lines are
reported as gaps rather than silently discarded.

A call without a recorded result has an **unknown outcome**. Recorded completion
does not establish current process state, a workflow verdict or permission to
retry a write. Recovery uses this evidence alongside actual workspace state and
native resume facilities. The reader does not implement crash recovery.

Schemas and retention vary. Initial validation uses local Codex Desktop 0.153.4
rollouts and Claude Orchflows transcripts, plus regression fixtures for cursor
pagination, Unicode, interrupted files, encrypted fields and spilled outputs.
Keep raw history local and share only deliberately selected results.
