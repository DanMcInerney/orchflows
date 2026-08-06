# Good variant: cumulative table plus bisect, same stream

The linear walk over the weight table is replaced by
`bisect_right` over a cumulative table. The random draws are consumed
in the same order and the picks are identical to the reference for
every seed — verified over 400 seeds at 50 draws each. It is here as
the false-positive guard for this angle: a benchmark that fails this
variant is asserting on the picker's internals rather than on its
stream, and its discrimination score is worthless. Expected verdict on
every case: PASS.
