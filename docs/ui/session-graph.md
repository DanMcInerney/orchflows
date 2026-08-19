# Session graph

The Session graph view renders only the reader's closed session and subagent
metadata projection. It shows the session root, subagent identity, type, spawn
depth, activity state, evidence label, parent topology, diagnostics, and opaque
activity identity. It does not render working-directory paths, prompts,
conversation content, tool inputs or outputs, command output, or file contents.

## Topology truth

Each connection carries visible provenance as well as line treatment:

- `spawn depth 1` attaches a first-level subagent to the session root.
- `recorded parent` attaches a subagent to another subagent whose safe identity
  resolves in the selected session.
- `inferred: no parent recorded` uses a dashed amber edge to the session root.
- `inferred: recorded parent unresolved` uses the same dashed treatment but
  separately names that a parent value existed and did not resolve.

Missing, malformed, and unreadable metadata stays unknown. An unresolved parent
never becomes a fabricated canonical relationship. Diagnostics appear ahead of
the view title; active state follows, then the graph, inspector evidence, and
historical activity metadata.

## Interaction and accessibility

Graph nodes are keyboard-focusable selections. Selection updates the inspector
without changing reader state. Zoom controls and the minimap have accessible
names; edges expose source, target, and provenance labels. State always uses a
glyph and word in addition to its status color, while inferred topology uses a
dashed edge, provenance text, and a diagnostic. Reduced-motion and forced-color
preferences retain the same information and visible selection.

The wide and compact populated and diagnostic identities are capture evidence.
They are not golden captures until separately approved by view identity.
