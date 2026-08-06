# Result contract

The envelope leading every dispatchable unit's `Return:` — the value a
combinator passes between runs, and the first thing a caller reads in
any result.

- `status` — exactly one of `complete` | `blocked` | `stalled` |
  `limited` | `failed`: the run-level terminal set
  [worklog.md](worklog.md) owns.
- `result` — the deliverable's identity, in the workspace's semantics;
  what a successor spec's `evidence` cites.
- `verification` — verdict entries per [verdict.md](verdict.md), one
  per required criterion, together covering the `result` identity.

Binding: every dispatchable unit — `orch-deliver`, `orch-task`,
`orch-investigate`, `orch-loop`, `orch-compose`, `orch-frontier`, and
every composition — leads its `Return:` with these three fields; further
Return fields follow them. Evaluators and utilities are exempt. The
law is [rules/composition.md](../rules/composition.md) rule 10.
