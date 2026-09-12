# Architecture

Every word in a skill, workflow, guidance file or doc fights for its life.

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen guidance.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

Every other agent is launched through these two. The host runs agents; orchflows adds no runtime, scheduler or workflow language. A workflow is a `SKILL.md` that loads other skills into the current context and delegates only through the primitives. A small workflow does one thing behind one entrypoint; a larger one invokes it by name, as a program imports a module, and adds only what is new at its level. Depth is unbounded; every level stays small.

## Where things live

Write the least prescription that produces the result now; each model release lets you delete more.

| Thing | Lives in | Changed by |
| --- | --- | --- |
| question, dates, sources, bounds, output location | the prompt | each request |
| quality criteria for one domain | `guidance/<domain>.md`; `guidance/<domain>.<narrower>.md` narrows it, any depth | model releases |
| composition, control flow, agent count | `SKILL.md` prose | nothing |
| deterministic mechanics: fetch, parse, bound, resume | `skills/<skill>/scripts/` of the owning library, tests beside them; core `scripts/` for the CLI | the mechanism |
| source knowledge | a library `guidance/` file narrowing a core name; operational notes in `references/` | the source |
| host facts | [hosts.md](hosts.md) | host releases |
| built-ins | core `skills/orch-*/`; that name is reserved | orchflows developers |
| custom workflows | `~/.orchflows/libraries/<lib>/skills/<workflow>/`; `personal` unless the caller names a library or repository | the user |
| outputs | the caller's workspace, never a package | each run |

A guidance file has `## Make` and `## Review` sections, matching orch-work and orch-review, either omitted when empty. The guidance for a name is every existing file named by that name or a dot-shortened form of it, in core `guidance/` then the library's, read general to specific with the more specific winning where they differ: `research.search-site.reddit` reads `research.md`, `research.search-site.md` and `research.search-site.reddit.md`, skipping any that do not exist. One-off criteria stay in the prompt. Defaults belong to the caller: no default window, source, model, effort or path.

## Three roots

| Root | Owner | Holds |
| --- | --- | --- |
| Core checkout | orchflows developers | `skills/`, `guidance/`, `docs/`, `scripts/`, `tests/`, `example-workflows/` |
| Home `~/.orchflows` | the user | `libraries/`, managed core, runtime: [home.md](home.md) |
| Project workspace | the task | outputs |

The managed core is the checkout minus `tests/` and `example-workflows/`; core `.md` files never link into those. Developers edit the checkout, run `python -m unittest discover -s tests`, load it as a plugin ([hosts.md](hosts.md)) and run its `setup` to update a home.

## A library

```text
<library>/
├── plugin.json  .claude-plugin/plugin.json  .codex-plugin/plugin.json   name, version, "skills": "./skills/"
├── README.md                        composition diagram, agent count, install, dependencies
├── references/                      context shared by several skills
├── guidance/<domain>.<narrower>.md  narrows core guidance by name
├── skills/<skill>/SKILL.md          frontmatter name + description, then prose
├── skills/<skill>/references/       knowledge only that skill loads
├── skills/<skill>/scripts/          mechanics that skill runs; tests/ beside them
└── trials/                          request.md, expected-behavior.md
```

Identity is `<library>:<skill>`. Links stay inside the package; other packages are reached by native skill name or a path resolved once at the outer boundary, after which children receive absolute paths. No checkout, home, cache or project path is written into a package. Setup installs no dependencies.

## Reference: social-search

`example-workflows/social-search/README.md`. Leaves launch one primitive each: `search-site` one orch-work, `rank-evidence` one orch-review. The coordinator invokes leaves and owns the agent count. Site knowledge is guidance; the handoff format is the shared `research.search-site.md`; the transcript reader is a script in the library that owns it. Loading a skill in context replaces a coordinating agent.

## Invariants

- A skill names a script, its inputs and its result, never its internals.
- Declare the agent count; extra reviews, loops or repairs only when the request asks.
- Gaps stay visible; missing work is never no-results evidence.
- Behavior is established by a trial on a real bounded request, not by valid frontmatter. [orch-build-workflow](../skills/orch-build-workflow/SKILL.md) imports existing leaves, writes missing ones, then a coordinator, then deletes every instruction the trial did not need.
