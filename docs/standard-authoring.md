# Standard authoring

The order of work when adding a domain standard — the standard factory of
[documentation.md](documentation.md) §7, its library instances the five
roots under `standards/`, a project's landing per
[custom workflow authoring](custom-workflow-authoring.md). The law
lives with its owners — admission, frontmatter, the section table, the
`narrows:` rules and the word ceiling in
[contracts/standard.md](../contracts/standard.md);
anatomy and body budgets in [rules/composition.md](../rules/composition.md)
§5; each existing standard's rationale in `DESIGN.md`. This file only orders the work and names
what each step feeds the next.

1. Admission first, in writing, against the contract's admission
   line. A section you cannot later state in the new workspace's
   semantics is evidence the domain is not new. A request that only
   narrows a domain a root already owns — a house style, one client's
   report shape, a family of checks one run wants — earns a narrowing
   rather than a second root: it names that root in `narrows:`, tightens
   only, and carries none of the three sections the section table reserves
   for a root. The steps below author a root; a narrowing writes step 3's
   `## Lens` entry and stops.
2. Workspace second — the root's `## Workspace` section, which
   [contracts/standard.md](../contracts/standard.md)'s
   section table defines. Every other section is expressed in
   those semantics.
3. Evidence third, inside `## Lens`'s deliverable entry — the entry keyed
   by the artifact kind the adapter emits. The artifact identities,
   observations, captures, sources, or executable checks appropriate to the
   domain. These describe what can demonstrate Goal without prescribing a
   ticket's proof methods.
4. Vocabulary fourth — `## Vocabulary`, and the domain's taste beyond the
   shared principles in that same deliverable entry — from the debts step 3
   created. Check each term against the T0 contracts and
   [docs/vocabulary.md](vocabulary.md) before keeping it — a
   collision with a pinned field name is permanent.
5. Cutting fifth — `## Lens`'s `### cut` entry: how a spec cuts and what
   every ticket carries.
6. Criteria sixth — the deliverable entry's finding classes, one per
   bullet, and which of them block. Then the adapter from the registry
   (with `## Stages` for the domain's narrative when it earns one).
7. Spec fields last — `## Spec fields` fall out of the sections above.
   Then `## Lens`'s `### root` entry, written against the binding the
   section table states for it. Then the description, in the shipped
   standards' shared idiom, ending in its "Stamp when …" sentence.

The finished standard is one manifest at `standards/<name>/STANDARD.md`,
and the contract's section table is the one table of what it carries.
Resolve one with
`uv run --no-project python scripts/standards.py resolve <name>`,
the resolver the verbs themselves use, and grade every section against
the contract's admission line before keeping it.

Close with the admission in
[custom workflow authoring](custom-workflow-authoring.md).
