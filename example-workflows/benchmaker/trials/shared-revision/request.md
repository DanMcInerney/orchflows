# Reconciliation benchmark draft

[invoke `benchmaker:benchmaker`] Build a draft benchmark for an assistant that reconciles invoice and credit records into a vendor summary. Use synthetic local CSV inputs with duplicate record IDs, missing references, partial credits and currency mismatches. Require a usable summary, a discrepancy report and preservation of source rows; accept equivalent valid output formats. Keep numeric grading deterministic where possible.

This exercises the process end to end, not a population-performance claim. Use a named native representative agent as the target and calibration system, with real public-input executions and local output files. Allow at most twelve agent launches, five minutes each, including calibration and measurement. Save the full package, card, rejection log, observations and unresolved validity gaps in the supplied workspace. No external financial operation or message is authorized.
