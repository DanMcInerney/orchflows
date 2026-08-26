# Cut lens (for `orch-critique` over an issued ticket set)

Judge the cut, never the deliverable, from the frozen root ticket and
the issued items alone. Every defect family falls on one side of this
division.

The reader is also the corrector: findings land as `tickets.py amend` on
the unclaimed items, `tickets.py new` for one the cut is missing, and
`cutcheck.py` re-run to exit 0 is what accepts them
([rules/verification.md](../../../../rules/verification.md) §11).

## Delegated

- `scripts/cutcheck.py` decides family 1, family 2, family 3, family 4,
  family 5 and family 6; its module docstring owns what each one is.
  Read its report.

## Kept

- Lifecycle fidelity: the draft is complete before validation; one
  validation receipt grades the exact root and cut generation digests; each
  `assignment_seal` covers the exact validated assignment; and only that
  sealed generation is eligible for ready, claim, or packet.
- Region fidelity: every same-artifact parallel pair has stable non-overlap
  proved at the pinned identity through a symbol, heading, JSON pointer, or
  adapter-equivalent ownership region, plus its required merge oracle. A line
  number or string inequality is not proof; without proof the cut uses
  dependency order or one sole owner.
- Amendment fidelity: a worker may append one canonical typed request to its
  Handoff and park, never edit its parent; integration routes the bounded
  caller disposition against the request's named generations.

- Unowned outcome: some item's completion test observes the root
  ticket's outcome across item boundaries, in the pack's workspace
  semantics — a
  set whose oracles each exercise only inputs they construct themselves
  decides nothing about what crosses between them.
- Slicing fidelity: the cut is the shape the stamped pack's `slicing`
  cell prescribes, terminal assembly item included
  ([contracts/pack-signature.md](../../../../contracts/pack-signature.md)).
- false edge: an edge no oracle-read or cited result identity
  justifies; without it a level widens at no cost. Read it from
  `cutcheck.py`'s `graph` block — `critical-path` and `level-width` —
  beside each item's oracles and `## Fixed inputs`.
- compound item: an item whose criteria partition into subsets with
  disjoint write scopes, each subset still discriminating — two atoms
  issued as one. The instruction ceiling `tickets.py new` enforces is
  this judgment's mechanical half, never the whole of it.
- vcs-prose fidelity: an `orch-tdd` item names a version-control
  exclusion only as its reserved `vcs.*` token, and prose naming one is
  refused `vcs-exclusion-not-tokenized`. The words that trip it are
  exactly git, worktree, branch, commit, merge, push, pull request and
  version control, matched whole once `-` and `_` have folded to spaces —
  so `no-commit` trips and `precommitted` does not. Stated here because
  the wording is chosen at the cut and only repaired after it, and
  because the two halves are deliberately unequal: only a word naming
  exactly one action rewrites mechanically, so git, branch and version
  control are found and never fixed, and an item excluded by one of them
  comes back for a decision this lens should have made.
  `scripts/tickets_lint.py` owns which words rewrite.

## Proving a copy

The can-fail demonstration
[rules/verification.md](../../../../rules/verification.md) §8 requires
builds its wrong result beside the tree; where that tree is a
repository, build the copy by clone, never by extract. An extract drops
`.git`, so an oracle reading history reads whichever repository encloses
the copy, or errors, and changes its verdict with no diagnostic. A copy
is faithful when everything the oracles read is present in it unchanged,
including what they read without naming it; evidence that with
`git rev-list --count` run in the copy and recorded beside every reading
taken there — one count proves the history came across and fingerprints
which revision was read, so `OK` beside a count is re-readable where a
bare `OK` is not. Runtime indicts a copy only when short: shorter than
expected means broken, longer means nothing, and runtime tracks the
checkout as much as the tree, so loose-object and ref counts belong
beside a timing reading.
