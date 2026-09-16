# Durable webhook inbox

A Python 3.11+ webhook inbox using only the standard library and SQLite. It accepts signed JSON objects, keeps exact request bodies, and provides token-protected tenant pages. No package installation or external service is needed.

## Start and configure

Create a private configuration file using `config.example.json` as the shape:

```json
{"tenants":{"alpha":{"secret":"replace-with-a-long-random-secret","token":"replace-with-a-long-random-token"}}}
```

Example credentials are test fixtures. Use distinct, strong credentials for every tenant. Tenant names and credentials are case-sensitive; names contain ASCII letters, digits, hyphens, or underscores. Use ASCII read tokens for interoperability with HTTP clients. HMAC secrets are encoded as UTF-8. Empty credentials and malformed tenant configuration fail startup. Protect configuration and database files using operating-system permissions; neither is encrypted by this application.

```console
python inbox.py --db inbox.sqlite3 --config config.example.json
python inbox.py --db inbox.sqlite3 --config config.example.json --host 127.0.0.1 --port 0
python inbox.py --help
```

The database is created if absent; its parent directory must exist. The default host is `127.0.0.1`, and the CLI default port is 8080. Port 0 selects an available port. Startup prints and flushes exactly one JSON line containing `host` and the actual `port`, then serves requests. `GET /health` returns `{"status":"ok"}` without credentials or event data. Health confirms that the HTTP process is reachable; it does not check disk capacity or database writability.

The programmatic factory remains `create_server(db_path, config_path, host='127.0.0.1', port=0)`. Its return value supports `server_address`, `serve_forever()`, `shutdown()`, and `server_close()`. When embedding, run `serve_forever()` on a thread, call `shutdown()` from another thread, then `server_close()`. Ctrl+C stops the CLI.

## Sign and submit

This complete standard-library example reads credentials, signs the exact bytes sent, and submits locally:

```python
import hashlib
import hmac
import http.client
import json
import time
from pathlib import Path

credentials = json.loads(Path("config.example.json").read_text(encoding="utf-8"))["tenants"]["alpha"]
body = json.dumps({"message": "hello"}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
timestamp = str(int(time.time()))
signature = hmac.new(
    credentials["secret"].encode("utf-8"),
    timestamp.encode("ascii") + b"." + body,
    hashlib.sha256,
).hexdigest()
connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=10)
try:
    connection.request("POST", "/webhooks/alpha", body=body, headers={
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "X-Event-ID": "example-1",
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    })
    response = connection.getresponse()
    print(response.status, json.loads(response.read()))
finally:
    connection.close()
```

The body must be a UTF-8 JSON object of at most 65,536 bytes, inclusive. Arrays/scalars, malformed JSON/UTF-8, and non-JSON numeric constants such as `NaN` fail with 400. Deeply nested JSON and large JSON numbers are validated without Python numeric conversion or recursive traversal; returned payloads preserve their JSON representation.

`X-Event-ID` is 1–128 printable ASCII characters without leading/trailing whitespace. It is stored exactly, including punctuation and SQL-looking text. `X-Timestamp` must be a canonical nonnegative decimal Unix-seconds integer. The server accepts times within 300 seconds inclusive of its integer Unix time. `X-Signature` must be exactly 64 lowercase hexadecimal characters. The HMAC input is the timestamp header's ASCII bytes, a literal dot, and the unchanged body bytes. Header values must not contain surrounding whitespace; normal clients add one separator space after the header colon. Repeated required headers and folded headers are rejected.

A decimal `Content-Length` is required. Missing/invalid length is 400; a declared body larger than the limit is 413. Transfer-encoded bodies are rejected. Connections close after every response, and body reads time out after 10 seconds. No request body, token, secret, or signature is included in routine application logs. Authentication errors return generic JSON objects.

## Retries and errors

Idempotency is scoped to `(tenant, event ID)`:

- First accepted body: 201 with `{"event_id":"example-1","duplicate":false}`.
- Authenticated byte-identical retry: 200 with `duplicate:true` and the original event ID.
- Authenticated different bytes for the same ID: 409, even when both bodies represent equal JSON values.

Every retry must have a currently valid timestamp and signature. Recompute those headers when retrying later, but preserve the exact body and event ID. Signature verification and read-token comparison use constant-time comparison. Requests failing validation/authentication and conflicting retries do not reserve event IDs or change stored events. Concurrent requests produce one stored event per tenant/ID.

