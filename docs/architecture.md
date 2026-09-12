# Architecture

Every word in a skill, workflow, guidance file or doc fights for its life.

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen guidance.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

Every other agent is launched through these two. The host runs agents; orchflows adds no agent runtime, scheduler or workflow language. A workflow is a `SKILL.md` that loads other skills into the current context and delegates through the primitives. A larger workflow composes smaller ones and adds only what it owns. Loading another skill does not launch another coordinator.

## Where things live

Write the least prescription that produces the result now; each model release lets you delete more.

| Thing | Lives in | Owner |
| --- | --- | --- |
| question, dates, sources, bounds, output location | the prompt | caller |
| quality criteria for one domain | `guidance/<name>.md` | domain guidance |
| composition, control flow, agent count | `SKILL.md` prose | the workflow composing those calls |
| package dependencies, guidance selection, resolved paths | the library's `references/library-context.md`, reused by its entrypoints | outermost package entrypoint |
| deterministic mechanics: fetch, parse, bound, resume | `skills/<skill>/scripts/`, tests beside them; core `scripts/` for the CLI | the library providing the mechanism |
| source knowledge | library guidance; operational notes in `references/` | the library using that source |
| host facts | [hosts.md](hosts.md) | core host documentation |
| built-ins | core `skills/orch-*/`; that name is reserved | orchflows developers |
| custom workflows | `~/.orchflows/libraries/<lib>/skills/<workflow>/`; `personal` unless the caller names a library or repository | the user |
| outputs | the caller's workspace, never a package | each run |

One-off criteria stay in the prompt. Defaults belong to the caller: no default window, source, model, effort or path.

## Guidance selection

A guidance file has `## Make` and `## Review` sections, either omitted when empty. The maker and reviewer read and apply their respective sections. This section owns the selection rule; workflows name the domains they need.

Select independent names, for example `writing`, `visual-design`, `short-video.marketing`. Dots specialize within a domain: for each name, visit its prefixes from general to specific, reading core then the selected libraries in caller-supplied order at each specificity. Thus `short-video.marketing` considers `short-video.md` before `short-video.marketing.md` in each package's `guidance/`. Library-only domains are valid. More specific guidance wins within its domain; independent domains compose without replacing one another. Keep each resolved file once, in first-use order.

Missing implicit parents are fine. An explicitly selected name must exist in at least one selected package; report a missing selection as a gap and block work that requires it. For an unfamiliar site or genre, select applicable general guidance instead of inventing a missing specialization.

Resolve these files and package dependencies once at the outer entrypoint, including a leaf invoked alone. Use available native skills or supplied package roots; a configured home also provides [CLI resolution](home.md). Pass concrete absolute paths and request context to composed skills and primitives. Reuse that context; extend it only for newly introduced dependencies. Profiles may supply additional names and package roots. No guidance inheritance graph or repeated resolution is needed in children.

## Three roots

| Root | Owner | Holds |
| --- | --- | --- |
| Core checkout | orchflows developers | `skills/`, `guidance/`, `docs/`, `scripts/`, `tests/`, `example-workflows/` |
| Home `~/.orchflows` | the user | `libraries/`, managed core, runtime: [home.md](home.md) |
| Project workspace | the task | outputs |

The managed core contains the root manifest, native plugin directories, `README.md`, `AGENTS.md`, `CLAUDE.md`, `LICENSE`, and `skills/`, `guidance/`, `docs/`, `scripts/`. Setup's `CORE_ENTRIES` owns that explicit packaging list. Tests and example libraries remain in the checkout; core Markdown links stay within the shipped core. Developers edit the checkout, run `python -m unittest discover -s tests`, load it as a plugin ([hosts.md](hosts.md)) and run its `setup` to update a home.

## A library

```text
<library>/
├── plugin.json  .claude-plugin/plugin.json  .codex-plugin/plugin.json   name, version, "skills": "./skills/"
├── README.md                        composition diagram, agent count, install, dependencies
├── references/                      context shared by several skills
├── guidance/<name>.md              domain or dotted specialization
├── skills/<skill>/SKILL.md          frontmatter name + description, then prose
├── skills/<skill>/references/       knowledge only that skill loads
├── skills/<skill>/scripts/          mechanics that skill runs; tests/ beside them
└── trials/                          request.md, expected-behavior.md
```

Identity is `<library>:<skill>`. Links stay inside the package; other packages are reached by native skill name or resolved paths. Do not bake machine-specific checkout, home, cache or project paths into a package. Declare runtime dependencies in its README; setup installs no library dependencies.

## Reference: social-search

The optional `example-workflows/social-search` library has three skills: `search-site` launches one orch-work, `rank-evidence` one orch-review, and `social-search` composes them. Site knowledge and the evidence handoff belong to its `research.search-site` guidance. Optional transcript acquisition belongs to the separate `research-acquire` library. The installed core has five skills; example libraries are separate packages, not built-ins.

## Invariants

- A skill names a script, its inputs and its result, never its internals.
- Declare the agent count; extra reviews, loops or repairs only when the request asks.
- Gaps stay visible; missing work is never no-results evidence.
- Behavior is established by a trial on a real bounded request, not by valid frontmatter. [orch-build-workflow](../skills/orch-build-workflow/SKILL.md) composes existing skills, authors what is missing and simplifies from observed behavior. An unexercised failure path is untested, not evidence that its handling is unnecessary.
