# Pack authoring

The order of work when adding a domain pack — the pack factory of
[documentation.md](documentation.md) §7, its library instances the five
under `packs/`, a project's landing per
[custom workflow authoring](custom-workflow-authoring.md). The law
lives with its owners — admission, cells, craft sections, sharing
constraints, and craft budget in
[contracts/pack-signature.md](../contracts/pack-signature.md);
anatomy and body budgets in [rules/composition.md](../rules/composition.md)
§5; each existing pack's rationale in `DESIGN.md`. This file only orders the work and names
what each step feeds the next.

1. Admission first, in writing, against the signature's admission
   line. A section you cannot later state in the new workspace's
   semantics is evidence the domain is not new.
2. Workspace second — the craft's `## Workspace` section, which
   [contracts/pack-signature.md](../contracts/pack-signature.md)'s
   craft-section table defines. Every other section is expressed in
   those semantics.
3. Evidence third — `## Evidence`: the artifact identities, observations,
   captures, sources, or executable checks appropriate to the domain. These
   describe what can demonstrate Goal without prescribing a ticket's proof
   methods.
4. Vocabulary fourth — `## Vocabulary` and, where the domain has taste
   beyond the shared principles, `## Shape` — from the debts step 3
   created. Check each term against the T0 contracts and
   [docs/vocabulary.md](vocabulary.md) before keeping it — a
   collision with a pinned field name is permanent.
5. Slicing fifth — `## Slicing`: how a spec cuts and what every ticket
   carries.
6. Lens sixth — `## Lens`, one finding class per bullet — the checking
   verb reads its criteria there. Then the three cells machinery
   branches on: adapter from the registry, stages (with `## Stages` for
   their narrative when it earns one), assembly.
7. Spec fields last — `## Spec fields` fall out of the sections above.
   Then `## Outline`, written against the binding the craft-section
   table states for it. Then the description, in the packs' shared
   idiom, ending in its "Stamp when …" sentence.

The finished pack is one craft document behind four cells, and the
signature's craft-section table is the one table of what the document
carries. Read a resolved pack with
`uv run --no-project python scripts/packs.py cells <digest>`,
the resolver the verbs themselves use, and grade every section against the
signature's admission line before keeping it.

Close with the admission in
[custom workflow authoring](custom-workflow-authoring.md).
