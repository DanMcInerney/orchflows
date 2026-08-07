# bad-ignore-case-output

The retention loop appends the comparison key rather than the line as it
was read, so under `--ignore-case` the output is case-folded. The
contract says the key is used only for comparison and a retained line is
written back byte for byte. Without `--ignore-case` the key equals the
line, so the seed is byte-identical to the reference on every
case-sensitive run.

A quality benchmark for a deterministic CLI must catch this because a
CLI's outcome is its exact bytes on stdout, not a normalised view of
them. Catching it needs two things at once: a case that sets
`--ignore-case` on mixed-case input, and an oracle that compares output
bytes rather than a case-insensitive or set-based match. A benchmark
that asserts "the duplicate is gone" — by counting lines, sorting, or
comparing case-insensitively — passes this seed, and would go on to
accept any future change that silently rewrote user data.

deviation: value-substitution
