---
name: orch-fixture
description: Freeze one completed ticket into a self-contained replayable fixture that feeds tournaments and canaries.
role: none
---

Require: one completed [ticket](../../../contracts/work-item.md) with
its accepted result and the run's frozen statement still present — its
spec, or for an ad-hoc run the ticket itself.

Choose what the fixture proves — one boundary or judgment, stated in its
README line. Freeze into `.orch/canary/<name>/`: the spec excerpt the
item depended on, the ticket, every fixed input pinned by identity,
every artifact an oracle compares against by content (golden captures,
external sources archived), the golden verdicts or score anchors, the
exact reproduction command, and — when the fixture bounds machinery —
the trace budget file (`<trace>.budget.json`) trace mining reads.
Redact everything else — a fixture that drags its run's context along
is not frozen. Score anchors for judged items stay out of the ticket
itself; judges are blind. Admit by replaying once through `orch-task`
and matching the golden result; a fixture that does not replay green is
not admitted.

Never: include transcript prose or unpinned identities; harvest an
unaccepted result; edit the source run's records.

Return: fixture path, what it proves, golden verdicts, and the
admission replay evidence.
