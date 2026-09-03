---
name: bakeoff
description: Compare named candidates made blind under one pack and return the winner's artifact line scored against a rubric sheet.
disable-model-invocation: true
---

Require: `candidates`, the named list under comparison, one line of brief
each; `pack`, the single pack every candidate is made under; `rubric`, the
name of the sheet carrying the comparison's criteria; and `bound`, each
candidate's budget.

    tickets.py frame-open <run> --goal-file <bakeoff-goal> --bound <bound> --workflow bakeoff

**Label before anything is made.** Give each candidate an opaque label in
an order you draw rather than the list's, and keep the label-to-name map in
the frame journal, where no later call reads it. A candidate's goal file
carries its own brief and its label; never its name, its author, its
provenance, or another candidate's brief.

**Make them together** — *fan-out*: "One `do` per named item, launched
together under the frame; the shape line lists them as one wave."

    tickets.py do <run> --pack <pack> --parent <frame> --isolation required
      --goal-file <candidate-goal> --bound <bound>

**Score them blind.** One judge over every candidate's typed artifact line,
in label order, with the rubric stamped:

    tickets.py judge <run> --pack <pack> --parent <frame> --sheet <rubric>
      --goal-file <judge-goal> --artifacts <line> [--artifacts <line>]...

Its goal: rank every line against the rubric sheet's criteria, name the
winning label, and say what separated it from the runner-up — in the
labels' terms alone. Unblind afterwards, against the map you kept, and
report a candidate that returned nothing as a gap — *declare-gaps*: "A gap
that remains is written as a gap, `[]` when there is none; silence is a
defect."

Never: reveal the incumbent to the judge — not by label order, not by a
sentence in its goal file, not by an artifact line naming which candidate
stands today; run the candidates serially; or stamp the rubric on a
candidate's making, which buys rubric-fitting instead of a comparison.

Return: `tickets.py frame-close <run> <frame> --done <check>`, whose done
reads the frame journal for one unblinded `winner: <typed artifact line>`
and the judge's `findings:` line.
