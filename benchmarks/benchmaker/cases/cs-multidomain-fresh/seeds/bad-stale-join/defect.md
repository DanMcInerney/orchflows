# bad-stale-join (near-miss)

The provenance chain still records two single-pack constructions in
a lawful order, but the document lane's `consumes_identity` is a
stale digest that matches no upstream `output_identity`: the doc
cases reference the code lane's output by an identity the join never
froze. Everything else is lawful — both domains are cased, the manifest is
schema-valid, the inner pool splits exactly as the reference package
splits it, and the qualification record is complete. That is what
makes this the near-miss: the packages differ by one identity string,
and only the join law (each edge consumes exactly the upstream frozen
identity) separates them. A benchmark whose cross-domain join is
unfrozen can silently drift: either lane can be rebuilt without the
other noticing.

deviation: dangling-reference @ cross-domain join locus (consumes_identity does not match the upstream frozen output_identity)
