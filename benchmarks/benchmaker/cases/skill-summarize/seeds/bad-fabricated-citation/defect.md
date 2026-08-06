# Planted defect: the citation set is opened

This variant declares `citation_ids: open` and instructs the writer to
close gaps with "the plausible source id the reader would expect". Its
summary is the predictable consequence: two sentences — the rollback
runbook and the customer refunds — carry `[S7]` and `[S9]`, ids no
heading in `evidence/sources.md` declares, attached to claims no source
in the set makes. Everything else holds: the prose is inside the word
bound and every sentence is cited, so the digest reads as the most
thorough of the four variants.

A benchmark for this target must catch it, because this is the failure
mode of a cited-summary prompt that costs a reader the most: a
fabricated citation does not look like an error, it looks like
evidence. A benchmark that only counted citations, or only checked that
each sentence had one, would score this variant highest. Resolving each
cited id against the closed source set is the cheapest check that
separates a citation from its imitation — and it is the deterministic
half, so a produced benchmark that leaves this to a judge has put a
byte-decidable fact behind a scoring opinion.
