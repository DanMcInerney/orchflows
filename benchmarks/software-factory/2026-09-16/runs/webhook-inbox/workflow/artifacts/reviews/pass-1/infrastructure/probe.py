"""Infrastructure review probes; no changes to the frozen candidate."""
import hashlib
import hmac
import http.client
import json
import queue
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'review-snapshots/pass-1-infrastructure'
sys.path.insert(0, str(SOURCE))
sys.dont_write_bytecode = True
from inbox import create_server

def record(label, **data):
    print(json.dumps({'probe': label, **data}), flush=True)

def request(address, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection(*address, timeout=15)
    try:
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()

def headers(event, body=b'{}'):
    timestamp = str(int(time.time()))
    signature = hmac.new(b'signing-secret', timestamp.encode()+b'.'+body, hashlib.sha256).hexdigest()
    return {'X-Event-ID': event, 'X-Timestamp': timestamp, 'X-Signature': signature}

def post(address, event, body=b'{}'):
    return request(address, 'POST', '/webhooks/alpha', body, headers(event, body))

def page(address):
    return request(address, 'GET', '/events/alpha', headers={'Authorization':'Bearer read-token'})

manifest = json.loads((ROOT / 'artifacts/pass-1/coordinator-manifest.json').read_text())
mismatches = [name for name, digest in manifest['files'].items()
              if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() != digest]
assert not mismatches, mismatches
record('snapshot_identity', files=len(manifest['files']), mismatches=mismatches,
       expected_tree=manifest['tree_sha256'])

with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as scratch:
    folder = Path(scratch)
    config = folder / 'config.json'
    config.write_text(json.dumps({'tenants': {'alpha': {'secret':'signing-secret', 'token':'read-token'}}}))
    db = folder / 'inbox.sqlite'
    server = create_server(db, config)
    address = server.server_address
    serve = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':0.01})
    serve.start()
    try:
        # SQLite's lock timeout must produce JSON 503 without reserving an ID;
        # the health endpoint and retry must recover without restarting.
        blocker = sqlite3.connect(db, isolation_level=None)
        blocker.execute('BEGIN IMMEDIATE')
        try:
            started = time.monotonic()
            status, result = post(address, 'locked')
            elapsed = time.monotonic()-started
            assert status == 503, (status,result)
        finally:
            blocker.rollback()
            blocker.close()
        assert request(address,'GET','/health') == (200, {'status':'ok'})
        assert page(address)[1]['items'] == []
        assert post(address,'locked')[0] == 201
        record('storage_lock_recovery', status=status, seconds=round(elapsed,3),
               failed_request_left_no_rows=True, retry_status=201)

        # A request already accepted before shutdown completes before close.
        client = socket.create_connection(address, timeout=5)
        body = b'{"during":"shutdown"}'
        wire = b'POST /webhooks/alpha HTTP/1.1\r\nHost: localhost\r\n'
        for key,value in headers('inflight', body).items():
            wire += key.encode()+b': '+value.encode()+b'\r\n'
        client.sendall(wire+b'Content-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body[:1])
        time.sleep(0.1)
        stopped = threading.Event()
        def close():
            server.shutdown()
            server.server_close()
            serve.join(2)
            stopped.set()
        closer = threading.Thread(target=close)
        closer.start()
        time.sleep(0.1)
        assert not stopped.is_set(), 'close abandoned active request'
        client.sendall(body[1:])
        response = http.client.HTTPResponse(client)
        response.begin()
        status = response.status
        response.read()
        client.close()
        closer.join(5)
        assert status == 201 and stopped.is_set() and not serve.is_alive()
        record('graceful_inflight_shutdown', status=status, request_drained=True,
               serving_thread_stopped=True)
    finally:
        if serve.is_alive():
            server.shutdown()
            server.server_close()
            serve.join(5)

    restarted = create_server(db,config,port=address[1])
    serve = threading.Thread(target=restarted.serve_forever,kwargs={'poll_interval':0.01})
    serve.start()
    try:
        before = page(restarted.server_address)
        assert [item['event_id'] for item in before[1]['items']] == ['locked','inflight']
        assert post(restarted.server_address,'inflight',body)[0] == 200
        record('factory_restart_same_port', rows=2, same_port=True, duplicate_status=200)
    finally:
        restarted.shutdown()
        restarted.server_close()
        serve.join(5)

    def start_cli():
        proc = subprocess.Popen([sys.executable,'-B',str(SOURCE/'inbox.py'),'--db',str(db),
                                 '--config',str(config),'--port','0'],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        lines = queue.Queue()
        threading.Thread(target=lambda: lines.put(proc.stdout.readline()),daemon=True).start()
        ready = json.loads(lines.get(timeout=5))
        assert ready['host'] == '127.0.0.1' and ready['port'] > 0
        return proc, (ready['host'],ready['port'])

    proc, address = start_cli()
    try:
        assert post(address,'cli-acknowledged')[0] == 201
        before = page(address)
    finally:
        proc.kill()
        proc.wait(timeout=5)
        stdout,stderr = proc.communicate()
        assert not stderr and not stdout, (stdout,stderr)
    proc,address = start_cli()
    try:
        assert page(address) == before
        assert post(address,'cli-acknowledged')[0] == 200
        assert post(address,'cli-acknowledged',b'{"different":true}')[0] == 409
        record('cli_abrupt_stop_restart', readiness_flushed=True, acknowledged_event_survived=True,
               sequence_and_payload_stable=True, duplicate_status=200, conflict_status=409)
    finally:
        proc.kill()
        proc.wait(timeout=5)
        stdout,stderr = proc.communicate()
        assert not stderr and not stdout, (stdout,stderr)
    original=sqlite3.connect(db)
    backup=sqlite3.connect(folder/'backup.sqlite')
    try:
        original.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert backup.execute('SELECT * FROM events').fetchall() == original.execute('SELECT * FROM events').fetchall()
        record('documented_sqlite_backup', integrity='ok', exact_rows_preserved=True)
    finally:
        backup.close()
        original.close()
record('result', status='PASS')
