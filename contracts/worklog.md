# Worklog contract (run view)

The run's state, rendered: `tickets.py worklog <run>` reads the run's
ticket directory and prints the view below; `--write` lands it at
`<state-root>/runs/<run>/worklog.md`, replacing only a file it rendered. There is never a second,
hand-written file — the tickets are the state, and every field here is
reconstructable from them by observation.

- `goal` — the root ticket's `## Objective` and `## Completion test`
  verbatim; for a loop run, the loop ticket's done-check and bound.
- `iterations` — every ticket in `claimed_at` order, each with its
  `## Verification` entries and, where its join failed, the blame class
  that join recorded ([work-item.md](work-item.md)).
- `failed_approaches` — the `## Result` and `## Feedback` of every
  `failed` or `limited` ticket, and of every loop iteration ticket: the
  approach and the evidence that killed it. A later iteration never
  re-walks one.
- `queued_scope` — the tickets that `depends_on` the run's gate:
  discovered work, queued behind the frozen goal and never merged into
  it.
- `terminal` — empty until the run exits, then the root ticket's
  `status` — for a loop run the loop ticket's — read in the run-level
  set `complete` | `blocked` | `stalled` | `limited` | `failed`;
  `stalled` is a run-level exit no ticket status carries
  ([work-item.md](work-item.md)). A parked-only pause is not an exit: no
  ticket is claimed, the pause names the external action awaited and
  every ticket queued behind it, and the run resumes from its tickets.

Fresh-context iteration, resumption, and post-hoc improvement read this
view instead of transcripts; transcripts are never state. The sink
layout it is rendered from is `scripts/tickets.py`'s.
