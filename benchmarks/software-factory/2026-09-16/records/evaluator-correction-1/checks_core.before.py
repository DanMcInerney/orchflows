"""Observable functional, persistence, and concurrency requirements."""

import concurrent.futures
import json
import sqlite3
import subprocess
import sys
import threading
import time

from harness import CONFIG, assert_ids, require, signed_headers, status_is


def health(s):
    result = status_is(s.request("GET", "/health"), 200)
    require(result == {"status": "ok"}, f"health disclosure/shape mismatch: {result!r}")


def cli(s):
    s.stop()
    result = subprocess.run([sys.executable, "inbox.py", "--help"], cwd=s.project, capture_output=True, text=True, timeout=8)
    require(result.returncode == 0, "CLI --help failed")
    require("--db" in result.stdout and "--config" in result.stdout, "help does not document required configuration")
    s.start(cli=True)
    health(s)


def accept_payload(s):
    payload = {"title": "Caf\u00e9 \u2603", "nested": {"n": 2, "ok": True}, "tags": [1, "x"], "empty": None}
    body = json.dumps(payload, ensure_ascii=False).encode()
    result = status_is(s.post(event_id="z-first", body=body), 201)
    require(result.get("event_id") == "z-first" and result.get("duplicate") is False, "first acceptance response mismatch")
    page = s.page()
    assert_ids(page, ["z-first"])
    require(page["items"][0]["payload"] == payload, "parsed payload changed")
    require(page["next_cursor"] is None, "last page cursor must be null")


def idempotency(s):
    body = b'{"x":1, "name":"payload"}'
    status_is(s.post(event_id="same", body=body), 201)
    before = s.page()
    duplicate = status_is(s.post(event_id="same", body=body), 200)
    require(duplicate.get("duplicate") is True and duplicate.get("event_id") == "same", "duplicate response mismatch")
    require(s.page() == before, "retry changed persisted state or sequence")


def raw_body_conflict(s):
    status_is(s.post(event_id="raw", body=b'{"a":1,"b":2}'), 201)
    before = s.page()
    for changed in [b'{ "a": 1, "b": 2 }', b'{"b":2,"a":1}', b'{"a":7,"b":2}']:
        status_is(s.post(event_id="raw", body=changed), 409)
    require(s.page() == before, "conflict mutated the original event")
    status_is(s.post(event_id="raw", body=b'{"a":1,"b":2}'), 200)


def separate_tenants(s):
    status_is(s.post("alpha", "shared-id", b'{"owner":"alpha"}'), 201)
    status_is(s.post("beta", "shared-id", b'{"owner":"beta"}'), 201)
    alpha, beta = s.page("alpha"), s.page("beta")
    assert_ids(alpha, ["shared-id"])
    assert_ids(beta, ["shared-id"])
    require(alpha["items"][0]["payload"] == {"owner": "alpha"}, "alpha leaked beta data")
    require(beta["items"][0]["payload"] == {"owner": "beta"}, "beta leaked alpha data")


def pagination(s):
    ids = ["z-last-lexically", "a-first-lexically", "middle", "q", "b"]
    for i, event_id in enumerate(ids):
        status_is(s.post(event_id=event_id, body=json.dumps({"i": i}).encode(), timestamp=int(time.time()) + 100 - i), 201)
    first = s.page(query="?limit=2")
    assert_ids(first, ids[:2])
    cursor = first["next_cursor"]
    require(cursor == str(first["items"][-1]["sequence"]), "cursor must encode last sequence as a decimal string")
    second = s.page(query=f"?cursor={cursor}&limit=2")
    require(second == s.page(query=f"?limit=2&cursor={cursor}"), "same cursor returned unstable page")
    assert_ids(second, ids[2:4])
    third = s.page(query=f"?limit=2&cursor={second['next_cursor']}")
    assert_ids(third, ids[4:])
    require(third["next_cursor"] is None, "final cursor must be null")
    all_items = first["items"] + second["items"] + third["items"]
    seqs = [item["sequence"] for item in all_items]
    require(seqs == sorted(set(seqs)), "sequences are not strictly increasing")
    empty = s.page(query=f"?cursor={seqs[-1] + 1000}")
    require(empty == {"items": [], "next_cursor": None}, "cursor beyond end must return empty page")


def default_page_and_limit(s):
    for i in range(53):
        status_is(s.post(event_id=f"n-{i:03}"), 201)
    page = s.page()
    require(len(page["items"]) == 50 and page["next_cursor"] is not None, "default page size must be 50")
    require(len(s.page(query="?limit=1")["items"]) == 1, "limit 1 not respected")
    all_items = s.page(query="?limit=100")
    require(len(all_items["items"]) == 53 and all_items["next_cursor"] is None, "limit 100 not respected")


