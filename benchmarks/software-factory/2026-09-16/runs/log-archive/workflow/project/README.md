# Support log archive starter

Python 3.11+; standard library only. Run from this directory:

```console
python -m unittest discover -s tests -v
python log_archive.py --file sample.ndjson --query "gateway timeout" --limit 10
```

The starter delegates to a deliberately slow, complete full-scan implementation. `baseline_reference.py` is a frozen reference; leave it unchanged. Implement the production API and CLI in `log_archive.py` (additional modules are allowed).

## Python API

```python
from log_archive import search_logs
result = search_logs(path, query='', service=None, level=None,
                     since=None, until=None, limit=50, offset=0)
# {'total': 123, 'items': [original_record, ...]}
```

- `path` is a string or an `os.PathLike` returning a string. A missing file raises `FileNotFoundError`; an unsupported path type raises `TypeError`.
- Input is UTF-8 NDJSON, one JSON object per line. Valid records have nonempty string `id`, `service`, and `level`; a string `message` (possibly empty); and a valid `timestamp` exactly `YYYY-MM-DDTHH:MM:SS.sssZ` in UTC. Years are 0001–9999, seconds 00–59, and the date must exist. A timestamp has exactly three millisecond digits. Blank lines, malformed JSON, nonobjects, missing required fields, wrong field types, empty required strings, and invalid timestamps are skipped. Additional JSON fields are preserved. Duplicate IDs and records are allowed. Archives in scope are valid UTF-8 files.
- `query` must be a string. Extract tokens matching `[A-Za-z0-9_]+` from the query and message. Match ALL query tokens to whole message tokens, case-insensitively. Punctuation separates tokens; it has no special query syntax. Repeated tokens have no extra effect. Empty queries or queries containing no tokens match every valid record. Unicode outside that ASCII token alphabet acts as a separator. For example, `ERROR-timeout` requires `error` and `timeout`; `err` does not match `error`.
- `service` and `level` are optional exact, case-sensitive string filters. `None` disables the filter; an empty string is accepted and matches no valid record. Other types raise `TypeError`.
- `since` and `until` are optional strings in the same valid timestamp format. Bounds are `[since, until)`. `None` disables a bound. Wrong types raise `TypeError`, bad formats/dates raise `ValueError`, and `since > until` raises `ValueError`. Equal bounds produce no matches.
- Results sort by timestamp ascending and retain original physical file order for equal timestamps. `total` counts ALL matches before pagination. `items` is the slice beginning at `offset`, with at most `limit` records.
- `limit` and `offset` must be integers excluding booleans. Wrong types raise `TypeError`; negative values raise `ValueError`. Zero limit and offsets beyond the end return empty items while preserving total. There is no arbitrary maximum limit.
- The returned value is a dict with exactly `total` (integer) and `items` (list). Items preserve complete original objects. Returned objects, including nested extras, belong to the caller: mutating them cannot change future search results.
- After a completed append, truncation, or atomic replacement, the next call reflects the new file contents. This includes replacement by a different file with the same byte length and preserved modification time. Separate archive paths must not share stale results. Concurrent searches, including simultaneous initial loads and reloads, must be safe. A call overlapping atomic replacement may reflect either complete file version; it must not mix versions or return corrupt data. Simultaneous in-place partial writes are outside scope. No explicit caller cache invalidation is allowed.
- For a call with multiple invalid arguments, the order of validation is unspecified. Resource/permission failures may propagate as ordinary OS errors.

## CLI

`python log_archive.py --file PATH [--query TEXT] [--service TEXT] [--level TEXT] [--since TIMESTAMP] [--until TIMESTAMP] [--limit INTEGER] [--offset INTEGER]`

Successful calls print one JSON result matching the API to stdout and exit 0. User errors, invalid values, or missing files exit nonzero with a useful error on stderr and no traceback. `--help` exits 0. No web UI or third-party dependencies are required.

## Acceptance and measurements

Correctness checks cover the contract above with held-out data: tokens, punctuation, ASCII boundaries, duplicate records, invalid lines, extras, ordering/ties, combined filters and bounds, pagination, invalid argument types/values, missing files, result mutation, separate paths, file changes, concurrent calls, and CLI behavior. Every asserted behavior is specified here; input fixtures may be withheld.

Performance uses a deterministic 30,000-record UTF-8 archive, varied token/filter/time/pagination queries, an untimed initial search for warming, and two sequential paired rounds against the pristine full-scan baseline. Both arms receive identical queries; round order alternates baseline/candidate then candidate/baseline. The reported throughput ratio is total baseline query time divided by total candidate query time. All timed answers must also be correct. The target is at least 5x; a speed result never overrides failed correctness. Setup and initial warming are excluded. The public check is `python -m unittest discover -s tests -v`; include a reproducible benchmark command and record measured results in your handoff.

The shared run context supplies the local release simulator and policy for contract `log-archive`. Follow its staged checks, observations, hold/rollback rules, and evidence requirements. Do not claim live production deployment.
