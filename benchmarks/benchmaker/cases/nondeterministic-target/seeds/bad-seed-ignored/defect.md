# Defect: the seed argument is accepted and never used

A module-level `random.Random()` is built from system entropy at
import and reused for every call; `draw` takes `seed` and ignores it.
The shard distribution stays correct — a 20,000-draw audit still lands
inside the 1.5-point tolerance — and only the property the runbook
replays incidents with is gone: two calls with the same seed return
different streams, and no archived trace ever reproduces. A benchmark
whose nondeterminism handling is "average many runs" or "assert the
histogram" scores this seed as a pass. Catching it requires either an
expected stream recorded for a pinned seed or an explicit same-seed
run-to-run equality case; both are the seed-pinning discipline this
angle exists to force.
