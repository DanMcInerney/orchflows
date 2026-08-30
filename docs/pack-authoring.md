# Pack authoring

The order of work when adding a domain pack — the pack factory of
[documentation.md](documentation.md) §7, its library instances the five
under `packs/`, a project's landing per
[custom workflow authoring](custom-workflow-authoring.md). The law
lives with its owners — admission, cells, sharing constraints, and craft
budget in [contracts/pack-signature.md](../contracts/pack-signature.md);
anatomy and body budgets in [rules/composition.md](../rules/composition.md)
§5; each existing pack's rationale in `DESIGN.md`. This file only orders the work and names
what each step feeds the next.

1. Admission first, in writing, against the signature's admission
   line. A cell you cannot later state in the new workspace's
   semantics is evidence the domain is not new.
2. Workspace second — the signature's `workspace` cell, which
   [contracts/pack-signature.md](../contracts/pack-signature.md)
   defines. Every other cell is expressed in those semantics.
3. Evidence third: the artifact identities, observations, captures, sources,
   or executable checks appropriate to the domain. These describe what can
   demonstrate Goal without prescribing a ticket's proof methods.
4. Craft fourth, from the debts step 3 created. Check each term
   against the T0 contracts and
   [docs/vocabulary.md](vocabulary.md) before keeping it — a
   collision with a pinned field name is permanent.
5. Slicing fifth: how a spec cuts and what every ticket carries.
6. Lens sixth: the craft's `## Lens` section, one finding class per
   bullet — the check lane reads its criteria there. Then the three
   cells machinery branches on: adapter from the registry, stages,
   assembly.
7. Required spec fields last — they fall out of the cells above. Then the
   `outline` cell, written against the binding
   [contracts/pack-signature.md](../contracts/pack-signature.md) states for it.
   Then the description, in the packs' shared idiom, ending in its
   "Stamp when …" sentence.

The finished pack projects three tastes — execute, check, outline — and that
same signature is the one table of which cells each carries. Read a projection
with `uv run --no-project python scripts/packs.py cells <digest> --for <lane>`,
the resolver the verbs themselves use, and grade every cell against the
signature's admission line before keeping it.

Close with the admission in
[custom workflow authoring](custom-workflow-authoring.md).
