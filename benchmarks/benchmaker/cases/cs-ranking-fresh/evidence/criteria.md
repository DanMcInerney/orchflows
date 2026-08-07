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
