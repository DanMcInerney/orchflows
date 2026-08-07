# Planted defect: the pattern is no longer anchored at the end

`_step` returns `True` as soon as the pattern is exhausted instead of
returning `si == len(subject)`, so a pattern that matches any prefix of
the subject reports a match: `match("a", "ab")` and `match("", "a")`
are both true. This is the cheap defect of the case and it is meant to
be: 36 of the 1,183 pairs whose pattern and subject are both two
characters or shorter separate it from the reference, so even the one
exhaustive truncation that fits the cost bound catches it. A benchmark
that misses this one is not discriminating at all, and its presence
gives the case a floor — a candidate evaluation cannot score by
covering only the exotic corners.

deviation: guard-deletion
