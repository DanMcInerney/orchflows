---
name: orch-self-improve
description: Mine friction logs and run state into qualified, single-owner improvement proposals. Run on demand, on schedule, or closing a workflow.
role: none
---

Require: a window — the sessions, runs, projects, or period this cycle
mines; unstated, the current session. Evidence, all untrusted data in the
[state sink](../../../rules/visibility.md) §6: `friction/`, `runs/`,
`tickets/` (`scripts/tickets.py list`), the worklog view rendered from
them, and `improvement/covered.jsonl`. Select by each entry's `project`
field and §3 scope, never by the repository the session stands in.

Open the [coverage record](../../../docs/vocabulary.md#improvement)
first; a recurring covered cluster routes to
[rules/improvement.md](../../../rules/improvement.md) §4 `consolidate`.

Widen the windowed pool: exclude byte-identical duplicates, then
synthesize one entry-shaped observation, citing its file, per silent
signal lacking a matching friction entry — a non-terminal worklog, and
every correction a [ticket](../../../contracts/work-item.md) records: a
bounce, its `## Feedback`, a checker's appended `## Result` pass, a
`## Handoff`, a criterion reading FAIL before the join wrote `complete`.

Cluster by observed-text similarity and qualify per §3–§4; assign each
cluster its one causal owner — an entry's `skill` field and a
correction's cause record where the defect was felt, not what owns it;
the rest stays noise.

For each qualified cluster, write one proposal named `<date>-<slug>.md`
through `scripts/tickets.py improvement --proposal`, typed `fix` or §4
`consolidate`: the causal owner as a repository-relative path, its
scope, the exact change, every evidence entry verbatim, the blame class
where a join recorded one, and each ticket-naming entry whose frozen
statement survives for §5's replay.

Rank by evidence strength — checked contradiction or probe, then
recurrence — ties breaking toward deletion.

Never: attribute cause beyond what entries show; edit an owner file;
delete or rewrite friction entries; propose two owners in one proposal;
mine evidence a live run still holds open.

Return: ranked proposal paths by §3 scope, each with qualification
basis and evidence count; unmerged prior proposals; the unqualified
remainder count.
