# Code craft

The shape principles every domain shares are
[rules/token-economy.md](../../../rules/token-economy.md) §10's.

## Vocabulary

- **seam** — a public boundary where behavior is observable and
  testable; completion checks live at seams.
- **tracer** — a thin end-to-end slice proving the seams early, before
  anything widens.
- **idiom** — the surrounding code's existing names and patterns; new
  code reconciles to them, never imports a foreign style.

## Shape

- Locality: a module owns one concern at one-read size (~100–500 lines);
  past the band presume a second concern — split at a seam, never shave
  prose to fit. Grow sideways: a new module at a seam, never girth.
- Explicit over clever: static, followable call sites; no runtime
  registries or metaprogrammed dispatch — they blind exact search and
  language servers at once.
- Failure is loud and typed: a silent fallback hides the red a later
  agent needs.
- Comments state only what code cannot: the module's opening contract,
  invariants, ordering constraints, why-not-the-obvious.
- Test economy: one deterministic, parallel-safe check per behavior at
  its seam; internals earn none, a check repeating covered behavior is
  deleted, and suite time is paid by every future change.
- Checks pin shapes, never sentences: assert a field, a set, a count
  by kind, or a verdict — never an owner file's prose; a ratchet
  counts the kind it was written for. A check reading an owner file
  reads a stable anchor — a heading, a backticked name, a fenced
  command — and its wrong result drops the fact, not the anchor,
  which would only prove the grep.

## Lens

- Correctness: does the revision satisfy the spec's acceptance,
  including its failure paths, not only the happy path?
- Contract fidelity: does every public seam still honor its declared
  Require/Return shape for callers outside this revision?
- Diff: does every changed line contribute to Goal inside the spec's
  stated surface — nothing incidental swept in, no check weakened to
  reach green?
- Shape: does the revision hold the idiom and simplification bar above
  rather than import a foreign pattern? The standards owner is a
  citable violation class.

Weigh in this order — a shape finding never outranks a correctness
finding. A finding is `blocking: true` when it shows a frozen
completion criterion false, or is a correctness finding at the fixed
identity; contract fidelity with no criterion failing, scope and shape
are `blocking: false` — reported, never repaired in the same run.

## Execute stages

- Implement at seams, reconciling with the surrounding idiom; take the
  tracer first where Goal leaves a seam unproven.
- Checks answer to Goal, never to the code: each acceptance behavior
  carries a check derived from the ticket's Goal, its failing reading
  recorded — authored at any point, weakened at none.
- Run the narrow affected checks; the full suite is the gate's row,
  never a unit's.
- For conflict or repair work, read both candidate diffs and the accepted
  blocker ledger; resolve only evidence-backed overlap and record the
  resulting identity.
- A clean repair is an explicit empty-set proof, not an unrecorded no-op.
- Conclude by recording the commit hash, commands run, and outstanding caveats.
