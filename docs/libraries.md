# Authoring libraries

Apply [architecture](architecture.md) for composition, guidance and execution. This page owns authoring placement, packaging and maintenance.

## Where things live

Give each instruction and mechanism one owner; reference shared facts. READMEs address humans; other live documentation addresses agents.

| Concept | Owner / location |
| --- | --- |
| Request and defaults: question, dates, sources, bounds, model, effort, output location | Caller prompt; [model and effort](architecture.md#model-and-effort) covers saved preferences |
| Saved process: dependencies, independence, gates, repetition, stopping conditions and allowed effects | Composing workflow's `SKILL.md` |
| Actual assignments, concurrency, ownership and integration | Caller applying the execution rules |
| Quality criteria, including source-specific preferences | `guidance/<domain>.md` |
| Shared contracts and operational knowledge | Library `references/`; skill-local `references/` for one consumer |
| Package dependencies and guidance requirements | `references/library-context.md`, reused by entrypoints |
| Resolved paths and request context | Resolve once; pass applicable context and extend it within each composed call's scope |
| Deterministic mechanics | Owning skill's `scripts/`, with sibling `tests/`; core CLI in `scripts/` |
| Package identity | Root `plugin.json` |
| Native skill discovery | Host manifests and catalogs per [hosts.md](hosts.md) |
| Host registration, execution and isolation facts | [hosts.md](hosts.md) |
| Setup, updates and home paths | [home.md](home.md) |
| Transcript access and interpretation | [history.md](history.md) |
| Run outputs and evidence | Caller workspace, never a package |

## Three roots

| Root | Contents / editing owner |
| --- | --- |
| Core checkout | Built-in `skills/orch-*/`, guidance, docs, CLI, tests, example libraries; orchflows developers |
| Home `~/.orchflows` | User-owned libraries and runtime; setup-managed core per [home.md](home.md) |
| Project workspace | Task outputs |

Reserve `orch-` for built-ins. Create custom workflows in `~/.orchflows/libraries/personal/skills/<workflow>/` unless the caller names another library or repository. Edit the checkout or user library, never managed core or host caches.

Setup's `CORE_ENTRIES` in `scripts/orchflows.py` owns the shipped file list. Tests and example libraries stay in the checkout; core Markdown links must resolve within the shipped core. To update core: edit the checkout, run `python -m unittest discover -s tests`, then [load it for development](hosts.md#register-and-refresh) or [run setup](home.md#setup) to update a home.

## A library

```text
<library>/
├── plugin.json                     package identity; Antigravity manifest
├── .claude-plugin/plugin.json      Claude, Grok Build and ZCode manifest
├── .codex-plugin/plugin.json       Codex manifest
├── .kimi-plugin/plugin.json        Kimi Code manifest
├── README.md                       composition, stopping rules, dependencies
├── references/                     shared context and contracts
├── guidance/<domain>.md            domain or dotted specialization
├── skills/<skill>/SKILL.md          frontmatter, invocation policy; instructions
├── skills/<skill>/agents/openai.yaml Codex invocation policy and UI metadata
├── skills/<skill>/references/       knowledge used by this skill only
├── skills/<skill>/scripts/          mechanics; sibling tests/
└── trials/                         request.md, expected-behavior.md
```

Skill identity is `<library>:<skill>`; [host invocation syntax](hosts.md#invocation-policy) can differ. Keep links within the package; reach other packages by native skill name or resolved paths. Never embed machine-specific paths. Declare runtime dependencies in the README; setup installs none for libraries. Root `plugin.json` declares `name`, `version` and `skills: "./skills/"` and also serves Antigravity. Keep the name and version aligned across host manifests; Kimi's manifest declares `skills: "./skills/"`. Existing user libraries need that manifest before installation in Kimi.

A reusable component declares inputs, dependencies, process, allowed effects, outputs and stopping conditions. Domain components stay in their libraries; optional shared libraries own cross-domain processes. Core remains independent of them.

## Invariants

- Skills name scripts, inputs and results; scripts own their internals.
- Establish behavior with a real bounded trial. Valid frontmatter proves no behavior; unexercised failure paths remain untested.
