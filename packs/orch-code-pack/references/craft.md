# Code craft

The code domain's terms and shape, per the signature's craft cell. Read
[rules/token-economy.md](../../../rules/token-economy.md) §10 for the
shape principles every domain shares; the bullets under Shape are
code's own.

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

- Never assemble an identifier by string concatenation; never drift to
  a synonym across modules.
- Locality: the unit is a module at roughly one-read size (~100–500
  lines).
- Explicit over clever: static, followable call sites; no runtime
  registries or metaprogrammed dispatch — they blind exact search and
  language servers at once.
- Comments state only what code cannot: invariants, ordering
  constraints, why-not-the-obvious.
- Nonzero exit is data: an expected nonzero exit from a read-only
  probe (a search with no matches, `git diff --no-index` on differing
  inputs) reports a result, not a tool failure — one probe's expected
  nonzero exit, or one absent path, never fails its sibling lanes in a
  parallel inspection.
- Shell probes use one dialect end to end. On Windows, pass `rg` concrete
  literal roots and use `-g` for filename globs; prefer literal or fixed-string
  patterns and the fewest quoting layers. In PowerShell, accumulate loop
  results before piping or formatting them.
