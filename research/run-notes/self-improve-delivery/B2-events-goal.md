Implement M2 of `research/self-improve-design-2026-09-01.md` (in your
worktree; its "Move 2" section is normative): the sink event stream.

Deliverables:

1. Event emission to `<sink>/events/<yyyy-mm>.jsonl` — monthly shards,
   one JSON line per terminal machine event, appended through the same
   locked-append idiom `tickets.py:_append_one_line` already provides.
   Every line carries the provenance head friction entries carry:
   `sink_convention, ts, project, run, ticket, host, session` — reuse
   the identity plumbing the tickets modules already hold; do not
   duplicate project-identity logic. Then an `event` field naming the
   kind, plus kind fields:
   - `frame-open` — emitted by `tickets_frame.py` at open; fields
     `workflow` (a new optional `--workflow <name>` flag on frame-open,
     null when absent) and `goal_head` (the sealed goal's first line,
     truncated to 200 chars).
   - `frame-close` — fields `children` (count of do/judge children),
     `judged` (bool), `unjudged_reason` (the journal's reason verbatim,
     null when judged), `done_exit` (the close's done reading when one
     exists, else null), `status`.
   - `land` — emitted at every `tickets.py land`: `status`, `done_exit`
     (null when no predicate), `attempts` (dispatch attempt count if
     cheaply available, else null), `elapsed_s` (from ticket open to
     land if cheaply available, else null).
   - `stalled` — emitted where the two-identical-repair-rounds verdict
     is decided, with the ticket id.

2. The reliability bar: emission is guarded — a failure to write an
   event costs the event and never the transition (mirror friction.py's
   swallow-and-name-on-stderr discipline). Only installed scripts write
   the stream; it is untrusted data like every sink stream.

3. `rules/visibility.md` §6: add the events stream to the sink-channel
   sentence beside run-state and improvement — one sentence, matching
   the section's existing style and staying inside any stated budgets.

4. `tests/test_events.py` — cover at least: one event per transition
   (frame-open with and without --workflow, frame-close judged and
   unjudged, land with and without a done predicate); each line parses
   and carries the provenance head; the locked append writes whole
   lines; an unwritable events root does not fail the land or close
   that triggered it. Use a temp sink-env-var fixture sink.
   If the serial-compat manifest must list the new module, regenerate
   with `uv run --no-project python tools/run_serial_compat.py
   --write-manifest` and commit the result.

Constraints: touch only `scripts/tickets_frame.py`,
`scripts/tickets_land.py`, whichever single existing tickets module the
shared emitter helper most naturally lives in (one owner — state your
choice in the report), `rules/visibility.md`, tests, and the
serial-compat manifest if regenerated. Do not create `scripts/events.py`
as a new standalone module unless nothing existing can own the helper
without a dependency inversion. Do not modify `scripts/friction.py` or
`scripts/harvest.py` (a sibling ticket owns harvest). Run the scoped
checks before closing:
`uv run --no-project python tools/run_tests.py --scope scripts/tickets_frame.py,scripts/tickets_land.py,tests/test_events.py`
and `uv run --no-project python tools/validate.py`.
