# Topology

1. Every run composes from these operators and no others: freeze the
   contract; dispatch and accept through the delegation boundary; execute
   through one of {single item, independent lanes, rolling dependency
   frontier, bounded loop}; join by {check, reduction, adjudication}; challenge
   adversarially only under stakes; correct at most once; escalate at
   most once.
2. Intake picks the smallest shape that fully owns the request,
   smallest-first:
   answer — evidence already in context decides it;
   ad-hoc — bounded work needing no frozen spec: ad-hoc ticket(s)
   with named acceptance criteria, oracles concretely specified at
   cut time, `pre-existing` provenance, independence and inline law
   per [rules/verification.md](verification.md) §10 and
   [rules/delegation.md](delegation.md) §2 — one item → `orch-task`;
   one bounded question → `orch-investigate`; independent items →
   parallel dispatch through the delegation boundary, every result
   crossing the join; dependent items → an ad-hoc set with edges and
   a caller-named bound under `orch-frontier`; the ticket files are
   the durable state, no spec and no worklog;
   deliver — work needing a frozen spec: lanes at scale, an assembly,
   or resumption across sessions — `orch-spec` counts the deliverable
   kinds the end state spans and stamps one pack per spec: one run,
   or a composition instance chaining single-pack deliveries, cut
   where the deliverable's kind changes, joined per rule 7;
   convergence needing independent blind lanes is a research
   delivery, never a single investigate lane; `orch-deliver` runs
   each stamped spec;
   fix — a failure with unknown cause → the `fix` composition, which
   proves the cause before repairing.
   Everything else — named compositions and scheduled snapshots —
   runs only when named; the routed set never grows. A request earns
   a name only when it carries an invariant routing cannot be trusted
   to preserve or a recurring multi-run shape; a named item earns a
   routed slot only when its natural-language trigger is
   unmistakable; everything else is a spec. Deliverables that are
   external world-state are refused or routed directly to kernel
   skills and engines. One-off routing stays inside rule 1's
   operators and the delegation boundary.
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
   item changes, and what such an observation costs in parallel is
   [composition.md](composition.md) §7's.
4. At most one terminal assembly item per run, depending on every unit
   item. Assembly rewrites its inputs, so unit verification upstream of
   it is invalidated at the join; the final gate re-verifies the
   assembled artifact.
5. One gate per run: a single `orch-review-fix` pass, one reviewer lane
   per stamped lens over the same fixed revision, findings validated
   jointly, one correction pass on the combined set. Never one gate per
   domain — cross-lens inconsistency is the most valuable finding class.
6. Escalation routes through the ticket's `## Handoff` section
   ([work-item.md](../contracts/work-item.md)): a new ad-hoc ticket
   records the origin run and dispatch id; the once-per-dispatch bound
   rides the origin ticket's `## Handoff`.
7. Multi-run work is a composition per
   [contracts/composition.md](../contracts/composition.md): seq joins
   one run's result identity into the successor spec's `evidence`;
   par requires disjoint write scopes and a named join; loop
   dispatches through `orch-loop`. A composition's `done_check` gates
   the whole. Mixed decomposition inside one graph is undefined.
   `orch-compose` is the executor for every named and runtime
   composition instance.
