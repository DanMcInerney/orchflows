# Good variant: same prices, band table instead of three expressions

The three hand-written band expressions are replaced by a loop over a
`(band size, discount percent)` table that consumes the order size
band by band. Totals are identical to the reference for every input,
including the floor at each band. It is here as the false-positive
guard: a benchmark that fails this variant is scoring implementation
shape rather than price, and its discrimination score is worthless.
Expected verdict on every case: PASS.
