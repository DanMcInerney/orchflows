# Custom workflow authoring

This file owns custom-item scope, procedure, adapters, and admission. Route the work by
the ordinary smallest-first shapes in [the host block](../templates/host-block.md),
and carry this exact file path in the sealed ticket's `## Context` as the
standards-owner and authoring-standard pointer. Decomposition preserves that
pointer in every member whose work is governed by it.

## Rings

A custom skill, pack, sheet, or workflow lives in one of three rings, and
`scripts/rings.py` reads them in one fixed order — nearest first:

| ring | where | what it holds |
| --- | --- | --- |
| project | `<repo>/.orchflows/` | items this repository ships to whoever clones it |
| home | `~/.orchflows/` | your own items, plus `imports/<name>/` for pinned external bundles |
| lib | the installed library | `skills/kernel/`, `skills/workflows/`, `packs/`, `sheets/`, and the `example-workflows/` gallery |

One bundle shape everywhere: a directory named `.orchflows` holding the
four item directories skills, packs, sheets, and workflows. A project ring is
one, the home ring's custom half is one, and a published repository that *is*
one — nothing else in it — is one too. Each `example-workflows/` entry is a bundle you can copy out.
Which ring an item belongs in is the placement rule,
[composition](../rules/composition.md) §14's.

The home ring is meant to be your git repository. `orchflows sync` writes the
`.gitignore` that draws its only line: the installed library, the pinned
clones, and the trust ledger are regenerable or machine-local and are ignored;
your items and your friction and run history are committed and travel. A new
machine is `git clone`, `install.py`, `orchflows sync`.

Two collision rules. `orch-` is a mechanically reserved floor: a ring item
taking the reserved `orch-` prefix is refused at resolution, naming its own
path, rather than shadowing a library verb or silently never running. Any
other collision resolves to the nearest ring and prints one shadow notice
naming both paths.

## Scope and landing

Author in a git-backed workspace under the code pack. Scope chooses the
landing zone; it is not an installation scope.

| scope | source landing | always-on rule landing | admission |
| --- | --- | --- | --- |
| canonical | this repository's owning tier | `rules/` or `templates/host-block.md` | repository validator, tests, and authoring lens |
| project | `<repo>/.orchflows/skills/<name>/SKILL.md` or `<repo>/.orchflows/workflows/<name>` | the repository's `AGENTS.md`, outside managed blocks | repository checks, first-use trust, and authoring lens |
| user | the home ring, or a git-backed authoring repository imported into it | user host integrations, outside managed blocks | source-repository checks and authoring lens before install |

Direct files under `~/.orchflows/lib/` are installed outputs, not git
code-pack candidates. Author or import their source in a repository first,
then install the accepted source and adapters explicitly. The shared
`install.py` remains a user-scope install for this canonical library; it does
not turn a ring item into an installation scope.

Custom items are outside library law and bind only at their declared scope.
The generic project defaults above apply only when the project's standards owner
names no more specific owner path. Never land at canonical scope what the request placed at custom
scope, or at a broader custom scope than requested.

## Trust

You installed the library and you authored the home ring, so both resolve
without asking. A project ring rides somebody's repository, so it does not:
the first time a resolving command reaches one, it refuses and names the
remedy. Two grants, and the refusal names both — `orchflows trust --once
<bundle>` allows exactly the resolution in front of you and records nothing
standing, `orchflows trust <bundle>` remembers until the bundle's ring content
changes. `orchflows untrust <bundle>` withdraws either.

The ledger is `~/.orchflows/trust.json`, outside every repository and
gitignored: a grant is a judgement about one machine and never syncs. Nothing
inside a project decides whether that project is trusted — a ring that shipped
its own ledger, or its own copy of the pack signature contract, changes
nothing. A pinned import needs no prompt, because adding it was the consent;
only a change to its pin puts it in front of you again.

Trust in a bundle is not trust in its prose running as your own reasoning. A
workflow you authored may drive inline in your session; an imported one
drives inside a frame you spawn an agent for, unless you decide otherwise for
that bundle. The convention costs a spawn and buys the same containment a
sealed child prompt has.

## Dependencies

The standard-library floor belongs to the library, not to what you author
on it: [ARCHITECTURE.md](../ARCHITECTURE.md)'s scripts tier states it,
and a ring item is outside it. There are three classes of dependency, each
with one home and one file, and they never share an environment.

An item's **own Python tooling** — what its own scripts import — goes in one
`requirements.txt` beside the item's manifest, pip's own format, pinned the
way you would pin anything you mean to reproduce. `orchflows sync` builds one
environment per declaring item under `~/.orchflows/envs/<kind>/<name>/`,
rebuilds it when the file changes, prunes it when the item leaves the ring,
and skips an untrusted project item — installing its packages runs its
content, which is exactly what trust grants. `orchflows env <kind> <name>`
prints the interpreter those scripts run through: its own environment when it
declares one, else the interpreter the library's own scripts use. Write that
command into the item's prose, never a path — an environment is
machine-local, regenerable, ignored by the home ring's `.gitignore`, and
never installed under `~/.orchflows/lib/`.

