# orchflows

![orchflows](docs/banner.png)

A skill library that turns Claude Code, Codex or Grok Build into an
orchestrator: subagents that work in parallel, real verification of
everything they produce, and workflows that improve themselves. You
just talk; it picks the right workflow.

## Install

    git clone https://github.com/DanMcInerney/orchflows
    cd orchflows
    ./install.sh          # install.cmd on Windows

Works with Claude Code, Codex and Grok Build, on Windows, macOS, and
Linux. It configures whichever CLI it finds. To update: `git pull`,
rerun.

Each host keeps its own user-scope surface under its own home, and each
home has an override the installer follows: `CLAUDE_CONFIG_DIR`,
`CODEX_HOME`, `GROK_HOME`. Grok Build's is skills at
`~/.grok/skills/<name>/SKILL.md`, role agents in `~/.grok/agents/`, a
`[subagents]` block merged into `~/.grok/config.toml`, and the always-on
instruction layer as one whole installer-owned file,
`~/.grok/rules/orchflows.md`.

This is a user install, the only installation scope. It creates or reuses
`~/.orchflows/runtime`, a private Python
environment used by installed commands even when installation starts from
an active project environment. Runtime dependencies are declared in
`requirements-runtime.txt`, with exact hashes for the local UI server and its
transitive closure.
Dry runs create nothing, and user uninstall retains the private runtime for
explicit manual cleanup.

## Observe

The local UI shows the current workflow graph without changing it. From a
checkout, start it with `uv run --no-project python scripts/ui.py`; an installed
copy runs through the private Python environment. It binds only to
`127.0.0.1`, serves its prebuilt assets offline, and exposes metadata rather
than prompts, tool output, or transcript contents. See the
[UI platform](docs/ui/platform.md) for installed commands, routes, security
boundaries, and the split between this platform and the dark-mode visual
experience that follows it.

## Use

Ask for things like you normally would. There are no skill names to
memorize.

    > why did memory double last release?
    # a cited answer from a read-only research lane

    > ship dark mode
    # one root ticket that cuts itself into tickets, parallel
    # subagents, one review gate, and a final verification against
    # what you asked for

    > fix the flaky login test
    # reproduce it, prove the cause, repair it, guard the repair

    > research the top three auth libraries, then integrate the winner
    # two root tickets, the second waiting on the first, automatically

Small requests stay small; medium and large work earn structure only when
their graph does. Those sizes are explanatory, never fields on the work.
Nothing marks "done" except an external check passing.

## More ways to use it

Routing projects four shapes: `answer` when evidence already decides,
`single` for one ordinary ticket, `graph` for a frozen root that needs
decomposition, and `spec` when that root must first be settled. Known-cause
work enters the smallest of those shapes; an unknown-cause failure uses fix.
Everything else runs only when you name it, so the routing table never
grows as the library does. The table is installed at
`~/.orchflows/host-block.md`, the one surface every turn already pays
for; `rules/topology.md` §2 owns what may enter it. If routing gets in
the way, `orch-off` stands it down for the session.

Name the bricks yourself when you want a specific shape:

    > orch-loop the build until `pytest -q` exits 0
    > orch-critique this cache design — rank what it gets wrong
    > evolve this blog post — no benchmark, derive a blind judge panel
    > evolve the summarizer prompt against the frozen benchmark

Or build your own workflow in plain English:

    > build me a workflow that researches, then builds, then always
      updates the documentation afterwards (favoring edits and
      deletions over additions), and automatically PRs and merges it

That gets admitted as a named workflow — a directory of ticket stubs
with the edges between them written down and one end-to-end done check
on the last one. It's project-local and callable by name from then on,
like a `/site-work-and-merge` you own; `orch-frontier` runs it.

Runs survive session death: every ticket is a file in one per-user
state sink outside every repository, so a fresh context — in any
checkout — resumes mid-flight. What a ticket is — anatomy, lifecycle,
review, failure handling — is [TICKETS.md](TICKETS.md).

Team setup: each teammate runs the user install. Repository-local custom
skills and compositions are ordinary repository work under
`<repo>/.orchflows`, governed by
[custom workflow authoring](docs/custom-workflow-authoring.md); they are not an installation scope. Uninstall:
`python install.py --user --uninstall` removes only what it generated;
`--dry-run` previews whether runtime apply will create, reuse, or repair.
`--claude-adapters {all,four}` chooses how much of the library
Claude gets first-class adapters for — `all` (the default) mints one per
package and template, `four` mints only `orch-spec`, `orch-frontier`,
and `fix` and leaves every other name to resolve at
`by-name/`. Default model and effort per role, all three hosts:
[profiles.md](skills/engines/orch-frontier/references/profiles.md). Edit
a rendered role agent to run your own; installs ask before replacing it
and keep it by default.

## The interesting parts

### It improves itself

Every run auto-logs its friction — retries, missing inputs,
workarounds — under an always-on law, and `trace.py` extracts each
session's requests, narration and tool calls into one event record.
`orch-self-improve` mines those logs into proposals you accept or
reject, each scoped to where the change lands: your **environment** (a
missing interpreter, a broken tool), your **project** (code or docs
that keep causing friction), or the **workflows** themselves. Real
proposals from my own usage:

- Offload a repeated piece of agent reasoning to a deterministic script
- A tiny AGENTS.md addition pointing agents at the packaged Python
  instead of whatever `python` is on `$PATH`
- Remove overlapping `orch-verify` steps from a workflow to speed it up
- Add a documentation-update step a user kept requesting manually

Chain any bricks and put `orch-self-improve` last and you have a
workflow that upgrades itself:

    > my release workflow: orch-investigate what merged since the last
      tag → a root ticket for the release notes under the content pack
      → orch-self-improve

