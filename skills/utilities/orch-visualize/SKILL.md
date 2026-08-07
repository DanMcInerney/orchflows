---
name: orch-visualize
description: Render any supplied subject as a verified visual page of diagrams, panels, and charts. Use when the user asks to see structure.
role: worker
---

Require: the subject — supplied or named content only; gather no new
evidence and decide nothing about it. Label every inferred connection
inferred. The page plus its prose preserves what the subject states;
any single visual may omit, never assert falsely.

Choose each visual by the subject's dominant relationship per the
form ladder in [references/authoring.md](references/authoring.md) —
Mermaid fences for graph shapes, kit `viz-html` fences for panel
shapes, `vega-lite` fences for data, prose or tables when no
relationship needs 2-D locality. A subject the lint rejects whole
splits into an overview plus per-node detail panels under the
reference's staging law. Write each visual plus at most one terse
paragraph — what it shows, the one thing to notice — to
`.orch/runs/viz/<subject>.md` unless the caller names a path.

Verify: run this package's `scripts/verify_mermaid.py --lint`; one
correction pass on rejection, then stop. Render with
`scripts/render_html.py`, view the page, and correct once from a
defect list. Report verified only after both exit 0 with render
mode svg; cdn mode is degraded, never verified. Otherwise return
failed with the diagnostic.

Never: decorate beyond the subject's own vocabulary; emit `-beta`
diagram types, legends, or a third abstraction level; describe an
unverified page as verified; add evidence the subject did not supply.

Return: status, file path, graph, chart, and component counts,
verifier evidence, per-visual explanations, and the rendered page
path with mode.
