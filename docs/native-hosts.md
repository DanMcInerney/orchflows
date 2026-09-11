# Native hosts

Host behavior below was checked against official documentation and local CLI surfaces on 11 September 2026. Use the fields and commands your installed host actually exposes.

## Load and invoke

The package keeps a portable root `plugin.json` and native Codex/Claude compatibility manifests over the same `skills/` directory. Setup creates catalogs under your orchflows home; the README shows how to register that home and install core and custom libraries. Catalog paths are relative to the home root, so `./libraries/social-search` stays valid after cloning elsewhere. Setup does not itself change native host settings. [Codex packaging](https://developers.openai.com/plugins/build/plugins).

Codex CLI/IDE supports `/skills` and `$social-search:social-search`; the app has a skill picker. Claude skills use names such as `/social-search:search-reddit`. Both hosts namespace installed plugin skills; their invocation commands are not interchangeable. Registering an arbitrary home catalog requires `codex plugin marketplace add /absolute/home`; Codex does not automatically scan `~/.orchflows/libraries`. [Codex skills](https://developers.openai.com/codex/skills), [Claude plugins](https://code.claude.com/docs/en/plugins), [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).

Both hosts install cached package copies. After editing a home library, update its native manifest version as required by your host and reinstall/update, then start a fresh session. On the inspected Codex CLI, use `codex plugin add social-search@orchflows-home`; local marketplaces are read locally, while `marketplace upgrade` refreshes Git snapshots. For Claude use `claude plugin marketplace update orchflows-home`, then `claude plugin update social-search@orchflows-home`. Inspect the loaded path if changes are missing. Authored source and run summaries remain under your home; host-owned caches and settings may live elsewhere. [Codex local plugins](https://developers.openai.com/plugins/build/plugins#how-local-marketplaces-work), [Claude versioning](https://code.claude.com/docs/en/plugins-reference#version-management).

For core development, the repository still supplies `orchflows-light-local` catalogs pointing at its root. Register that checkout and install `orchflows-light@orchflows-light-local` using the same host commands. Use one enabled core installation to avoid duplicate names. Claude also supports `claude --plugin-dir /absolute/path/to/orchflows-light` for a local session. To inspect an unregistered workflow, ask the agent to read and follow its absolute `SKILL.md` path; this does not register a named skill.

## Resources and composition

Resolve a relative link from the file containing it, not the current project directory. For a loaded `skills/delegate-work/SKILL.md`, `../../standards/` is inside that same package. A copied or cached installation must retain the package's skills, standards and documentation together. Copying only individual skill folders loses those links. Custom libraries resolve external core dependencies through the [home CLI](home-library.md), then pass concrete file paths to workers; they do not link into a presumed sibling source checkout.

Workflow composition means loading another native skill's instructions in the current orchestrator. A workflow can instead ask a child to orchestrate when the actual host supports that nesting. Claude's `context: fork` selects a child context; it does not itself select a worktree. This package's skills stay in the current context and allow native skill invocation. [Claude skills](https://code.claude.com/docs/en/skills).

Place scripts, references and assets beside the skill that uses them and link them where needed. Resolve script paths from the loaded skill directory; resolve inputs and outputs from the assignment's workspace. Claude's `${CLAUDE_SKILL_DIR}` is available there, but is not portable Codex syntax. Ordinary dependency tools suffice. [Codex skills](https://developers.openai.com/codex/skills), [Claude skills](https://code.claude.com/docs/en/skills).

## Workspaces and native agents

Every delegated repository assignment, including review, uses its own worktree at the intended input state. Prefer native per-child worktree creation when the actual launch interface supports it. Claude's Agent tool and agent definitions support `isolation: worktree`. Confirm the starting revision: host defaults can start from a default branch rather than the current candidate. [Claude worktrees](https://code.claude.com/docs/en/worktrees).

A Codex app session worktree does not automatically isolate its children. The child interface inspected here has no worktree or working-directory argument. Where that is still true, create an ordinary Git worktree and explicitly direct all child operations there, for example:

```sh
git worktree add -b task-candidate "../task-candidate" <intended-commit>
git worktree add --detach "../task-review" <candidate-commit>
```

Replace the example paths, branch and commits for the task. This is a working convention, not a filesystem sandbox. Use a native child isolation field if your installed interface provides one. Session-level features are not evidence of child isolation. [Codex worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees), [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Worktrees begin from Git state; uncommitted changes, ignored setup files and outside artifacts need deliberate transfer or explicit access. A reviewer must receive the actual candidate. For non-repository tasks, use the host's appropriate workspace and artifact access; external sources need not become Git repositories. Use native messaging, waiting and continuation for results and repairs. Integrate with the host or Git, check the combined work and preserve needed changes before native or Git cleanup. [Claude worktrees](https://code.claude.com/docs/en/worktrees).

## Models and effort

Inherit native defaults unless the caller selects an available native agent, model or effort option. This package supplies no model presets or settings changes.

Codex custom agents live in project `.codex/agents/*.toml` or user `~/.codex/agents/`. Their native fields include `name`, `description`, `developer_instructions`, and optional `model` and `model_reasoning_effort`. [Codex custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Claude custom agents live in project `.claude/agents/*.md` or user `~/.claude/agents/`; Markdown frontmatter includes `name`, `description`, and optional `model`, `effort` and `isolation`, with instructions in the body. Use the host's current supported values and limits. [Claude custom agents](https://code.claude.com/docs/en/sub-agents).

The skills instruct native agent launches; permissions and workspace lifecycles remain with the host and Git. If a needed native capability is unavailable, say so instead of implying it ran.
