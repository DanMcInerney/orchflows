---
name: orch-visualize
description: Render any supplied subject as a verified visual page of diagrams, panels, and charts. Use when the user asks to see structure.
role: worker
---

Require: the subject — supplied or named content only.

Choose each visual's form by the subject's dominant relationship, on
the ladder in [references/authoring.md](references/authoring.md), and
stage a subject the lint rejects whole as that reference says. Author
each visual plus one terse paragraph — what it shows, the one thing to
notice — at the caller's named path, else `viz/<subject>.md` in the
workspace; the rendered `<subject>.html` beside it is the deliverable.

Verify: run this package's `scripts/verify_mermaid.py --lint`; one
correction pass on rejection, then stop. Render with
`scripts/render_html.py`. Start `python scripts/preview.py <rendered-html>`,
wait for its JSON URL, open that HTTP URL for the defect-list look pass, and
require the helper's successful exit; forbid `file://` for verification.
Correct once from the defect list. Verified when the verifier, renderer, and
preview helper all exit 0; anything else returns failed with the page path and
the diagnostic.

Never: decorate beyond the subject's own vocabulary; assert what the
subject does not state or leave an inferred connection unlabeled;
describe an unverified page as verified.

Return: status, the rendered page path — the deliverable;
then the markdown source path, graph, chart, and component counts,
verifier evidence, and per-visual explanations.
