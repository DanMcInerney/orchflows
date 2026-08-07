deviation: value-substitution @ refill-margin off-by-one locus

near-miss — the closest-to-lawful violation in this seed set. Exactly
one expected value in `cases/cases.json` is wrong: the full-refill
boundary case records the post-refill full-burst acquire as denied, as
if the bucket refilled to one token below burst. The package's expected
values were computed against the defective refill margin, so its
scoring fails the correct reference implementation and would accept the
off-by-one variant at that boundary. Every other case, component, and
digest is lawful and the identity is re-minted.

Burn note: `value-substitution` is a census name reused from the
fresh-locus menu; the refill-margin off-by-one locus was never seeded
before.