The coolest part: it runs on itself. I run `orch-self-improve` across
all sessions in a project, then point a second run at the first one.

### Tournaments: evolve and benchmaker

The `benchmaker` composition builds a qualified benchmark for any
target with an observable outcome — a prompt, a skill, a script. The
`evolve` composition then runs a tournament against it:
bounded generations planned deterministically from settled public outcomes,
blind judges, and promotion only when a frozen rule and margin are beaten.
Together they turn "make this
better" into a measured campaign instead of vibes. The dataflow is in
[compositions/benchmaker/template.md](compositions/benchmaker/template.md);
`skill-tournament` applies
the same loop to the library's own skills.

### Visualize anything

[`orch-visualize`](skills/utilities/orch-visualize/SKILL.md) renders a
supplied subject as a verified visual page, choosing diagrams, panels,
or charts from its relationships. This delivery view points to
[`orch-spec`](skills/workflows/orch-spec/SKILL.md),
[`orch-decompose`](skills/kernel/orch-decompose/SKILL.md), and
[`orch-frontier`](skills/engines/orch-frontier/SKILL.md);
[verification](rules/verification.md) owns acceptance. This view shows
only the checker-or-gate choice; that rule owns the other ordinary paths and
their details:

```mermaid
flowchart TD
    spec["orch-spec — freeze one root ticket"] --> pack{"stamp a domain pack"}
    pack --> dec["orch-decompose — cut ordered units"]
    dec --> frontier["orch-frontier — dispatch ready units"]
    frontier --> exec["unit executor"]
    exec --> path{"independence path"}
    path -->|unit-local| checker["fresh checker"]
    path -->|gate-deferred| join["orch-integrate — each return crosses once"]
    checker --> join
    join -->|named downstream gate| gate["composite gate"]
    join -->|otherwise| accepted["accepted result"]
    gate --> accepted
```

## Design

### The problem

Skill libraries break the same four ways:

- **Overly specific, handcrafted prompts.** As models get smarter,
  overprescription degrades output quality.
- **Manual chaining by the user.** First run `/brainstorm`, then run
  `/to-prd`, then run... blah blah blah.
- **Domain-specific.** The workflow for writing a blog is basically the
  workflow for shipping a feature: outline the goal, build each section
  in parallel, review the output for cohesion and consistency. You
  don't need a `/write-blog` skill and a `/build-feature` skill.
- **Static.** Run 100 hits the same snags as run 1.

orchflows answers each in structure: tiny composable skills where
every word fights for its life; autorouting instead of memorized
chains; domain-blind workflows retargeted by data packs; and
self-improvement wired into every run.

### Legos

- **One brick, one job.** `orch-frontier` runs the graph,
  `orch-critique` challenges Goal and evidence, `orch-verify` independently
  decides Goal, `orch-loop` iterates, and the `fix` workflow proves the cause
  before repairing it.
- **One stud pattern.** Five frozen contracts — work-item, verdict,
  worklog, pack-signature, result — are the only interfaces. Anything
  that emits one plugs into anything that takes one.
- **One return shape.** Every dispatchable unit returns one result
  envelope — status, result identity, verification — so any unit's
  output feeds any successor's evidence. A named workflow is just
  tickets with the edges between them written down, so a chain needs
  no per-pair glue.

You snap bricks by naming them; the agent snaps them by routing. Same
bricks either way.

### Skills and workflows

    orchflows
    │
    ├── Layer 0 · contracts/ — the narrow waist: hash-pinned data shapes, the only
    │                         interface between everything above them
    ├── Layer 1 · skills/    — everything callable: kernel/ primitives that call no
    │                         skill, engines/ that add control flow, workflows/
    │                         assembled from both, instances/ that do a domain's
    │                         hands-on work, utilities/
    ├── Layer 2 · packs/     — per-domain data (code, content, research, design),
    │                         never control flow
    └── Layer 3 · compositions/ — named workflows, callable like any skill

Four layers, dependencies pointing one way. `ARCHITECTURE.md` is the
codemap — what lives where, who owns it — and `ls` is the current list;
this README does not keep a second copy of it.

### Packs

    packs/
    ├── orch-code-pack     — delivers code        · tests and checks       · executor orch-tdd
    │                        workspace: git, one worktree per work item
    ├── orch-content-pack  — delivers documents   · artifact evidence     · executor orch-draft, assembly orch-edit
    │                        workspace: document tree with outline slots
    ├── orch-design-pack   — delivers rendered UI · capture evidence      · executor orch-render
    │                        workspace: git plus render (view × breakpoint × state)
    └── orch-research-pack — delivers answers     · source evidence       · executor orch-investigate, assembly orch-synthesize
                             workspace: evidence store of lane packets

A pack is pure data — no control flow. It supplies the domain's
vocabulary, artifact evidence, executors, workspace rules, and design
principles, all satisfying one frozen pack-signature, so everything the
library builds inside a domain stays cohesive. Stamp a different pack
on the root ticket and the identical pipeline ships code, documents,
research, or UI.

### Advantages over Anthropic's Dynamic Workflows

Against the shipped runtime as documented on 2026-08-15
([the workflows docs](https://code.claude.com/docs/en/workflows)) —
saved workflows are no longer the difference, so this is what is:

- **Cross-harness.** One library drives Claude Code, Codex and Grok
  Build.
- **Verification is contractual, not merely available.** Adversarial
  review is house advice there; here Goal, executor evidence, and the
  applicable independent path stand between an executor's claim and "done".
- **Self-improving.** Nothing there mines runs into fixes; here friction
  and traces feed `orch-self-improve`, including on itself.
- **Survives session death.** Exit mid-run and a workflow starts fresh
  there; here every ticket is a file in a per-user state sink, so any
  fresh context in any checkout resumes mid-flight.
