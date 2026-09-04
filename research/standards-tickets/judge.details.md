One judgment pass over the joined tip, reading all four units together. This is a pointer file: the spec's own `##` headings are not ticket sections, so passing the spec itself as `--details-file` refuses with `unknown ticket section`.

Spec of record: research/standards-spec-2026-09-04.md. Read section 0 (the closed decisions a unit may report against but not reverse), section 1 (the frozen goal this tip must satisfy), section 2 (the fixed names and shapes), and section 3, whose four subsections are the four units below.

Unit details, each the assignment its child answered:

- U0 — the contract: research/standards-tickets/U0.details.md
- U1 — resolution and pinning: research/standards-tickets/U1.details.md
- U2 — the items: research/standards-tickets/U2.details.md
- U3 — the rename: research/standards-tickets/U3.details.md

Artifacts, pasted verbatim from each unit's closing note before this ticket was issued:

- U0 artifact: <PASTE U0'S artifact: LINE HERE, VERBATIM>
- U1 artifact: <PASTE U1'S artifact: LINE HERE, VERBATIM>
- U2 artifact: <PASTE U2'S artifact: LINE HERE, VERBATIM>
- U3 artifact: <PASTE U3'S artifact: LINE HERE, VERBATIM>

Read the four together, not one at a time: the reason this pass runs once, at the end, is that a defect where two units meet is invisible to a per-unit judge. This run's seams, in the order worth reading them:

- **U0 against U3.** U0 deleted two contracts and U3 repointed every link into them. A dangling link is a miss; so is a link repointed to a section `contracts/standard.md` does not actually carry.
- **U1 against U2.** U1 built the `narrows:` walk while the items still declared `packs:`; U2 gave them `narrows:`. Check that what U1 walks and what U2 wrote are the same field with the same spelling, and that U1's tests are not still asserting the shape U2 replaced.
- **U2 against U3.** U2 changed item content in place; U3 moved and renamed the files. A `git mv` that lost U2's edit, or an edit U3 re-applied on top of U2's, both show here.
- **The rename against itself.** U3's own grep is its deliverable. Re-run it rather than trusting the pasted output, and check the survivors it defended are genuinely ordinary English.

Numbers the frozen goal fixes, each of which you re-derive rather than read from a report: `install.py --dry-run` plans twenty-five fewer entries than the base commit's 359, decomposing into twenty deleted host adapters and five collapsed second files; the host block is at most 400 words; `AGENTS.md` is at most 230 words. A count that does not decompose that way is a finding even if the total happens to match.

Each unit's `## Report` records the readings its Details asked for. A claim in a report that no command output supports is a finding.
