# Code lens (for `orch-critique`)

Terms per [craft](craft.md). Read every diff inside the surrounding
file it lands in — a hunk alone hides the context a false positive
needs.

- Correctness: does the revision satisfy the spec's acceptance,
  including its failure paths, not only the happy path?
- Contract fidelity: does every public seam still honor its declared
  Require/Return shape for callers outside this revision?
- Scope: does every changed line sit inside the ticket's write scope
  and the spec's stated surface, with nothing incidental swept in?
- Shape: does the revision hold the craft reference's idiom and
  simplification bar rather than import a foreign pattern? The
  standards owner is a citable violation class.

Weigh in this order — a shape finding never outranks a correctness
finding.
