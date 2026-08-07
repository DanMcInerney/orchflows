# Planted defect (near-miss): ranges exclude their upper endpoint

`_in_class` keeps `char == low` for single members but tests
`low <= char < high` for genuine ranges, so `[a-c]` matches `a` and `b`
and rejects `c`. This is the case's near-miss: every other construct —
literals, `*`, `?`, plain sets, negation, `[a-a]`, malformed patterns —
behaves exactly as the reference does, so the only witnesses are inputs
whose pattern carries a real range and whose subject presents that
range's upper endpoint at that position. The shortest such pattern is
five characters (`[a-c]`), so an exhaustive sweep of patterns four
characters or shorter cannot see it at any subject length. In the
smallest sweep that can — both strings at five characters or fewer,
24,180,520 pairs — exactly 18 pairs separate it from the reference, a
density of 7.4e-7; a uniform sample of 2,000 pairs is expected to
contain 0.0015 of them. Only an evaluation that reasons from the
language's boundary rules and picks the endpoint deliberately catches
it, and that is what a benchmark for this target has to demonstrate
inside the cost bound.

deviation: boundary-shift
