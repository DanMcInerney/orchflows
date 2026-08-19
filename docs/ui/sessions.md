# Sessions view

Sessions is the read-only metadata index at `/sessions`. It lists only closed fields supplied by `orchflows.experience.v1`: session identity, title metadata, last-modified metadata, agent count, diagnostic labels, and optional safe client and project labels. Selecting a row follows the canonical `/sessions/{session}` route for the topology-only agent graph.

The view deliberately labels absent facts as **Unknown client** and **Project metadata unavailable**. It does not infer either value from a title, identifier, transcript-root slug, or filesystem path. A known label appears only when the platform supplies the corresponding closed `client` or pre-redacted `project` field.

Prompts, tool inputs and outputs, command output, file contents, paths, transcript messages, and subagent conversations are not view inputs and are never rendered. The adapter copies only the seven closed fields above and drops every other property before rendering. React text rendering keeps metadata inert.

## Deterministic identities

The view manifest owns six identities:

- `Sessions/wide/populated` and `Sessions/compact/populated` render addressable rows with explicit unknown client/project facts.
- `Sessions/wide/empty` and `Sessions/compact/empty` render a named empty state with no row or search affordance.
- `Sessions/wide/diagnostic` and `Sessions/compact/diagnostic` place the diagnostic status before the index and retain only safe metadata.

The source manifest spells these identities as `sessions--{state}--{breakpoint}`. Captures are fresh evidence and remain `no-golden` until a user separately approves them.

## Interaction and accessibility

Session rows are native links, the filter is a labelled native search field, and diagnostic and empty changes use status semantics. Keyboard order is filter then session rows. Meaning is repeated by icon, text, and border rather than color alone. The compact treatment reflows row metadata without changing reading or focus order. Shared focus, reduced-motion, forced-colors, spacing, surface, status, radius, and row-height tokens remain the only visual vocabulary.
