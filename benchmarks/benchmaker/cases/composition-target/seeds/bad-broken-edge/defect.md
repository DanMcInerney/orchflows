# Planted defect: the edge carries an artifact nobody made — the near-miss

The single edge reads `seq collect → reduce — carries `notes.md``, but
`collect` produces `notes.jsonl`. Both step ids resolve, the chain
covers every step with one start and one end, every step is bound by an
invariant, and the done check names the terminal artifact and states a
predicate over it. One backticked identity in one edge does not resolve
to anything the file declares, and the handoff it describes is between
`reduce` and a file no step produces.

This is the near-miss. Every check a structural validator reaches for
first — step ids declared, edges well formed, chain connected,
invariants present, done check non-trivial — passes. A benchmark built
around the graph of step ids scores this file clean, because the graph
is intact: it is the artifact identity riding the edge that dangles, and
artifact identities are the thing the id graph does not model.

A benchmark for this target must catch it, because the carried identity
is the whole content of `seq`: the predecessor's result becomes the
successor's evidence, so an edge whose artifact resolves to nothing
describes a step consuming evidence that was never produced. Catching it
requires the benchmark to have modeled produces/consumes as a second
relation over the same steps — which is precisely the modeling decision
that separates a benchmark of a workflow from a benchmark of a graph.
