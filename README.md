# orchflows-light

Five core skills, plain-Markdown guidance and a portable home for Codex and Claude Code. Small workflows compose through two delegation primitives. The host runs the agents; orchflows adds no agent runtime, scheduler or workflow language. Python utilities handle setup and native history.

| Built-in | Does |
| --- | --- |
| [orch-work](skills/orch-work/SKILL.md) | A fresh child makes a result under chosen guidance. |
| [orch-review](skills/orch-review/SKILL.md) | A fresh child who did not make it reviews without fixing. |
| [orch-dynamic-workflow](skills/orch-dynamic-workflow/SKILL.md) | Deliver a request when the user names no workflow or skill, with concurrent makers and one final review. |
| [orch-build-workflow](skills/orch-build-workflow/SKILL.md) | Author workflows or guidance, try them on representative work, simplify from observed use. |
| [orch-self-improve](skills/orch-self-improve/SKILL.md) | Mine native history to fix the environment, a workflow or orchflows itself. |

The first two are the primitives; the other three compose them. A useful dynamic run can later become a trial for `orch-build-workflow`.

Optional libraries live under `example-workflows/` in the repository and install separately:

| Library | Provides |
| --- | --- |
| `social-search` | Three skills: collect a source scope, rank evidence, compose both. |
| `research-acquire` | Scripted public-source acquisition and transcript readers. |
| `short-video` | Three skills: make a film, review its exports, compose both. |

These packages are examples and reusable dependencies; none enlarges the installed five-skill core.

## Install

Python 3.11+ (`python` on Windows), from a complete checkout:

```sh
python3 /path/to/orchflows-light/scripts/orchflows.py setup
```

This creates `~/.orchflows` with a managed core, Python environment and host catalogs. It initializes Git without committing and sets host concurrency to 15 (`--concurrency N`, `--skip-host-config`). Add `--example social-search`, `--example research-acquire` or `--example short-video` to seed an editable library once. See [home](docs/home.md) for paths, updates and migration of existing libraries.

Register the home with your host, then start a new session:

```sh
codex plugin marketplace add ~/.orchflows
codex plugin add orchflows-light@orchflows-home
```

```sh
claude plugin marketplace add ~/.orchflows
claude plugin install orchflows-light@orchflows-home --scope user
```

Install each optional library by the same command with its package name. Hosts cache plugins: after editing a library, refresh it and start a new session.

## Use

Invoke `$orchflows-light:orch-dynamic-workflow` in Codex or `/orchflows-light:orch-dynamic-workflow` in Claude Code, or name a specific workflow. Put the requested result, constraints and output location in the prompt. Social-search groups sources into collection assignments, then sends their evidence to one reviewer:

```text
social-search → search-site per assignment → orch-work → evidence
             → rank-evidence → orch-review → ranked, cited assessment
```

Ask `orch-build-workflow` for a workflow, domain guidance or specialization. Custom workflows land in `~/.orchflows/libraries/personal/` unless you name another location.

## Docs for agents

[AGENTS.md](AGENTS.md) routes agents to these; Claude Code reads it through [CLAUDE.md](CLAUDE.md).

- [Architecture](docs/architecture.md): design contracts, composition, where anything belongs.
- [Home](docs/home.md): the home tree and CLI.
- [Hosts](docs/hosts.md): register, refresh, isolation, host-specific settings.
- [History](docs/history.md): read transcripts as evidence.
- [Authoring guidance](guidance/orchflows.md): preferences for reusable workflows, guidance and libraries.
- [Domain guidance](guidance/): Code, Research, Writing, Visual design, Data analysis; `guidance/code.api.md` specializes Code.