An item's **non-Python tooling** — ffmpeg, node, a browser, an API key — goes
in `tools.txt` beside the manifest, one requirement per line, or `env <NAME>`
for a variable. Nothing installs it: `orchflows sync` and `orchflows check`
report each missing tool or variable with its line, and never print a
variable's value. An item's **Node tooling** for its own scripts goes in
`package.json` plus a committed lockfile beside the manifest; `orchflows
sync` runs the lockfile install into the item's `node_modules` directory
under the same trust rule.

The **artifact's** own dependencies are none of those three. A game's
three.js, a site's build tool and their lockfiles belong to the workspace's
own manifest, installed by the child in its worktree as part of making the
artifact and committed with it. Orchflows never owns them; a workflow that
needs them present for its `done` probe declares the toolchain in its own
`tools.txt` instead. An item that declares nothing runs as it always did, and
what it imports is its own suite's claim to make. A sheet declares nothing at
all: it carries knowledge, so a `scripts` directory, a `requirements.txt` and
a `tools.txt` inside one are refused.

## The five flows

- **Create** — `orchflows new {skill|pack|workflow} <name>` scaffolds into the
  project ring when you stand in a project, else the home ring. The
  self-hosted route stays: an orchflows run can author a pack.
- **Use it everywhere** — put it in the home ring and push. Every machine that
  clones and syncs has it, on every host the installer detected.
- **Share it with a team** — commit it to the project ring. Teammates get it
  on clone, behind the first-use trust prompt, and
  `orchflows sync --project` writes the committed host adapters that travel
  with the repository.
- **Publish it** — make the bundle its own repository. Consumers run
  `orchflows add <git-url>@<pin>`, which refuses a branch name: only a tag or
  a full commit SHA is a pin, and `imports.lock` is what restores the clone.
- **Discover** — `orchflows list` shows every item resolvable from where you
  stand, its ring, its trust state, and every shadow, through the same
  resolver dispatch uses. `orchflows check [<ring-dir>]` then grades those
  items — this project's ring when you stand in a project, else the home
  ring — with the library compiler's own checks, and exits 1 on a refusal.

## What a workflow is made of

A workflow is a skill whose prose calls other skills, down to two callables.
`tickets.py do` makes one artifact through one stamped pack's craft;
`tickets.py judge` reads fixed artifacts and returns findings. Each call is
one minting command: it mints the ticket, seals it, pins the pack digest,
takes the lease, establishes the workspace, and emits the `launch` you
invoke verbatim. Every call names exactly one pack — that call's craft,
workspace semantics, and evidence discipline — so two domains in one
deliverable are two calls and a handoff, never one call with two tastes.
Depth mixes packs freely, because callables never share a workspace.

