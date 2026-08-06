# Planted defect: the report lies about what the code enforces

`error_strings` and `render_report` read the field key `require` instead of
`required`, so the report calls every field optional and never lists the
`email: required` message; the generated validator is untouched and still
rejects a record with no `email`. The code artifact is correct and the human
artifact contradicts it, which is the exact failure a single-domain benchmark
cannot see: every deterministic test of the generated module passes, so a
benchmark that materialized only a code-pack run scores this seed as good. A
quality benchmark for this target must judge the report half as its own graded
artifact — checking the report's per-field claims against the schema and
against what the validator actually emits — because the report is what a
person reads before trusting the generated module, and a confidently wrong
report is worse than no report.
