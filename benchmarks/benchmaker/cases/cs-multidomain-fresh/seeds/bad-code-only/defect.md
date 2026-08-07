# bad-code-only

The document domain was dropped from the package's input space: the
runnable case set contains only code-domain cases, scoring requires
only code-domain ids, and the doc-domain case mappings are gone. The
code-domain half is entirely lawful — parsing, ordering, exit-code
and CRLF cases all discriminate — so an implementation that renders
an unlawful document while computing the right entries scores as
correct. A cross-domain target has been benchmarked as a single-domain
target; the single-domain-blindness pair in the fixed inner pool
makes the omission observable: the code-correct/doc-broken variant
passes this package.

deviation: input-class-drop @ document-domain locus (doc cases absent from the runnable case set and scoring)
