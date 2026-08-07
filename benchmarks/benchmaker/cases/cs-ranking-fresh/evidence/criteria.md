# Candidate criteria — eligibility spec and scored criteria

The fixed inner target is the four candidate release-note artifacts in
`candidates/`. A benchmark package for this target verifies, then
ranks. Candidate identity is the file stem.

## Required deterministic criteria (eligibility)

- R1: a line exactly `## Summary` is present.
- R2: no line exceeds 80 characters.
- R3: a line matching `version = "<digits>.<digits>.<digits>"`
  (exactly that shape, double quotes) is present.

Verification is decided before any scoring. A candidate failing any
required criterion is EXCLUDED: it never receives a rank, not even
last place.

## Secondary scored criteria

- S1: one point per `## ` section heading, capped at five.
- S2: two points when a `## Risks` section is present.
- J1 (judged class): a clarity band scored from the fixed candidate
  bytes and from nothing else — two points when no line exceeds 60
  characters, otherwise one point. The judge never executes,
  re-derives, or regenerates a candidate; its input is the frozen
  evidence.

Aggregate = S1 + S2 + J1.

## Tie policy law

Ties must be declared, deterministic, and never arrival-ordered: the
package's scoring must state its tie rule; equal aggregates share one
competition rank with an explicit tie marker; and the published
ranking must be byte-identical under any permutation of the input
order.

## Published ranking grammar

The package's runner prints the ranking to stdout, one line per
candidate, in exactly these two line forms:

    EXCLUDED <candidate-id> [<detail>...]
    RANK <rank> <candidate-id> <aggregate> [TIE]

Whitespace-separated tokens; on an `EXCLUDED` line the candidate id is
the second token; on a `RANK` line the tokens are the literal `RANK`,
the competition rank, the candidate id and the aggregate score, and a
shared rank carries the literal final token `TIE`. Every input
candidate appears on exactly one line.

## Scoring declaration

`scoring/policy.json` declares the scoring law with at least these
keys and values:

    {
      "verification_before_judging": true,
      "judge_scope": "fixed-evidence",
      "tie_policy": {
        "declared": true,
        "deterministic": true,
        "rule": "<the tie rule, stated as a non-empty string>"
      }
    }

## Package command lines

The package exposes `runner/run.py`, `scoring/policy.json` and
`scoring/aggregate.py`, whatever its manifest locators say:

- `python runner/run.py --verify-only <candidate-or-impl-dir>` — runs
  required verification only; the exit code is the verdict (0
  eligible, nonzero not).
- `python runner/run.py <candidate.md> [<candidate.md>...]` — verifies
  then ranks the given fixed candidates and prints the published
  ranking grammar above; exit 0 on a completed ranking.
- `python scoring/aggregate.py <ranking.txt>` — re-checks a saved
  ranking artifact against the grammar and tie law; exit 0 when it
  conforms.

Manifest and qualification record shapes are in `interchange.md`
beside this file.
