# Topology

1. Every run composes from these operators and no others: freeze the
   contract; dispatch and accept through the delegation boundary; execute
   through one of {single item, lanes, rolling dependency
   frontier, bounded loop}; join by {check, reduction, adjudication}; challenge
   adversarially only under stakes; correct at most once; escalate at
   most once.
2. Intake picks the smallest shape that fully owns the request. The
   branch table is [templates/host-block.md](../templates/host-block.md)'s;
   this rule owns only what may enter it. The routed set never grows: a
   request earns a name only when it carries an invariant routing cannot
   be trusted to preserve or a recurring multi-run shape; a named item
   earns a routed slot only when its natural-language trigger is
   unmistakable; everything else is a ticket. Deliverables that are
   external world-state are refused or routed directly to kernel skills
   and engines. One-off routing stays inside rule 1's operators and the
   delegation boundary.
3. Decomposition emits [work items](../contracts/work-item.md); domains
   extend the item, never replace it. The lawful set is the finest cut
   in which every item is an atom: one observable end state; a
   completion test discriminating it alone (`scripts/cutcheck.py`
   family 1); a closed write scope (family 3); oracles reading nothing
   a sibling writes (family 4); an instruction inside the stub ceiling
   ([token-economy.md](token-economy.md) §11). A coarser item is a
   compound item
   ([cut-lens.md](../skills/kernel/orch-decompose/references/cut-lens.md)),
   never a safe default; below the atom is padding — an item no oracle
   discriminates from a sibling — which is where cutting finer stops.
   Count is unbounded above; width past the host profile is the
   frontier's queue, not the cut's. A decomposition that
   cannot cover most acceptance criteria under the stamped slicing
   returns a decision gap, never a forced slicing. An edge exists
   only where the dependent's oracle reads what the predecessor
   writes or its `## Fixed inputs` cite the predecessor's result
   identity — never for ordering preference. A cut's write scope
   covers every artifact its own objective and completion test name,
   resolved against the workspace before issue; a cut that cannot cover
   them is widened or re-cut, never issued. An artifact more than one
   item would write is given to exactly one item — one on the first
   frontier the rest depend on, or a closing item depending on them —
   never shared; the recurring ones are `ARCHITECTURE.md`, a `SKILL.md`
   roster, a fixture copying a source, `tests/pins.json`, and a test
   module pinning several owners. Observing is not naming: an
   artifact a test only observes — asserting that it is unchanged
   included — stays outside the write scope, which covers only what the
   item changes. Reads are scope all the same: an item whose completion
   test observes an artifact outside its own write scope is
   parallel-safe only against siblings that change nothing that could
   move the verdict it observes, in the workspace where it observes it —
   isolation keeping a sibling's in-flight change out of that workspace
   qualifies as squarely as disjointness does. A sibling's write counts
   as material until shown immaterial. An ad-hoc set is a cut like any
   other: every clause here binds it, and `scripts/cutcheck.py` reads
   it before its first dispatch.
4. At most one terminal assembly item per run, depending on every unit
   item. Assembly rewrites its inputs, so unit verification upstream of
   it is invalidated at the join; the final gate re-verifies the
   assembled artifact.
5. A decomposed physical run has one root ticket and one composite gate
   over one fixed revision — stubs per
   [work-item.md](../contracts/work-item.md), Root ticket. Every additional
   reviewer is a unique named lens feeding that same gate's one repair and
   one verification. Never one gate per domain — cross-lens inconsistency
   is the most valuable finding class.
6. Escalation: [delegation.md](delegation.md) §9.
7. Multi-run work is successor roots linked by accepted result identities:
   seq opens a successor run only after the predecessor's result identity is
   resolved from `## Result` and cited among the successor's `## Fixed
   inputs`; par is the absence of such an edge, which rule 3's disjointness
   already governs, joined by a successor whose fixed inputs cite all of
   their accepted identities; loop is a ticket whose executor is
   `orch-loop`. A named
   multi-run shape is a template
   ([work-item.md](../contracts/work-item.md)) run by `orch-frontier`.
   Mixed decomposition inside one graph is undefined.
