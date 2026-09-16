# Independent webhook-inbox evaluator

Run with the same Python interpreter used for the case (Python 3.11+):

```console
python evaluate.py --project /absolute/path/to/build --output /absolute/path/to/results.json
python -m unittest -v test_harness
```

The evaluator invokes the published server factory in a subprocess and exercises real HTTP requests over ephemeral loopback ports. Every named check has independent temporary SQLite/configuration state; the restart check deliberately reuses its own database. The CLI check separately starts `inbox.py` through the published command. Builder-authored tests are never imported. Server processes are terminated and temporary state removed after each check, including failures. Exit 0 means all selected checks passed; exit 1 means at least one failed or errored. `--only NAME` supports diagnosis; use the full set for comparison.

The output contains named checks, categories, pass/fail/error status, evidence on failure, durations, totals, and hashes of the evaluator code. Categories are interface, behavior, data, concurrency, security, and validation. Scores are check counts, not a claim of complete security assurance. A server startup failure is an `error`, not silently skipped work.

Requirements and all expected statuses are published in the case's `prompt.md`. Concrete payloads, identifiers, and malformed-input selections here are evaluator fixtures. Invalid-input tests ordinarily isolate one error class. Malformed signatures are 400; well-formed but incorrect signatures are 401. Unknown-tenant tests use otherwise well-formed authentication material; the tenant has no valid credentials by definition. Duplicate/conflict authentication tests use well-formed, incorrect signatures and expect 401 before exposing idempotency. Malformed timestamp fixtures are correctly signed over the malformed header bytes, so no separate signature mismatch is introduced. Content-Length validation sends the same valid body/signature while changing only the length header.

The timestamp check uses ±290 seconds as accepted and ±360 as rejected, avoiding scheduling races at exactly ±300. Concurrency tests accept whichever writer wins and do not assume thread ordering. Sequences may be global or tenant-specific as long as each tenant's published monotonic contract holds. Cursor checks never assume sequences start at 1 or are contiguous. Data assertions use HTTP responses and the SQLite integrity check, never an assumed table schema or implementation style.

Limitations needing artifact review: constant-time credential comparison, absence of external dependencies/services, exact raw-payload storage beyond observable retry semantics, comprehensive secret-log auditing, documentation, checked patch, and release/human-approval claims. No production endpoint is contacted.

`calibration-starter.json` records substantive failures against the incomplete starter. `calibration-signing.txt` records signing helper calibration. `manifest.json` freezes source SHA-256 values and the exact prompt hash before build dispatch; no reference implementation is included.
