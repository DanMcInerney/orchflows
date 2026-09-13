# orchflows-light

Composable workflows for Codex and Claude Code: five skills, domain guidance and a portable home for your libraries. The host runs the agents.

## One concept, one owner

Each instruction or mechanism has one home; other layers reference it.

| Concept | Owner |
| --- | --- |
| Request: result, constraints, sources, dates | Your prompt |
| Coordination: steps, delegation, review, repairs | Workflow skills (`SKILL.md`) |
| Quality: domain preferences for making and reviewing | `guidance/` |
| Shared knowledge: dependencies, context, handoff contracts | `references/` |
| Mechanics: setup, history, acquisition, parsing | `scripts/`, with tests |
| Package identity and skill discovery | Plugin manifests |
| Agent execution and isolation | Codex or Claude Code |
| Results and run evidence | Your project workspace |

The outer workflow resolves dependencies and guidance once, then passes that context through its calls. Detailed contracts live in [architecture](docs/architecture.md).

## Five core skills

| Skill | Purpose |
| --- | --- |
| [orch-work](skills/orch-work/SKILL.md) | One fresh agent makes a result. |
| [orch-review](skills/orch-review/SKILL.md) | One independent agent reviews without fixing. |
| [orch-dynamic-workflow](skills/orch-dynamic-workflow/SKILL.md) | Coordinate a request and one final review. |
| [orch-build-workflow](skills/orch-build-workflow/SKILL.md) | Create workflows or guidance; refine through trials. |
| [orch-self-improve](skills/orch-self-improve/SKILL.md) | Use agent history to improve the environment or workflows. |

The first two are delegation primitives; the others compose them. Loading a skill applies instructions in the current agent; delegation creates a child.

## Layout

```text
skills/             five core skills
guidance/           domain preferences and dotted specializations
docs/               agent-facing contracts and operations
scripts/ + tests/   core CLI and checks
example-workflows/  separately installed libraries and runnable examples
```

Optional libraries: `social-search` collects and ranks evidence; `research-acquire` provides public-source readers; `short-video` makes and reviews films; `3d-browser-game` develops Three.js games through mechanics experiments, Blender assets and independent playtests.

The complete Nightbind game built with the 3D workflow lives beside it at `example-workflows/nightbind/`, with editable Blender sources and local run instructions. It is a runnable project, not an installable workflow library.

Your editable libraries live in `~/.orchflows/libraries/`; `personal` is the default for new workflows. Setup maintains the core under `~/.orchflows/.local/`. Task outputs stay in the project workspace.

## Install and use

From a checkout, with Python 3.11+:

```sh
python scripts/orchflows.py setup
```

Setup creates the home, Python environment and host catalogs, initializes Git without committing, and sets host concurrency to 15. Options: `--concurrency N`, `--skip-host-config`, or `--example NAME` to seed one library.

Register and install with your host, then start a new session:

```sh
codex plugin marketplace add ~/.orchflows
codex plugin add orchflows-light@orchflows-home
```

```sh
claude plugin marketplace add ~/.orchflows
claude plugin install orchflows-light@orchflows-home --scope user
```

Invoke `$orchflows-light:orch-dynamic-workflow` in Codex or `/orchflows-light:orch-dynamic-workflow` in Claude Code. Name a more specific skill when it fits; put the result, constraints and output location in your prompt.

[AGENTS.md](AGENTS.md) routes agents to [architecture](docs/architecture.md), [setup and updates](docs/home.md), [host registration and refresh](docs/hosts.md), [history](docs/history.md) and [authoring guidance](guidance/orchflows.md).
