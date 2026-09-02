Implement M3–M5 of `research/self-improve-design-2026-09-01.md` (in
your worktree; its "Move 3" drafted body is normative): the workflow
body and the law repoints.

Standards owner and authoring-standard pointer for this work:
`docs/custom-workflow-authoring.md` — apply its workflow-admission
rules and authoring lens.

Deliverables:

1. `example-workflows/self-improve/SKILL.md` — replace the body with
   the design doc's "Move 3" drafted body verbatim (frontmatter: keep
   `name: self-improve`, `disable-model-invocation: true`; take the
   draft's description). Strip the blockquote `> ` prefixes; keep the
   command blocks as indented code. Adjust only what
   `tools/validate.py` demands (the workflow tier's 450-word body
   budget, description budget, link resolution — the two law links in
   the draft must resolve from the file's location). Do not weaken the
   never-rules or the seam-judge/unjudged sentences.

2. `rules/improvement.md` §6 — re-point the cycle sentence at the new
   shape: the cycle is harvest (deterministic slice under the sink's
   covered watermarks), then mine, then deliver; the standing qualify
   step is gone (§4's recurrence arithmetic is computed mechanically at
   harvest; contradiction and owner assignment remain the mine's
   judgment; the delivery's `done` proves exactness). Keep §§1–5
   untouched. Match the file's voice; smallest diff that states the
   new shape.

3. M5 sweep: search the repository for goal-file templates or
   references named for the old self-improve pipeline (mine/qualify/
   deliver goal templates, sealed-batch template remnants). Delete or
   mark superseded anything found inside this repository; if nothing
   exists in-repo, state that finding explicitly in your report.

Constraints: touch only `example-workflows/self-improve/`,
`rules/improvement.md`, and any M5 findings; do not touch scripts or
tests (sibling tickets own harvest.py and the event stream — cite
their surfaces exactly as the design doc spells them). Run before
closing: `uv run --no-project python tools/validate.py` and
`git diff --check`.
