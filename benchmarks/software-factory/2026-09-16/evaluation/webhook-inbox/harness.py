"""Isolated black-box HTTP fixture; never imports builder-authored tests."""

import hashlib
import hmac
import http.client
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CONFIG = {"tenants": {
    "alpha": {"secret": "alpha-eval-hmac-92fa5e", "token": "alpha-eval-read-714b02"},
    "beta": {"secret": "beta-eval-hmac-f8b6c3", "token": "beta-eval-read-993d2a"},
}}


def signed_headers(tenant, event_id, body, timestamp=None, secret=None):
    stamp = str(int(time.time())) if timestamp is None else str(timestamp)
    key = CONFIG["tenants"][tenant]["secret"] if secret is None else secret
    digest = hmac.new(key.encode("utf-8"), stamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    return {"X-Event-ID": event_id, "X-Timestamp": stamp, "X-Signature": digest}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def status_is(response, expected):
    status, value = response
    require(status == expected, f"expected HTTP {expected}, received {status}: {value!r}")
    require(isinstance(value, dict), f"response must be a JSON object, received {type(value).__name__}")
    return value


class Sandbox:
    def __init__(self, project):
        self.project = Path(project).resolve()
        self.temp = tempfile.TemporaryDirectory(prefix="webhook-eval-")
        self.root = Path(self.temp.name)
        self.db = self.root / "inbox.sqlite3"
        self.config = self.root / "tenants.json"
        self.config.write_text(json.dumps(CONFIG), encoding="utf-8")
        self.process = None
        self.log = None
        self.round = 0

    def start(self, cli=False):
        self.round += 1
        ready = self.root / f"ready-{self.round}.json"
        log_path = self.root / f"server-{self.round}.log"
        self.log = log_path.open("wb")
        if cli:
            command = [sys.executable, "inbox.py", "--db", str(self.db), "--config", str(self.config), "--port", "0"]
        else:
            command = [sys.executable, str(Path(__file__).with_name("server_runner.py")), "--project", str(self.project), "--db", str(self.db), "--config", str(self.config), "--ready", str(ready)]
        self.process = subprocess.Popen(command, cwd=self.project, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("server exited before readiness: " + log_path.read_text(encoding="utf-8", errors="replace")[-2500:])
            data = None
            if cli:
                for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict) and "host" in item and "port" in item:
                            data = item
                            break
                    except ValueError:
                        continue
            elif ready.exists():
                data = json.loads(ready.read_text(encoding="utf-8"))
            if data:
                require(data["host"] == "127.0.0.1", "default/explicit bind must be IPv4 loopback")
                require(isinstance(data["port"], int) and 0 < data["port"] < 65536, "readiness port must identify the bound ephemeral port")
                self.address = (data["host"], data["port"])
                return self
            time.sleep(0.025)
        raise TimeoutError("server did not become ready within 10 seconds")

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None

    def restart(self):
        self.stop()
        return self.start()

    def close(self):
        self.stop()
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(*self.address, timeout=8)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            raw = response.read(2_000_000)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeError) as error:
                raise AssertionError(f"HTTP {response.status} response is not UTF-8 JSON: {raw[:160]!r}") from error
            require(isinstance(payload, dict), "HTTP response must be a JSON object")
            return response.status, payload
        finally:
            conn.close()

    def post(self, tenant="alpha", event_id="event-1", body=b'{"value":1}', **kwargs):
        headers = signed_headers(tenant, event_id, body, **kwargs)
        return self.request("POST", f"/webhooks/{tenant}", body, headers)

    def get(self, tenant="alpha", query="", token=None):
        actual_token = CONFIG["tenants"][tenant]["token"] if token is None else token
        return self.request("GET", f"/events/{tenant}{query}", headers={"Authorization": "Bearer " + actual_token})

    def page(self, tenant="alpha", query=""):
        result = status_is(self.get(tenant, query), 200)
        require(isinstance(result.get("items"), list), "items must be an array")
        require("next_cursor" in result, "next_cursor is required")
        for item in result["items"]:
            require(isinstance(item, dict), "each item must be an object")
            require(type(item.get("sequence")) is int and item["sequence"] > 0, "sequence must be a positive integer")
            require(isinstance(item.get("event_id"), str), "event_id must be a string")
            require(isinstance(item.get("payload"), dict), "payload must be a JSON object")
        return result


def assert_ids(page, ids):
    require([item["event_id"] for item in page["items"]] == ids, f"unexpected event IDs: {page['items']!r}")
