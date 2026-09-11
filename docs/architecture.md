# Architecture

Every word in a skill, workflow, standard or doc fights for its life.

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen standards.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

Every other agent is launched through these two. The host runs agents; orchflows adds no runtime, scheduler or workflow language. A workflow is a `SKILL.md` that loads other skills into the current context and delegates only through the primitives. A small workflow does one thing behind one entrypoint; a larger one invokes it by name, as a program imports a module, and adds only what is new at its level. Depth is unbounded; every level stays small.

## Where things live

Write the least prescription that produces the result now; each model release lets you delete more.

| Thing | Lives in | Changed by |
| --- | --- | --- |
| question, dates, sources, bounds, output location | the prompt | each request |
| quality criteria for one lens | `standards/<lens>.md`; `standards/<lens>/<sub>.md` specializes it | model releases |
| composition, control flow, agent count | `SKILL.md` prose | nothing |
| deterministic mechanics: fetch, parse, bound, resume | `skills/<skill>/scripts/` of the owning library, tests beside them; core `scripts/` for the CLI | the mechanism |
| source knowledge | a profile skill or `references/` | the source |
| host facts | [hosts.md](hosts.md) | host releases |
| built-ins | core `skills/orch-*/`; the prefix is reserved | orchflows developers |
| custom workflows | `~/.orchflows/libraries/<lib>/skills/<workflow>/`; `personal` unless the caller names a library or repository | the user |
| outputs | the caller's workspace, never a package | each run |

A workflow that needs prose deleted after a model release was over-specified. A standard is one lens with Doing and Reviewing sections, matching orch-work and orch-review; a specialization opens with `Extends:` and is passed with its parent. One-off criteria stay in the prompt. Defaults belong to the caller: no default window, source, model, effort or path.

## Three roots

| Root | Owner | Holds |
| --- | --- | --- |
| Core checkout | orchflows developers | `skills/`, `standards/`, `docs/`, `scripts/`, `tests/`, `example-workflows/` |
| Home `~/.orchflows` | the user | `libraries/`, managed core, runtime: [home.md](home.md) |
| Project workspace | the task | outputs |

The managed core ships root files, `skills/`, `standards/`, `docs/` and `scripts/`; core `.md` files never link into `tests/` or `example-workflows/`. Developers edit the checkout, run `python -m unittest discover -s tests`, load it as a plugin ([hosts.md](hosts.md)) and run its `setup` to update a home.

## A library

```text
<library>/
├── plugin.json  .claude-plugin/plugin.json  .codex-plugin/plugin.json   name, version, "skills": "./skills/"
├── README.md                        composition diagram, agent count, install, dependencies
├── references/                      context shared by several skills
├── skills/<skill>/SKILL.md          frontmatter name + description, then prose
├── skills/<skill>/references/       knowledge only that skill loads
├── skills/<skill>/scripts/          mechanics that skill runs; tests/ beside them
└── trials/                          request.md, expected-behavior.md
```

Identity is `<library>:<skill>`. Links stay inside the package; other packages are reached by native skill name or a path resolved once at the outer boundary, after which children receive absolute paths. No checkout, home, cache or project path is written into a package. Setup installs no dependencies.

## Reference: social-search

`example-workflows/social-search/`, or `~/.orchflows/libraries/social-search/` after setup. N sources → N workers + 1 reviewer.

- Leaf: `search-site` launches one `orch-work` for any named site; `rank-evidence` launches one `orch-review` over supplied evidence; `prepare-evidence` shapes the handoff inside the worker. Leaves work alone.
- Profile: `search-reddit` … `search-polymarket` invoke `search-site` with a few sentences of source knowledge, never control flow or an agent.
- Coordinator: `social-search` chooses profiles, fans out, gathers, invokes `rank-evidence` once; it owns the agent count and repeats nothing a leaf says. Loading a skill in context replaces a coordinating agent.
- Script: `research-acquire` `inspect_source.py` owns transcript fetch, parse, fallback and bounds; `references/source-readers.md` resolves it by package resource.

The files carry the remaining patterns: `references/library-context.md` resolves dependencies once, and skills that need it open "Reuse or establish library context"; `search-site` returns a handle when the caller gathers, else awaits, and quotes the worker's assignment ending "Work without child agents"; `trials/` holds a real bounded request and observable acceptance.

## Invariants

- A skill names a script, its inputs and its result, never its internals.
- Declare the agent count; extra reviews, loops or repairs only when the request asks.
- Gaps stay visible; missing work is never no-results evidence.
- Behavior is established by a trial on a real bounded request, not by valid frontmatter. [orch-build-workflow](../skills/orch-build-workflow/SKILL.md) imports existing leaves, writes missing ones, then a coordinator, then deletes every instruction the trial did not need.
