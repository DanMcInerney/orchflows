# Worklog contract (run view)

The run's state, rendered: `tickets.py worklog <run>` reads the run's
ticket directory and prints the view below; `--write` lands it at
`<state-root>/runs/<run>/worklog.md`, replacing only a file it rendered. There is never a second,
hand-written file — the tickets are the state, and every field here is
reconstructable from them by observation. Free notes a run appends
through `tickets.py run-state --note` land in `runs/<run>/notes.md`
beside the view and are not the view.

A decomposed root-ticket run is one physical run with one root and one
composite gate. Answer and direct-single work keep their ordinary independence
path. A successor has its own run view after its predecessor result is fixed.

- `goal` — the root ticket's `## Goal` and `## Context` verbatim; for a loop
  run the loop ticket's, and for a template run its terminal ticket's.
- `iterations` — every ticket in `claimed_at` order, each with its
  `## Verification` entries.
- `failed_approaches` — the `## Result` and `## Feedback` of every
  `failed` or `limited` ticket, and of every loop iteration ticket: the
  approach and the evidence that killed it. A later iteration never
  re-walks one.
- `queued_scope` — the tickets that `depends_on` the run's gate:
  discovered work, queued behind the frozen goal and never merged into
  it.
- `terminal` — empty until the run exits, then the root ticket's
  `status` — for a loop or template run the loop or terminal ticket's —
  read in the terminal set
  [work-item.md](work-item.md) owns: `complete` | `blocked` | `stalled` |
  `limited` | `failed`. A parked-only pause is not an exit: no
  ticket is claimed, the pause names the external action awaited and
  every ticket queued behind it, and the run resumes from its tickets.

Fresh-context iteration, resumption, and post-hoc improvement read this
view instead of transcripts; transcripts are never state. The sink
layout it is rendered from is `scripts/tickets.py`'s.

For a multi-kind request, `successors.md` beside this view is the durable
successor plan: ordered kind, pack, proposed run/root ids and `planned` or
`opened` state. It is not a transcript and not a second worklog. `orch-spec`
is its sole writer; a drained `orch-frontier` reads it to trigger successor
materialization from the predecessor's accepted result identity.
