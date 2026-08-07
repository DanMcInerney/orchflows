# candidate-ranking — what a qualified benchmark must demonstrate

Angle: **ranking**. Every other positive case proves benchmaker can
build a pass/fail benchmark for one implementation. This case tests
whether benchmaker produces a benchmark whose outcome is a rankable
quantity over a candidate set — the shape `evolve`,
`skill-tournament`, and `orch-panel` consume. The target is a
candidate-set ranker; a qualified benchmark for it must demonstrate,
on its own evidence:

- **a total order or explicit ties** — equal aggregates share one
  rank under competition-style numbering, never an arbitrary order;
- **a margin the scoring declares** — adjacent score differences are
  part of the outcome, not an afterthought;
- **required deterministic failure excluded from ranking** — an
  ineligible candidate is removed, not ranked low
  (`docs/benchmaker.md`: required failure never enters ranking);
- **aggregation fixed before candidates are seen** — the weights file
  is the whole policy; nothing derived from the candidate set may
  bend it (the candidate-blind design law).

## Discrimination (required)

The produced benchmark must score `target/rank.py` and
`seeds/good-alt/rank.py` as passing and each of these as failing:

| seed | reachable only through |
| --- | --- |
| `bad-reweight-goodhart` | a candidate set with complementary pass patterns, where rarity-scaled weights flip the fixed-weight order |
| `bad-tie-arrival` (near-miss) | an exact score tie observed under two permutations of the record arguments, or the `tie` marker and rank skip checked directly |
| `bad-self-score` | a record carrying a `self_score` key that contradicts its computed aggregate |
| `bad-inert-no-order` | any case that observes ordering at all — one rank line, one margin, one exclusion |

`seeds/good-alt` is a second correct ranker with different internals
(queue-scan parsing, groupby grouping). A benchmark that imports the target and calls
its helpers rather than running the command-line contract fails
good-alt and is not qualified: the outcome under test is the
process's bytes and exit status.

Failing `bad-tie-arrival` is the discrimination floor. A benchmark
whose candidate sets all have distinct scores has established that
the tool sorts, not that its published order is independent of
arrival — the exact nondeterministic-rank defect a ranking consumer
cannot tolerate.

## Oracle shape

- Exact stdout bytes with LF endings — rank lines, then margin lines,
  then exclusion lines. Two seeds survive any oracle that only checks
  which candidate is first.
- Permutation invariance is part of the outcome: the same records in
  a different argument order must produce identical bytes.
- Exit status is part of the outcome: 0 on success — including the
  all-excluded run — and 2 with empty stdout on every usage error.
- The self-declared law: a benchmark case must include a record with
  an extra self-description key and score it by computed aggregate
  only. Self-declared evidence never enters ranking, mirroring the
  qualification law that self-declared verdicts qualify nothing.

## Reproducibility

Fixed JSON bytes in, fixed text bytes out. Integer arithmetic only —
no floats, no clock, no randomness, no network. Two runs of the
produced benchmark on the same implementation yield identical
verdicts; the ranking itself must be identical under record-argument
permutation.

## Cost

Within `bound`: one full benchmark run under 10 s wall clock, single
process, stdlib only, at most 25 cases. Rankings over three to five
synthetic candidates are ample; discrimination, not scale, is what
this case pressures.

## Gaps

None. `evidence/spec.md` fixes every clause the seeds touch, and
`evidence/records/` exhibits a complete worked invocation. A blocked
or gap-declaring return is the wrong answer for this case.
