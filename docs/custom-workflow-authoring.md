# Custom workflow authoring

This file owns custom-item scope, procedure, adapters, and admission. Route the work by
the ordinary smallest-first shapes in [the host block](../templates/host-block.md),
and carry this exact file path in the sealed ticket's `## Context` as the
standards-owner and authoring-standard pointer. Decomposition preserves that
pointer in every member whose work is governed by it.

## Scope and landing

Author in a git-backed workspace under the code pack. Scope chooses the
landing zone; it is not an installation scope.

| scope | source landing | always-on rule landing | admission |
| --- | --- | --- | --- |
| canonical | this repository's owning tier | `rules/` or `templates/host-block.md` | repository validator, tests, and authoring lens |
| project | `<repo>/.orchflows/skills/<name>/SKILL.md` or `<repo>/.orchflows/compositions/<name>` | the repository's `AGENTS.md`, outside managed blocks | repository checks and authoring lens |
| user | a git-backed authoring repository, then an explicit user install | user host integrations, outside managed blocks | source-repository checks and authoring lens before install |

Direct files under `~/.orchflows/skills/` are installed outputs, not git
code-pack candidates. Author or import their source in a repository first,
then install the accepted source and adapters explicitly. The shared
`install.py` remains a user-scope install for this canonical library; it does
not turn a project custom item into an installation scope.

Custom items are outside library law and bind only at their declared scope.
A custom skill or composition never uses the reserved `orch-` prefix. The
generic project defaults above apply only when the project's standards owner
names no more specific owner path. Project defaults exist only for skills and
compositions; a custom pack, contract, or router lands at the owner path the
project names. Never land at canonical scope what the request placed at custom
scope, or at a broader custom scope than requested.

## Procedure

1. Route existing machinery first. If a stamped spec, skill, or composition
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
4. For a composition, start from the nearest template under `compositions/`,
   pin its open decisions, and keep control flow in ticket stubs. A
   multi-stage pack's stages run at one role, [roles.md](../rules/roles.md)
   §4's alone; a loop is a stub's `loop` field. Run
   `tickets.py instantiate` against the finished template as deterministic
   admission.
5. Build host integrations from the top-level [host records](../hosts/). Use
   the selected record's installed-item template, legal frontmatter, launch
   verb and native fields, role profile, and capability classification. The
   rendered adapter is the install input; custom prose never restates those
   bindings. For example, a role-bearing Claude skill may use the host-legal
   `context: fork` plus its matching `agent`, but never copies the item's
   orchflows-only `role`. At every call site, resolve the declared role from
   the selected rendered adapter. At that call site, use the native binding that owner returns.
   Cross-host dispatch invariants remain in
   [role profiles](../hosts/profiles.md).
6. Run the target repository's required checks. In this library that means
   tools/validate.py, affected tests, template instantiation when applicable,
   adapter/routing/role tests when host surfaces change, and the full required
   checks before acceptance. Install only the accepted source identity.

## Composition admission

A composition carries only its manifest, ticket stubs, and placeholder values.
It carries no schema, validator, fixture format, or script. Repository admission
refuses those artifacts inside a composition, schema or fixture-format artifacts
named for it under [shared references](../compositions/references/), and any
composition-named module under scripts. Validation a composition needs instead
belongs to pack data when it is domain craft or to a T0 contract when machinery
branches on it; a composition that needs another shape exposes that missing
owner.

The already-shipped `browser-game` machinery is the sole exception, named in the
validator's dated 2026-08-28 allowlist. The validator reports that exception as a
warning; it admits neither another composition nor an unnamed compatibility
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
