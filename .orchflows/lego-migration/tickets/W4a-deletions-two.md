# W4a — deletions-two (wave 4, parallel with W4b, worker: sonnet)

## Goal

The template era's machinery is gone: `tickets.py instantiate` and its
support (`tickets_instantiate.py` or successor, placeholder grammar,
`entry:` kinds, `discover_templates`), the reader's workflow-summary
manifest requirement and file (`reader/docs/workflow-summary-manifest.json`
+ the SummaryManifestError gate that forced R.03's wall on 2026-08-31),
and installer paths that copied or indexed template directories.
Workflow name resolution stays: the rings resolver's `workflow` kind
now points at workflow SKILL.md entries (W3b's shape) — `orchflows
list` keeps listing them; anything that resolved `template.md` resolves
the skill file.

## Context

- owners: `scripts/tickets_instantiate.py` and friends,
  `installer/packages.py` `discover_templates` + template copying,
  `scripts/rings.py` workflow leaf (`template.md` → `SKILL.md`),
  `reader/scripts/ui_workflows_*` template globs and the
  summary-manifest reader, their tests and `tests/fixtures/ui/`
- you branch from the W3 merge tip: all eight workflows are already
  skills, so nothing live rides what you delete — grep-verify that
  claim FIRST and stop with a report if anything still does
- DISJOINT from W4b by agreement: you own scripts/installer/reader;
  W4b owns prose docs, rules, vocabulary, host block, README, TICKETS

## Details

- The frozen reader dist is CI-verified byte-for-byte — if a projection
  change would force a frontend rebuild, take the W3b precedent
  (payload shape preserved, content repointed) and report the residue
  as the standing reader-rebuild successor instead of rebuilding.
- Deletion-first commits; refusals that named instantiate repoint to
  "invoke the workflow skill".
- Done: gate + preflight green; grep proves
  `instantiate|entry:|discover_templates|SummaryManifestError` route
  nowhere live; `orchflows list` in a temp fixture still lists a
  workflow from lib and a ring; manifest last.
- Report: commits; deletion inventory with line counts; the rings
  workflow-leaf diff; anything preserved for the frozen dist with the
  successor note.

## Report
