# cli-dedupe — what a qualified benchmark must demonstrate

Angle: **deterministic-cli**. This case tests whether benchmaker
produces a benchmark with a crisp, byte-exact outcome and enough
boundary coverage to separate a correct implementation from a
near-miss.

## Discrimination (required)

The produced benchmark must score `target/dedupe.py` and
`seeds/good-alt/dedupe.py` as passing and each of these as failing:

| seed | reachable only through |
| --- | --- |
| `bad-default-unbounded` | a no-flag invocation whose repeats are not adjacent |
| `bad-ignore-case-output` | `--ignore-case` on mixed-case input, scored on exact bytes |
| `bad-blank-line-drop` | input that contains a blank line |
| `bad-window-off-by-one` (near-miss) | an explicit `--window N` with a repeat at distance exactly `N + 1` |

`seeds/good-alt` is a second correct implementation with different
internals and no `dedupe` function. A benchmark that imports the target
as a module and calls its helpers, rather than running the command-line
contract, fails good-alt and is not qualified: the outcome under test is
the process's bytes and exit status, not its call graph.

Failing the near-miss is the case's discrimination floor. A benchmark
that catches only `bad-default-unbounded` has established that the tool
deduplicates, not that it obeys its contract, and must not be qualified.

## Oracle shape

- Exact stdout bytes, not line counts, sorted sets, or
  case-insensitive comparison — two of the seeds survive any oracle that
  normalises output.
- Exit status is part of the outcome: 0 on success, 2 on a negative
  `--window` and on an unreadable input file.
- stdin and the `FILE` argument are the same contract and both must be
  exercised.

## Reproducibility

Every case is a fixed byte string in, a fixed byte string out. No clock,
no randomness, no network, no filesystem state beyond a temporary input
file. Two runs of the produced benchmark on the same implementation must
yield identical verdicts. Output must be compared with `\n` line
endings on every platform.

## Cost

Within `bound`: a full run under 10 s wall clock in one process, at most
25 cases. The input space here is small enough that an exhaustive suite
would also fit — the discrimination requirement, not the budget, is what
this case pressures.

## Gaps

None. `evidence/spec.md` fixes every clause the seeds touch, and the
changelog names the historical directions of drift. A blocked or
gap-declaring return is the wrong answer for this case.
