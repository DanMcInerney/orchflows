"""Independent data-lens probes; only local review scratch files are mutated."""
import concurrent.futures
import hashlib
import hmac
import http.client
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
SNAPSHOT = Path(sys.argv[1])
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SNAPSHOT))
from inbox import create_server

config = ROOT / 'config.json'
config.write_text(json.dumps({'tenants': {'alpha': {'secret': 'probe-alpha', 'token': 'read-alpha'}, 'beta': {'secret': 'probe-beta', 'token': 'read-beta'}}}), encoding='utf-8')
db = ROOT / 'probe.sqlite3'
active = []

def start(path):
    server = create_server(path, config)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
    thread.start()
    active.append((server, thread))
    return server.server_address

def stop_all():
    while active:
        server, thread = active.pop()
        server.shutdown()
        server.server_close()
        thread.join(5)
        assert not thread.is_alive()

def request(addr, tenant='alpha', event=None, body=b'{}'):
    connection = http.client.HTTPConnection(*addr, timeout=20)
    try:
        if event is None:
            connection.request('GET', '/events/' + tenant + '?limit=100', headers={'Authorization': 'Bearer read-' + tenant})
        else:
            timestamp = str(int(time.time()))
            signature = hmac.new(('probe-' + tenant).encode(), timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
            connection.request('POST', '/webhooks/' + tenant, body, {'X-Event-ID': event, 'X-Timestamp': timestamp, 'X-Signature': signature})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()

def rows(path):
    con = sqlite3.connect(path)
    try:
        return con.execute('SELECT sequence,tenant,event_id,raw_body FROM events ORDER BY sequence').fetchall()
    finally:
        con.close()

def emit(name, **details):
    print(json.dumps({'probe': name, 'outcome': 'PASS', **details}), flush=True)

try:
    addresses = [start(db), start(db)]
    barrier = threading.Barrier(24)
    bodies = [b'{"number":1}' if index % 2 else b'{ "number":1 }' for index in range(24)]
    def send(index):
        barrier.wait(10)
        return request(addresses[index % 2], event='shared', body=bodies[index])[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
        statuses = list(pool.map(send, range(24)))
    assert statuses.count(201) == 1, statuses
    assert statuses.count(200) == 11 and statuses.count(409) == 12, statuses
    assert len(rows(db)) == 1
    emit('two_servers_shared_database_conflict', counts={str(s): statuses.count(s) for s in set(statuses)})

    exact_id = "x'); DROP TABLE events; --"
    exact_body = b'\r\n{ "caf\xc3\xa9":"\\u03bb", "n":-0.00e+00 } \t'
    for tenant in ('alpha', 'beta'):
        assert request(addresses[0], tenant=tenant, event=exact_id, body=exact_body)[0] == 201
    assert all(row[3] == exact_body for row in rows(db) if row[2] == exact_id)
    before = rows(db)
    assert request(addresses[1], event=exact_id, body=exact_body)[0] == 200
    assert request(addresses[1], event=exact_id, body=b'{}')[0] == 409
    assert rows(db) == before
    emit('exact_bytes_ids_tenant_scope_and_stable_sequence', rows=len(before), body_sha256=hashlib.sha256(exact_body).hexdigest())

    con = sqlite3.connect(db)
    con.execute('CREATE TABLE effect_probe(value TEXT)')
    con.execute("CREATE TRIGGER forced_failure BEFORE INSERT ON events WHEN NEW.event_id='storage-error' BEGIN INSERT INTO effect_probe VALUES ('should-rollback'); SELECT RAISE(FAIL, 'forced storage failure'); END")
    con.commit()
    assert request(addresses[0], event='storage-error')[0] == 503
    assert rows(db) == before
    assert con.execute('SELECT * FROM effect_probe').fetchall() == []
    con.execute('DROP TRIGGER forced_failure')
    con.commit()
    con.close()
    assert request(addresses[1], event='storage-error')[0] == 201
    emit('storage_error_rolls_back_partial_effects_and_does_not_reserve_id', error_status=503, retry_status=201)

    backup = ROOT / 'backup.sqlite3'
    source = sqlite3.connect(db)
    target = sqlite3.connect(backup)
    try:
        source.backup(target)
        assert target.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert source.execute('PRAGMA journal_mode').fetchone() == ('wal',)
    finally:
        target.close()
        source.close()
    expected = rows(db)
    assert rows(backup) == expected
    stop_all()
    restored = start(backup)
    assert request(restored, event=exact_id, body=exact_body)[0] == 200
    assert request(restored, event=exact_id, body=b'{}')[0] == 409
    assert request(restored, event='after-restore')[0] == 201
    assert rows(backup)[-1][0] > expected[-1][0]
    emit('online_backup_integrity_restore_and_sequence_continuity', backed_up_rows=len(expected), next_sequence=rows(backup)[-1][0])
    stop_all()

    crashdb = ROOT / 'crash.sqlite3'
    process = subprocess.Popen([sys.executable, '-B', str(SNAPSHOT / 'inbox.py'), '--db', str(crashdb), '--config', str(config), '--port', '0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=SNAPSHOT)
    try:
        ready = json.loads(process.stdout.readline())
        addr = (ready['host'], ready['port'])
        for index in range(20):
            assert request(addr, event='accepted-' + str(index), body=exact_body)[0] == 201
        expected_crash = rows(crashdb)
        process.kill()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        stderr = process.stderr.read()
        process.stdout.close()
        process.stderr.close()
        (ROOT / 'crash-stderr.txt').write_text(stderr, encoding='utf-8')
    recovered = start(crashdb)
    assert rows(crashdb) == expected_crash
    assert request(recovered, event='accepted-0', body=exact_body)[0] == 200
    assert request(recovered, event='accepted-0', body=b'{}')[0] == 409
    assert request(recovered, event='after-crash')[0] == 201
    assert rows(crashdb)[-1][0] > expected_crash[-1][0]
    emit('abrupt_process_termination_retains_acknowledged_events', acknowledged_events=20, retry_status=200, conflict_status=409)
finally:
    stop_all()
