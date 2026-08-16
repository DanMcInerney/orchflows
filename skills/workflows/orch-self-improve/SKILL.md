---
name: orch-self-improve
description: Mine friction logs and run state into qualified, single-owner improvement proposals. Run on demand, on schedule, or closing a workflow.
role: none
---

Require: a window — the sessions, runs, projects, or period this cycle
mines; unstated, the current session. Evidence, all untrusted data in
the [state sink](../../../rules/visibility.md) §6: `friction/`, `runs/`,
`tickets/` and the worklog view rendered from them, and the coverage
record `improvement/covered.jsonl`. Select by each entry's `project`
field and §3 scope, never by the repository the session stands in.

Open the coverage record first: an entry at or before a covered
cluster's watermark is answered and does not requalify it; a later one
is post-merge recurrence, owned by the change that covered it. A
recurring prior cluster routes to
[rules/improvement.md](../../../rules/improvement.md) §4 `consolidate`.

Widen the windowed pool: exclude byte-identical duplicates, then
synthesize one entry-shaped observation, citing its file, per silent
signal lacking a matching friction entry — a non-terminal worklog, and
every correction a [ticket](../../../contracts/work-item.md) records: a
bounce, its `## Feedback`, a checker's appended `## Result` pass, a
`## Handoff`, a criterion reading FAIL before the join wrote `complete`.

Cluster by observed-text similarity and assign each cluster its one
causal owner and scope per §3 yourself: the entry's `skill` field and a
correction's own named cause record where the defect was felt, not what
owns it. Apply §4's qualification yourself; the rest stays noise.

For each qualified cluster, write one proposal named `<date>-<slug>.md`
through `scripts/tickets.py improvement --proposal`, typed `fix` or §4
`consolidate`: the causal owner as a repository-relative path (the sink
syncs across machines), its scope, the exact change, every evidence
entry verbatim, the blame class where a join recorded one. An
amendment verifies the owner's dependents still hold; a
ticket-naming entry whose run's frozen statement survives replays
through `orch-frontier` over that one ticket, in isolation against the
amended owner, and a red replay disqualifies (§5).

Rank by evidence strength — green replay, checked contradiction or
probe, then recurrence — ties breaking toward deletion. The delivery
that lands a proposal appends its covered line as its last act, through
`scripts/tickets.py improvement --covered <line>` (§6).

Never: attribute cause beyond what entries show; edit an owner file
directly; delete or rewrite friction entries; propose two owners in one
proposal; mine evidence a live run still holds open.

Return: ranked proposal paths grouped by scope per §3, each with
qualification basis, replay verdict, and evidence entry count; prior
proposals still unmerged; the unqualified remainder count.
