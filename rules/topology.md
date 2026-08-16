# Topology

1. Every run composes from these operators and no others: freeze the
   contract; dispatch and accept through the delegation boundary; execute
   through one of {single item, independent lanes, rolling dependency
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
   extend the item, never replace it. One item is a lawful cut: a cut
   is forced only by parallelism, disjoint write scopes, isolation, or
   resumption — never made to look thorough. A decomposition that
   cannot cover most acceptance criteria under the stamped slicing
   returns a decision gap, never a forced slicing. A cut's write scope
   covers every artifact its own objective and completion test name,
   resolved against the workspace before issue; a cut that cannot cover
   them is widened or re-cut, never issued. Observing is not naming: an
   artifact a test only observes — asserting that it is unchanged
   included — stays outside the write scope, which covers only what the
   item changes. Reads are scope all the same: an item whose completion
   test observes an artifact outside its own write scope is
   parallel-safe only against siblings that change nothing that could
   move the verdict it observes, in the workspace where it observes it —
   isolation keeping a sibling's in-flight change out of that workspace
   qualifies as squarely as disjointness does. Immateriality is shown,
   never assumed: name the sibling's write and the part of the artifact
   the verdict turns on, and show the two disjoint under the observing
   method itself; what is not shown disjoint counts as material.
4. At most one terminal assembly item per run, depending on every unit
   item. Assembly rewrites its inputs, so unit verification upstream of
   it is invalidated at the join; the final gate re-verifies the
   assembled artifact.
5. One gate per run: a single `orch-review-fix` pass, one reviewer lane
   per stamped lens over the same fixed revision, findings validated
   jointly, one correction pass on the combined set. Never one gate per
   domain — cross-lens inconsistency is the most valuable finding class.
6. Escalation rides the ticket's `## Handoff`
   ([work-item.md](../contracts/work-item.md)) under
   [delegation.md](delegation.md) §9's once-per-dispatch bound.
7. Multi-run work is root tickets on `depends_on` edges: seq is an
   edge, the predecessor's `## Result` identity cited among the
   successor's `## Fixed inputs`; par is the absence of an edge, which
   rule 3's disjointness already governs, with the join a ticket
   depending on all of them; loop is a ticket whose executor is
   `orch-loop`. A named multi-run shape is a template instantiated into
   one run's ticket directory and run by `orch-frontier`; its terminal
   ticket's completion test gates the whole. Mixed decomposition inside
   one graph is undefined.
