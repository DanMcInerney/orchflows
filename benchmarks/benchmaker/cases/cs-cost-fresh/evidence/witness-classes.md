# named defect witness classes — W1, W2, W3

Historical defects in engines of this shape fall into three named
classes. A benchmark input WITNESSES a class when it can distinguish a
correct engine from an engine carrying that class's defect; a suite
that carries no witness for a class cannot see that class's defect at
all.

## W1 — start-boundary equality (dense, ~2 in 10)

Defect family: range boundaries treated exclusively at the start.
Witness: a query whose `start` equals the timestamp of at least one
record matching the query's level predicate.

Density: the fixed corpus holds 20,000 records over a 100,000-second
span, so a uniformly chosen query boundary lands on some record's
timestamp roughly 2 times in 10. Witnesses are everywhere; missing this
class takes effort.

## W2 — duplicate timestamps (medium, ~1 in 10^2)

Defect family: records collapsing on timestamp collision (only the
first of equal-timestamp records counted).
Witness: a query whose range contains at least two records sharing a
timestamp, both matching the level predicate.

Density: the generator reuses the previous record's timestamp once per
100 records, so ~200 collision pairs exist among 20,000 records — a
1-in-10^2 class. A moderately wide window usually catches one.

## W3 — day-rollover instant (sparse, ~1 in 10^4)

Defect family: records at a UTC day rollover instant (`ts % 86400 ==
0`) dropped by day-bucketing index layers; the narrowest variants drop
the rollover record only when it sits exactly at the query's start
boundary.
Witness: a query whose `start` equals the timestamp of a
rollover-instant record in the corpus (the record matching the level
predicate). Such a witness catches both the broad drop and the
boundary-instant variant.

Density: the generator plants one rollover-instant record per 10,000
records — density 10^-4, exactly two such records in the fixed corpus,
and their instants are 2 values out of 100,000 possible boundary
choices. Blind uniform selection needs on the order of 10^4 draws to
hit one; the budget is 60 queries. A suite witnesses W3 by deliberate
selection or not at all.
