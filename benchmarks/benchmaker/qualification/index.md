# Qualification verdict set

Rendered by contexts disjoint from every builder, from bytes and
captured outputs only. Full entries with evidence: q1-verdicts.md
(deterministic criteria), q2-verdicts.md (evidence and judged
criteria, protected store, matched-model liveness trials),
q3-delta-verdicts.md (first re-mint delta), and
q4-supersession-verdicts.md — the AUTHORITATIVE verdict set for the
current bytes: the 2026-08-07 shape-licensing supersession (evidence
additions in all 16 cases, ~49 probe crash→clean-FAIL conversions,
store relocation) re-rendered QC-1/2/4/5/7/8/9/10 fully over current
bytes, inherited QC-6 under a git scope proof (no seed byte
changed), and recorded 0 tracebacks across 160 probe runs.

| criterion | verdict | oracle_class | context | required |
| --- | --- | --- | --- | --- |
| QC-1 schema-valid | PASS | deterministic | Q4 | yes |
| QC-2 probe inversion + declared trials | PASS | deterministic | Q4 | yes |
| QC-3 seal reproducibility | PASS | deterministic | Q4 anchors + post-re-mint verify (SEALS.md) | yes |
| QC-4 provenance-traced | PASS | deterministic | Q4 | yes |
| QC-5 equivalence bridge (64/64 through their named checks; 0 equivalent; 0 tracebacks) | PASS | evidence | Q4 full re-render | yes |
| QC-6 burn-law (0 violations; 2 defect.md freshness-paragraph deficiencies noted) | PASS | evidence | Q2, inherited by Q3+Q4 scope proofs (no seed byte changed) | yes |
| QC-7 judged rerun variance (0.0 across 3 runs, output bytes identical) | PASS | judged | Q4 re-render | yes |
| QC-8 cost-within-bound (suite sweep 171 s actual) | PASS | deterministic | Q4 | yes |
| QC-9 canary integrity (16/16 public placements incl. new evidence files clean; store migrated byte-identical, protected half in all 5 store files) | PASS | deterministic | Q4 | yes |
| QC-10 blocked-return shape | PASS | deterministic | Q4 | yes |

Overall: PASS with the weakest oracle_class judged (QC-7). QC-3's
oracle is `tools/seal_set.py --verify` over the shipped tree; its
run record lives in SEALS.md, outside the sealed scope, to avoid
digest self-reference.

Recorded findings that are not failures:
- Re-mint event: after Q1/Q2 rendered, one file was amended (the
  bad-seal-drift seed's desync re-authored as a content amendment; see
  SEALS.md) — Q3 re-qualified over the sealed bytes with a one-file
  scope proof, re-rendering QC-1/2/3/4/5/8/9/10 and inheriting QC-6/7
  by byte-identity of their evidence (q3-delta-verdicts.md).
- Liveness trials (Q2, matched builder model): cs-cli-fresh PASS on
  attempt 3 — attempts 1-2 failed on probe-dictated interchange
  shapes the case evidence does not license (E1-class signal);
  cs-intake-refusal PASS on attempt 2. Contamination caveat: the Q2
  context had read probe internals before the trials.
- cs-cli-fresh probe robustness: a string `"overall": "PASS"` (the
  shape cs-judged-fresh's own target uses) crashes the probe →
  UNVERIFIED path, recorded for a successor fix.
- Q2 friction (contract-gap): the cs-nondet-fresh probe globs
  `stream-*.json` at the store root; the store's per-case layout
  note records the required flat placement.
