---
name: orch-visualize
description: Render any supplied subject as verified Mermaid diagrams with a terse explanation. Use when the user asks to see structure.
role: worker
---

Require: the subject — supplied or named content only; gather no new
evidence and decide nothing about the subject. Label every inferred
connection inferred.

Choose the diagram by the subject's own shape — for a skill or
workflow, resolve every backticked call recursively; stop on a
missing dependency or cycle and say so. Preserve what the subject
states: order, branches, parallel lanes, loop bounds and exits,
failure returns. Conditional or weak edges dotted; defect edges red;
cycles as real back-edges.

Write Mermaid blocks plus at most one terse paragraph per diagram —
what it shows and the one thing to notice — to
`.orch/runs/viz/<subject>.md` unless the caller names a path. Verify
before returning: run this package's `scripts/verify_mermaid.py` on the
output; one correction pass on rejection, then stop. Report verified
only after exit 0, with graph count; otherwise return failed with the
verifier's diagnostic. On the dispatch's request, render the verified
page with `scripts/render_html.py` — a self-contained `<subject>.html`
beside the source — and report its mode (cdn mode is degraded).

Never: decorate beyond the subject's own vocabulary; describe an
unverified page as verified; add evidence the subject did not supply.

Return: status, file path, graph count, verifier evidence, and the
per-diagram explanations; rendered page path with mode only on request.
