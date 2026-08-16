# Cut lens (for `orch-critique` over an issued ticket set)

Judge the cut, never the deliverable, from the frozen root ticket and
the issued items alone. Every defect family falls on one side of this
division.

## Delegated

- [`scripts/cutcheck.py`](../../../../scripts/cutcheck.py) decides
  family 1, family 2, family 3, family 4, family 5 and family 6; its
  module docstring owns what each one is. Read its report — a family
  re-derived here by eye is read twice and trusted neither time.

## Kept

- Unowned outcome: some item's completion test observes the root
  ticket's outcome across item boundaries, in the pack's workspace
  semantics — a
  set whose oracles each exercise only inputs they construct themselves
  decides nothing about what crosses between them.
- Slicing fidelity: the cut is the shape the stamped pack's `slicing`
  cell prescribes, terminal assembly item included
  ([contracts/pack-signature.md](../../../../contracts/pack-signature.md)).

## Proving a copy, and reading a cut verdict

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

The check §11 accepts a cut's own repair on is `cutcheck.py` re-run to
exit 0 against the revision the set was cut from. Exit 0 means no
finding whose class lies outside the advisory set, not that the set is
clean: an advisory finding is reported and exits 0. A cut verdict is not
portable between hosts — an oracle naming an interpreter one host lacks
is reported there as `unrunnable-oracle` and is silent here, so a
verdict is read only on the host that produced it.
