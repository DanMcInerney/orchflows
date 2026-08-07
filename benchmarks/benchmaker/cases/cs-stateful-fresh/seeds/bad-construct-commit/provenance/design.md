# schema-migration benchmark — frozen evaluation design

Target: the schema-migration tool fixed by the case evidence
(`spec.md`). The defining defects of this tool class appear only on
the second run against the same state, so the oracle's law is the
two-run transcript: every scoring pass executes the implementation at
least twice against the same state directory and asserts the
second-run (escaped) state, byte for byte.

Boundary:

- First-run law: v1 data becomes v2 under the serialization law; the
  journal is written complete (`applied` and `checksum`, checksum
  over the exact migrated bytes).
- Second-run law: a run against migrated state changes nothing —
  `data.json` and `journal.json` byte-identical before and after.
- Pre-migrated state: runs against an already-migrated directory
  with a complete journal change nothing.
- Environment pinning: the scoring path passes an explicit
  controlled environment (a fixed allowlist of platform variables
  only) to the inner process; the spec's no-env-dependence law is
  scored, not trusted. State lives in the journal file, never in the
  environment.

Runner interface (frozen): `python <runner-locator> IMPL` where IMPL
is a directory holding `migrate.py` (or a direct path to it). The
runner resolves its package root by walking up to `manifest.json`,
reads cases and scoring through the manifest locators, constructs
each case's state directory in scratch space, executes the two-run
transcript, and emits one JSON object on stdout: `{"impl", "cases":
[{"id", "pass", "detail", "runs": [{"run", "state_dir", "ok"}, ...]}],
"pass"}`, exit 0 on aggregate pass, 1 otherwise. The per-case `runs`
transcript records every execution and the state directory it ran
against.

Scoring: every case is required; aggregation is all-required-pass;
all comparisons are byte-exact under the spec's serialization law.
