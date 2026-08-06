# What a qualified benchmark for `store.py` must demonstrate

The target carries state across process boundaries. A benchmark for it is
judged as much on its harness as on its assertions: a suite that cannot
guarantee the store starts empty is measuring the previous run.

## Setup and teardown isolation — the required proof

The produced benchmark must demonstrate, as a first-class result and not as a
remark:

1. **Fixed state location.** The suite chooses the state path it passes to
   `--state`; it never lets the tool pick one, and never reuses the
   repository or the user's home for it.
2. **Setup from clean.** Each suite run begins with that location absent.
3. **Teardown.** Each suite run removes what it created, leaving nothing
   behind for the next.
4. **Two consecutive suite runs from clean state agree.** Run the whole
   suite, tear down, run it again: the second run's outcome — every command's
   exit code and output, in order — must equal the first's. A benchmark that
   reports only pass or fail per run, with no transcript to compare, cannot
   make this claim and does not qualify.

Point 4 is the one that costs something and the one that matters. It is the
only check that reaches state escaping the declared location, because such
state is invisible to the run that creates it.

## Discrimination

The benchmark must pass `target/store.py` and `seeds/good-variant/`, and fail
all three bad seeds:

| seed | caught by | reachable in one suite run? |
| --- | --- | --- |
| `bad-state-leak` | the two-run transcript comparison | no |
| `bad-delete-masks` | deleting an already-deleted key, and a key never stored | yes |
| `bad-overwrite-empty` | overwriting with the empty string | yes |

`bad-state-leak` is the case's point: it passes a complete, careful single
suite run and fails only when a second run from clean state disagrees with the
first. A benchmark that runs its suite once certifies it. `bad-overwrite-empty`
is the near-miss: correct for every non-empty value, so only a scenario that
treats the empty string as data catches it.

The good variant stores the same state in a different on-disk encoding: any
assertion against the state file's bytes, key order, or whitespace fails a
good seed, which is itself a benchmark defect. Oracles must be written against
the CLI contract.

## Reproducibility and cost

There is no clock, no network, and no randomness; every difference between two
runs is state. Each command is one short subprocess, so the whole suite — run
twice — stays inside the case bound. A benchmark that grows the scenario
combinatorially buys no discrimination the two-run comparison does not already
give.

## Out of scope

Concurrency and locking; state file corruption recovery; performance; the
state file's format.
