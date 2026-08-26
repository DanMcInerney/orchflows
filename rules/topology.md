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
   A gate-only cut is the sole zero-unit form: its coverage map assigns
   every root criterion to the composite gate and emits zero `<id>.NN` unit
   tickets. It is not padding because that composite gate discriminates the
   root result.
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
   is the most valuable finding class. An opt-in ordered lens bundle is
   sealed on one critique-and-repair ticket: it consumes entries in bundle
   order, each with a unique lens identity and its evidence, before that
   gate's one verification.
5a. The pack is the item's, not the run's: a cut may stamp several, and the
   gate reviews each domain under its own lens. What a run cannot span is
   workspace semantics — a gate stub carries the root's records, so a
   member's pack raises its stamp only where that adapter carries them too.
   Genuinely different workspaces are successor runs under rule 7.
6. Escalation: [delegation.md](delegation.md) §9.
7. Multi-run work is successor roots linked by accepted result identities:
   seq opens a successor run only after the predecessor's result identity is
   resolved from `## Result` and cited among the successor's `## Fixed
   inputs`; par is the absence of such an edge, which rule 3's disjointness
   already governs, joined by a successor whose fixed inputs cite all of
   their accepted identities; loop is a ticket whose executor is
   `orch-loop`. Intake persists every sequential remainder in the first
   run's `successors.md`; under [work-item.md](../contracts/work-item.md#root-ticket),
   `orch-spec` is its sole writer and materialization
   owner, and a completed frontier is the durable trigger that returns the
   predecessor identity to it before the request is reported finished. A named
   multi-run shape is a template
   ([work-item.md](../contracts/work-item.md)) run by `orch-frontier`.
   Decomposition across incompatible workspace semantics is rule 5a's.
8. A v2 assignment cut advances only through `draft`, `validated`, and
   `sealed`. The draft is the complete implementation cut: units,
   dependencies, ownership regions, coverage map, and composite gate.
   Validation grades one exact draft snapshot and records its validation
   receipt. Run-lock compare-and-swap seals only that exact validated digest;
   only then are its units eligible for ready, claim, or packet.
9. The public v2 references are `root_generation`, `cut_generation`, and
   `assignment_seal`; a generation identity is exactly
   `v2:<root|cut>:<root-id>:<ordinal>:sha256:<digest>`. The root digest covers
   frozen root assignment fields and excludes cut membership, lifecycle
   bookkeeping, and executor-owned sections. The cut digest covers its
   referenced root generation, unit and gate assignment digests, coverage-map
   digest, ownership-region declarations, and merge-oracle identities; it
   excludes lifecycle bookkeeping, executor-owned sections, and
   self-referential generation fields. Storage is content-addressed,
   script-owned run state; filename and layout are internal.
10. An ownership region uses a symbol, heading, JSON Pointer, or
    adapter-equivalent selector. A same-artifact parallelism request requires
    a merge oracle and a stamped adapter proving stable non-overlap at a
    pinned identity. Without that proof, use dependency order or one sole owner.
    A line number is not region identity, and string inequality is not proof
    of non-overlap.
11. V2 migration is additive: absence of v2 fields means v1, and no v1 value
    is reinterpreted. All claimed or terminal v1 tickets are never rewritten
    and preserve their execution and history. A live v1 root opens a successor or
    new v2 root citing its Handoff or Result identity; pending or ready v1
    remains v1 unless the caller explicitly recuts or migrates it. New
    `orch-spec` and `orch-decompose` producers may opt into v2 while legacy
    and ad-hoc producers remain v1. Existing v0 admission and migration
    behavior is preserved; v1 pending, receipt, cohort, ready, claim, and
    packet semantics do not change. A named-field or enum change to the work
    item or pack signature lands as explicit T0 supersession with
    tests/pins.json re-pinned. The ordered lens bundle is an additive opt-in:
    v0 and v1 stay unchanged, and already sealed, claimed or terminal v2 cuts
    stay unchanged.
