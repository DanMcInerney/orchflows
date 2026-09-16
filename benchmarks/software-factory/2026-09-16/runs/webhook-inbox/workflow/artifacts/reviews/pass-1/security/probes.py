import hashlib, hmac, http.client, json, pathlib, socket, sqlite3, sys, tempfile, threading, time
from unittest.mock import patch
from contextlib import closing

snapshot = pathlib.Path(sys.argv[1])
report = pathlib.Path(__file__).parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(snapshot))
from inbox import create_server

manifest = json.loads((report.parents[2] / "pass-1" / "coordinator-manifest.json").read_text())
actual = {name: hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in manifest["files"]}
assert actual == manifest["files"], "snapshot identity mismatch"
results = [{"check":"snapshot_file_hashes", "result":"pass", "files":len(actual)}]
with tempfile.TemporaryDirectory(dir=report) as tmp:
    root = pathlib.Path(tmp)
    credentials = {"alpha":{"secret":"a-secret-\u03bb", "token":"a-token"}, "beta":{"secret":"b-secret","token":"b-token"}}
    (root/"config.json").write_text(json.dumps({"tenants":credentials}), encoding="utf-8")
    server = create_server(root/"events.db", root/"config.json")
    runner = threading.Thread(target=server.serve_forever, kwargs={"poll_interval":0.01})
    runner.start()
    def rows():
        with closing(sqlite3.connect(root/"events.db")) as db:
            return db.execute("select sequence,tenant,event_id,raw_body from events order by sequence").fetchall()
    def wire(headers, body=b"{}", method="POST", path="/webhooks/alpha", extra=b""):
        with socket.create_connection(server.server_address, timeout=3) as conn:
            data = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n".encode()
            data += b"\r\n".join(headers) + b"\r\n\r\n" + body + extra
            conn.sendall(data)
            conn.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(conn)
            response.begin()
            raw = response.read()
            return response.status, json.loads(raw)
    def signed(event="event", body=b"{}", tenant="alpha", timestamp=None):
        timestamp = str(int(time.time())) if timestamp is None else timestamp
        signature = hmac.new(credentials[tenant]["secret"].encode(), timestamp.encode()+b"."+body, hashlib.sha256).hexdigest()
        return [b"Content-Length: "+str(len(body)).encode(), b"X-Event-ID: "+event.encode(),
                b"X-Timestamp: "+timestamp.encode(), b"X-Signature: "+signature.encode()]
    def reject(label, headers, expected, body=b"{}", method="POST", path="/webhooks/alpha", extra=b""):
        before = rows()
        status, value = wire(headers, body, method, path, extra)
        assert status == expected, (label, status, expected)
        assert rows() == before, (label, "write effect")
        text = json.dumps(value)
        for values in credentials.values():
            for secret in values.values():
                assert secret not in text, (label,"credential disclosure")
        for header in headers:
            if header.lower().startswith(b"x-signature:"):
                sig=header.split(b":",1)[1].strip().decode("latin-1")
                if len(sig)>=32:
                    assert sig not in text, (label,"signature disclosure")
        results.append({"check":label,"status":status,"rows_unchanged":True,"credentials_absent":True})
    try:
        body=b'{"nested":{"content":"\\u03bb"}}'
        assert wire(signed("fixed",body),body)[0]==201
        for key in (b"X-Event-ID",b"X-Timestamp",b"X-Signature",b"Content-Length"):
            headers=signed()
            duplicated=next(h for h in headers if h.startswith(key))
            reject("duplicate "+key.decode(),headers+[duplicated.lower() if key==b"Content-Length" else duplicated],400)
        for label,extra in [
            ("folded signature",b" continuation"),
            ("whitespace before colon",b"X-Signature : "+"0".encode()*64),
            ("transfer-encoding chunked",b"Transfer-Encoding: chunked"),
            ("transfer-encoding identity",b"Transfer-Encoding: identity")]:
            reject(label,signed()+[extra],400)
        for idx in range(4):
            headers=signed()
            headers[idx]=headers[idx].replace(b": ",b":  ",1)
            reject("extra leading space "+str(idx),headers,400)
        reject("tenant alpha signature to beta",signed(tenant="alpha"),401,path="/webhooks/beta")
        reject("tenant alpha token to beta",[b"Authorization: Bearer a-token"],401,b"", "GET","/events/beta")
        reject("duplicate authorization",[b"Authorization: Bearer a-token",b"authorization: Bearer a-token"],401,b"", "GET","/events/alpha")
        for token in (b"a-token ",b" a-token",b"a-token\t",b"a-token\x00",b"A-token"):
            reject("token grammar "+repr(token),[b"Authorization: Bearer "+token],401,b"","GET","/events/alpha")
        for label,value in [("raw-body tamper",b'{"changed":1}'),("non UTF8",b'{"x":"\xff"}'),("malformed nested JSON",b'{"x":'+b'['*1500+b'0'+b']'*1499+b'}')]:
            headers=signed(body=value)
            if label=="raw-body tamper":
                headers=signed(body=b'{"signed":1}')
                headers[0]=b"Content-Length: "+str(len(value)).encode()
            reject(label,headers,401 if label=="raw-body tamper" else 400,value)
        with patch("inbox.time.time",return_value=2000000):
            for timestamp in ("1999699","2000301"):
                reject("stale/future retry "+timestamp,signed("fixed",body,timestamp=timestamp),401,body)
            headers=signed("fixed",body)
            headers[-1]=b"X-Signature: "+b"0"*64
            reject("bad signature identical retry",headers,401,body)
        headers=signed()
        headers[0]=b"Content-Length: 3"
        reject("truncated framing",headers,400)
        injection="x'); DROP TABLE events; --"
        assert wire(signed(injection))[0]==201
        assert any(row[2]==injection for row in rows())
        results.append({"check":"SQL-looking event ID preserved","result":"pass"})
        before=rows()
        status,value=wire(signed("pipeline"),extra=b"POST /webhooks/alpha HTTP/1.1\r\n\r\n")
        assert status==201 and len(rows())==len(before)+1
        results.append({"check":"connection closes before pipelined second request","result":"pass"})
        status,page=wire([b"Authorization: Bearer b-token"],b"","GET","/events/beta?cursor=0")
        assert status==200 and page["items"]==[]
        results.append({"check":"authenticated beta list has no alpha rows","result":"pass"})
    finally:
        server.shutdown()
        server.server_close()
        runner.join()
(report/"probe-results.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps({"checks":len(results),"result":"PASS","snapshot_files_match":True}))