`tickets.py frame-open` opens the invocation's frame and `frame-close` ends
it. A frame is pack-less and lease-less: it is a journal, not
craft-governed work, and its driver is the session you are already talking
to. Write the calls in whatever order, parallelism, branching or bounded
repetition the job needs — that prose *is* the control flow, and there is no
engine under it to keep in step. That prose is also the frame's shape, so a
saved workflow's root `frame-open` names `--workflow <name>` instead of
`--shape "<line>"`: the body a reader can already open is the wave plan, and
restating it on the command line would be the same plan in two places. Only
a driver improvising the waves writes the line itself
([vocabulary](vocabulary.md)'s **routing shape** owns its grammar).

Two obligations bind every driver — relay the **typed artifact line**
([vocabulary](vocabulary.md)) rather than summarise it, and read the
**journal** ([work-item.md](../contracts/work-item.md)'s `frame` bullet) at
the head of a wave rather than only after a crash — and your body states
neither. `tickets.py frame-open` prints the frame law with the payload it
returns, so the driver reads it at the moment it opens the frame; a body
that restates it is a second owner of it.

## Deterministic calls, or a planning `do`

Write the calls literally when you know them: the same three `do`s every
time is a better workflow than a planner asked to rediscover them. Only
where the calls depend on what the work finds does a planning `do` earn its
context — and which craft sections each kind of call reads is
[vocabulary](vocabulary.md)'s craft-section entry.

## Which work earns a callable

A callable spends a whole child's context, so spend it on the four things
prose in your own session cannot buy. Ask, in order:

- **Does it need a second agent?** Independent eyes on your own output, or
  breadth you want run in parallel — not work you are about to do anyway.
- **Must it survive a crash?** A sealed ticket and a journal outlive the
  session; a paragraph of reasoning does not.
- **Does it land somewhere risky?** An isolated candidate worktree, an
  evidence-bound merge, and a `done` predicate `land` executes are what a
  claim of success is worth checking against.
- **Does it need the audit trail?** Someone will ask later what was decided
  and on what evidence.

None of the four: write it in the prose and move on. One or more: it is a
callable, and which callable is whether it makes something or reads something.
Closing a frame over two or more `do` children refuses unless the tree holds
a judging child or the journal states `unjudged: <reason>`
([work-item.md](../contracts/work-item.md)'s `frame` bullet owns the
refusal); take the refusal seriously — it is asking whether anyone looked at
the composition, which no member could see from its own seat.

## Idioms

The control-flow sentences whose wording recurs across workflows. Quote one
verbatim; a paraphrase is a second wording of one fact, and which steps earn
one is [composition](../rules/composition.md) §13's.

- **bounded-repair** — Where the judge blocks, one repair `do` is handed the
  `findings:` line verbatim, then one re-judge; two rounds is the bound.
- **fan-out** — One `do` per named item, launched together under the frame;
  the shape line lists them as one wave.
- **freeze** — Fix the identity before any candidate exists and forbid every
  later call from touching it.
- **declare-gaps** — A gap that remains is written as a gap, `[]` when there
  is none; silence is a defect.
- **outside-close** — Close on a command run outside every child; never on a
  child's own claim.

## Procedure

1. Route existing machinery first. If a stamped spec, skill, or workflow
   already expresses the request, use it instead of minting another item.
2. Fix the intended contract, target tier, scope, owner path, and observable
   admission before writing. Apply the overlap rule in
   [composition](../rules/composition.md) §6 and the placement rule in
   [token economy](../rules/token-economy.md) §6.
3. For a skill, use the anatomy and carriage rules in
   [composition](../rules/composition.md) §§5, 10–11. For a pack, follow
   [pack authoring](pack-authoring.md) and the
   [pack signature](../contracts/pack-signature.md), which owns the four
   cells and every craft section — `## Lens`'s `### root` entry included, so
   a custom pack a planner freezes a root against fills it like any other. A T0 shape change is a
   supersession change and follows its contract's pinning procedure.
4. For a workflow, write it step by step rather than from a template. For
   each step ask the four questions in *Which work earns a callable* above:
   none of the four and the step is a sentence in your prose, one or more
   and it is a callable. Then the recurrence rule,
   [composition](../rules/composition.md) §13, picks the rung — reusable
   workflow, sentence, or idiom — and an idiom is quoted from *Idioms*
   above, never reworded. Craft one assignment wants and no other is a
   **sheet** stamped on that call; a method one call runs inside the kernel
   contract is an **applied skill** pinned with `--skill`
   ([composition](../rules/composition.md) §12). Its `Return:` is what
   `frame-close` records, and its `done` is a command something outside the
   workflow runs. A multi-stage pack's stages run at one role,
   [roles.md](../rules/roles.md)
   §4's alone. Invoking the finished body against a scratch run, and reading
   the tickets it opened, is its deterministic admission.
5. Build host integrations from the top-level [host records](../hosts/). Use
   the selected record's installed-item template, legal frontmatter, launch
   verb and native fields, role profile, and capability classification. The
   rendered adapter is the install input; custom prose never restates those
   bindings. For example, a role-bearing Claude skill may use the host-legal
   `context: fork` plus its matching `agent`, but never copies the item's
   orchflows-only `role`. At every call site, resolve the declared role from
   the selected rendered adapter. At that call site, use the native binding that owner returns.
   Cross-host dispatch invariants remain in
   [role profiles](../hosts/profiles.md). A ring item's adapters are generated
   rather than hand-written, and carry a pointer or a command and never a
   preprocessing construct.
6. Run the target repository's required checks. In this library that means
   tools/validate.py, affected tests,
   adapter/routing/role tests when host surfaces change, and the full required
   checks before acceptance. Install only the accepted source identity.

## Workflow admission

A workflow carries its `SKILL.md` body and the references beside it. It
carries no schema, validator, fixture format, or script. Repository admission
refuses those artifacts inside a workflow, schema or fixture-format artifacts
named for it under [shared references](../example-workflows/references/), and any
workflow-named module under scripts. It also grades the body as a skill's:
the name matches its directory, the description is present and inside budget,
the body fits the workflow tier's word budget, and the manual-invocation flag
[composition](../rules/composition.md) §1 requires is declared. Validation a
workflow needs instead
belongs to pack data when it is domain craft or to a T0 contract when machinery
branches on it; a workflow that needs another shape exposes that missing
owner.

The already-shipped `browser-game` machinery is the sole exception, named in the
validator's dated 2026-08-28 allowlist. The validator reports that exception as a
warning; it admits neither another workflow nor an unnamed compatibility
mode.

## Authoring lens

Review the fixed artifact independently against these owners:

- sentence value, what-versus-how, placement, description, and budgets:
  [token economy](../rules/token-economy.md) §§1–2, 6, 8, 11;
- overlap, anatomy, and carriage: [composition](../rules/composition.md)
  §§5–6, 10–11;
- ownership and dependency direction: [visibility](../rules/visibility.md)
  §§2–4;
- pack purity and signature completeness:
  [pack signature](../contracts/pack-signature.md);
- vocabulary: [vocabulary](vocabulary.md), using its meanings and no others;
- implemented enforcement and non-normative illustrations:
  [documentation](documentation.md) laws 6, 9.

Record the item and adapter paths, deterministic admission evidence, boundary
findings, and verification observations. Failure handling follows
[composition](../rules/composition.md) §8.
