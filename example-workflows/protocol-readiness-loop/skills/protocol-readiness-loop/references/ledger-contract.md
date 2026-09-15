# Convergence ledger contract

Write one UTF-8 JSON object per line in phase order. Use schema `protocol-readiness-ledger/v1`. Every record contains:

- `cycle_id`, `round_id`, `phase`;
- `phase_started_at`, `phase_ended_at`, `phase_duration_ms`;
- `active_worker_ms` and `handoff_queue_ms`;
- `findings_entering`, `accepted`, `rejected`, `unresolved`, `newly_introduced`;
- `conformance_defect_count`, `stress_finding_count`;
- `blockers_by_failure_class` and `failure_class_evidence`;
- `current_protocol_path`, `current_protocol_sha256`;
- `terminal_disposition`, `terminal_reason`, `next_action`.

Times are timezone-aware RFC 3339 strings. Durations are nonnegative integer milliseconds. Write the literal string `UNKNOWN` for each value that cannot be proven; do not use zero as a substitute. When phase start and end are known, the duration must match their difference to the nearest millisecond. Known active-worker plus handoff/queue time may not exceed phase duration.

Finding-flow fields are unique arrays of stable finding identifiers. Counts are nonnegative integers. `blockers_by_failure_class` maps stable class identifiers to positive counts. Each mapped class has a `failure_class_evidence` object containing nonempty `invariant`, `observable_failure`, `boundary` and `evidence` values; recurrence also records `same_as` in the adjudication and change map.

Only the final record has a non-null `terminal_disposition` and nonempty `next_action`. It uses one status from the closed compatibility vocabulary. A `BLOCKED` record has a structured reason object with `code`. Mechanism routing additionally records `authorization: "separate"` and `loop_built_probe: false`; recurrence records the class identifiers and `revisions_observed`; conformance exhaustion records `repair_attempts` and `repair_limit`.

Validate a ledger from the skill directory with:

```sh
python scripts/validate_readiness_ledger.py <ledger.jsonl>
```

The validator prints one JSON result and exits 0 for valid input or 1 with enumerated errors. It checks representation and routing invariants, not whether a protocol is substantively ready.