Missing/malformed POST authentication headers return 400. A well-formed incorrect signature or out-of-window timestamp returns 401. Missing/malformed/incorrect read authorization returns 401. Unknown tenants and unrecognized GET/POST routes return 404. SQLite failures return 503 with a generic message. Retry transient storage errors using the same event ID and body; a lost response can safely be retried because the commit may already have succeeded. Successful and error responses are JSON objects.

## Read pages

```python
import http.client
import json
from pathlib import Path
from urllib.parse import urlencode

credentials = json.loads(Path("config.example.json").read_text(encoding="utf-8"))["tenants"]["alpha"]
cursor = "0"
while True:
    connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=10)
    try:
        connection.request("GET", "/events/alpha?" + urlencode({"limit": "50", "cursor": cursor}),
                           headers={"Authorization": "Bearer " + credentials["token"]})
        response = connection.getresponse()
        page = json.loads(response.read())
        if response.status != 200:
            raise RuntimeError(f"Read failed: {response.status}")
        for item in page["items"]:
            print(item["sequence"], item["event_id"], item["payload"])
    finally:
        connection.close()
    cursor = page["next_cursor"]
    if cursor is None:
        break
```

`limit` defaults to 50 and must be a canonical decimal integer from 1 through 100. `cursor` defaults to `0` and must be a canonical nonnegative decimal string. Unknown/repeated parameters and malformed values return 400. Sequences are positive integers, assigned on first insertion, and increasing within each tenant. They are database-wide, so gaps are normal. No ordering depends on event IDs, sender timestamps, or body contents. Retries/conflicts never change sequences.

Pages include events with `sequence > cursor`, oldest first. `next_cursor` is the last returned sequence as a decimal string only when another event is already available; otherwise it is JSON null. Reusing a cursor without writes gives the same page. Beyond-last cursors give an empty page and null. Cursors contain no tenant authority: applying another tenant's numeric cursor still filters only the authenticated tenant's events. To poll for future arrivals after reaching null, retain the last event sequence yourself.

## Storage and operations

The `events` table stores a global auto-increment integer sequence, tenant text, exact event-ID text, and exact body bytes as a BLOB. A uniqueness constraint covers tenant and event ID; a tenant/sequence index supports pagination. Each request opens its own SQLite connection. `BEGIN IMMEDIATE` makes duplicate inspection and insertion one transaction; parameterized SQL protects all supplied values. WAL journaling and `synchronous=FULL` protect committed data across process restarts. SQLite serializes writers; this is intended for modest local workloads, and write contention waits up to 10 seconds before returning a storage error.

Use a local filesystem supported by SQLite. Monitor disk usage and file permissions; there is no retention, pruning, encryption, queue delivery, metrics endpoint, rate limiting, or TLS termination in this application. Removing a configured tenant stops HTTP access but does not delete its stored rows. Configuration is loaded at startup, so credential rotation requires restarting; old credentials stop authenticating after restart. Keep clocks synchronized.

For a consistent live backup, use Python's `sqlite3.Connection.backup()` API. Do not copy only the main database file while WAL writers are active. For an offline copy, stop all servers and copy the database and any remaining `-wal`/`-shm` sidecars together. Restore into a separate location, run `PRAGMA integrity_check`, and verify authenticated reads before switching over. Preserve backups before schema changes. The starter had no event schema, so this change only creates the new table and index; arbitrary pre-existing incompatible schemas are not migrated.

Bind to loopback unless a separately reviewed deployment supplies access controls, TLS, request/concurrency limits, secret handling, monitoring, and backup/restore procedures. The built-in threaded HTTP server is the required local service interface, not a complete internet-facing service platform. Authentication, signature verification, and tenant authorization require human approval before any live release under `AGENTS.md`. The shared local release policy also disallows webhook simulator deployment. This deliverable is prepared for that review and has not been deployed.

## Checks and review artifacts

```console
python -m unittest -v test_smoke
python -m unittest -v
python -m py_compile inbox.py test_inbox.py test_smoke.py
```

The public smoke tests are unchanged. Additional tests cover tenant isolation, strict headers/query values, body-size boundaries, exact-byte conflicts, malformed JSON and UTF-8, timestamp boundaries, SQL-looking IDs, pagination, huge cursors/numbers, deep JSON, storage rollback, concurrent duplicate/conflicting submissions, shared-database servers, restart durability, and CLI readiness. A seeded grammar check compares 1,000 generated JSON objects and 3,000 mutations with the standard JSON parser.

The run's sibling `artifacts/` directory contains the checked patch, raw test outputs (including initial failures and their repairs), source manifest, release-status evidence, `HANDOFF.md`, and `RESULT.json`. The handoff records actual release disposition and the pending security review.
