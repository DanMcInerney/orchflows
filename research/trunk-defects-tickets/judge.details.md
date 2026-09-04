One judgment pass over the joined tip, reading all four units together. This is a pointer file: the spec's own `##` headings are not ticket sections, so passing the spec itself as `--details-file` refuses with `unknown ticket section`.

Spec of record: research/trunk-defects-spec-2026-09-03.md. Read section 0 (the closed decisions a unit may report against but not reverse), section 1 (the frozen goal this tip must satisfy), section 2 (the fixed names and shapes), and section 3, whose four subsections are the four units below.

Unit details, each the assignment its child answered:

- U1 — the seal reads the ticket: research/trunk-defects-tickets/U1.details.md
- U2 — a retirement can be graded: research/trunk-defects-tickets/U2.details.md
- U3 — the manifest stops colliding: research/trunk-defects-tickets/U3.details.md
- U4 — the judgment cadence is law: research/trunk-defects-tickets/U4.details.md

Artifacts, pasted verbatim from each unit's closing note before this ticket was issued:

- U1 artifact: <PASTE U1'S artifact: LINE HERE, VERBATIM>
- U2 artifact: <PASTE U2'S artifact: LINE HERE, VERBATIM>
- U3 artifact: <PASTE U3'S artifact: LINE HERE, VERBATIM>
- U4 artifact: <PASTE U4'S artifact: LINE HERE, VERBATIM>

Read the four together, not one at a time: the reason this pass runs once, at the end, is that a defect where two units meet is invisible to a per-unit judge. Three seams to read first — `tests/serial_compat_manifest.json`, which every unit's new check rewrites and which U3 reshapes; `tests/test_staleness_and_remedies.py`, which U1 and U2 both append to; and `docs/lifecycle.md`, which U2 regenerates and whose row count must not have moved.

Each unit's `## Report` records the readings its Details asked for. A claim in a report that no command output supports is a finding.
