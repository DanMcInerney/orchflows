# bad-default-tie

The scoring policy declares no tie rule, and the runner silently
applies its sort's stable default: equal aggregates keep input
arrival order and receive strictly sequential ranks with no tie
marker. On any pool with distinct scores the output is byte-identical
to the reference; only an exact tie observed under two input
permutations exposes the undeclared default. Locus note: the
default-substitution census name was burned at the cli-dedupe family
(a CLI default-value locus); this seed's locus is the ranking tie
policy, a different family and a different mechanism, per the
design's fresh-locus argument.

deviation: default-substitution @ tie-policy locus (an undeclared arrival-ordered default tie break silently applied)
