# Custom workflow authoring

This file owns custom-item scope, procedure, adapters, and admission. Route the work by
the ordinary smallest-first shapes in [the host block](../templates/host-block.md),
and carry this exact file path in the sealed ticket's `## Context` as the
standards-owner and authoring-standard pointer. Decomposition preserves that
pointer in every member whose work is governed by it.

## Rings

A custom skill, pack, or workflow lives in one of three rings, and
`scripts/rings.py` reads them in one fixed order — nearest first:

| ring | where | what it holds |
| --- | --- | --- |
| project | `<repo>/.orchflows/` | items this repository ships to whoever clones it |
| home | `~/.orchflows/` | your own items, plus `imports/<name>/` for pinned external bundles |
| lib | the installed library | `skills/`, `packs/`, and the `example-workflows/` gallery |

One bundle shape everywhere: a directory named `.orchflows` holding the
three item directories skills, packs, and workflows. A project ring is one, the home ring's
custom half is one, and a published repository that *is* one — nothing else in
it — is one too. Each `example-workflows/` entry is a bundle you can copy out.

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
  resolver dispatch uses.

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
   cells and every craft section — `## Outline` included, so a custom pack a
   planner freezes a root against fills it like any other. A T0 shape change is a
   supersession change and follows its contract's pinning procedure.
4. For a workflow, start from the nearest template under `example-workflows/`,
   pin its open decisions, and keep control flow in ticket stubs. A
   multi-stage pack's stages run at one role, [roles.md](../rules/roles.md)
   §4's alone; a loop is a stub's `loop` field. Run
   `tickets.py instantiate <name>` against the finished template as
   deterministic admission.
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
   tools/validate.py, affected tests, template instantiation when applicable,
   adapter/routing/role tests when host surfaces change, and the full required
   checks before acceptance. Install only the accepted source identity.

## Workflow admission

A workflow carries only its manifest, ticket stubs, and placeholder values.
It carries no schema, validator, fixture format, or script. Repository admission
refuses those artifacts inside a workflow, schema or fixture-format artifacts
named for it under [shared references](../example-workflows/references/), and any
workflow-named module under scripts. Validation a workflow needs instead
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
  [documentation](documentation.md) laws 5–6.

Record the item and adapter paths, deterministic admission evidence, boundary
findings, and verification observations. Failure handling follows
[composition](../rules/composition.md) §8.
