One judgment pass over the joined tip, reading all four units together. This is a pointer file: the spec's own `##` headings are not ticket sections, so passing the spec itself as `--details-file` refuses with `unknown ticket section`.

Spec of record: research/standards-spec-2026-09-04.md. Read section 0 (the closed decisions a unit may report against but not reverse), section 1 (the frozen goal this tip must satisfy), section 2 (the fixed names and shapes), and section 3, whose four subsections are the four units below.

Unit details, each the assignment its child answered:

- U0 — the contract: research/standards-tickets/U0.details.md
- U1 — resolution and pinning: research/standards-tickets/U1.details.md
- U2 — the items: research/standards-tickets/U2.details.md
- U2b — the resolver: research/standards-tickets/U2b.details.md
- U3 — the rename: research/standards-tickets/U3.details.md

There are five units, not the spec's four. The driver added U2b at the wave-2 join, from a defect U2 reported and the spec's section 4 denied was possible: the collapse has two halves, the items ceasing to carry a cells table and the resolver ceasing to read one, and the spec assigned the first to U2 and the second to nobody. Judge U2b as you judge the others, against its own Details; and judge the driver's decision to add it, which is recorded in the frame journal at record journal:005-u2, as you would judge a planner's.

Artifacts, pasted verbatim from each unit's closing note before this ticket was issued:

- U0 artifact: git:ca83a8fe22255d031e384b81df1d264ba84823d1
- U1 artifact: git:423400e27177db13d1983d7a76777c00eaa5ee2b
- U2 artifact: git:18d52cb4e6aaf5a71855c9a1f2ecb1d611cd48a6
- U2b artifact: git:ce549cca130a5b6b77e511cb0b4648b84c5d103e
- U3 artifact: git:fbb98b47a60d6cbc6b9458482c314744e4bd98c2

Read the four together, not one at a time: the reason this pass runs once, at the end, is that a defect where two units meet is invisible to a per-unit judge. This run's seams, in the order worth reading them:

- **U0 against U3.** U0 deleted two contracts and U3 repointed every link into them. A dangling link is a miss; so is a link repointed to a section `contracts/standard.md` does not actually carry.
- **U1 against U2.** U1 built the `narrows:` walk while the items still declared `packs:`; U2 gave them `narrows:`. Check that what U1 walks and what U2 wrote are the same field with the same spelling, and that U1's tests are not still asserting the shape U2 replaced.
- **U2 against U3.** U2 changed item content in place; U3 moved and renamed the files. A `git mv` that lost U2's edit, or an edit U3 re-applied on top of U2's, both show here.
- **U2 against U2b, and the driver's two integration commits.** U2b removed the cells-table apparatus U2's items stopped carrying, made the digest the directory tree `contracts/standard.md` names, and repointed `_signature_digest` from the contract U0 deleted -- where it had been returning `None`, silently, with no check going red. Check that the digest actually moves for each of the four things that should move it and does not for the one that should not, and that the signature binding is not vacuous. Two commits in the joined history are the driver's own, not a child's: 4333043f resolving the U1/U2 import conflict inside U2's candidate, and the Details edits at ce9faaa0, 7f72334a and 6c4a7bdd. Read them as you read a child's.
- **The rename against itself.** U3's own grep is its deliverable. Re-run it rather than trusting the pasted output, and check the survivors it defended are genuinely ordinary English.

Numbers the frozen goal fixes, each of which you re-derive rather than read from a report: `install.py --dry-run` plans twenty-five fewer entries than the base commit's 359, decomposing into twenty deleted host adapters and five collapsed second files; each of the eight manifests is under `STANDARD_BUDGET`, 1200 words, and neither `CRAFT_BUDGET` nor `SHEET_BUDGET` names anything; the host block is at most 400 words; `AGENTS.md` is at most 230 words. A count that does not decompose that way is a finding even if the total happens to match.

Two things about the budget are worth checking rather than assuming, because both are easy to get subtly wrong: that it counts whitespace-separated words over the *whole* manifest including frontmatter, not a body or a section; and that the same number applies to a root and to a narrowing, since the spec's decision 4 deliberately retired the old asymmetry. A validator that still prices the two differently, under any name, is a finding.

Four numbers in the frozen goal came out differently from the spec's prediction, and each is a place where a report could be made to look right. The install count is 333, not the 334 the goal implies: the base was 358 rather than 359 because U0's two deleted contracts against its one new file had already moved it, so the reduction from `main` decomposes as twenty host adapters plus five collapsed second files plus one net contract. Re-derive that decomposition yourself rather than accepting it; a total that matches by coincidence is the failure this paragraph is guarding.

Each unit's `## Report` records the readings its Details asked for. A claim in a report that no command output supports is a finding.
