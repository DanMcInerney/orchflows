---
name: orch-mechanize
description: Replace a repeated deterministic step with a tested script. Mandatory at the second repetition of the same step.
role: worker
---

Require: the step observed at least twice, its exact inputs and expected
output, and evidence it is deterministic — same inputs, same output, no
judgment inside.

Write the script in stdlib Python 3, cross-platform, to `.orch/bin/` for
run-local steps or the owning package's `scripts/` for library steps.
Test it against the observed repetitions before first use; the test is
the admission. Integration detail — endpoints, flags, versions, auth —
belongs here and never in a skill body.

Never: mechanize judgment; ship an untested script; hide a script's
failure by falling back to manual repetition silently (log the friction,
then fall back).

Return: script path, usage line, and the test evidence.
