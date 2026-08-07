# csvmerge benchmark — frozen evaluation design

Target: the `csvmerge` CLI as fixed by the case evidence (`spec.md`,
`transcripts.md`). Observable outcome: process argv in, stdout bytes
and exit status out. One oracle class: deterministic byte comparison.

Boundary:

- Every documented clause with an observable witness is cased: merge
  order, cross-file deduplication, `--prefer` on shared keys including
  a shared key at the maximum position, LF/CRLF input equivalence,
  data-error and usage-error exits.
- Tolerance law: the oracle compares stdout after normalizing CRLF to
  LF — terminator form is declared insignificant by the spec, so a
  CRLF-terminated but otherwise identical output conforms.
- Anchoring: at least one runnable case reproduces an exhibited
  transcript from `transcripts.md` verbatim (t1, t2 and t3 are all
  anchored).

Runner interface (frozen): `python <runner-locator> IMPL` where IMPL
is a directory holding `csvmerge.py` (or a direct path to the file).
The runner resolves its package root by walking up to `manifest.json`,
reads the runnable case set and scoring data through the manifest
locators, executes each case in a scratch directory, and emits one
JSON object on stdout: `{"impl", "cases": [{"id", "pass", "detail"}],
"pass"}`, exiting 0 when the aggregate passes and 1 otherwise.

Scoring: every case is required; aggregation is all-required-pass.
