# What a qualified benchmark for nondeterministic-target must show

## The measured failure

The target is random, so a benchmark can only score it by removing the
randomness — and the three seeds are chosen so that each of the two
cheap ways of doing that catches at most one of them:

| benchmark strategy | bad-uniform-weights | bad-seed-ignored | bad-restream |
| --- | --- | --- | --- |
| same seed twice, outputs equal | pass | **caught** | pass |
| histogram within a tolerance | **caught** | pass | pass |
| pinned seed vs recorded stream | **caught** | **caught** | **caught** |

A benchmark that reruns and averages, or that asserts only on shares,
certifies a picker whose stream nobody can replay. `bad-restream` is
the near-miss: reproducible, correctly weighted, and wrong — it fails
only against a fixed expected stream.

## Required of the produced benchmark

1. **Every case pins a seed.** No case may assert on an unpinned run,
   and no case may accept "any of these outputs". An unpinned case is
   a reproducibility failure of the benchmark itself, whatever it
   claims about the target.
2. **At least one recorded-stream case.** The full list for a pinned
   seed and draw count compared for equality against a fixed expected
   list. Pinning without a recorded expectation catches nothing but
   `bad-seed-ignored`.
3. **At least one same-seed repeat case.** Two calls, or two
   processes, under one seed must return identical streams. This is
   what makes the `bad-seed-ignored` verdict deterministic rather than
   probabilistic: an entropy-driven picker would have to reproduce
   both the recorded stream and itself, which for a 12-draw stream is
   below 1e-15.
4. **A distributional case with a declared sample size and
   tolerance.** If the benchmark carries a statistical oracle it must
   state both numbers and run under a pinned seed. The runbook's
   published tolerance is 1.5 percentage points at 20,000 draws —
   shard 0 between 5,700 and 6,300. An undeclared tolerance, or a
   tolerance wide enough to admit a uniform picker (16.7 against 30
   points), is a qualification failure.
5. **Cross-process reproducibility.** At least one case exercises the
   `--seed` CLI in its own process, so a picker seeded per import
   rather than per call cannot hide inside one interpreter.
6. **Discrimination stated as a score.** Each seed named with its
   verdict; every `bad-*` seed fails at least one case, and
   `good-cumulative` — a bisect rewrite with an identical stream —
   passes every case. Failing `good-cumulative` means the benchmark is
   asserting on internals, and its discrimination number is void.
7. **Cost within bound.** Under `case.toml`'s bound: the
   distributional case is capped at 20,000 draws, and the run stays
   under 10 s. Averaging thousands of runs to beat down noise is the
   cost failure this angle invites — pin the seed instead.

## Protected evidence

`seeds/` is ground truth and is never referenced by `evidence/` or by
`target/`. The evidence records the stream for seed 3 only; the
probe's seeds, 7 and 11, are held back so a benchmark that merely
copies the recorded example is still scored against streams it has not
seen.
