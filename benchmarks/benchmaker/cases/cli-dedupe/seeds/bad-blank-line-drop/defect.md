# bad-blank-line-drop

The retention loop skips any empty line before computing its key, so
every blank line is deleted from the output instead of being treated as
an ordinary line whose key is the empty string. The contract states the
first blank line in a window is retained and later ones are suppressed
like any other repeat. On input with no blank lines the seed is
byte-identical to the reference.

A quality benchmark for a deterministic CLI must catch this because the
empty line is the input alphabet's boundary value, and a text filter
that eats paragraph breaks corrupts every prose document it touches.
Catching it requires a case whose input actually contains a blank line —
a benchmark built only from word-list fixtures never generates one.
Blank-line handling is also the difference between "retained lines" and
"non-empty lines" as the window's unit, so a suite that ignores it is
blind to a whole class of window drift as well.

deviation: input-class-drop
