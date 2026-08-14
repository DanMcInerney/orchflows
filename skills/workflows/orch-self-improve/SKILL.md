---
name: orch-self-improve
description: Mine friction logs and run state into qualified, single-owner improvement proposals. Run on demand, on schedule, or closing a workflow.
role: none
---

Require: a window — the sessions, runs, projects, or period this cycle
mines; unstated, the current session. Evidence, all in the state sink:
`friction/`, `runs/`, `tickets/`, `trace.py` traces, and the coverage
record `improvement/covered.jsonl`. Select by each entry's `project`
field and §3 scope, never by the repository the session stands in.

Open the coverage record first: an entry at or before a covered
cluster's watermark is answered and does not requalify it; a later
one is post-merge recurrence, owned by the change that covered it. A
recurring prior cluster routes to
[rules/improvement.md](../../../rules/improvement.md) §4 `consolidate`.

Widen the windowed pool: exclude byte-identical duplicates, then
synthesize one entry-shaped observation, citing its file, per silent
signal lacking a matching friction entry — a non-terminal worklog, a
trace's repeated failure, and every correction a
[ticket](../../../contracts/work-item.md) records: a bounce, its
`## Feedback`, a checker's appended `## Result` pass, a `## Handoff`,
a criterion reading FAIL before the join wrote `complete`. List
tickets with `scripts/tickets.py list`.

Cluster by observed-text similarity and assign each cluster its one
causal owner and scope per §3 yourself: the entry's `skill` field and a
correction's own named cause record where the defect was felt, not what
owns it. Apply §4's qualification yourself; the rest stays noise.

For each qualified cluster, write one proposal named `<date>-<slug>.md`
through `scripts/tickets.py improvement --proposal <name> (--file
<path> | --text <string>)`, typed `fix` or §4 `consolidate`: the single
causal owner and its scope; the exact change; every evidence entry
verbatim; the blame class where a join recorded one. An amendment
verifies the owner's dependents still hold. A ticket-naming entry whose
run's frozen statement survives replays through `orch-task` in
isolation against the amended owner — a red replay disqualifies (§5).

Rank by evidence strength — green replay, checked contradiction or
probe, then recurrence — ties breaking toward deletion. Proposals
are the cycle's durable output; at merge a covered line is appended
through `scripts/tickets.py improvement --covered <line>`.

Never: attribute cause beyond what entries show; edit an owner file
directly; delete or rewrite friction entries; propose two owners in one
proposal; mine evidence a live run still holds open.

Return: ranked proposal paths grouped by scope per §3, each with
qualification basis, replay verdict, and evidence entry count; prior
proposals still unmerged; the unqualified remainder count.
