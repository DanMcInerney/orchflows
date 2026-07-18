# Code craft

The code domain's terms and shape, per the signature's craft cell.

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

What a metered, search-navigating reader pays least for:

- One name per concept, one concept per name; symbols unique enough
  that exact search finds every use. Never assemble an identifier by
  string concatenation; never drift to a synonym across modules.
- Locality: a module owns one concern end to end at roughly one-read
  size (~100–500 lines); understanding one feature never requires a
  scatter-gather across layers.
- Flat application code: breadth parallelizes, depth serializes. Add
  depth only behind a contract strong enough that readers never
  descend past it.
- Explicit over clever: static, followable call sites; no runtime
  registries or metaprogrammed dispatch — they blind exact search and
  language servers at once.
- Comments state only what code cannot: invariants, ordering
  constraints, why-not-the-obvious.
- Design for the oracle: behavior a completion test cannot observe at
  a seam is shaped wrong, whatever its elegance.
- Nonzero exit is data: an expected nonzero exit from a read-only
  probe (a search with no matches, `git diff --no-index` on differing
  inputs) reports a result, not a tool failure — one probe's expected
  nonzero exit, or one absent path, never fails its sibling lanes in a
  parallel inspection.
- Shell probes use one dialect end to end. On Windows, pass `rg` concrete
  literal roots and use `-g` for filename globs; prefer literal or fixed-string
  patterns and the fewest quoting layers. In PowerShell, accumulate loop
  results before piping or formatting them.
