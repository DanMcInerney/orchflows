---
name: self-improve
description: Mine the state sink's friction and run evidence into one qualified proposal and land it in its owner. Use on demand or closing a run.
disable-model-invocation: true
---

Require: a `window` — the sessions, runs, projects or period this cycle
mines — and a `workspace`, the repository holding the proposal's causal
owner. Mining is read-only; only the delivery writes.

    tickets.py frame-open <run> --goal-file <cycle-goal>

The frame's `## Report` is the cycle's working memory. Re-read it and every
child's state from the sink before each decision, then append that decision
with `tickets.py result <run> <frame> --by <frame>`. Keep every returned
`artifact:` and `findings:` line verbatim; the next call is handed the line.

**Mine**, one read-only call:

    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --goal-file <mine-goal> --bound "<= 60 tool calls"

Its goal: ranked proposals for the window, each written to the sink's
`improvement/` through `tickets.py improvement --proposal` with one causal
owner, its scope, the exact change and every evidence entry verbatim — and
the top-ranked proposal named as this cycle's delivery target, or the
finding that nothing qualified. The goal hands the child
[the improvement law](../../rules/improvement.md), whose §4 states the
qualification and ranking it applies.

**Qualify**, one judge over what the mine returned:

    tickets.py judge <run> --pack orch-content-pack --parent <frame>
      --artifacts <artifact-line> --goal-file <qualify-goal>

It asks whether the top-ranked proposal qualifies on §4's terms: evidence
no covered watermark already answers, one causal owner, and a change stated
exactly enough to land. That PASS is what opens the delivery and nothing
else does. On FAIL the cycle closes here, the ranked proposals its result.

**Deliver**, once, and only then:

    tickets.py do <run> --pack orch-code-pack --parent <frame>
      --isolation required --goal-file <land-goal> --bound "<= 120 tool calls"

Its goal: the proposal's exact change landed in `workspace` at its causal
owner, the owner's dependents still holding, the owner's required checks
green at the landed revision, and — as the delivery's last act — the covered
line appended through `tickets.py improvement --covered`, citing that
revision. Then one `judge` over the landed artifact under the same law,
which is the frame's second judge and its A2 witness.

Never: land a proposal the mine did not rank first, edit an owner outside
the proposal's scope, edit a friction entry or a prior covered line, rank on
evidence a covered watermark already answers, or mark a criterion complete
on the delivering child's own claim.

Return: `tickets.py frame-close <run> <frame> --done <gate>`, whose done is
the owner's own required gate at the landed revision — an exit code read
outside the delivery, never a claim inside it.
