---
name: evolve
description: Evolve one target through bounded candidate generations against one frozen evaluation. Manual-only campaign.
disable-model-invocation: true
---

Require: `target`, the identity being evolved; `incumbent`, its fixed
starting result/evidence identity; `evaluation`, the frozen evaluation
identity — mode, criteria, promotion rule, margin and search policy — or
`none` when one must be designed first; `writer`, the skill each candidate
is written through; `bound`, the campaign's budget; and `mutation_scope`,
the candidate workspace, which is the campaign call's alone.

    tickets.py frame-open <run> --goal-file <campaign-goal> --bound <bound> --workflow evolve


**Design the evaluation** only where `evaluation` is `none` — a supplied
frozen identity is already the campaign's, and every call below reads that
instead:

    tickets.py do <run> --pack orch-code-pack --parent <frame>
      --goal-file <eval-goal> --bound "<= 40 tool calls"

Its goal: one candidate-blind evaluation for `target`, frozen before any
candidate exists — identity, mode, scoring criteria, required admission and
regression criteria, artifact-evidence adapter, promotion rule, margin and
search policy — written into that call's `## Report` and nowhere inside
`mutation_scope`. In judged mode the accepted design owns the judge brief,
criteria, aggregation and adapter; in benchmark mode the qualified
benchmark and its runner own them.

**Admit the incumbent**: one `judge --pack orch-code-pack` whose typed
artifact line is `incumbent`'s fixed evidence identity, verdicts over the
frozen evaluation's required admission and regression criteria. A covered
PASS is what permits generation to open, and nothing else does.

**Generations, until the promotion rule and margin are met over the final
incumbent's score card or `bound` is spent.** Each generation is prose, not
machinery: one `do --pack orch-code-pack --isolation required` per
candidate, written through `writer` inside `mutation_scope` and handed the
eligibility findings verbatim; one `judge` scoring the incumbent and every
eligible candidate blind against the frozen evaluation;
`search_plan.py advance` selecting the next search-policy/v1 cases. The
judge's verdict is the loop's only exit condition.

**Close the campaign**: one `judge --pack orch-code-pack` over the final
incumbent — one score card naming it and the admitted result/evidence
behind it.

Never: rank an ineligible candidate; keep a candidate lacking PASS on every
required admission criterion — kill it, a score never compensates;
re-execute or substitute admitted evidence; expose protected evidence; call
`benchmaker`; activate a selected candidate; add a closing wrapper; take an
archive member as anything but an exploration parent; or unfreeze a
campaign constant — a changed constant starts a new campaign and
re-evaluates every retained candidate rather than continuing this one.

Return: `tickets.py frame-close <run> <frame> --done <check>` over that
final score card and the admitted evidence it cites.
