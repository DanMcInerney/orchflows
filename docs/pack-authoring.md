# Pack authoring

The order of work when adding a domain pack. The law lives with its
owners — admission, cells, sharing constraints, and craft budget in
[contracts/pack-signature.md](../contracts/pack-signature.md); anatomy
and body budgets in [rules/composition.md](../rules/composition.md)
§5; the build gate in `orch-build`; each existing pack's rationale in
[DESIGN.md](../DESIGN.md). This file only orders the work and names
what each step feeds the next.

1. Admission first, in writing, against the signature's admission
   line. A cell you cannot later state in the new workspace's
   semantics is evidence the domain is not new.
2. Workspace second: what identities, baselines, and write scopes
   mean. Every other cell is expressed in these semantics.
3. Oracle policy third: the exact checks with their classes.
   Deterministic rows shape the executor's unit loop; each judged
   dimension owes a craft term, or fresh judges re-invent it per
   verdict.
4. Craft fourth, from the debts step 3 created. Check each term
   against the T0 contracts and
   [docs/vocabulary.md](vocabulary.md) before keeping it — a
   collision with a pinned field name is permanent.
5. Slicing fifth: how a spec cuts and what every ticket carries.
6. Executor and lens sixth: bind an existing instance when its
   contract already matches; write a new one only when the unit loop
   genuinely differs, named by its method.
7. Required spec fields last — they fall out of the cells above, and
   every command an oracle row names must arrive through a spec field.
   Then the description, in the packs' shared idiom, ending in its
   "Stamp when …" sentence.

Close with `orch-build`'s gate.
