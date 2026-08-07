# bad-inert-no-order

The inert variant: the intended behavior is absent. Every input is
parsed and validated exactly like the reference — usage errors still
exit 2 — but no aggregation happens at all. The seed prints the
candidate names in arrival order, one per line, with no ranks, no
scores, no ties, no margins, and no required-failure exclusions, and
exits 0 as if that were a ranking.

This is the qualification protocol's mandatory inert seed for the
ranking outcome. Any benchmark that actually observes ordering —
compares one rank line, one margin, one exclusion — fails it
immediately. A benchmark this seed passes is not observing the
intended behavior (for instance, one that only checks the exit
status, or that the output mentions every candidate), and its
discrimination for ordering must be recorded UNVERIFIED.

deviation: ordering-absent
