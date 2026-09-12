# Architecture

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen guidance.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

All delegation goes through these primitives. The host owns agent execution; orchflows adds no runtime, scheduler or workflow language. Loading a `SKILL.md` applies its instructions in the caller's context; it does not launch an agent. Composing workflows add only their own decisions and supply each child's assignment and context.

Choose planning, delegation and isolation from unknowns, dependencies and edit conflicts. Run independent work concurrently.

## Where things live

Give each instruction and mechanism one owner; reference shared facts. READMEs address humans; other live documentation addresses agents.

| Concept | Owner / location |
| --- | --- |
| Request and defaults: question, dates, sources, bounds, model, effort, output location | Caller prompt |
| Coordination: composition, control flow, agent count | Composing workflow's `SKILL.md` |
| Quality criteria, including source-specific preferences | `guidance/<domain>.md` |
| Shared contracts and operational knowledge | Library `references/`; skill-local `references/` for one consumer |
| Package dependencies and guidance requirements | `references/library-context.md`, reused by entrypoints |
| Resolved paths and request context | Outermost entrypoint; pass through composed calls |
| Deterministic mechanics | Owning skill's `scripts/`, with sibling `tests/`; core CLI in `scripts/` |
| Package identity | Root `plugin.json` |
| Native skill discovery | Host manifests and catalogs per [hosts.md](hosts.md) |
| Host registration, execution and isolation facts | [hosts.md](hosts.md) |
| Setup, updates and home paths | [home.md](home.md) |
| Transcript access and interpretation | [history.md](history.md) |
| Run outputs and evidence | Caller workspace, never a package |

## Guidance selection

Guidance records domain preferences in `## Make` and `## Review`; omit empty sections. Apply Make when producing and Review when assessing. Workflows name required domains; select `orchflows` for authoring workflows, guidance or libraries. A domain being extended is source material for its author.

Resolve once at the outer entrypoint, including a leaf invoked alone:

1. Select independent domain names, such as `writing`, `visual-design`, `short-video.marketing`.
2. For each name, visit dotted prefixes from general to specific. At each prefix, read core then selected libraries in caller-supplied order. Example: `short-video` across packages, then `short-video.marketing` across packages.
3. Keep each resolved file once, in first-use order. More specific guidance wins within its domain; independent domains compose.
4. Missing implicit parents are allowed; library-only domains are valid. An explicit selection must exist in core or a selected library; report a gap and block dependent work otherwise. Use general guidance for unfamiliar sites or genres.
5. Resolve package dependencies through native skills, supplied roots or the [home CLI](home.md#resolve). Pass absolute paths and request context unchanged to composed skills and primitives; extend only for new dependencies.

Selected libraries may supply removable model corrections under existing domain names. Normal specificity applies; model names are not domain specializations.

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
├── plugin.json                     name, version, skills: "./skills/"
├── .claude-plugin/plugin.json      Claude manifest
├── .codex-plugin/plugin.json       Codex manifest
├── README.md                       composition, agent count, install, dependencies
├── references/                     shared context and contracts
├── guidance/<domain>.md            domain or dotted specialization
├── skills/<skill>/SKILL.md          frontmatter name + description; instructions
├── skills/<skill>/references/       knowledge used by this skill only
├── skills/<skill>/scripts/          mechanics; sibling tests/
└── trials/                         request.md, expected-behavior.md
```

Skill identity is `<library>:<skill>`. Keep links within the package; reach other packages by native skill name or resolved paths. Never embed machine-specific paths. Declare runtime dependencies in the README; setup installs none for libraries.

## Invariants

- Skills name scripts, inputs and results; scripts own their internals.
- Declare agent counts; extra reviews, loops or repairs require a caller request.
- Report missing work as a gap, never as no-results evidence.
- Establish behavior with a real bounded trial. Valid frontmatter proves no behavior; unexercised failure paths remain untested.
