# orchflows-light

Two skill primitives, plain-Markdown quality standards and a portable home for Codex and Claude Code. Small workflows compose into larger ones the way modules compose into a program. The host runs the agents; orchflows adds no runtime or workflow language.

| Built-in | Does |
| --- | --- |
| [orch-work](skills/orch-work/SKILL.md) | A fresh child makes a result under chosen standards. |
| [orch-review](skills/orch-review/SKILL.md) | A fresh child who did not make it reviews without fixing. |
| [orch-build-workflow](skills/orch-build-workflow/SKILL.md) | Author a workflow, run a real trial, cut what the trial did not need. |
| [orch-self-improve](skills/orch-self-improve/SKILL.md) | Mine native history to fix the environment, a workflow or orchflows itself. |

The first two are the primitives; the other two are built from them.

## Install

Python 3.11+ (`python` on Windows), from a complete checkout:

```sh
python3 /path/to/orchflows-light/scripts/orchflows.py setup --example social-search
```

This creates `~/.orchflows`: a venv, a managed core copy, an editable `libraries/social-search`, and host catalogs. It initializes Git without committing and sets both hosts' agent concurrency to 15 (`--concurrency N`, `--skip-host-config`). Rerun from a newer checkout to update the core; your libraries are untouched. The home is a Git repository; `.local/` is ignored. `ORCHFLOWS_HOME` or `--home` relocates it.

Register the home with your host, then start a new session:

```sh
codex plugin marketplace add ~/.orchflows
codex plugin add orchflows-light@orchflows-home
codex plugin add social-search@orchflows-home
```

```sh
claude plugin marketplace add ~/.orchflows
claude plugin install orchflows-light@orchflows-home --scope user
claude plugin install social-search@orchflows-home --scope user
```

Invoke `$social-search:social-search` in Codex or `/social-search:social-search` in Claude Code. Hosts cache plugins: after editing a library, refresh it and start a new session.

## Use

Put the question, dates, sources, bounds and output location in the prompt. The example launches one worker per source and one reviewer:

```text
social-search → search-reddit / search-youtube / search-site → orch-work → evidence
             → rank-evidence → orch-review → ranked, cited assessment
```

Ask `orch-build-workflow` for your own workflow; it lands in `~/.orchflows/libraries/personal/`. `setup --example research-acquire` adds optional scripted readers (YouTube transcripts, bounded acquisition). Both examples live in `example-workflows/`.

## Docs for agents

[AGENTS.md](AGENTS.md) routes agents to these; Claude Code reads it through [CLAUDE.md](CLAUDE.md).

- [Architecture](docs/architecture.md): primitives, composition, where anything belongs.
- [Home](docs/home.md): the home tree and CLI: setup, doctor, resolve, update, restore.
- [Hosts](docs/hosts.md): register, refresh, isolation, host-specific settings.
- [History](docs/history.md): read transcripts as evidence.
- [Standards](standards/): Code, Research, Writing, Visual design, Data analysis; `standards/code/api.md` specializes Code.

Renamed: `delegate-work` → `orch-work`, `delegate-review` → `orch-review`, `build-workflow` → `orch-build-workflow`. Removed: `make-and-review`, `compare-approaches`, `parallel-build`, `record-run`, `setup-library`, `run start`/`finish`.
