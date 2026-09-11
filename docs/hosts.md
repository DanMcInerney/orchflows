# Hosts

Checked on 2026-09-11 against Codex CLI 0.144.0, Codex Desktop 0.153.4 and current Claude Code. Use what the installed host exposes; if a needed capability is unavailable, say so rather than implying it ran.

## Register and refresh

Setup writes catalogs; hosts do not scan `~/.orchflows`. Register once, install each library, start a new session. Hosts load cached copies; missing changes mean a stale cache. Keep one enabled core installation. An unregistered `SKILL.md` can be followed by absolute path; that registers nothing.

| | Codex | Claude Code |
| --- | --- | --- |
| Register home | `codex plugin marketplace add <home>` | `claude plugin marketplace add <home>` |
| Install | `codex plugin add <lib>@orchflows-home` | `claude plugin install <lib>@orchflows-home --scope user` |
| After editing a library | bump the native manifest version; `codex plugin add <lib>@orchflows-home` | `claude plugin marketplace update orchflows-home`; `claude plugin update <lib>@orchflows-home` |
| Invoke | `$<lib>:<skill>` or `/skills` | `/<lib>:<skill>` |
| Core development | register the checkout's `orchflows-light-local` catalog; install `orchflows-light@orchflows-light-local` | same, or `claude --plugin-dir <checkout>` |
| Concurrency, set to 15 by setup | `[agents] max_threads` in `$CODEX_HOME/config.toml` or `~/.codex/config.toml`: open spawned threads, primary excluded. CLI 0.144.0 spelling; `max_concurrent_threads_per_session` is normalized to it | `env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY = "15"` in `$CLAUDE_CONFIG_DIR/settings.json` or `~/.claude/settings.json`: slots shared by parallel tools and subagents |
| Custom agent definitions | `.codex/agents/*.toml`, `~/.codex/agents/` | `.claude/agents/*.md`, `~/.claude/agents/` |

## Loading

A relative link resolves from the file containing it; a cache holding single skill folders breaks `../../standards/`. Claude `context: fork` gives a child context, not a worktree; built-ins stay in the current context. Resolve scripts from the loaded skill directory; `${CLAUDE_SKILL_DIR}` is Claude-only. Resolve inputs and outputs from the assignment workspace.

## Isolation

A child may use the current workspace when edits cannot overlap; a read-only reviewer may inspect a stable candidate there. Otherwise give it a worktree at the intended revision. Claude: `isolation: worktree` on the Agent tool or agent definition; confirm the starting commit, since defaults may branch from the default branch. Codex: the child interface has no workspace argument; create one and direct every child operation there:

```sh
git worktree add -b task-candidate ../task-candidate <commit>
git worktree add --detach ../task-review <candidate-commit>
```

Worktrees start from Git state; transfer uncommitted files deliberately. Integrate through the host or Git, check the combined result, then clean up. Non-repository work uses the host's workspace and artifact access.

Sources: [Codex plugins](https://developers.openai.com/plugins/build/plugins), [Codex skills](https://developers.openai.com/codex/skills), [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Codex worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees), [Claude plugins](https://code.claude.com/docs/en/plugins), [Claude skills](https://code.claude.com/docs/en/skills), [Claude subagents](https://code.claude.com/docs/en/sub-agents), [Claude worktrees](https://code.claude.com/docs/en/worktrees), [Claude env vars](https://code.claude.com/docs/en/env-vars).
