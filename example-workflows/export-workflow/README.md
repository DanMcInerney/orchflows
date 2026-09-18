# Export Workflow

Turn an Orchflows workflow into a standalone native skill folder. Bundle selected guidance, scripts and dependencies; translate orchestration to host-native delegation and report anything that cannot be preserved. Runtime inputs remain configurable for the next task.

## Try it

```text
$export-workflow:export-workflow
Export social-search:social-search for Codex into ./exports/social-search.
Preserve supported source scopes and configurable runtime inputs. Trial it
with synthetic search/source fixtures and simulated external effects.
Include a portability report identifying changes and validation gaps.
```

Claude Code: `/export-workflow:export-workflow`. This skill is manual-only by default. Supply a source path or library/skill identity and optional host/destination; defaults are the current host and `exports/<skill-name>/`. Source files stay untouched. Existing destinations are preserved unless updating was requested.

## Export and validate

1. Resolve reachable workflows, guidance, references, scripts/assets and prerequisites; bundle dependencies once, preserve licenses and rewrite paths.
2. Preserve supported decisions, delegation, independence, scoped guidance/settings, handoffs and stopping bounds.
3. Trial the relocated export in a fresh top-level session with only the export, ordinary synthetic inputs and declared prerequisites. Simulate external effects under core's workflow-trial contract; record interventions and untested integrations.
4. Independently review source fidelity and trial evidence. Allow one repair pass and, for changed behavior, one affected retrial; no second review.

Authoring trials establish simulated behavior, not live integration. This limits validation, not the exported workflow's authorized production capabilities.

Delivery is one installable folder plus a sibling report: source revision/hashes, selected libraries/guidance order, host, bundled dependencies, external prerequisites, behavior changes, review/delivered identities and validation limits. Outputs/report stay outside the installable folder. Unresolved required behavior makes the export incomplete.

The [export contract](skills/export-workflow/references/export-contract.md) defines fidelity. Tools, runtimes and authentication remain prerequisites; export provisions none. Single-file or single-agent constraints can require disclosed losses. Source updates need re-export; installation/registration is separate.

## Install

From a complete Orchflows checkout with Python 3.11+:

```sh
python scripts/orchflows.py setup --example export-workflow
```

Setup preserves existing library copies and installs no runtime dependencies. Follow core `docs/hosts.md` for registration/installation and start a new session; verify availability by name.

Requires core 0.11.0+ including `orch-review-revise-once`, native child delegation, filesystem access, source workflow/dependencies and bounded-trial tools. See [library context](references/library-context.md), [trial request](trials/request.md) and [acceptance](trials/expected-behavior.md); trial plans are not observed results.
