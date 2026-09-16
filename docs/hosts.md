# Hosts

Installer commands checked 2026-09-16: Codex 0.144.0, Claude Code 2.1.270. Host behavior is version-dependent.

Additional integrations researched from official documentation on 2026-09-16: Google Antigravity (`agy`), Kimi Code, Grok Build and Z.ai's ZCode. Antigravity CLI 1.0.14 and Grok 1.0.5 passed local plugin installation/discovery checks. Kimi 0.29.0 is installed locally, but is older than the documented plugin/model-pool surface; native loading was not verified. ZCode registration and agent behavior are documentation-verified only. These checks do not establish authenticated workflow execution.

## Register and refresh

[Setup](home.md#setup) detects supported executables and registers core through the Codex, Claude Code, Antigravity and Grok Build CLIs. It also installs an explicitly requested example and refreshes home libraries already installed in each host, subject to the ownership checks below. Kimi Code and ZCode need the reported in-app steps. Use `setup --host <name>` to select a host or `setup --host none` to prepare only the home; `doctor` checks the same host state without changing registrations.

Keep one enabled core installation. Setup preserves disabled plugins, registrations belonging to another source and multiple installations, reporting an action instead of choosing for you. Unsupported CLI versions and failed host commands remain visible while other hosts continue. Start a new session after installation. Following an unregistered `SKILL.md` by absolute path does not register it.

Use these native commands for optional libraries, development and manual recovery:

| | Codex | Claude Code |
| --- | --- | --- |
| Register home | `codex plugin marketplace add <home>` | `claude plugin marketplace add <home>` |
| Install | `codex plugin add <lib>@orchflows-home` | `claude plugin install <lib>@orchflows-home --scope user` |
| After editing a library | bump manifest versions; `codex plugin add <lib>@orchflows-home` | bump manifest versions; `claude plugin marketplace update orchflows-home`; `claude plugin update <lib>@orchflows-home` |
| Invoke | `$<lib>:<skill>` or `/skills` | `/<lib>:<skill>` |
| Core development | register the checkout's `orchflows-local` catalog; install `orchflows@orchflows-local` | same, or `claude --plugin-dir <checkout>` |
| Custom agent definitions | `.codex/agents/*.toml`, `~/.codex/agents/` | `.claude/agents/*.md`, `~/.claude/agents/` |

Concurrency is unchanged unless requested; see [concurrency settings](#concurrency) for supported hosts and the meaning of each limit. The legacy `--skip-host-config` preserves settings without disabling registration.

If installed files remain stale, bump the package version in all host manifests and rerun setup. Claude may reuse its cached copy when the version is unchanged. Setup reports mismatched files and leaves private host caches untouched.

Setup verifies installed package contents. Read-only Codex checks verify the source, enabled registration and manifest version; its inventory does not expose the cached package path, so `doctor` cannot detect changed cache contents at the same version. Rerun setup to refresh and verify that copy.

Registration references: [Codex plugins](https://developers.openai.com/plugins/build/plugins), [Claude plugins](https://code.claude.com/docs/en/plugins).

### Google Antigravity (`agy`)

Use `setup --host agy`, or let automatic detection find `agy`. For manual installation or checkout development, run `agy plugin validate <package-root>`, then `agy plugin install <package-root>` and `agy plugin list`. Antigravity consumes the existing root `plugin.json` and copies the complete package; no additional manifest or marketplace is required. [Antigravity CLI plugins](https://www.agy.dev/docs/cli/plugins/).

CLI 1.0.14 installs into `~/.gemini/config/plugins/<name>/`. This is the global plugin location documented for Antigravity desktop too; desktop loading was not exercised. The CLI plugins page still lists a private directory, but the 1.0.2 changelog records the switch to shared configuration. Use the native inventory to verify your version's registration. [Desktop plugins](https://www.agy.dev/docs/plugins/), [CLI changelog](https://www.agy.dev/changelog?tab=cli).

Setup records its installations in the home's `.local/agy-installs.json`. It refreshes only enabled copies owned by that home whose cached contents still match the previous receipt. Disabled, changed or untracked copies remain untouched and require action. Old CLI versions can retain deleted files when reinstalling; setup refreshes its own copies through native uninstall/install and verifies the resulting files. Do not edit Antigravity's caches or import registry to register a package.

Use `/skills` and its displayed command to invoke a workflow. Manual-only invocation enforcement is unverified; setup reports that policy gap as a warning. Current documentation describes newer releases than the tested 1.0.14, including Markdown custom agents added in 1.1.6. Check the installed host's available tools before relying on the delegation controls below. [Skills](https://www.agy.dev/docs/skills/), [CLI changelog](https://www.agy.dev/changelog?tab=cli).

### Kimi Code

When detected, Kimi is reported as `needs_action` with its resolved install command. Enter `/plugins install <absolute-package-root>` inside Kimi, followed by `/reload` or `/new`. For core, the package root is `<home>/.local/packages/orchflows`; for a library it is `<home>/libraries/<directory>`. Repeat the install after source changes. For development, install the checkout itself. Setup and doctor cannot verify this in-app step through a supported shell command.

Kimi requires `.kimi-plugin/plugin.json` (or `kimi.plugin.json`), supplied for core and bundled examples. A minimal manifest has `name`, `version` and `skills: "./skills/"`; it does not consume the Claude manifest. Local installation copies the complete package under `$KIMI_CODE_HOME/plugins/managed/`, preserving its resources. User configuration defaults to `~/.kimi-code/config.toml`. [Kimi plugins](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins), [manifest parser](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/app/plugin/manifest.ts).

Plugin skills keep their unqualified frontmatter names: `/skill:orch-dynamic-workflow`. Same-named skills from different libraries can collide; keep installed skill names unique or report the ambiguity and resolve the intended package by absolute path. [Kimi skills](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html), [skill registry](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/features/skill/catalog/registry.ts).

### Grok Build

Setup checks `grok inspect --json` for an effective installation before installing core, including Claude-compatible copies. For manual installation or another library, use `grok plugin install <absolute-package-root>`. Use the checkout path during development. Verify with `grok plugin validate <package-root>` and `grok inspect --json` from the intended workspace; after edits, run `grok plugin update` and verify the loaded paths. `grok plugin marketplace add <home>` also registers the Claude-compatible catalog for browsing in `/plugins`. [CLI reference](https://docs.x.ai/build/cli/reference).

Grok reads the existing `.claude-plugin` packages and can discover an existing Claude installation automatically. Keep only one core enabled and check for stale compatible copies before adding another. Skills appear in `/skills` and as `/<skill-name>`; use the displayed qualified name when a collision requires it. Grok honors `disable-model-invocation`; skill-frontmatter `model` and `effort` do not select agent settings. [Skills and plugins](https://docs.x.ai/build/features/skills-plugins-marketplaces).

Grok 1.0.5 can copy a local plugin on Windows while `plugin update` reports it as a live link. For a stale enabled user installation from this exact home, setup uses native uninstall with `--keep-data` followed by reinstall and verification. Compatible, disabled and foreign installations remain untouched.

### Z.ai / ZCode

When detected, ZCode is reported as `needs_action` with its resolved home path. In ZCode with a workspace open, go to **Settings → Plugins → Create → Add marketplace**, choose the home directory, and install `orchflows` and the wanted libraries. Setup generates the root `marketplace.json` with package paths and versions. ZCode reads the existing `.claude-plugin/plugin.json`; no duplicate ZCode manifest is needed. For checkout development, add the checkout's root marketplace instead. Setup and doctor cannot verify this in-app step through a supported shell command.

After edits, bump package versions, rerun setup, refresh the marketplace and check for plugin updates. ZCode compares the catalog entry version with the installed manifest version. The documented registration route is the app UI; do not assume a `zcode plugin` shell command exists. [ZCode plugins](https://zcode.z.ai/en/docs/plugin).

Z.ai can alternatively supply the model behind Claude Code, retaining Claude's registration and invocation behavior. Configure that provider using [Z.ai's Claude Code instructions](https://docs.z.ai/devpack/tool/claude), then use the Claude installation above. The documented Anthropic-compatible endpoint is `https://api.z.ai/api/anthropic`; credentials and model mappings remain user-owned.

## Concurrency

`setup --concurrency N` sets positive integer limits only for detected, selected hosts. Without that flag, settings remain untouched. These controls have different scopes; setting the same number does not imply identical execution behavior. Changed files retain backups, malformed or unsupported layouts are preserved, and failures do not prevent other hosts from being processed. An unsupported selected host is reported even when another host's update succeeds.

| Host | User configuration | Limit changed |
| --- | --- | --- |
| Codex | `$CODEX_HOME/config.toml`, default `~/.codex/config.toml` | `[agents] max_threads`: open spawned threads, primary excluded |
| Claude Code | `$CLAUDE_CONFIG_DIR/settings.json`, default `~/.claude/settings.json` | `env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`: shared parallel read-only tools and subagents |
| ZCode | `~/.zcode/cli/config.json` | `toolConcurrency.maxConcurrency`: parallel tool batches, including subagent calls |
| Kimi Code | `$KIMI_CODE_HOME/config.toml`, default `~/.kimi-code/config.toml` | `[background] max_running_tasks`: running background Bash tasks and background Agent calls |
| Grok Build | `$GROK_HOME/config.toml`, default `~/.grok/config.toml` | `[subagents] max_concurrent`: admitted subagents in a session |
| Antigravity | No verified writable setting | Reported as unsupported for tuning; registration still proceeds |

Current Codex documentation names `max_concurrent_threads_per_session`; setup's `max_threads` remains a supported alias. Native configuration takes effect in new sessions and higher-precedence settings can override user files. [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents#global-settings), [Claude concurrency](https://code.claude.com/docs/en/env-vars).

ZCode Desktop 3.11.2's installed engine 0.16.5 confirms the default cap of 10, the JSON key and the fixed user-config path. Its environment override is **`ZCODE_MAX_TOOL_CONCURRENCY`**, including the prefix. That engine's config loader does not relocate this file through `ZCODE_HOME`; an explicit native `--settings` file or project settings can supersede it. This support adapts [#201 by ozymandiashh](https://github.com/DanMcInerney/orchflows/pull/201); local checks exercised its configuration parser, not authenticated scheduling.

Kimi 0.29.0 validates the background key. Kimi 0.43.1 also recognizes preferred `[task] max_running_tasks`; setup synchronizes that key when already present so it cannot shadow the updated background limit. It leaves other task settings intact. `KIMI_CODE_BACKGROUND_MAX_RUNNING_TASKS` overrides both. The separate **`KIMI_CODE_AGENT_SWARM_MAX_CONCURRENCY`** controls AgentSwarm; no persistent TOML equivalent was verified, so setup does not alter it or shell profiles. [Configuration](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/config-files), [environment variables](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/env-vars), [0.43.1 task settings](https://github.com/MoonshotAI/kimi-code/blob/%40moonshot-ai%2Fkimi-code%400.43.1/packages/agent-core-v2/src/agent/task/configSection.ts).

Grok requires an existing explicit boolean `subagents.enabled` before tuning; setup preserves either true or false and the separate queue/fail `limit_behavior`. Adding the section can change native enablement, so setup reports missing enablement instead of choosing it. `GROK_MAX_CONCURRENT_SUBAGENTS` overrides the file. Current official source documents the numeric limit; installed 1.0.5 contains the setting symbols but does not expose an effective-limit inspection command. Native scheduling enforcement was not exercised. [Configuration reference](https://github.com/xai-org/grok-build/blob/482711333c7195dc16a272777f86086d615e2afb/crates/codegen/xai-grok-pager/docs/user-guide/26-config-reference.md#L519), [resolver](https://github.com/xai-org/grok-build/blob/482711333c7195dc16a272777f86086d615e2afb/crates/codegen/xai-grok-shell/src/config/mod.rs#L281).

Conflicting environment overrides for ZCode, Kimi background tasks and Grok leave that host's file untouched and report the variable to adjust. Matching overrides allow the requested write. Other native project/session overrides still take precedence. Antigravity's documented concurrent agents and nesting depth are not a verified configurable concurrency cap; checked its [settings](https://www.agy.dev/docs/cli/settings/) and [subagent documentation](https://www.agy.dev/docs/subagents/) on 2026-09-16.

## Invocation policy

Apply the [invocation policy](architecture.md#invocation) per skill; a library manifest does not set it for its skills. The automatic fallback, `orch-dynamic-workflow`, sets `policy.allow_implicit_invocation: true` for Codex and `disable-model-invocation: false` for hosts that support it. Other skills default to the manual-only settings below.

| Host | Manual-only setting | Explicit invocation |
| --- | --- | --- |
| Codex | `policy.allow_implicit_invocation: false` in `skills/<skill>/agents/openai.yaml` | `$<library>:<skill>` or the skill picker |
| Claude Code | `disable-model-invocation: true` in `SKILL.md` frontmatter | `/<library>:<skill>` |
| Antigravity | Unverified: no documented manual-only setting | `/skills` and its displayed command |
| Kimi Code | `disable-model-invocation: true` in `SKILL.md` frontmatter | `/skill:<skill>` |
| Grok Build | `disable-model-invocation: true` in `SKILL.md` frontmatter | `/<skill>` or the displayed qualified command |
| ZCode | Unsupported: enabled skill metadata remains model-visible | `$<skill>` or the slash picker |

Keep skills enabled and user-invocable. Include `interface.display_name` and `interface.short_description` in Codex metadata. Opting a skill into automatic selection requires changing both metadata settings. Refresh the installed plugin after changing these files.

ZCode ignores unsupported frontmatter and has no native manual-only skill switch. Explicit invocation works, but automatic selection cannot be restricted to the dynamic fallback. Report this policy gap; use Claude Code with Z.ai when native enforcement is required. Do not relabel the skill as disabled or claim equivalent enforcement. [ZCode skills](https://zcode.z.ai/en/docs/skill).

Antigravity documents automatic skill discovery but does not establish support for `disable-model-invocation`. Keep that field for other hosts and report the unverified policy. Its `disable-slash-command` setting hides explicit invocation while leaving model invocation available; it does not enforce this contract. [Antigravity skills](https://www.agy.dev/docs/skills/), [CLI changelog](https://www.agy.dev/changelog?tab=cli).

These settings control native skill invocation. Claude also blocks model calls and subagent preloading for manual-only skills; if a composed step requires a blocked native call, the user must invoke it. Do not bypass a host rejection. [Codex invocation policy](https://learn.chatgpt.com/docs/build-skills#optional-metadata), [Claude invocation control](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill).

## Loading

Resolve links from the containing file, scripts from the loaded skill's directory, and inputs/outputs from the assignment workspace. Copying only skill folders breaks package-relative links such as `../../guidance/`. `${CLAUDE_SKILL_DIR}` is Claude-only; `context: fork` launches a child context without filesystem isolation. Orchflows built-ins use the current context. [Codex skills](https://developers.openai.com/codex/skills), [Claude skills](https://code.claude.com/docs/en/skills).

Install complete packages on every host. Kimi also exposes `${KIMI_SKILL_DIR}`, but shared Orchflows instructions use relative package links. Adding a skills directory alone is not a substitute for preserving the package root.

## Delegation

Use a fresh native child for each primitive. Kimi's `Agent` supports fresh `coder` children; built-in children cannot delegate again, while custom agents can declare subagents. ZCode's native `Agent` has independent context and cannot spawn grandchildren. Keep composition in the top-level coordinator and dispatch its leaf assignments there; a workflow requiring a nested coordinator must report that gap. [Kimi agents](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents), [ZCode subagents](https://zcode.z.ai/en/docs/subagents).

Grok's full-capability type is `general-purpose`; its `explore` and `plan` types cannot run shell commands or edits. Use a full-capability fresh reviewer when verification requires tests, while retaining the review assignment's no-repair contract. Ensure subagents are enabled. [Grok subagents](https://docs.x.ai/build/features/subagents).

Antigravity documents `invoke_subagent` with fresh conversation context; the `self` type retains the parent's instructions and tools. Pass each assignment's guidance and inputs explicitly. Native messaging wakes idle children, and nesting is limited to ten child levels. Use the controls actually exposed by the installed version. [Antigravity subagents](https://www.agy.dev/docs/subagents/).

## Model and effort

Apply the [resolved assignment choices](architecture.md#model-and-effort) through the controls exposed by the current host. Unset controls use native defaults, which may differ from the coordinator's settings. Writing a model name in a child's prompt does not select it.

| Host | Native controls |
| --- | --- |
| Codex | Use the spawn tool's model and reasoning-effort fields when exposed, such as `model` and `reasoning_effort`. If full-history forks disallow overrides, use a fresh or partial context fork. |
| Claude Code | The Agent tool supports a model override. Effort is configured in an agent definition's `effort` field; use a definition that supplies the requested setting when the invocation has no effort field. Unset effort inherits the session's setting. |
| Antigravity | Documented custom agents select `model: inherit`, `flash` or `pro`; use exposed native child controls when available. No per-child effort field is documented. Top-level `--model` and `--effort` select the CLI session, not a child override; report unsupported requested settings. |
| Kimi Code | On versions with model pools, `Agent.model` selects a configured `[secondary_model]` alias or `primary`; without a pool it inherits the caller. There is no per-call effort field. Check model `default_effort`, pool overrides and `force` before claiming a choice was honored. Resuming cannot change the model. |
| Grok Build | Use the exposed native subagent controls or an existing agent type with the requested model routing (`[subagents.models]`). Do not treat skill-frontmatter `model`/`effort` or top-level CLI flags as child overrides; report absent child controls as a gap. |
| ZCode | Existing custom agent definitions can set `model` and `thoughtLevel`; `thoughtLevel` requires an explicit model. With an inherited model, effort follows the parent. Definitions live under `~/.zcode/agents/` and reload in new sessions. |

Kimi model pools became generally available in 0.42.0; the locally installed 0.29.0 does not establish support for them. [Kimi configuration](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/config-files.html), [changelog](https://www.kimi.com/code/docs/en/kimi-code-cli/release-notes/changelog.html), [Grok settings](https://docs.x.ai/build/settings/reference), [ZCode subagents](https://zcode.z.ai/en/docs/subagents).

Antigravity's documented child model choices are tiers; do not silently map a requested model identifier to one. [Custom subagents](https://www.agy.dev/docs/subagents/), [CLI model and effort flags](https://antigravity.google/docs/cli/headless/).

Check native configuration when it can override a launch choice. Codex custom agent files can override explicit spawn values; absent explicit values, subagent defaults precede parent settings. Selecting a different model without effort can select that model's default effort. Claude precedence can also depend on environment overrides and host version. Use only supported model/effort combinations and report an unhonored request before dependent work. Do not create standing host configuration as an implicit fallback.

Reuse a worker only if the host can honor the repair assignment's settings. If the continuation tool cannot change them, launch a fresh worker with the joined result and repair context. [Codex agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents), [Claude agent configuration](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields).

## Isolation

When a child needs isolation, use a worktree at the intended revision. Claude supports `isolation: worktree`; confirm the starting commit, since the default may use the remote default branch. If Codex's child tool has no workspace argument, create a worktree and direct every child operation there:

```sh
git worktree add -b codex/task-candidate ../task-candidate <commit>
git worktree add --detach ../task-review <candidate-commit>
```

Transfer needed uncommitted files explicitly. Continue existing children through native messaging. Integrate through the host or Git, check the combined result, then clean up. Non-repository work uses host workspace/artifact access. [Codex worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees), [Claude worktrees](https://code.claude.com/docs/en/worktrees).

Grok supports native subagent worktree isolation; verify the starting revision and included local changes. Kimi and ZCode's independent conversation contexts do not isolate files; use the explicit Git worktree procedure when their child tools expose no workspace control. [Grok worktrees](https://docs.x.ai/build/features/worktrees).

Antigravity documents child workspace modes `inherit`, `branch` (an isolated Git worktree) and `share`. Verify the starting revision and included changes when using `branch`. Its `/fork` command copies conversation history without isolating files. [Antigravity subagents](https://www.agy.dev/docs/subagents/), [conversation forks](https://www.agy.dev/docs/cli/conversations/).
