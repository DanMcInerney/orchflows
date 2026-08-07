# Defect: band subtotals round to nearest instead of flooring

Each discounted band subtotal is `round(x / 100)` rather than
`x // 100`, so a fraction of a cent is rounded up instead of dropped —
16 units at 199 bills 3045 instead of 3044, and 64 units at 175 bills
9844 instead of 9843. This is the near-miss: it agrees with the
reference on every order whose discounted band subtotals land on a
whole cent, and every worked example in `evidence/` was written with a
list price of 250, 400 or 1000, which does exactly that. A benchmark
catches it only by pricing an order whose band subtotal is fractional
— a list price that is not a multiple of ten, at a quantity that
reaches the volume or bulk band. It is the second reason
example-mirroring fails here: the visible evidence is silent on the
one input class that separates a documented rule from its plausible
neighbor.

deviation: boundary-shift
