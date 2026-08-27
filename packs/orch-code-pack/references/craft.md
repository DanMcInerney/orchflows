# Code craft

The shape principles every domain shares are
[rules/token-economy.md](../../../rules/token-economy.md) §10's.

## Vocabulary

- **seam** — a public boundary where behavior is observable and
  testable; completion checks live at seams.
- **tracer** — a thin end-to-end slice proving the seams early, before
  anything widens.
- **tautological check** — a check that asserts the implementation's
  shape instead of its behavior; void per rules/verification.md §8.
- **idiom** — the surrounding code's existing names and patterns; new
  code reconciles to them, never imports a foreign style.

## Shape

- Locality: the unit is a module at roughly one-read size (~100–500
  lines).
- Explicit over clever: static, followable call sites; no runtime
  registries or metaprogrammed dispatch — they blind exact search and
  language servers at once.
- Comments state only what code cannot: invariants, ordering
  constraints, why-not-the-obvious.
- Checks pin shapes, never sentences: a test asserts a field, a set, a
  count by kind, or a verdict — not an owner file's prose, and never a
  whole report where it means one finding kind; a ratchet counts the
  kind it was written for. Where a check must read an owner file, it
  reads a stable anchor — a heading, a backticked name, a field, a
  fenced command — never a sentence; the wrong result it fails against
  drops the fact, not the anchor, which would only prove the grep.

## Lens

- Correctness: does the revision satisfy the spec's acceptance,
  including its failure paths, not only the happy path?
- Contract fidelity: does every public seam still honor its declared
  Require/Return shape for callers outside this revision?
- Diff: does every changed line contribute to Goal, with no unrelated change
  and the spec's stated surface, with nothing incidental swept in?
- Shape: does the revision hold the idiom and simplification bar above
  rather than import a foreign pattern? The standards owner is a
  citable violation class.

Weigh in this order — a shape finding never outranks a correctness
finding. A finding is `blocking: true` when it shows a frozen
completion criterion false, or is a correctness finding at the fixed
identity; contract fidelity with no criterion failing, scope and shape
are `blocking: false` — reported, never repaired in the same run.
