# Result contract

The envelope leading every dispatchable unit's `Return:` — the value a
combinator passes between runs, and the first thing a caller reads in
any result.

- `status` — exactly one of `complete` | `blocked` | `stalled` |
  `limited` | `failed`: the terminal set
  [work-item.md](work-item.md) owns.
- `result` — the deliverable's identity, in the workspace's semantics;
  what a successor's `## Fixed inputs` cites.
- `verification` — verdict entries per [verdict.md](verdict.md), one
  per required criterion, together covering the `result` identity.
