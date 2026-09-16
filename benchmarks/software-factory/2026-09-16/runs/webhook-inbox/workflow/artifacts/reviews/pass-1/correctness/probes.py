"""Independent review probes; no candidate edits or external dependencies."""
import hashlib
import hmac
import http.client
import json
import socket
import sqlite3
import sys
import tempfile
import threading
import time
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT.parents[3] / 'review-snapshots' / 'pass-1-correctness'
sys.path.insert(0, str(SNAPSHOT))
from inbox import create_server

def emit(name, actual, expected):
    print(json.dumps({'probe': name, 'actual': actual, 'expected': expected, 'pass': actual == expected}), flush=True)
    assert actual == expected, name

manifest = json.loads((ROOT.parents[2] / 'pass-1' / 'coordinator-manifest.json').read_text())
emit('snapshot_matches_coordinator_manifest', all(hashlib.sha256((SNAPSHOT / name).read_bytes()).hexdigest() == value for name, value in manifest['files'].items()), True)
with tempfile.TemporaryDirectory(dir=ROOT) as directory:
    directory = Path(directory)
    config = directory / 'config.json'
    config.write_text(json.dumps({'tenants': {'alpha': {'secret': 'secret', 'token': 'token'}}}))
    db = directory / 'probe.sqlite3'
    server = create_server(db, config)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
    thread.start()
    def request(method, path, body=None, headers=None):
        client = http.client.HTTPConnection(*server.server_address, timeout=5)
        try:
            client.request(method, path, body, headers or {})
            response = client.getresponse()
            raw = response.read()
            return response.status, json.loads(raw, parse_int=str, parse_float=str)
        finally:
            client.close()
    def post(identifier, body):
        timestamp = str(int(time.time()))
        signature = hmac.new(b'secret', timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
        return request('POST', '/webhooks/alpha', body, {'X-Event-ID': identifier, 'X-Timestamp': timestamp, 'X-Signature': signature})
    def page(query=''):
        return request('GET', '/events/alpha' + query, headers={'Authorization': 'Bearer token'})
    def count():
        with closing(sqlite3.connect(db)) as connection:
            return connection.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    try:
        body = b'{"x":"' + 'é'.encode() * 32764 + b'"}'
        emit('utf8_exact_65536_bytes', len(body), 65536)
        emit('utf8_exact_limit_accepted', post('multibyte', body)[0], 201)
        emit('utf8_limit_plus_one_rejected', post('oversized', body + b' ')[0], 413)
        emit('oversize_no_row', count(), 1)
        complex_body = b' \r\n{"quoted":"} , \\\"payload\\\": {", "n": -0.00E+999999, "v": [null,true,false]}\t'
        emit('raw_json_boundary_accepted', post('complex', complex_body)[0], 201)
        payload = page()[1]['items'][1]['payload']
        emit('raw_payload_retains_number', payload['n'], '-0.00E+999999')
        emit('raw_byte_whitespace_conflict', post('complex', complex_body.strip())[0], 409)
        for suffix in ('?cursor=%30', '?limit=%31&cursor=0'):
            emit('decoded_canonical_query_' + suffix, page(suffix)[0], 200)
        for suffix in ('?cursor=%', '?cursor=%0', '?cursor=0%00', '?%6cimit=1&limit=2', '?cursor=0&&limit=1'):
            emit('malformed_query_' + suffix, page(suffix)[0], 400)
        for body in (b'\xef\xbb\xbf{}', b'{"x":"\xed\xa0\x80"}', b'{"x":01}', b'{"x":1.}', b'{"x":.1}', b'{"x":1e}'):
            emit('malformed_json_' + body.hex(), post('malformed', body)[0], 400)
        emit('invalid_requests_preserve_count', count(), 2)
        emit('invalid_id_remains_reusable', post('malformed', b'{}')[0], 201)
        huge_cursor = '1' + '0' * 10000
        emit('ten_thousand_digit_cursor', page('?cursor=' + huge_cursor), (200, {'items': [], 'next_cursor': None}))
        for method in ('PUT', 'DELETE', 'PATCH', 'OPTIONS'):
            status, value = request(method, '/events/alpha')
            emit('unsupported_method_json_' + method, (status, isinstance(value, dict)), (501, True))
        with closing(sqlite3.connect(db)) as connection:
            stored = connection.execute('SELECT raw_body FROM events WHERE event_id=?', ('complex',)).fetchone()[0]
        emit('stored_bytes_exact', stored == complex_body, True)
        print(json.dumps({'result': 'all independent probes passed'}), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
