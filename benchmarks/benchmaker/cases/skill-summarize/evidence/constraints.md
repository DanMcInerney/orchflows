# The outcome contract

The target is a prompt. Its observable outcome is the summary it
produces from `sources.md`. That summary is correct when all four hold:

1. **Word bound.** At most 120 words, counting whitespace-separated
   tokens of the body, excluding markdown heading lines and excluding
   citation tokens themselves.
2. **Closed citation set.** Every citation token has the form `[S<n>]`
   and names an id declared in `sources.md`. An id outside that set is
   a fabrication, not a citation.
3. **Citation coverage.** Every sentence of the body carries at least
   one citation.
4. **Faithfulness.** Every claim is supported by the source it cites,
   the summary covers the rollout outcome and the incident, and it
   adds no recommendation the sources do not carry.

Constraints 1–3 are decidable by reading bytes. Constraint 4 is not:
two summaries can both satisfy 1–3 while one of them attaches a real
citation to a claim its source never made.

The prompt must declare 1–3 in a machine-readable form so a checker can
confirm the prompt carries the contract rather than inferring it from
prose. The declaration block is fenced with the info string
`constraints` and holds one `key: value` per line:

    max_words: 120
    citation_ids: closed
    citation_coverage: every-sentence
