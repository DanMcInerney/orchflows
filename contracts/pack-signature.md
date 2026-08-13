# Pack signature

The cells every pack must provide, and the constraints between them. A
generic workflow references domains only through these cells; a pack
provides data satisfying them and never control flow. If a workflow needs
judgment no cell promises, the signature leaks: either every pack gains
the cell, or the judgment belongs in the workflow — never in one pack.

Cells:

- `slicing` — reference describing the decomposition strategy: how a spec
  cuts into work items and the item extensions the domain adds.
- `executor` — the named skill bound to unit work items.
- `assembly` — whether a terminal assembly item exists and what runs it,
  in exactly one of two forms: a backticked skill name bound to that
  item, or the bare word none followed by an em-dash gloss naming what
  stands in for the assembly. An empty cell or free prose is malformed.
- `lens` — the review binding: a named skill, or `orch-critique` plus a
  lens reference whose criteria are restated fresh from the spec.
- `oracle_policy` — the oracle table: for each criterion kind, the exact
  oracle and its oracle_class per [verdict.md](verdict.md); where green
  is measured and what it is compared against; any deviation from
  verdict.md's class policy. The class policy and the overall verdict
  rule stay verdict.md's: state a deviation, never a paraphrase.
- `workspace` — what identities, baselines, and write scopes mean in this
  domain (git revisions and paths; document slots; evidence stores).
  Where it uses a term `craft` defines, the cell cites `craft` for the
  definition instead of restating it.
- `required_spec_fields` — the fields a spec must carry for decomposition
  to accept it.
- `craft` — reference owning the domain's vocabulary, and its shape where
  the domain has one of its own. Vocabulary is mandated: each term
  defined once and used with exactly that meaning in specs, tickets,
  lenses, and verdicts; a term no spec field, item extension, lens
  criterion, or executor consumes is a defect. Shape is optional and
  carries only the principles this domain does not share with the
  others, outranked by the workspace's own standards on conflict.
  Budget: 60 non-empty lines.

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
workspace semantics, read strictly. A cell earns its slot only when the
content behind it would differ between two packs, and no other cell
already carries that content.
