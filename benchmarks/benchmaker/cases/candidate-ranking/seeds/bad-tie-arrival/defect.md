# bad-tie-arrival (near-miss)

Equal scores are not a tie here. The seed sorts eligible candidates by
score with a stable sort and hands out strictly sequential ranks, so
two candidates on the same score land on different ranks in whatever
order their records arrived on the command line. No `tie` marker is
ever printed, the rank after k equal scores is not skipped, and a
zero margin is reported between "adjacent" candidates that the
contract says share one rank.

On every input whose scores are distinct this seed is byte-identical
to the reference — ranks, margins, exclusions, exit codes, all of it.
It is reachable only through a case that both produces an exact score
tie and observes arrival-order independence: score the same records
under two permutations of the arguments, or check the `tie` marker
and competition-style rank skip directly. A benchmark whose candidate
sets happen to have all-distinct scores reports this ranker correct
while its published order silently depends on the order the harness
happened to enumerate candidates — the nondeterministic-rank failure
this case's angle exists to catch. This near-miss is the case's
discrimination floor.

deviation: arrival-order-tie-break
