# Hosts

CLI commands checked 2026-09-12: Codex 0.144.0, Claude Code 2.1.233. Host behavior is version-dependent.

## Register and refresh

Setup writes catalogs; register the home, install each library, then start a new session. Keep one enabled core installation. If edits are missing, check the installed cache and restart. Following an unregistered `SKILL.md` by absolute path does not register it.

| | Codex | Claude Code |
| --- | --- | --- |
| Register home | `codex plugin marketplace add <home>` | `claude plugin marketplace add <home>` |
| Install | `codex plugin add <lib>@orchflows-home` | `claude plugin install <lib>@orchflows-home --scope user` |
| After editing a library | bump manifest versions; `codex plugin add <lib>@orchflows-home` | bump manifest versions; `claude plugin marketplace update orchflows-home`; `claude plugin update <lib>@orchflows-home` |
| Invoke | `$<lib>:<skill>` or `/skills` | `/<lib>:<skill>` |
| Core development | register the checkout's `orchflows-light-local` catalog; install `orchflows-light@orchflows-light-local` | same, or `claude --plugin-dir <checkout>` |
| Concurrency key written by setup | `[agents] max_threads` in `$CODEX_HOME/config.toml` or `~/.codex/config.toml`: open spawned threads, primary excluded | `env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` in `$CLAUDE_CONFIG_DIR/settings.json` or `~/.claude/settings.json`: parallel read-only tools and subagents |
| Custom agent definitions | `.codex/agents/*.toml`, `~/.codex/agents/` | `.claude/agents/*.md`, `~/.claude/agents/` |

Concurrency takes effect in new sessions; higher-precedence settings may override it. Current Codex documentation names `max_concurrent_threads_per_session`; setup's `max_threads` remains a supported alias. [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents#global-settings), [Claude concurrency](https://code.claude.com/docs/en/env-vars).

Registration references: [Codex plugins](https://developers.openai.com/plugins/build/plugins), [Claude plugins](https://code.claude.com/docs/en/plugins).

## Loading

Resolve links from the containing file, scripts from the loaded skill's directory, and inputs/outputs from the assignment workspace. Copying only skill folders breaks package-relative links such as `../../guidance/`. `${CLAUDE_SKILL_DIR}` is Claude-only; `context: fork` launches a child context without filesystem isolation. Orchflows built-ins use the current context. [Codex skills](https://developers.openai.com/codex/skills), [Claude skills](https://code.claude.com/docs/en/skills).

## Isolation

When a child needs isolation, use a worktree at the intended revision. Claude supports `isolation: worktree`; confirm the starting commit, since the default may use the remote default branch. If Codex's child tool has no workspace argument, create a worktree and direct every child operation there:

```sh
git worktree add -b codex/task-candidate ../task-candidate <commit>
git worktree add --detach ../task-review <candidate-commit>
```

Transfer needed uncommitted files explicitly. Continue existing children through native messaging. Integrate through the host or Git, check the combined result, then clean up. Non-repository work uses host workspace/artifact access. [Codex worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees), [Claude worktrees](https://code.claude.com/docs/en/worktrees).
