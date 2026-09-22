# Hosts

Host behavior varies by version. No check below establishes authenticated workflow execution.

| Host | Last verified locally | Documentation last checked |
| --- | --- | --- |
| Codex | 0.144.0 installer commands, 2026-09-16 | Skills and delegation 2026-09-21; 0.155.1 on 2026-09-22 |
| Claude Code | 2.1.270 installer commands, 2026-09-16; loading by name in native trials; 2.1.280, installed after the recheck below, for same-version plugin refresh only, 2026-09-22 | 2.1.280 (required for Opus 5.5), 2026-09-22 |
| Antigravity (`agy`) | CLI 1.0.14 installation and discovery, 2026-09-16 | CLI 1.2.6, 2026-09-21 |
| Kimi Code | Installed 0.29.0 predates documented plugin and model-pool support; native loading unverified | 2.0.2, 2026-09-21 |
| Grok Build | 1.0.5 installation and discovery, 2026-09-16 | 2026-09-16 |
| ZCode | Registration and agent behavior documentation-verified only | 3.14.1, 2026-09-21 |

Documentation rechecked 2026-09-22 for Claude Code 2.1.280 (required for Opus 5.5) and Codex 0.155.1; installed CLIs remained Claude Code 2.1.270 and Codex 0.144.0, so facts added that day are documentation-verified only.

## Register and refresh

