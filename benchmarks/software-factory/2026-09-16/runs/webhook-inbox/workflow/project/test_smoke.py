"""Public smoke test: intentionally fails until ingestion/auth/storage are built."""

import hashlib
import hmac
import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from inbox import create_server


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = create_server(Path(self.temp.name) / "inbox.sqlite3", Path(__file__).with_name("config.example.json"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def test_health(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))

    def test_signed_roundtrip_and_retry(self):
        body = b'{"message":"hello"}'
        timestamp = str(int(time.time()))
        signature = hmac.new(b"alpha-example-hmac-secret-2026", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        headers = {"X-Event-ID": "smoke-1", "X-Timestamp": timestamp, "X-Signature": signature}
        status, result = self.request("POST", "/webhooks/alpha", body, headers)
        self.assertEqual(status, 201)
        self.assertEqual(result["duplicate"], False)
        self.assertEqual(self.request("POST", "/webhooks/alpha", body, headers)[0], 200)
        status, page = self.request("GET", "/events/alpha", headers={"Authorization": "Bearer alpha-example-read-token-2026"})
        self.assertEqual(status, 200)
        self.assertEqual([(item["event_id"], item["payload"]) for item in page["items"]], [("smoke-1", {"message": "hello"})])


if __name__ == "__main__":
    unittest.main()
