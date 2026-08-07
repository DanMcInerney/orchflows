# Provenance — candidate-ranking benchmark package

Source trace (case evidence -> package component):

- evidence/criteria.md (eligibility spec R1-R3, scored criteria
  S1/S2/J1, tie policy law) -> cases/cases.json, scoring/policy.json,
  runner/run.py.
- evidence/candidates/ (the four fixed artifacts) -> the pool this
  package verifies and ranks; their bytes are inputs, never copied
  into this package.

This provenance records ranking machinery only. No comparison of the
fixed candidates is authored here; the published ranking is the
package's runtime output, produced by the machinery above.

Licensing: synthesis@41ee9ea2 claims 21,59 — verification decides
eligibility before judgment, and required deterministic failure never
enters a ranking.
