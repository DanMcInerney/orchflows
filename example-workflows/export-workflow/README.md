# Export Workflow

`/export-workflow` converts an Orchflows workflow into a standalone native skill folder. It bundles selected guidance and dependencies, replaces core primitive calls with native host delegation, and reports behavior that cannot be preserved. The resulting skill runs without an Orchflows installation; native tools, source access and language runtimes can remain prerequisites.

After installing this library, invoke `export-workflow:export-workflow` with a workflow path or library/skill identity, destination and optional target host:

> Export social-search:social-search for Codex into exports/social-search, retaining all supported source scopes. Test its live search on uv adoption friction in GitHub and Hacker News.

The [workflow](skills/export-workflow/SKILL.md) creates the folder in the caller's context, delegates one bounded trial through `orch-work`, then obtains one independent `orch-review`. It permits one repair pass and one affected retrial. This normally uses two fresh children, at most three, plus the exported workflow's declared children for each trial. The [export contract](skills/export-workflow/references/export-contract.md) owns preservation rules and validation limits.

The trial exercises the source's primary capability with available, authorized tools. Live retrieval requires discovery and source inspection; fixtures alone establish only the offline path. Parallel collection, independent review, loops and supported model controls remain in the export. Shared guidance becomes a snapshot, helper entrypoints may be flattened, and updates require re-export. A single-file or single-agent export is a separate constraint that can require disclosed losses.

## Install and dependencies

From a complete Orchflows checkout, run `python scripts/orchflows.py setup --example export-workflow` with Python 3.11+. Setup preserves an existing library. Register and install `export-workflow` from the resulting home catalog using core `docs/hosts.md`; setup alone does not make it available by name. The workflow is manual-only on Codex and Claude Code. Its native names are `$export-workflow:export-workflow` in Codex and `/export-workflow:export-workflow` in Claude Code.

Requires Orchflows 0.7.0+, native child delegation, filesystem access, the source workflow and its selected dependencies, and tools needed for the bounded trial. [Library context](references/library-context.md) resolves these package dependencies. Creating an export does not install or register that exported skill.

[Trial requests](trials/request.md) and [acceptance criteria](trials/expected-behavior.md) support repeatable validation; they are not proof that every workflow, site or host has been tested.