def tenant_cursor_isolation(s):
    for i in range(4):
        status_is(s.post("alpha", f"alpha-{i}"), 201)
        status_is(s.post("beta", f"beta-{i}"), 201)
    alpha = s.page("alpha", "?limit=2")
    beta_all = s.page("beta")["items"]
    number = int(alpha["next_cursor"])
    beta = s.page("beta", f"?cursor={number}")
    require(beta["items"] == [item for item in beta_all if item["sequence"] > number], "foreign numeric cursor crossed tenant boundary or misfiltered rows")


def persistence(s):
    status_is(s.post(event_id="persist", body=b'{ "durable": true }'), 201)
    status_is(s.post("beta", "persist", b'{"b":1}'), 201)
    alpha, beta = s.page(), s.page("beta")
    s.restart()
    require(s.page() == alpha and s.page("beta") == beta, "events/sequences lost across restart")
    status_is(s.post(event_id="persist", body=b'{ "durable": true }'), 200)
    status_is(s.post(event_id="persist", body=b'{"durable":true}'), 409)
    status_is(s.post(event_id="after-restart"), 201)
    require(s.page()["items"][-1]["sequence"] > alpha["items"][-1]["sequence"], "sequence did not advance after restart")
    s.stop()
    require(s.db.exists(), "specified SQLite database was not created")
    with sqlite3.connect(s.db) as connection:
        require(connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity check failed")


def concurrent_identical(s):
    barrier = threading.Barrier(12)
    def send(_):
        barrier.wait(timeout=8)
        return s.post(event_id="race", body=b'{"shared":true}')
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(send, range(12)))
    statuses = [code for code, _ in results]
    require(statuses.count(201) == 1 and statuses.count(200) == 11, f"non-atomic duplicate results: {statuses}")
    for status, response in results:
        require(response.get("duplicate") is (status == 200), "wrong duplicate flag in concurrent response")
    assert_ids(s.page(), ["race"])


def concurrent_conflicting(s):
    barrier = threading.Barrier(10)
    def send(index):
        barrier.wait(timeout=8)
        return index, s.post(event_id="race-conflict", body=json.dumps({"writer": index}).encode())
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(send, range(10)))
    accepted = [index for index, (status, _) in results if status == 201]
    require(len(accepted) == 1, f"expected one successful writer: {results!r}")
    require(all(status in (201, 409) for _, (status, _) in results), "conflicting race returned an invalid status")
    page = s.page()
    assert_ids(page, ["race-conflict"])
    require(page["items"][0]["payload"] == {"writer": accepted[0]}, "winner body differs from stored body")


def concurrent_distinct(s):
    def send(index):
        return s.post(event_id=f"distinct-{index}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(send, range(24)))
    require(all(status == 201 for status, _ in results), f"distinct concurrent writes failed: {[status for status, _ in results]}")
    page = s.page()
    require(len(page["items"]) == 24, "concurrent writes lost rows")
    seqs = [item["sequence"] for item in page["items"]]
    require(seqs == sorted(set(seqs)), "concurrent sequences are unstable/nonunique")


def sql_input(s):
    event_id = "x'); DROP TABLE events; --"
    payload = {"sql": "' OR 1=1 --", "nested": {"value": "alpha; DELETE FROM events"}}
    status_is(s.post(event_id=event_id, body=json.dumps(payload).encode()), 201)
    status_is(s.post(event_id="ordinary"), 201)
    page = s.page()
    assert_ids(page, [event_id, "ordinary"])
    require(page["items"][0]["payload"] == payload, "SQL-looking content was changed")
    require(s.page("beta")["items"] == [], "SQL-looking input crossed tenant boundary")


CHECKS = [
    ("health_minimal", "interface", health),
    ("cli_help_ephemeral_loopback", "interface", cli),
    ("signed_unicode_payload_roundtrip", "behavior", accept_payload),
    ("identical_retry_idempotent", "behavior", idempotency),
    ("raw_bytes_conflict_preserves_original", "data", raw_body_conflict),
    ("tenant_scoped_ids_and_payloads", "security", separate_tenants),
    ("stable_oldest_first_pagination", "behavior", pagination),
    ("default_and_boundary_page_sizes", "behavior", default_page_and_limit),
    ("foreign_numeric_cursor_isolation", "security", tenant_cursor_isolation),
    ("sqlite_restart_idempotency_and_sequence", "data", persistence),
    ("concurrent_identical_single_row", "concurrency", concurrent_identical),
    ("concurrent_conflicts_one_winner", "concurrency", concurrent_conflicting),
    ("concurrent_distinct_no_lost_rows", "concurrency", concurrent_distinct),
    ("sql_looking_inputs_are_data", "security", sql_input),
]
