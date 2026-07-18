# Topology

1. Every run composes from these operators and no others: freeze the
   contract; dispatch and accept through the delegation boundary; execute
   through one of {single item, independent lanes, rolling dependency
   frontier, bounded loop}; join by {check, reduction, adjudication}; challenge
   adversarially only under stakes; correct at most once; escalate at
   most once.
2. Intake picks the smallest shape that fully owns the request, smallest-
   first: a direct answer from evidence already in context; a one-off
   bounded route to `orch-task` through an ad-hoc ticket — any request
   that fits one executor's context and bound routes here, named
   acceptance criteria included, oracles concretely specified at cut
   time — `pre-existing` provenance, independence and inline law per
   [rules/verification.md](verification.md) §10 and
   [rules/delegation.md](delegation.md) §2; one lane answering a bounded question →
   `orch-investigate`; independent one-offs: dispatch each packet in
   parallel through the delegation boundary, every result crossing the
   join; dependent one-offs: cut the ad-hoc set with edges, name its
   run bound, and run `orch-frontier` over it — the ticket files are
   the durable state, no spec and no worklog; independence enters per
   [rules/verification.md](verification.md) §10; else — only when the work
   needs a frozen spec: lanes at scale, an assembly, or resumption
   across sessions — a pattern, stamped by shape of done, each with
   one entrypoint: acceptance met once → deliver (`orch-deliver`) —
   convergence needing independent blind lanes stamps a research delivery
   instead, never a single investigate lane; a done-check decides exit →
   loop(<body>) (`orch-loop` dispatching the stamped body); best verified
   candidate → evolve (orch-evolve, manual-only); an unexplained
   failure → fix (`orch-fix`, which proves the cause before
   repairing); a consequential decision or approved spec
   as the deliverable → decision (`orch-spec`, with `orch-elicit` and
   `orch-panel`); no terminal done → scheduled snapshot (`orch-triage`, or
   a bounded delivery under a scheduler).
   Deliverables that are external world-state are out of scope: refused
   or routed directly to kernel skills and engines, never forced into a
   pattern. One-off routing stays inside rule 1's operators and the
   delegation boundary.
3. Decomposition emits [work items](../contracts/work-item.md); domains
   extend the item, never replace it. One item is a lawful cut: a cut
   is forced only by parallelism, disjoint write scopes, isolation, or
   resumption — never made to look thorough. A decomposition that
   cannot cover most acceptance criteria under the stamped slicing
   returns a decision gap, never a forced slicing.
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
7. Mixed-domain work chains single-domain runs through a composition:
   one run's synthesis becomes the next spec's `evidence`. Mixed
   decomposition inside one graph is undefined.
