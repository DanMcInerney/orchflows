# Social Search

A portable user library for bounded, cited research across selected sites. The coordinator gives independent source workers separate allowances and output directories, joins their evidence, then sends it to one fresh judge for global ranking and synthesis. Generic named-site search and saved-evidence ranking also work independently.

## Install and invoke

Use orchflows-light 0.3.0 or a compatible core exposing `setup`, `resolve`, `run start` and `run finish`. Bootstrap requires Python 3.11+ and creates a home virtual environment; this library declares no third-party Python dependencies. Its optional acquisition backend uses only Python 3.9+ standard-library features and runs with the home interpreter.

From an available core package, invoke `scripts/orchflows.py setup --example social-search` with Python 3.11+. The default destination is `~/.orchflows/libraries/social-search`; `--home` or `ORCHFLOWS_HOME` selects another home. Setup seeds the complete example only when that library is absent. It preserves user changes and does not register a native plugin. See the shared [home/runtime reference](references/home-runtime.md) for exact installed paths, dependency lookup, restored-home prerequisites and run ownership.

This directory is the portable source package. Root `plugin.json` carries its identity; `.codex-plugin/plugin.json` supports Codex and `.claude-plugin/plugin.json` supports Claude Code over the same eleven `skills/` folders. Register this complete package with the actual host's native plugin flow. Home libraries are not discovered merely by being placed on disk. Native hosts may cache copies; refresh/reinstall and start a fresh session after edits, checking the loaded path. Keep the home library authoritative and preserve its changes when adopting a newer example.

Public identity is `social-search:<skill-name>`. Codex can select `$social-search:social-search` or a component through its native skill UI; Claude uses `/social-search:social-search` when installed. Native skill syntax differs from the core CLI's package identity. An agent with file access can resolve and load the concrete entrypoint through `resolve social-search --skill social-search`, then use the same package resources from an unrelated project without reading a source checkout.

## Components and flow

```text
social-search (current orchestrator; one outer run)
  -> selected source workers, concurrent within capacity and source limits
       source profile -> search-site
                         -> prepare-evidence before/after collection
                         -> native public reads or optional research-acquire
  -> join actual results, including explicit gaps
  -> rank-research (one fresh judge; owns HTML criteria)
  -> optional one targeted continuation of original workers and same judge
```

| Skill | Public task |
| --- | --- |
| [social-search](skills/social-search/SKILL.md) | Select sources, allocate shared bounds, coordinate workers and judge, finalize its outer run. |
| [search-site](skills/search-site/SKILL.md) | Search any named site/domain and return locally ranked evidence. |
| [search-reddit](skills/search-reddit/SKILL.md) | Reddit threads and actual comment context. |
| [search-youtube](skills/search-youtube/SKILL.md) | Video/transcript evidence and selected comments. |
| [search-x](skills/search-x/SKILL.md) | X posts, account statements and conversation context. |
| [search-hacker-news](skills/search-hacker-news/SKILL.md) | HN stories and actual participant comments. |
| [search-github](skills/search-github/SKILL.md) | GitHub issues, releases, discussions and implementation evidence. |
| [search-polymarket](skills/search-polymarket/SKILL.md) | Contracts, prices and resolution terms matched to the requested horizon. |
| [prepare-evidence](skills/prepare-evidence/SKILL.md) | Prepare/check the handoff in the current worker, without extra agents or reads. Owns the [evidence contract](skills/prepare-evidence/references/evidence-contract.md). |
| [rank-research](skills/rank-research/SKILL.md) | Judge saved evidence, deduplicate and rank globally; write synthesis, evidence-only output or [offline HTML](skills/rank-research/references/html-dossier.md). |
| [research-acquire](skills/research-acquire/SKILL.md) | Optional bounded discovery, semantic selection and resumed depth acquisition with receipts. |

The core dependencies are native delegation through `orchflows-light:delegate-work`, Research and Writing standards, and native-host guidance, resolved once through the installed CLI. `delegate-review` is optional for an explicitly requested separate review. Source profiles, preparation and ranking run in their assigned current context without spawning children. The coordinator requires a host with native child agents; if that capability is missing, report the gap. Individual components remain usable.

## Inputs, outputs and composition

An ordinary request supplies the question, intended use, sources, publication/event window or explicit all-time, any separate information cutoff/forecast horizon, required depth and output. Resolve material timeframe ambiguity; there is no default thirty-day window. A composition also passes concrete resolved package/core/runtime paths, one parent run context, separate worker output paths, and allocated retrieval/result/time limits. Workers reuse that context and never start duplicate logs.

Default output is a concise ranked cited report with synthesis. Ask for evidence-only output or a single offline HTML file when useful. Source workers write `results.md` with stable IDs, original locators, inspectable support, dates/unknowns and coverage limitations. Prepare-evidence checks those actual materials; the judge independently assesses support and does not rerun preparation on compatible handoffs. Ranking saved evidence requires no new acquisition. Arbitrary named-domain work can use search-site directly without adding a profile; another workflow can combine any of these skills.

An independent invocation owns one home run; nested calls reuse the parent's. Default artifacts live under that run, while explicit project output paths are honored and referenced in its compact summary. The run record and summary are trackable; raw responses and bulk artifacts are ignored by default. Preserve required evidence separately when sharing history. Instructions never write generated output into this source library.

## Limits and validation

Native public tools are the default. Their calls are not measured backend network attempts, and installed routes do not promise live access. Use research-acquire only when its supported reads or deterministic per-plan caps, receipts and resume are needed. It cannot enforce a single budget across independent plans without caller allocation; shared-origin plans need serialization. Refusals, missing depth, unknown counts, incomplete window reach and unavailable historical observations remain explicit gaps. A valid packet or empty result does not establish research completeness.

One targeted evidence follow-up is allowed within remaining authority and bounds. Source workers do not draft competing final reports. The judge is independent of collection; its prose has no additional independent review unless requested. Required gaps prevent full completion even when a qualified answer is useful.

The [bounded forward trial](trials/request.md) and [acceptance criteria](trials/expected-behavior.md) cover ordinary-project use, overlap, evidence and logging. They are a trial specification, not a claim that a native run passed. [Provenance and checks](references/provenance.md) describes the preserved MIT backend, offline checks and their limits. Keep executable acquisition scripts, adapters and fixtures unchanged when editing workflow instructions unless intentionally undertaking a separate backend change.
