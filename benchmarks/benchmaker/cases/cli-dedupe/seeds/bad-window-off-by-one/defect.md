# bad-window-off-by-one (near-miss)

The window eviction test reads `len(recent) > window + 1`, so the seed
remembers one more retained line than `--window N` permits. A repeat at
a distance of exactly `N + 1` retained lines — which the contract says
has fallen out of the window and must be retained — is suppressed
instead. Every other distance, every default-window run, and every flag
combination behave exactly like the reference.

A quality benchmark for a deterministic CLI must catch this because
`--window N` is the target's only numeric parameter and the boundary at
distance `N + 1` is the only place its value is observable at all. The
near-miss is reachable only by a case that pins a concrete `N` and
places a repeat one line beyond it: an input like `a b c a` under
`--window 2`. A suite that exercises the tool only in its default
unbounded mode, or that puts repeats adjacent to each other, scores this
seed identical to the reference and reports a benchmark that cannot
distinguish a correct window from a wrong one. This is the case's
discrimination floor — a benchmark that misses it has tested that
dedupe deduplicates, not that it obeys its contract.

deviation: boundary-shift
