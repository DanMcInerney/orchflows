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

When `## Return fields` carries `return-size`, `result` has the narrower
machine-readable shape `result: <canonical JSON identity payload>` in the
ticket's `## Result`. The payload is the fixed-input identity grammar's inner
object and resolves to exactly one UTF-8 text artifact. The built-in counter
named by the clause measures those resolved bytes, not the ticket prose or
the executor's message.

The join runs `tickets.py result-grade` for `<run> <id>` over that identity
before trusting it. A missing, ambiguous, unresolved, non-text, or oversized result
cannot be accepted or marked `complete`; `set-status complete` repeats the
same grade. The other terminal statuses remain available when a bounded
result is rejected or effort is exhausted.
