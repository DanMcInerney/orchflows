# Durable webhook inbox

Python 3.11+ and the standard library are sufficient. `TASK.md` defines the public
contract; `AGENTS.md` defines the mandatory human security review before release.
This candidate has no live deployment approval.

## Start and configure

Create a private configuration file shaped like `config.example.json`:

```json
{"tenants":{"alpha":{"secret":"replace-with-private-signing-secret","token":"replace-with-private-read-token"}}}
```

Names, secrets, tokens and event IDs are case-sensitive. Tenant names use ASCII
letters, digits, hyphens and underscores. Credentials are nonempty strings;
use high-entropy distinct credentials for each tenant and printable ASCII read
tokens. Secrets are UTF-8 encoded for signing. Protect the config, database,
sidecars and backups using operating-system permissions. Example credentials are
test fixtures. Configuration is loaded once; restart to apply changes. Removing
a tenant from configuration prevents access without deleting its stored events.

```console
python inbox.py --db inbox.sqlite3 --config config.example.json
python inbox.py --help
```

The default address is `127.0.0.1:8080`. Optional `--host` and `--port` override
these values. Port `0` selects an available port. Before serving, the process
prints and flushes exactly one readiness JSON line with `host` and actual `port`.
The database is created if absent; its parent directory must already exist.

Embedding is supported through
`create_server(db_path, config_path, host='127.0.0.1', port=0)`. Run
`serve_forever()` on your serving thread. From another thread, call `shutdown()`,
then `server_close()` and join the serving thread. Shutdown waits for in-flight
requests to finish; request socket and SQLite busy timeouts are ten seconds.
Ctrl+C stops the CLI. Do not call `shutdown()` from the `serve_forever()` thread.

`GET /health` returns `{"status":"ok"}`. It checks process responsiveness; it
does not query the database or disclose configuration or events.

## Sign and submit

The signature is lowercase hexadecimal HMAC-SHA256 over the exact ASCII
timestamp, a period, and the exact body bytes. Compute `Content-Length` from
bytes, not characters. This standard-library example reads the local fixture
configuration without printing credentials:

```python
import hashlib, hmac, http.client, json, time
from pathlib import Path

credentials = json.loads(Path("config.example.json").read_text())["tenants"]["alpha"]
body = json.dumps({"message": "hello"}, separators=(",", ":")).encode("utf-8")
timestamp = str(int(time.time()))
signature = hmac.new(credentials["secret"].encode("utf-8"),
                     timestamp.encode("ascii") + b"." + body,
                     hashlib.sha256).hexdigest()
connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=15)
try:
    connection.request("POST", "/webhooks/alpha", body, {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "X-Event-ID": "order-123",
        "X-Timestamp": timestamp,
        "X-Signature": signature,
    })
    response = connection.getresponse()
    print(response.status, json.loads(response.read()))
finally:
    connection.close()
```

Bodies must be UTF-8 JSON objects of at most 65,536 bytes, inclusive. JSON
`NaN` and `Infinity` literals are rejected. Event IDs are 1–128 printable ASCII
characters with no leading/trailing whitespace; interior spaces and SQL-looking
text are data. Timestamp headers must be canonical nonnegative decimal Unix
seconds and within 300 seconds of server time, inclusive. Keep the host clock
synchronized. Duplicate required headers, folded headers, malformed lengths,
transfer encoding and noncanonical authentication values are rejected.

The first accepted `(tenant, event ID)` returns 201 and `duplicate:false`.
Reusing that ID with the identical bytes returns 200 and `duplicate:true`;
different bytes return 409 even when the JSON values are equivalent. Every retry
requires a fresh valid timestamp and signature. Preserve the body bytes and ID
when retrying after a network timeout: a commit may have completed before the
response was lost. Validation failures never reserve an ID or update an event.

## Read pages

Use `GET /events/alpha?limit=50&cursor=0` with
`Authorization: Bearer TOKEN`, taking TOKEN from that tenant's configuration.
The response is an object containing `items` and `next_cursor`. Each item contains
its positive integer `sequence`, exact `event_id`, and JSON object `payload`.
Payload JSON is embedded from the validated raw body, preserving valid number
precision and representation without conversion through floating-point values.

Pages are ordered by insertion sequence. The default limit is 50; valid limits
are canonical integers 1–100. The default cursor is `0`; valid cursors are
canonical nonnegative decimal strings, including numbers above SQLite's range
(which return an empty page). Send the returned `next_cursor` in the next request.
Null means no more rows currently exist. New writes may appear on later reads;
pagination is not a snapshot across multiple requests. Repeating a cursor without
writes repeats the page. Sequence values are globally allocated; each tenant's
values strictly increase and may have gaps. A cursor carries no tenant authority.
Unknown, repeated or malformed query parameters return 400.

Errors are JSON objects: 400 for malformed requests, 401 for failed or stale
authentication, 404 for unknown paths or tenants, 409 for conflicting event bytes,
413 for excessive body size, and 503 for a storage error. Unsupported HTTP methods
receive a JSON error. Routine request logging is disabled, and error messages do
not echo headers, bodies, credentials or signatures.

## Storage, recovery and operating limits

`inbox_store.py` stores `events(sequence, tenant, event_id, raw_body)` in SQLite.
The body is a BLOB. A unique constraint on `(tenant, event_id)` and an immediate
transaction serialize identity checks and inserts. Every SQL value is bound as
a parameter. Reads use the `(tenant, sequence)` index. SQLite WAL mode and FULL
synchronous commits preserve acknowledged events across normal restart and
provide SQLite's documented crash recovery subject to filesystem durability.
Connections are per operation and always closed. No process-memory event cache
or cleanup job exists; events and their IDs are retained indefinitely.

Use a local durable filesystem, reserve disk space, and monitor database growth.
Do not put the WAL database on an unsupported shared/network filesystem. To
back up a running service, use Python's `sqlite3.Connection.backup()` API to a
new destination, then validate the backup with `PRAGMA integrity_check`. For an
offline backup, stop the service cleanly before copying the database. Do not copy
only the main database while WAL writes may be active. Backups contain tenant
payloads; apply the same access restrictions as the primary database.

Restore into a separate directory while stopped, verify integrity and sample
tenant pages, then select the restored path at startup. Restoring an older backup
loses later events and idempotency records, so retain the original files and
reconcile with senders before resuming ingestion. Test recovery with a copy first.

The standard-library HTTP server has no TLS, rate limiter, global admission cap
or production process supervision. It defaults to loopback. Public exposure
requires a separately reviewed TLS/authentication boundary, connection/request
limits and service supervision. Socket timeouts limit idle waits, not total
request duration under a slow trickle. Large numbers of clients can exhaust
threads. The JSON parser's nesting/resource limits apply; excessively nested JSON
is rejected with 400. Read pages may contain up to 100 maximum-size events.
Signatures cover timestamp and body, as required by the contract, but not event
ID; protect captured signatures and use TLS before any nonlocal deployment.

## Checks and release

```console
python -m unittest -v test_smoke
python -m unittest discover -v
python -m py_compile inbox.py
python inbox.py --help
git diff --check
```

Tests use isolated temporary directories, loopback ephemeral ports, and no
external services. Added checks exercise raw-header faults, authentication,
cross-tenant access, exact idempotency, concurrent requests, persistence, paging,
limits and CLI startup. See `RELEASE_HANDOFF.md` for the human review gate and
proposed operating/rollback checks. No live or simulator deployment is authorized.
