---
name: orch-visualize
description: Render any supplied subject as a verified visual page of diagrams, panels, and charts. Use when the user asks to see structure.
role: worker
---

Require: the subject — supplied or named content only; decide nothing
about it. Label every inferred connection inferred. The page plus its
prose preserves what the subject states; any single visual may omit,
never assert falsely.

Choose each visual's form by the subject's dominant relationship, on
the ladder in [references/authoring.md](references/authoring.md), and
stage a subject the lint rejects whole as that reference says. Author
each visual plus one terse paragraph — what it shows, the one thing to
notice — at the caller's named path, else `viz/<subject>.md` in the
workspace; the rendered `<subject>.html` beside it is the deliverable.

Verify: run this package's `scripts/verify_mermaid.py --lint`; one
correction pass on rejection, then stop. Render with
`scripts/render_html.py`, view the page, correct once from a defect
list. Verified only when the verifier exits 0 and the render reports
mode svg — cdn is never verified; anything else returns failed with the
page path and the diagnostic.

Never: decorate beyond the subject's own vocabulary; describe an
unverified page as verified; add evidence the subject did not supply.

Return: status, the rendered page path with mode — the deliverable;
then the markdown source path, graph, chart, and component counts,
verifier evidence, and per-visual explanations.
