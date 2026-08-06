# Planted defect (near-miss): one report message drifts from the emitted string

The report-only helper `error_strings` prints `email: is required` where the
generated validator emits `email: required`. Nothing else moves: the code half
is byte-for-byte the reference behaviour, the report's field table is correct,
every field is named, every message the validator can emit has a plausible
bullet next to it, and the wording drift reads like ordinary prose polish.
This is the near-miss because it survives the two checks a hurried benchmark
actually writes — run the generated module, then confirm the report mentions
every field — and only fails a check that couples the halves: the set of
messages the report advertises must equal the set the generated validator
demonstrably emits. A quality benchmark for a two-artifact generator must
grade that coupling, or it will certify documentation that sends a reader
looking for a string the code never produces.
