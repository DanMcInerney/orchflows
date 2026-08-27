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
- `lens` — the review binding: a named skill, or `orch-critique` with the
  pack's craft `## Lens`.
- `oracle_policy` — the oracle table: for each criterion kind, the exact
  oracle and its oracle_class per [verdict.md](verdict.md); any deviation
  from verdict.md's class policy. The class policy and the overall verdict
  rule stay verdict.md's, and where green is measured follows from them:
  state a deviation, never a paraphrase.
- `workspace` — what identities, isolation, candidate diffs, and conflict
  handling mean in this domain (git revisions; documents; evidence stores).
  Where it uses a term `craft` defines, the cell cites `craft` for the
  definition instead of restating it. The selected ticket adapter is a
  stable mechanism key in code, never executable pack content. A new identity
  kind changes that key together with adapter code, workspace/craft ownership,
  and tests; packs remain data.
- `required_spec_fields` — the fields a spec must carry for decomposition
  to accept it.
- `craft` — reference owning the domain's vocabulary, and its shape where
  the domain has one of its own. Vocabulary is mandated: each term
  defined once and used with exactly that meaning in specs, tickets,
  lenses, and verdicts; a term no other cell or executor consumes is a
  defect. Shape is optional and
  carries only the principles this domain does not share with the
  others, outranked by the workspace's own standards on conflict.
  Budget: 60 non-empty lines.

Sharing constraints, checked at pack review:

- The assembly item's Goal names the final integrated result.
- The executor's and assembly's Return files per
  [work-item.md](work-item.md)'s filing law — the ticket, or the store
  the packet names.
- Every candidate form the slicing emits is expressible in `workspace`.
- Every domain term another cell uses — a required spec field, a lens
  criterion, an item extension — is defined once: in `craft`, or inline
  in the cell that uses it.

Purity: a pack body contains no delegation language, no stop states, no
conditionals, and no Return contract. What the validator mechanically
checks is `tools/validate.py`'s to say; the rest of purity is checked at
pack review under the library lens. A pack that wants control flow is a
signature defect, not a pack feature.

Admission: a domain earns a pack only for a new oracle class or new
workspace semantics, read strictly. A cell earns its slot only when the
content behind it would differ between two packs, and no other cell
already carries that content.

## T0 supersession

One note governs both T0 shapes, and [work-item.md](work-item.md) states
it. A named-field or enum change to this signature is that note's, down to
the `tests/pins.json` re-pin it requires; nothing here restates it.
