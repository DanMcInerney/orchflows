# Defect: every shard is picked uniformly, weights unread

`draw` returns `rng.randrange(len(WEIGHTS))`, so all six shards take
about 16.7 percent of the traffic and `WEIGHTS` is decoration. The
seed still pins the stream, so a benchmark that only checks
reproducibility — same seed twice, same answer — scores it as a pass.
Under a pinned seed of 11 across 20,000 draws shard 0 takes 3,379
instead of 6,099, roughly thirteen points below its weight and far
outside the runbook's 1.5-point tolerance. A benchmark catches it by
comparing an exact recorded stream, or by a distributional case with a
declared sample size and tolerance; a benchmark carrying neither is
testing that the tool is repeatable, not that it is right.
