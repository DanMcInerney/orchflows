# Ticket inspector

The ticket inspector is the read-only technical drill-down for one canonical
ticket selection. Its feature module lives under `reader/web/src/features/inspector`
and exports the `ticket` view identity for the platform registry.

## Evidence contract

The tabs keep their claims deliberately narrow:

- **Overview** answers what the ticket is, what is happening, and what the
  canonical readiness facts say happens next.
- **Details** shows routing, dependencies, Goal, Context, Suggested files,
  bound, claim, and pack. It links the exact executor to a contained skill or
  script source only when the projection carries an explicit canonical
  workflow and source association. Otherwise it says `Executor source
  unavailable`; it never infers a definition from the run slug or executor.
- **Proof** preserves every projected criterion, verdict, oracle, oracle
  class, evidence identity, and unknown state. Its judgment explanation is a
  mechanical companion containing only the projected Result, Feedback, Risks,
  and rationale identity. Missing fields remain `Unavailable`, and an absent
  rationale is labeled `Rationale unavailable`; the browser authors no
  rationale.
- **Artifacts** lists only projected structured artifact identities. A
  resolvable opaque ID becomes a contained link under
  `/api/v1/runs/{run}/tickets/{ticket}/artifacts/{artifact_id}`. Prose-only,
  malformed, traversal-shaped, or unresolved entries remain visible as
  unavailable and never become links.
- **Friction** includes a record only when both its run and ticket identities
  match the selection.
- **History** contains only the closed durable claim/event projection. When
  no such evidence exists, it says `History unavailable` and does not infer
  work from transcript activity.
- **Raw** displays the selected ticket markdown in a React text node inside a
  `pre` element. It never interprets HTML, and host paths are redacted before
  display.

The artifact inventory endpoint is
`/api/v1/runs/{run}/tickets/{ticket}/artifacts`; its opaque IDs are the only
values the browser carries into the contained reader route. Caller-supplied
project or workspace paths and prose result text are never converted into
artifact links. The server owns state-sink containment, redaction, ETags,
GET/HEAD parity, and generic error behavior; the feature owns only progressive
presentation of that closed projection.

Prompts, tool inputs and outputs, command output, file contents, and subagent
conversation contents remain outside every inspector field.

## Navigation and states

The `tab` query parameter is the durable tab identity. Pointer activation,
arrow-key tab selection, browser history, and a direct URL all resolve the
same tab. When `tab` is absent, deterministic capture fixtures select their
named state: `running-overview`, `proof-pass`, `proof-fail`,
`friction-present`, `history-unavailable`, or `raw-escaped`.

The view uses the frozen platform tokens, the 4px spacing scale, 44–52px row
scale, and existing card and control radii. State is always communicated with
a glyph, word, and border in addition to color. Radix tabs provide the tablist
and keyboard semantics; visible focus, forced colors, reduced motion, and the
compact breakpoint inherit the platform accessibility contract.

The shared view registry and expanded live projection are integration seams
owned outside this feature. Until those corrected seams are present, direct
component tests are authoritative for behavior and capture completion remains
pending rather than inferred.
