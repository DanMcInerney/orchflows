# Friction view

Friction is the read-only problem log for the Observe experience. It answers
three questions without turning the browser into a workflow engine: what was
observed, what was expected, and which canonical run or ticket (if any) owns
the evidence.

## View identities

The rendered contract owns four identities from `docs/ui/view-manifest.json`:

- `friction--populated--wide`
- `friction--populated--compact`
- `friction--empty--wide`
- `friction--empty--compact`

`populated` renders the closed friction projection supplied by
`orchflows.experience.v1`. `empty` deliberately renders no records or reader
diagnostics so the absence treatment remains deterministic even when the
fixture corpus contains problem logs.

## Information and interaction contract

Unreadable and skipped-record counts appear first as an attention notice.
Each valid record then presents category, timestamp, observed condition,
expected condition, host label, and exact run/ticket linkage. A run link opens
`/runs/{run}`; a ticket link opens `/runs/{run}/tickets/{ticket}`. Missing
identifiers remain explicit and never produce a guessed link.

The view has no mutation controls. Its only actions are ordinary same-origin
links into existing read-only Workflows routes. Links are keyboard reachable,
carry descriptive text as well as the machine identity, and retain the
shell's visible focus treatment. Headings, landmarks, timestamps, record
lists, and diagnostics remain meaningful without color or hover. The compact
layout stacks timestamps and metadata while retaining the same reading and
focus order. Forced-colors uses system border and link colors; reduced-motion
inherits the shell's motion suppression.

## Projection and privacy

The feature copies only `ts`, `category`, `host`, `observed`, `expected`,
`run`, and `ticket` string fields from each friction record. All values render
through React text nodes. Absolute Windows and common Unix home paths are
replaced with `[redacted path]` before rendering. Unknown keys are discarded,
including any prompt, tool input/output, file content, command output, or
conversation-shaped data accidentally attached to a client object.

The feature never reads a transcript, filesystem path, remote asset, or API
outside the predecessor-owned experience feed. The dark surfaces, 4px spacing
scale, 44–52px information rows, radii, status colors, focus color, UI font,
and monospace identity treatment all resolve through the shared design
tokens.
