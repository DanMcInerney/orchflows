---
name: drift-canary
description: Detect behavior drift when a model, effort, or host binding changes — before it surfaces as production friction.
disable-model-invocation: true
---

Require: `canary_set`, the frozen fixture directory of golden items, and the
new binding under suspicion — the model id, effort level and host this run
reads against. There is no scheduler: a profiles change or an announced
model update is a person invoking this by name, which is why it never
model-invokes.

    tickets.py frame-open <run> --goal-file <drift-goal> --workflow drift-canary


**Re-run the set**:

    tickets.py do <run> --pack orch-research-pack --parent <frame>
      --goal-file <rerun-goal> --bound "<= 60 tool calls"

Its goal: for each item in the read-only `canary_set`, one `tickets.py do
--pack <item-pack> --goal-file <item-goal> [--details-file <item-details>]`
re-issue under a nested run of its own beneath `.orch/canary/`, each copy
carrying its own result at one recorded model id, effort level and host
binding — and the golden set byte-identical to its input identity when the
call closes.

**Read the delta**:

    tickets.py judge <run> --pack orch-content-pack --parent <frame>
      --artifacts <rerun-artifact-line> --goal-file <diff-goal>

One verdict per canary item against its golden result. A divergence is a
signal, not a failure: a better model may beat the golden result, so the
verdict records the delta and its direction and a human decides. The
findings file is the per-item verdict set.

**File the signal**, once, only for the divergences the judge named:

    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --goal-file <friction-goal> --bound "<= 40 tool calls"

Its goal quotes the judge's `findings: <path>` line verbatim and asks for
one friction entry per named divergence in the improvement evidence sink,
each citing the verdict it came from, so the delta between the new binding
and the frozen one survives this session.

Never: edit a golden result inside a canary run; add, remove or reorder a
canary item to make the set run; or treat divergence as failure.

Return: `tickets.py frame-close <run> <frame> --done <check>`, whose done
reads that every canary item carries a verdict against its golden result
and every divergence carries one friction entry.
