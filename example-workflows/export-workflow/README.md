# Export Workflow

**Your best workflow, ready to travel.**

Turn an orchflows workflow into a standalone native skill folder that runs without orchflows installed. Export Workflow gathers the selected guidance, scripts and dependencies, translates orchestration into native host delegation and writes down anything it cannot preserve.

Use it to hand a useful workflow to a teammate, carry it into another host or keep a portable snapshot of a setup you want to reuse. The export keeps runtime inputs configurable, so the next person can give it their own task.

## Try it

After installation, paste into Codex:

```text
$export-workflow:export-workflow
Export social-search:social-search for Codex into ./exports/social-search,
retaining all supported source scopes. Test its live search on uv adoption
friction in GitHub and Hacker News. Include the portability report and
identify any behavior the standalone version cannot preserve.
```

In Claude Code, use `/export-workflow:export-workflow` with the same request. This workflow is manual-only by default on both hosts. The example requires the source `social-search` library and authorized access to its search tools.

Give it a workflow path or library/skill identity, a destination and an optional target host. It defaults to the current host and `exports/<skill-name>/` in your workspace. The source stays untouched; an occupied destination gets a new location unless you asked to update that export.

## Pack it. Try it. Review it.

The [workflow](skills/export-workflow/SKILL.md) creates the export in the caller's context, then tests whether it can stand on its own:

1. **Follow the dependencies.** Read the reachable workflows, guidance, references, scripts and assets. Bundle what the skill needs, preserve licenses and rewrite paths.
2. **Preserve the behavior.** Translate core work/review calls into native delegation, retaining the workflow's supported decisions, deliberate process counts, handoffs, stopping conditions and caller constraints.
3. **Try it elsewhere.** Give a fresh top-level trial session the exported folder, ordinary inputs and declared prerequisites in an unrelated disposable workspace. Record interventions and anything the trial could not exercise.
4. **Get an independent verdict.** A new reviewer compares the source, export and trial evidence without making repairs. Make at most one repair pass and, if behavior changed, one affected retrial. There is no second review.

Trial the export under its own orchestration, then independently review source fidelity and observed behavior. One repair pass and an affected retrial may follow; no second review is implied.

A live-search workflow gets a live discovery-and-source-inspection trial when authorized tools are available. Fixtures establish only the offline path. Missing capabilities remain explicit validation gaps; a bounded successful trial does not establish every branch, site or host.

## What travels with it

| Source feature | Standalone result |
| --- | --- |
| Selected layered guidance | A bundled snapshot preserving precedence and Make/Review roles. |
| Work, independent review, parallel collection and handoffs | Native delegation preserving supported composition and ownership. |
| Loops, repairs and model/effort controls | The source's bounds and supported settings, with unsupported controls disclosed. |
| Helper workflows, references, scripts and assets | Local dependencies and paths; helper entrypoints may be flattened. |
| Tools, runtimes and authentication | Declared external prerequisites; export does not provision them. |

You receive one installable skill folder and a sibling report naming source revision or hashes, selected libraries and guidance order, target host, bundled dependencies, external requirements, behavior changes and validation limits. Trial outputs and the report stay outside the installable folder. Unresolved required behavior makes the deliverable incomplete.

The [export contract](skills/export-workflow/references/export-contract.md) defines the preservation rules. A single-file or single-agent export is an extra constraint that can require disclosed losses. Source updates require re-export. Installing and registering the exported skill is a separate step.

## Install and requirements

From a complete orchflows core checkout, with Python 3.11+:

```sh
python scripts/orchflows.py setup --example export-workflow
```

Setup copies the example into your orchflows home and preserves an existing library copy. Follow core `docs/hosts.md` to register and install `export-workflow@orchflows-home`, then start a new session. Setup alone does not make the workflow available by name.

Requires orchflows 0.10.0+, native child delegation, filesystem access, the source workflow and its selected dependencies, and the tools needed for the bounded trial. [Library context](references/library-context.md) resolves package dependencies. Setup installs no library runtime dependencies.

The [trial requests](trials/request.md) and [acceptance criteria](trials/expected-behavior.md) support repeatable validation; they are not proof that every workflow, site or host has been tested.
