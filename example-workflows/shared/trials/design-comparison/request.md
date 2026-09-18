# Compare an operational reporting increment

Use `design-loop:test-increment` to compare the supplied baseline and candidate implementations of `closed_total(records)`. Resolve core, shared and design-loop from the supplied isolated home. Select `code` and `design-iteration` guidance.

The intended increment excludes open records from the total. Required existing behavior includes returning zero for empty input and summing closed records, including negative adjustments. Execute both implementations on the same cases in `cases.json`, preserve the original files, and return actual results and comparison evidence. Do not adopt a candidate or fix either version. Put evaluation artifacts in the supplied output directory.
