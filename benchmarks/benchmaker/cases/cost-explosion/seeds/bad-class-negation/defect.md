# Planted defect: a leading `!` is read as a set member

`_parse_class` drops the branch that consumes a leading `!` and sets
`negated`, so `[!a]` becomes the ordinary set `{!, a}` — it matches the
two characters it was written to exclude and rejects everything else.
Only patterns that negate a set can distinguish it, and the shortest of
those is four characters (`[!a]`), so no exhaustive sweep of patterns
three characters or shorter sees it at all. In the smallest sweep that
can — both strings at four characters or fewer, 893,101 pairs — exactly
27 pairs separate it from the reference, one pair in 33,000. A uniform
sample of 2,000 pairs from that space is expected to contain 0.06 of
them. A benchmark catches this defect by choosing negated sets on
purpose, which is the case's demand: the evaluation must be selected
from the input space, not drawn from it.
