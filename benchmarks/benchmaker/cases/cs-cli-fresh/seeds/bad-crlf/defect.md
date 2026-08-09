# bad-crlf

The package's output comparison is strict byte equality: the
CRLF-to-LF normalization the spec's tolerance clause requires was
removed from the runner's `outputs_match`. The spec declares
line-terminator form insignificant on output, so an implementation
that emits CRLF-terminated but otherwise identical bytes conforms —
and this package fails it. Every other component is lawful: the case
set, scoring, qualification, and manifest are unchanged, and the fixed
inner pool (which emits LF throughout) scores identically to the
reference package. Only an implementation exercising the tolerance
boundary observes the deviation, which is exactly the breadth the
probe's CRLF wrapper exists to measure.

Freshness: the predecessor case family burned boundary-shift at value
and window-arithmetic loci; the line-terminator form of the oracle
comparison is a locus no predecessor seed occupied.

deviation: boundary-shift @ CRLF line-terminator locus of the package oracle's output comparison
