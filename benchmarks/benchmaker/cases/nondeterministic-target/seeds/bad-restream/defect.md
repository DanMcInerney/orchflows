# Defect: a fresh stream per draw, so seed 3 no longer replays

Instead of drawing from one `Random(seed)` stream, each request builds
`Random(seed + index)` and takes its first value. The result is fully
reproducible and correctly weighted — 20,000 draws under seed 11 put
shard 0 at 6,099, dead on its weight — but the stream is not the
documented one: seed 3 prints `0 0 2 3 1 0 1 2` where the notes record
`0 1 1 2 2 0 0 3`, and every archived trace stops replaying while the
histogram does not move. This is the near-miss. Reproducibility checks
pass it, distributional checks with any tolerance pass it, and only a
case that compares the full stream for a pinned seed against a
recorded expectation catches it. It is also the reason "pin a seed"
alone is not the requirement: the pinned run must be scored against a
fixed expected stream, not merely against itself.
