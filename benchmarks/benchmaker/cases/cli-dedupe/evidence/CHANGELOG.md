# dedupe changelog

## 0.3.0

- `--ignore-case` no longer alters the bytes that are written. Earlier
  releases echoed the case-folded comparison key instead of the line as
  it was read; downstream tooling that diffed output against the source
  file broke on mixed-case input.

## 0.2.0

- The `--window` bound is now measured over *retained* lines. 0.1
  counted input lines, so a run of repeats consumed window slots and
  evicted keys early. Reports of both directions of drift — repeats
  surviving that should have been suppressed, and repeats suppressed
  that should have survived — traced to this.
- Empty lines are ordinary lines. 0.1 skipped them unconditionally,
  which silently collapsed paragraph breaks in prose input.

## 0.1.0

- Initial release: unbounded, case-sensitive deduplication of standard
  input.
