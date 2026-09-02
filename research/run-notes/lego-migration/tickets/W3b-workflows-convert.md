# W3b — workflows-convert (wave 3, parallel with W3a, worker: opus)

## Goal

All eight example workflows are workflow SKILLS — a SKILL.md whose
prose calls bricks — and every one renders manual-invocation-only.
Two crafted conversions are the proofs: **super-research** (frame-open;
one deterministic `do(research-pack, source…)` line per live source,
parallel; a coverage `judge` loop ≤2 with targeted follow-up `do`s per
named gap — the window-reach table is the craft fact the calls lean
on; frame-close with the dossier verifier as done) and **self-improve**
(frame-open; one `do(content-pack, mine window…)` reading the
improvement law; `judge` qualifies; if a proposal qualifies, one gated
delivery: `do(code-pack, land it)` + `judge` + close with the required
gate as done). The other six (benchmaker, browser-game, drift-canary,
evolve, renovate, skill-tournament) convert MECHANICALLY: each template
stub is already a frozen brick call — render its executor/pack/goal
into a call line, its placeholders into intake sentences, its gate
stubs into judge lines; template.md's description becomes the skill
description; reference schemas stay as references/.

## Context

- owners: `example-workflows/*` (each entry becomes
  SKILL.md [+ references/], stubs and template.md deleted per entry),
  installer workflow-adapter rendering (`installer/packages.py`
  workflow adapter body: now "invoke the skill" prose + REQUIRED
  `disable-model-invocation: true` frontmatter for every workflow
  adapter — and ring rendering preserves source flags, closing the gap
  found 2026-08-31 where the home-ring super-research adapter lost its
  manual-only flag), reader workflow projections that globbed
  `template.md` (repoint to workflow SKILL.md; the summary-manifest
  requirement dies in W4a — leave the manifest file untouched)
- you branch from the W2 merge tip; W1's doors and W2a's frames exist —
  the crafted bodies name real commands
- DISJOINT from W3a by agreement: you do not touch scripts/tickets_*
  or contracts; the old instantiate layer still works this wave —
  your entries simply stop using it

## Details

- A workflow SKILL.md body: intake sentences (placeholders become
  "takes: window, question…"), frame-open line, the call lines
  (deterministic) or planning-`do` line (flexible), judge lines, the
  A2-satisfying judge-or-unjudged posture, frame-close with done.
  Follow the design's /market-thesis + /super-research shapes.
- Where a stub encoded something no brick call can say yet, keep the
  entry faithful and report the gap rather than inventing machinery
  (escape hatch — evolve's paired-promotion is the likely case).
- Body budgets per tier are law; workflows are workflow-tier bodies.
- Done: gate + preflight green; every entry greps free of template.md;
  `orchflows sync` in a temp home renders all eight with the
  manual-only flag; one crafted proof exercised end-to-end in a temp
  sink (super-research with a stub source list is acceptable — fake
  the sources' goals, prove the frame/do/judge shape drives).
- Report: commits; both crafted SKILL.md bodies verbatim; per-entry
  conversion notes with any reported gaps; the adapter flag proof.

## Report
