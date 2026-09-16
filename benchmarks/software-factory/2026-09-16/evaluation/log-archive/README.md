# Frozen log-archive evaluator

Keep this directory outside both build-arm projects. `calibration_candidate.py` is an evaluator-only positive control and must not be copied into a starter or disclosed as implementation guidance. `oracle.py` computes expected results independently from the baseline and candidate. The evaluator imports only the public API and runs the documented CLI; it does not inspect implementation structure.

```console
python evaluate.py --project PATH_TO_CANDIDATE --output PATH_TO_REPORT_JSON
python calibrate.py --starter PATH_TO_ORIGINAL_STARTER --output-dir PATH_TO_CALIBRATION_EVIDENCE
```

Evaluation operates on fresh temporary archives, never modifies candidate source, and produces individually named assertions plus a separate performance object. `correctness_passed` requires every assertion; `acceptance_passed` additionally requires at least 5x throughput. Baseline answer checks are included to expose reference/evaluator disagreement. A candidate import or benchmark failure is reported as `evaluation_completed=false`, not silently omitted. The process exits successfully when it wrote a report, so consumers must inspect the booleans.

Performance uses 30,000 deterministic records, 16 queries, and two sequential paired rounds, alternating order. Both implementations receive one initial untimed search. Both receive exactly the same measured query sequence and files. Timing covers only API query loops; expected-answer generation and validation occur outside timing. No build-arm runs should overlap these measurements.

The original starter is the negative speed control and must pass every functional assertion. The independent cached linear-scan calibration implementation is the positive control. Calibration records live in `calibration/`. Release policy and staged-rollout evidence are assessed separately by the shared release simulator; this evaluator only scores the application contract.

On Windows, the overlap test retries transient `PermissionError` while an atomic replacement marks the old file for deletion. Ordinary OS failures are allowed by the public contract; every successful read must still return a complete allowed snapshot, and the read after the final replacement must return the final version. The evaluator leaves its temporary working directory before cleanup, and CLI subprocesses disable bytecode writes.
