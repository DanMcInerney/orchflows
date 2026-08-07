Masks only the first secret in a line (`count=1`). Every one of the four
evidence examples carries at most one secret, so this variant reproduces all
four exactly; only the intent sentence's "every value" makes it wrong. A
benchmark built by transcribing the examples into cases passes this variant,
which is the whole failure mode the sparse-evidence angle tests: thin evidence
must be read for its stated intent and its uncovered boundaries declared as
gaps, not narrowed to the examples that happen to be written down.

deviation: quantifier-narrowing
