# Pack signature

The cells every pack must provide, and the constraints between them. A
generic workflow references domains only through these cells; a pack
provides data satisfying them and never control flow. If a workflow needs
judgment no cell promises, the signature leaks: either every pack gains
the cell, or the judgment belongs in the workflow — never in one pack.

Cells:

- `slicing` — reference describing the decomposition strategy: how a spec
  cuts into work items, the item extensions the domain adds, and
  whether one terminal assembly item exists.
- `executor` — the named skill bound to unit work items.
- `assembly` — the named skill bound to the terminal item, or `none`.
- `lens` — the review binding: a named skill, or `orch-critique` plus a
  lens reference whose criteria are restated fresh from the spec.
- `oracle_policy` — the oracle table: for each criterion kind, the exact
  oracle and its oracle_class per
  [verdict.md](verdict.md); what green means; deviations from
  verdict.md's class policy.
- `workspace` — what identities, baselines, and write scopes mean in this
  domain (git revisions and paths; document slots; evidence stores).
- `required_spec_fields` — the fields a spec must carry for decomposition
  to accept it.
- `craft` — reference owning the domain's vocabulary and shape: each
  term defined once and used with exactly that meaning in specs,
  tickets, lenses, and verdicts; shape principles that hold across
  every workspace in the domain, outranked by the workspace's own
  standards on conflict. Budget: 60 non-empty lines. A term no spec
  field, item extension, lens criterion, or executor consumes is a
  defect.

Sharing constraints, checked at pack review:

- The assembly item's completion test carries the final gate's criteria.
- The executor's and assembly's Return files per
  [work-item.md](work-item.md)'s filing law — the ticket, or the store
  the packet names.
- Every write scope the slicing cuts is expressible in `workspace`.
- Every domain term another cell uses — a required spec field, a lens
  criterion, an item extension — is defined in `craft`.

Purity: a pack body contains no delegation language, no stop states, no
conditionals, and no Return contract. The validator mechanically checks
the Require/Never/Return labels, the eight-cell table, and that every
named skill and reference resolves; the rest of purity is checked at
pack review under the library lens. A pack that wants control flow is a
signature defect, not a pack feature.

Admission: a domain earns a pack only for a new oracle class or new
workspace semantics, read strictly.
