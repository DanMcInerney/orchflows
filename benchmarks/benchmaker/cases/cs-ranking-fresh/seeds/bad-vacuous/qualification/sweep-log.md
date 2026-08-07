# Qualification sweep log — candidate-ranking package

Inner pool sweep (eligibility verdicts, --verify-only):

- reference: VERDICT PASS
- good-variant: VERDICT PASS
- bad-no-summary: VERDICT FAIL (R1)
- bad-long-lines: VERDICT FAIL (R2)
- near-miss-line81: VERDICT FAIL (R2, at the exact boundary plus one)

Pool run over the four fixed artifacts: one EXCLUDED line for the
required-defective artifact, three RANK lines, byte-identical under
input-order permutation across two runs.

Reproducibility: integer arithmetic over fixed bytes; no clock, no
randomness. Two sweeps produced identical bytes.

Cost: full sweep completes in a fraction of one small-tier probe run.
