# Planted defect: the bound is raised, then spent

This variant declares `max_words: 400` where the case's contract is 120,
and its prose pushes the other way too — "restating a source in full is
a feature, not padding". The summary it produces obeys its own inflated
bound and runs far past the case's: every citation resolves, every
sentence is cited, and the result is not a summary at all but the
source set retyped at length.

A benchmark for this target must catch it, because a length bound is the
only thing separating a summary from its input, and it is the constraint
a prompt most easily launders — not by ignoring the bound, but by
restating it more generously and then honoring the restatement. So the
bound has to be held by the benchmark, not read out of the candidate:
any benchmark that extracts `max_words` from the prompt under test and
scores against that number scores this variant as compliant. Holding the
case's own constant is what makes the check failable, and a failable
oracle is the qualification requirement this seed exercises.

deviation: constraint-relaxation
