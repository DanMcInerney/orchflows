---
name: orch-fixture
description: Freeze one completed ticket into a self-contained replayable fixture that feeds tournaments and canaries.
role: none
---

Require: one completed [ticket](../../../contracts/work-item.md) with
its accepted result and the run's frozen statement still present — its
spec, or for an ad-hoc run the ticket itself.

Choose what the fixture proves — one boundary or judgment, stated as its
line in the canary set's README. Freeze into that set, whose layout
`.orch/canary/README.md` owns: the ticket under `tickets/canary/`, the
spec excerpt the item depended on, every fixed input pinned by identity,
every artifact an oracle compares against by content (golden captures,
external sources archived), and its golden verdicts or score anchors in
`golden.json`.
Redact everything else — a fixture that drags its run's context along
is not frozen. Score anchors for judged items stay out of the ticket
itself; judges are blind. Admit by replaying once through `orch-frontier`
over a directory holding that one ticket, and matching the golden result;
a fixture that does not replay green is not admitted.

Never: include transcript prose or unpinned identities; harvest an
unaccepted result; edit the source run's records.

Return: fixture path, what it proves, golden verdicts, and the
admission replay evidence.
