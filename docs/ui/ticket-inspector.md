# Ticket inspector

The ticket inspector is the read-only technical drill-down for one canonical
ticket selection. Its feature module lives under `web/src/features/inspector`
and exports the `ticket` view identity for the platform registry.

## Evidence contract

The tabs keep their claims deliberately narrow:

- **Overview** answers what the ticket is, what is happening, and what the
  canonical readiness facts say happens next.
- **Details** shows routing, dependencies, accepted inputs, write scope,
  bound, claim, and pack. A field absent from the closed projection is labeled
  `Unavailable`; the browser never invents metadata.
- **Proof** preserves every projected criterion, verdict, oracle, oracle
  class, evidence identity, and unknown state.
- **Friction** includes a record only when both its run and ticket identities
  match the selection.
- **History** contains only the closed durable claim/event projection. When
  no such evidence exists, it says `History unavailable` and does not infer
  work from transcript activity.
- **Raw** displays the selected ticket markdown in a React text node inside a
  `pre` element. It never interprets HTML, and host paths are redacted before
  display.

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
