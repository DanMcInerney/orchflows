# Claude Code transcript fixture corpus

A synthetic `~/.claude/projects` tree. `tests/test_ui.py` copies it into a
temporary directory and stamps a deterministic mtime on each session file,
because the index orders on last activity and a copy takes whatever the
clock says. No test reads the operator's real transcripts: the reader
resolves the `~/.claude/projects` default in `main` alone, so a test that
supplies no root gets a named empty state rather than the real tree.

Layout, as observed on a live host on 2026-08-10: sessions at
`<slug>/<uuid>.jsonl`; a per-session directory `<slug>/<uuid>/` holding
`subagents/agent-<id>.meta.json` and `agent-<id>.jsonl` alongside a
`tool-results/`. The slug is the working directory with every separator
replaced by `-`. `worktree-state` carries its fields one level down under
`worktreeSession`, not flat.

Two further facts, observed the same day over 305 subagents on that host,
neither of them anybody's contract. A subagent is spawned by an
`assistant` record carrying a `tool_use` block named `Agent` whose `id` is
the subagent's `toolUseId`, and it has returned once a `user` record
carries a `tool_result` block whose `tool_use_id` is that same id — both
blocks one level down, under `message.content`. That pair is the only
evidence of activity there is, and `tool-results/`
carries none of it — no subagent's `toolUseId` named a file there. The
tool *name* is what makes the pair evidence: a `toolUseId` is an ordinary
tool-use id and any tool's call and result can be recorded under one. And
`parentAgentId` is present on every depth-2 record and on no depth-1
record, resolving in every case to the sibling whose stem is
`agent-<parentAgentId>`.

| fixture | shape it carries |
|---|---|
| `-Users-dmcinerney-tools-alpha/1111….jsonl` | healthy: two `ai-title` records, so the *last* one is the label; a `worktree-state` whose `originalCwd` agrees with the slug; one record of every other observed type; and the three activity shapes — an `Agent` call that returned (`toolu_alpha_01`), one that has not (`toolu_alpha_02`), and a `Bash` call and result under a *subagent's* `toolUseId` (`toolu_alpha_03`), which is evidence of nothing about that subagent |
| `…/1111…/subagents/agent-aa1{1,2,3}.meta.json` | three subagents, two at `spawnDepth` 1 and one at 2; one carries a `model` key the spec's evidence does not list, one a `description` carrying markup. The depth-2 record carries no `parentAgentId`, so its attachment is not provable |
| `…/1111…/subagents/agent-aa11.jsonl` | a subagent's own transcript: megabytes on a real host, never opened here. Its every line carries the sentinel |
| `…/1111…/tool-results/toolu_alpha_01.json` | a tool result beside the transcript, never opened. Carries the sentinel |
| `-Users-dmcinerney-tools-alpha/2222….jsonl` | no `ai-title`, no `worktree-state`, no session directory: the named-fallback label, the slug-decoded working directory, and zero subagents |
| `-Users-dmcinerney-tools-beta-repo/3333….jsonl` | an `aiTitle` carrying `<script>alert(1)</script>`; `originalCwd` is `…/beta-repo`, which the slug decode cannot recover — the hyphen in `beta-repo` is indistinguishable from an encoded separator |
| `…/3333…/subagents/agent-bb2{1,2,3}.meta.json` | `bb21` carries markup in both `agentType` and `description`, the second with the quote characters an attribute context has to survive; `bb22` is an object whose every field is the wrong type; `bb23` is not JSON at all |
| `-Users-dmcinerney-tools-beta-repo/4444….jsonl` | malformed: a line that is not JSON, a line that is JSON and not an object, a blank line that is neither. Still labelled, and in the same project directory as `3333…`, where its working directory can only come from the slug |
| `-Users-dmcinerney-tools-beta-repo--claude-worktrees-wt-one/5555….jsonl` | truncated: a partial final line with no newline. `worktreePath` and `originalCwd` both present, so the worktree path wins |
| `…/5555…/subagents/agent-cc3{1,2}.meta.json` | the provable attachment: `cc32` is at depth 2 and its `parentAgentId` resolves to `cc31`. Neither appears in the transcript, so both states are `unknown` |
| `not-an-encoded-path/6666….jsonl` | empty, under a directory name that does not decode to a path at all |

Every `user` and `assistant` body, every `last-prompt`, attachment, tool
input, tool result and file-history record in this corpus carries the
string `ZQXJVWNTRPKB-transcript-content-must-not-render`. The spec's
renderable set — `sessionId`, `aiTitle`, the `worktree-state` fields,
timestamps, sizes, counts and the subagent metadata — carries it nowhere,
so a sentinel on any rendered route is a content leak and nothing else.

Six sessions across four project directories. Their assigned mtimes
interleave the directories, so an index that grouped by directory would
still pass an ordering assertion made over one of them.

`git` tracks no empty directory, so the "session with no `subagents/`"
case is a session with no session directory at all — which is also what a
real host shows for a session that spawned nothing.