[Setup](home.md#setup) detects executables, registers core and requested examples through Codex, Claude Code, Antigravity and Grok Build CLIs, and refreshes installed home libraries under the ownership checks below. Kimi Code and ZCode require reported in-app steps. `setup --host <name>` selects a host; `--host none` prepares only home. `doctor` checks without changing registrations.

Keep one enabled core installation. Setup preserves disabled, foreign and multiple installations and reports required action. Unsupported CLI versions or failed commands do not stop other hosts. Start a new session after installation. Reading an unregistered `SKILL.md` by absolute path does not register it.

Use these native commands for optional libraries, development and manual recovery:

| | Codex | Claude Code |
| --- | --- | --- |
| Register home | `codex plugin marketplace add <home>` | `claude plugin marketplace add <home>` |
| Install | `codex plugin add <lib>@orchflows-home` | `claude plugin install <lib>@orchflows-home --scope user` |
| After editing a library | rerun setup (see below), or `codex plugin add <lib>@orchflows-home` | rerun setup (see below), or `claude plugin marketplace update orchflows-home`; `claude plugin uninstall <lib>@orchflows-home --keep-data`; `claude plugin install <lib>@orchflows-home --scope user` |
| Invoke | `$<lib>:<skill>` or `/skills` | `/<lib>:<skill>` |
| Core development | register the checkout's `orchflows-local` catalog; install `orchflows@orchflows-local` | same, or `claude --plugin-dir <checkout>` |
| Custom agent definitions | `.codex/agents/*.toml`, `~/.codex/agents/` | `.claude/agents/*.md`, `~/.claude/agents/` |

Concurrency changes only on request; see [limits and supported hosts](#concurrency).

After editing a library, rerun setup; leave manifest versions unchanged. Setup refreshes each installed package natively, then compares installed files with the source. Claude Code installs versioned cache copies that `plugin update` leaves stale at an unchanged version (observed on 2.1.280), so setup uninstalls and reinstalls a Claude package whose installed files differ (reinstall while a session has the plugin loaded is untested). Files that still differ are reported; setup never edits private host caches. Kimi Code and ZCode refresh through the in-app steps below.

Setup verifies installed contents. Read-only Codex checks verify source, enabled registration and version; inventory omits the cache path, so `doctor` cannot detect same-version cache changes. Rerun setup to refresh and verify them.

Registration references: [Codex plugins](https://developers.openai.com/plugins/build/plugins), [Claude plugins](https://code.claude.com/docs/en/plugins).

### Google Antigravity (`agy`)

Use `setup --host agy` or automatic detection. For manual installation/development: `agy plugin validate <package-root>`, `agy plugin install <package-root>`, then `agy plugin list`. Antigravity reads root `plugin.json` and copies the complete package; no extra manifest or marketplace. [CLI plugins](https://www.agy.dev/docs/cli/plugins/).

CLI 1.0.14 installs into `~/.gemini/config/plugins/<name>/`, also documented for desktop; desktop loading is untested. Verify registration through your version's native inventory. [Desktop plugins](https://www.agy.dev/docs/plugins/).

Setup records installations in home's `.local/agy-installs.json`. It refreshes only enabled copies owned by that home with cached contents matching the previous receipt. Disabled, changed or untracked copies remain untouched and require action. Setup refreshes owned copies through native uninstall/install, then verifies files. Never register by editing caches or import registry.

Invoke through `/skills` and its displayed command. Antigravity documents no manual-only setting; setup warns. Documentation covers releases newer than tested 1.0.14, including Markdown custom agents added in 1.1.6. Check installed tools before relying on delegation controls below. [Skills](https://www.agy.dev/docs/skills/), [CLI changelog](https://www.agy.dev/changelog?tab=cli).

### Kimi Code

Detected Kimi reports `needs_action` with a resolved command. Inside Kimi, run `/plugins install <absolute-package-root>`, then `/reload` or `/new`. Core root: `<home>/.local/packages/orchflows`; library: `<home>/libraries/<directory>`; development: checkout. Repeat after source changes. Setup/doctor cannot verify this in-app step through a supported shell command.

Kimi requires `.kimi-plugin/plugin.json` or `kimi.plugin.json`, supplied for core/examples, with `name`, `version` and `skills: "./skills/"`; it ignores Claude's manifest. Local installation copies the complete package into `$KIMI_CODE_HOME/plugins/managed/`. Default user configuration: `~/.kimi-code/config.toml`. [Plugins](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins), [manifest parser](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/app/plugin/manifest.ts).

Skills retain unqualified frontmatter names, e.g. `/skill:orch-build-workflow`; the model's `Skill` tool rejects qualified names. User, project and later sources silently shadow a same-named plugin skill, so keep installed names unique across libraries and resolve an intended package by absolute path. [Skills](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html), [registry](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/features/skill/catalog/registry.ts).

### Grok Build

Before installing core, setup checks `grok inspect --json` for effective installations, including Claude-compatible copies. Manually install with `grok plugin install <absolute-package-root>`; use the checkout for development. Verify with `grok plugin validate <package-root>` and workspace-local `grok inspect --json`; after edits, rerun setup, which reinstalls stale copies as described below, and verify loaded paths. `grok plugin marketplace add <home>` registers the Claude-compatible catalog for `/plugins`. [CLI reference](https://docs.x.ai/build/cli/reference).

Grok reads `.claude-plugin` packages and can discover Claude installations automatically. Check for stale compatible copies and keep one core enabled. Skills appear in `/skills` and as `/<skill-name>`; use displayed qualified names for collisions. Grok honors `disable-model-invocation`; skill-frontmatter `model`/`effort` do not select agent settings. [Skills and plugins](https://docs.x.ai/build/features/skills-plugins-marketplaces).

Grok 1.0.5 can copy Windows local plugins while `plugin update` reports live links. For stale enabled user installations from this exact home, setup natively uninstalls with `--keep-data`, reinstalls and verifies. Compatible, disabled and foreign installations remain untouched.

### Z.ai / ZCode

Detected ZCode reports `needs_action` with the resolved home path. With a workspace open, use **Settings → Plugins → Create → Add marketplace**, choose home, and install `orchflows` and wanted libraries. Setup generates root `marketplace.json` with package paths/versions. ZCode reads `.claude-plugin/plugin.json`; no extra manifest. For development, add the checkout's root marketplace. Setup/doctor cannot verify this in-app step through a supported shell command.

After edits, rerun setup, then uninstall and reinstall the edited library in the app (untested). ZCode compares catalog and installed-manifest versions, so same-version edits do not appear as updates. Registration is documented through UI; do not assume a `zcode plugin` shell command. [Plugins](https://zcode.z.ai/en/docs/plugin).

Z.ai can supply Claude Code's model while retaining Claude's registration/invocation. Follow [provider setup](https://docs.z.ai/devpack/tool/claude), then the Claude installation above. Documented Anthropic-compatible endpoint: `https://api.z.ai/api/anthropic`; credentials and model mappings remain user-owned.

## Concurrency

`setup --concurrency N` sets positive integer limits in detected, selected hosts only; otherwise settings remain untouched. Equal numbers have different effects across scopes. Changes retain backups; malformed/unsupported layouts remain unchanged. Report each failed or unsupported host while continuing others.

| Host | User configuration | Limit changed |
| --- | --- | --- |
| Codex | `$CODEX_HOME/config.toml`, default `~/.codex/config.toml` | `[agents] max_threads`: open spawned threads, primary excluded |
| Claude Code | `$CLAUDE_CONFIG_DIR/settings.json`, default `~/.claude/settings.json` | `env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`: shared parallel read-only tools and subagents; running subagents are also capped by `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (default 20, 2.1.217+; setup does not change it; ultracode sessions are exempt; documented for 2.1.280, not observed with the Claude Code on PATH, 2.1.270) |
| ZCode | `~/.zcode/cli/config.json` | `toolConcurrency.maxConcurrency`: parallel tool batches, including subagent calls |
| Kimi Code | `$KIMI_CODE_HOME/config.toml`, default `~/.kimi-code/config.toml` | `[background] max_running_tasks`: running background Bash tasks and background Agent calls |
| Grok Build | `$GROK_HOME/config.toml`, default `~/.grok/config.toml` | `[subagents] max_concurrent`: admitted subagents in a session |
| Antigravity | No verified writable setting | Reported as unsupported for tuning; registration still proceeds |

Codex documentation names `max_concurrent_threads_per_session`; setup uses supported alias `max_threads`. Configuration takes effect in new sessions; higher-precedence settings can override user files. [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents#global-settings), [Claude concurrency](https://code.claude.com/docs/en/env-vars).

ZCode Desktop 3.11.2's engine 0.16.5 confirms default cap 10, the JSON key and fixed user-config path. **`ZCODE_MAX_TOOL_CONCURRENCY`** overrides it. `ZCODE_HOME` does not relocate this file; native `--settings` or project settings can supersede it. Local checks covered the parser, not authenticated scheduling.

Setup writes only `[background] max_running_tasks`. A `[task] max_running_tasks` override prevents editing; remove it before tuning. Other task settings remain untouched. `KIMI_CODE_BACKGROUND_MAX_RUNNING_TASKS` overrides the background limit. **`KIMI_CODE_AGENT_SWARM_MAX_CONCURRENCY`** separately controls AgentSwarm; without a verified TOML equivalent, setup changes neither it nor shell profiles. [Configuration](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/config-files), [environment variables](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/env-vars), [0.43.1 task settings](https://github.com/MoonshotAI/kimi-code/blob/%40moonshot-ai%2Fkimi-code%400.43.1/packages/agent-core-v2/src/agent/task/configSection.ts).

Grok tuning requires an existing boolean `subagents.enabled`; setup preserves its value and queue/fail `limit_behavior`. Adding the section can change enablement, so missing enablement is reported. `GROK_MAX_CONCURRENT_SUBAGENTS` overrides the file. Official source documents the numeric limit; installed 1.0.5 has setting symbols but no effective-limit inspection command. Scheduling enforcement is untested. [Configuration](https://github.com/xai-org/grok-build/blob/482711333c7195dc16a272777f86086d615e2afb/crates/codegen/xai-grok-pager/docs/user-guide/26-config-reference.md#L519), [resolver](https://github.com/xai-org/grok-build/blob/482711333c7195dc16a272777f86086d615e2afb/crates/codegen/xai-grok-shell/src/config/mod.rs#L281).

Conflicting ZCode, Kimi background or Grok environment overrides leave files untouched and report the variable to adjust; matching overrides permit the write. Native project/session precedence still applies. Antigravity's concurrent agents/nesting depth do not establish a configurable cap; [settings](https://www.agy.dev/docs/cli/settings/) and [subagent docs](https://www.agy.dev/docs/subagents/) checked 2026-09-16.

## Invocation policy

Apply [invocation policy](architecture.md#invocation) per skill, not library manifest. `orch-dynamic-workflow` (for top-level tasks without explicit workflow/primitive selection) and named dependencies such as `orch-work`, `orch-review` and shared components use `disable-model-invocation: false` and Codex `policy.allow_implicit_invocation: true`. Other shipped skills use manual-only settings below. Automatic selection is a host/model decision, not deterministic routing or permission for child workflows.

| Host | Manual-only setting | Explicit invocation |
| --- | --- | --- |
| Codex | `policy.allow_implicit_invocation: false` in `skills/<skill>/agents/openai.yaml` | `$<library>:<skill>` or the skill picker |
| Claude Code | `disable-model-invocation: true` in `SKILL.md` frontmatter | `/<library>:<skill>` |
| Antigravity | None documented: skills remain model-visible | `/skills` and its displayed command |
| Kimi Code | `disable-model-invocation: true` in `SKILL.md` frontmatter | `/skill:<skill>` |
| Grok Build | `disable-model-invocation: true` in `SKILL.md` frontmatter | `/<skill>` or the displayed qualified command |
| ZCode | Unsupported: enabled skill metadata remains model-visible | `$<skill>` or the slash picker |

Keep skills enabled and user-invocable; include Codex `interface.display_name` and `interface.short_description`. Change both invocation settings to allow automatic selection, then refresh the installed plugin.

ZCode ignores unsupported frontmatter and cannot disable automatic skill selection; explicit invocation works. Report the gap; use Claude Code with Z.ai when enforcement is required. Never claim equivalent enforcement or label the skill disabled. [Skills](https://zcode.z.ai/en/docs/skill).

Antigravity documents automatic discovery, not `disable-model-invocation` support. Keep the field for other hosts and report missing enforcement. `disable-slash-command` hides explicit invocation but permits model invocation, so cannot enforce this contract. [Skills](https://www.agy.dev/docs/skills/), [CLI changelog](https://www.agy.dev/changelog?tab=cli).

These settings also govern loading by name: Claude and Kimi hide manual-only skills from the model and refuse its calls (Claude also blocks subagent preloading); Codex omits them from the model's skill list. ZCode and Antigravity cannot hide skills, so dependencies load there regardless. Codex and Claude Code expose plugin skills as `<library>:<skill>`. Grok uses bare skill names, qualified only when names collide; Kimi, ZCode and Antigravity use bare skill names. Load a named dependency by the name its host exposes. Composition applies loaded workflow files in the coordinator; same-package steps follow relative links, and supplied paths may be read directly where permitted. A refused or missing named dependency is a packaging defect: never bypass the rejection; report it as a capability gap. [Codex policy](https://learn.chatgpt.com/docs/build-skills#optional-metadata), [Claude control](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill), [Kimi skills](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html).

## Loading

Resolve links from their containing file, scripts from the loaded skill directory, and inputs/outputs from the assignment workspace. Skill-only copies break links such as `../../guidance/`. `${CLAUDE_SKILL_DIR}` is Claude-only; `context: fork` creates child context without filesystem isolation. Built-ins use current context. [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Claude skills](https://code.claude.com/docs/en/skills).

Install complete packages on every host. Kimi exposes `${KIMI_SKILL_DIR}`, but shared instructions use package-relative links and require the package root.

## Delegation

Use a fresh native child per primitive. On Claude Code the `fork` subagent type inherits the conversation and parent model, so it is not a fresh child (documented for 2.1.280; not observed with the Claude Code on PATH, 2.1.270); launch primitives with a non-fork type. On Codex, launch primitives without inherited history (`fork_context: false` on multi-agent v1, `fork_turns: "none"` on v2); full-history forks carry the maker's conversation, as observed 2026-09-22 with gpt-5.6-luna on Codex 0.156.0. Skill `context: fork` is separate. Kimi `Agent` supports fresh `coder` children; built-in children cannot delegate, while custom agents may declare subagents. ZCode `Agent` has independent context and cannot spawn grandchildren. Claude Code (three layers by default; documented for 2.1.280, not observed with the Claude Code on PATH, 2.1.270), Codex and Antigravity let children spawn children; there the assignment's no-delegation rule is the control. Compose and dispatch leaves in the top-level coordinator; report workflows requiring nested coordinators as a gap. [Kimi agents](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents), [ZCode subagents](https://zcode.z.ai/en/docs/subagents).

Grok's full-capability type is `general-purpose`; `explore`/`plan` cannot run shell commands or edit. Review tests require a fresh full-capability reviewer bound by the no-repair contract. Ensure subagents are enabled. [Grok subagents](https://docs.x.ai/build/features/subagents).

Antigravity documents `invoke_subagent` with fresh context; `self` retains parent instructions/tools. Pass assignment guidance and inputs explicitly. Native messaging wakes idle children; nesting is limited to ten child levels. Use controls exposed by the installed version. [Subagents](https://www.agy.dev/docs/subagents/).

## Workflow trials

Manual trial requests write `[invoke <library>:<skill>]` where the tester types the host's [explicit invocation](#invocation-policy); plain-text names cannot start manual-only skills. Use a disposable workspace and realistic synthetic fixtures covering relevant formats and failures. Supplied documents inform fixtures and remain read-only. Point mutable workflow inputs at disposable synthetic copies; execute required mutations there. Copy real content only when essential and authorized for that trial; never transform originals.

Replace external reads with fixtures where possible and external writes with local fakes capturing proposed payloads. Email/calendar trials produce drafts and fake receipts, never real messages/invitations. Verify service sandboxes or dry-runs cannot reach live resources; withhold production credentials and disable outbound access where available. Directories alone do not isolate APIs. Skip uncontainable branches and report gaps. Authoring does not authorize live execution; live trials require an explicit request covering those effects.

Trial composing workflows in a fresh separate top-level session with its own coordinator, ordinary inputs and declared dependencies; exclude authoring history and expected answers. Only the authoring coordinator launches it; workers must not launch trials or become nested coordinators. Nondelegating leaves may be trialed through `orch-work`. Report unavailable required independent sessions as validation gaps.

Keep outputs outside packages. Required independent judgments need real reviewers, never service fakes. Record fixture/source identities, preparation, interventions, simulated effects and untested integrations. Verify unchanged references, required fixture mutations and captured outbound effects. Audit native launches, assignments and continuations; only the trial coordinator directs agents. Verify model/effort in native metadata and guidance in assignment context. Simulation establishes local behavior, not live integration.

## Model and effort

Apply [resolved assignment choices](architecture.md#model-and-effort) through exposed native controls. Unset controls use native defaults, possibly different from the coordinator. Model names in prompts do not select models.

| Host | Native controls |
| --- | --- |
| Codex | Exposed spawn model/effort fields, e.g. `model` and `reasoning_effort`. If full-history forks forbid overrides, use fresh or partial context. |
| Claude Code | Agent model override; agent-definition `effort` when invocation has no effort field. Unset effort inherits the session. Opus 5.5 sessions default to `medium`; a top-level user `effortLevel` does not apply to it; `CLAUDE_CODE_EFFORT_LEVEL` overrides session effort (documented for 2.1.280; not observed with the Claude Code on PATH, 2.1.270). Forks ignore model overrides (documented for 2.1.280; not observed with the Claude Code on PATH, 2.1.270). |
| Antigravity | Documented custom-agent tiers: `model: inherit`, `flash`, `pro`; use exposed child controls. No documented child effort field. CLI `--model`/`--effort` select the top-level session; report unsupported child requests. |
| Kimi Code | With model pools, `Agent.model` selects a configured `[secondary_model]` alias or `primary`; otherwise inherits caller. No per-call effort field; check `default_effort`, pool overrides and `force`. Resumption cannot change model. |
| Grok Build | Exposed child controls or existing agent type with requested routing (`[subagents.models]`). Skill-frontmatter `model`/`effort` and top-level CLI flags are not child overrides; report absent controls. |
| ZCode | Existing definitions in `~/.zcode/agents/` set `model`/`thoughtLevel` and reload in new sessions. `thoughtLevel` requires explicit model; inherited models inherit effort. |

Kimi model pools became generally available in 0.42.0; installed 0.29.0 does not establish support. [Kimi configuration](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/config-files.html), [changelog](https://www.kimi.com/code/docs/en/kimi-code-cli/changelog), [Grok settings](https://docs.x.ai/build/settings/reference), [ZCode subagents](https://zcode.z.ai/en/docs/subagents).

Never silently map requested model identifiers to Antigravity tiers. [Custom subagents](https://www.agy.dev/docs/subagents/), [CLI model/effort flags](https://antigravity.google/docs/cli/headless/).

Check configuration that may override launch choices. Codex custom-agent files can override explicit spawn values; absent explicit values, subagent defaults precede parent settings. Changing model without effort may select its default effort. Claude model precedence: per-call `model`, then agent-definition `model`, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the main model; `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` forces one model (documented for 2.1.280; not observed with the Claude Code on PATH, 2.1.270). Use supported combinations; report unhonored requests before dependent work. Never create standing host configuration as an implicit fallback.

Reuse workers only if the host can honor repair settings. If continuation cannot change them, launch a fresh worker with the joined result and repair context. [Codex configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents), [Claude configuration](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields).

## Isolation

When children need isolation, use worktrees at the intended revision. Claude's `isolation: worktree` branches from the remote default branch unless the user sets `worktree.baseRef: "head"`, and copies tracked files only (`.worktreeinclude` adds ignored files; documented for 2.1.280, not observed with the Claude Code on PATH, 2.1.270); confirm the commit. If Codex's child tool lacks a workspace argument, create a worktree and direct all child operations there:

```sh
git worktree add -b codex/task-candidate ../task-candidate <commit>
git worktree add --detach ../task-review <candidate-commit>
```

Transfer needed uncommitted files explicitly. Continue children through native messaging. Integrate through host or Git, check the combined result, then clean up. For non-repository work, use host workspace/artifact access. [Codex worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees), [Claude worktrees](https://code.claude.com/docs/en/worktrees).

For Grok's native worktree isolation, verify revision and included local changes. Kimi/ZCode conversation isolation does not isolate files; use explicit worktrees when child tools lack workspace controls. [Grok worktrees](https://docs.x.ai/build/features/worktrees).

Antigravity documents `inherit`, `branch` (isolated worktree) and `share` child workspaces. Verify `branch` revision and included changes. `/fork` copies conversation without isolating files. [Subagents](https://www.agy.dev/docs/subagents/), [forks](https://www.agy.dev/docs/cli/conversations/).
