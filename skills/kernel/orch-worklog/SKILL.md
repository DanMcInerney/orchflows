---
name: orch-worklog
description: Create or advance a run's worklog state file. Use at run start and after every iteration or join.
role: none
---

Require: the run id — with the spec's objective and acceptance (or
the loop's done-check) at creation — and for an existing run its
worklog at `.orch/runs/<run>/worklog.md`.

Maintain the file per
[contracts/worklog.md](../../../contracts/worklog.md): freeze the goal
at creation — objective plus acceptance, or the done-check for a loop
run; append iteration entries, failed approaches, queued scope, and
blame classes as they happen; set the terminal state exactly once,
with the deciding evidence. A child dispatching a permitted helper
lane appends its own entry at dispatch time, per
[rules/delegation.md](../../../rules/delegation.md) §11. Judge what
enters: a failed approach needs
the evidence that killed it; detail that decides nothing for a later
iteration stays out. Keep entries as identities and verdicts, never
transcript prose.

Never: edit the frozen goal; delete a failed approach; let queued scope
migrate into the goal.

Return: the worklog path and the next action it implies.
