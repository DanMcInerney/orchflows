# schema migration tool — specification

`migrate.py` migrates a data directory from schema v1 to schema v2
and is idempotent on every later run. Python 3.9 standard library
only. stdin unused.

## Invocation

    migrate.py DATA_DIR

Exactly one argument, a directory containing `data.json`. Any other
count, or a missing directory or `data.json`, is a usage error.

## Data formats

- v1 `data.json`: `{"schema": 1, "records": [[NAME, QTY], ...]}` —
  each record a two-element array.
- v2 `data.json`: `{"schema": 2, "records": [{"name": NAME,
  "qty": QTY}, ...]}` — same records, same order, as objects.
- Serialization law: files are written as
  `json.dumps(value, sort_keys=True)` plus one trailing `\n`, UTF-8.

## Journal

State lives in `DATA_DIR/journal.json` and nowhere else. After a
migration the tool writes:

    {"applied": ["v1-to-v2"], "checksum": "sha256:HEX"}

where `HEX` is the SHA-256 of the exact bytes of the migrated
`data.json`. Both fields are required; the serialization law applies.

## Run semantics

- First run (no `journal.json`): read v1 `data.json`, write the v2
  form, write the journal, exit 0.
- Any later run (`journal.json` lists `v1-to-v2`): change nothing —
  `data.json` and `journal.json` must be byte-identical before and
  after the run — and exit 0. This is the idempotency law; the
  defining defects of this tool class appear only on the second run.
- No environment dependence: behavior is a function of DATA_DIR
  contents only. Environment variables must not influence any run.

## Exit codes

- `0` — migrated, or already migrated.
- `1` — data error: `data.json` is neither lawful v1 nor lawful v2.
- `2` — usage error.
