"""Behavioral cases for the one-shot visualization preview helper."""

import contextlib
import http.client
import io
import json
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from .support import ROOT, SCRIPTS

import preview  # noqa: E402


PREVIEW = SCRIPTS / "preview.py"
SKILL = SCRIPTS.parent / "SKILL.md"


class _PreviewProcess:
    def __init__(self, path):
        self.process = subprocess.Popen(
            [sys.executable, str(PREVIEW), str(path)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def readiness(self):
        line = self.process.stdout.readline()
        return line, json.loads(line)

    def finish(self, timeout=5):
        stdout, stderr = self.process.communicate(timeout=timeout)
        return self.process.returncode, stdout, stderr

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
            self.process.communicate()


class TestPreviewReadinessAndExactFile(unittest.TestCase):
    def test_missing_input_is_refused_before_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(PREVIEW), str(Path(tmp) / "missing.html")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("existing file", result.stderr)

    def test_ready_server_exposes_only_the_frozen_target_then_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            page = directory / "target.html"
            page.write_bytes(b"<h1>frozen target</h1>")
            (directory / "sibling.html").write_bytes(b"secret sibling")
            preview = _PreviewProcess(page)
            self.addCleanup(preview.close)

            line, payload = preview.readiness()
            self.assertEqual(line.strip(), json.dumps(payload, separators=(",", ":")))
            parsed = urllib.parse.urlsplit(payload["url"])
            self.assertEqual("http", parsed.scheme)
            self.assertEqual("127.0.0.1", parsed.hostname)
            self.assertGreater(parsed.port, 0)
            self.assertEqual("/target.html", parsed.path)
            self.assertIsNone(preview.process.poll(), "readiness must be flushed live")

            connection = http.client.HTTPConnection(parsed.hostname, parsed.port)
            connection.request("GET", "/sibling.html")
            refused = connection.getresponse()
            refused.read()
            self.assertEqual(404, refused.status)
            self.assertIsNone(preview.process.poll())

            connection.request("GET", parsed.path)
            response = connection.getresponse()
            body = response.read()
            connection.close()
            self.assertEqual(200, response.status)
            self.assertEqual(b"<h1>frozen target</h1>", body)
            self.assertEqual("text/html; charset=utf-8", response.getheader("Content-Type"))
            self.assertEqual(str(len(body)), response.getheader("Content-Length"))
            self.assertEqual("no-store", response.getheader("Cache-Control"))

            returncode, stdout, stderr = preview.finish()
            self.assertEqual(0, returncode, stderr)
            self.assertEqual("", stdout)
            self.assertEqual("", stderr)

    def test_head_and_refusals_do_not_consume_encoded_filename_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            page = directory / "a space#%中.html"
            original = "<p>byte-identical ∥ 中文</p>".encode("utf-8")
            page.write_bytes(original)
            preview_process = _PreviewProcess(page)
            self.addCleanup(preview_process.close)

            _, payload = preview_process.readiness()
            parsed = urllib.parse.urlsplit(payload["url"])
            expected_path = "/a%20space%23%25%E4%B8%AD.html"
            self.assertEqual(expected_path, parsed.path)
            connection = http.client.HTTPConnection(parsed.hostname, parsed.port)

            connection.request("HEAD", expected_path)
            response = connection.getresponse()
            self.assertEqual(b"", response.read())
            self.assertEqual(200, response.status)
            self.assertEqual(str(len(original)), response.getheader("Content-Length"))
            self.assertIsNone(preview_process.process.poll())

            refused_paths = ("/", expected_path + "?variant=1", "/%2e%2e/sibling.html")
            for refused_path in refused_paths:
                connection.request("GET", refused_path)
                response = connection.getresponse()
                body = response.read()
                self.assertEqual(404, response.status)
                self.assertNotIn(str(directory).encode("utf-8"), body)

            for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
                connection.request(method, expected_path)
                response = connection.getresponse()
                body = response.read()
                self.assertGreaterEqual(response.status, 400)
                self.assertNotIn(str(directory).encode("utf-8"), body)
            self.assertIsNone(preview_process.process.poll())

            page.write_bytes(b"changed after readiness")
            connection.request("GET", expected_path)
            response = connection.getresponse()
            self.assertEqual(original, response.read())
            connection.close()
            self.assertEqual(200, response.status)
            returncode, stdout, stderr = preview_process.finish()
            self.assertEqual(0, returncode, stderr)
            self.assertEqual("", stdout)
            self.assertEqual("", stderr)


class TestPreviewFailureCleanup(unittest.TestCase):
    def test_read_and_bind_failures_emit_no_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_bytes(b"page")
            for label, read_patch, server_factory in (
                (
                    "read",
                    mock.patch.object(Path, "read_bytes", side_effect=OSError),
                    preview._PreviewServer,
                ),
                (
                    "bind",
                    contextlib.nullcontext(),
                    lambda _address, _handler: (_ for _ in ()).throw(OSError()),
                ),
            ):
                stdout, stderr = io.StringIO(), io.StringIO()
                with self.subTest(failure=label), read_patch:
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
                        stderr
                    ):
                        returncode = preview._serve(
                            page, timeout_seconds=0.02, server_factory=server_factory
                        )
                self.assertNotEqual(0, returncode)
                self.assertEqual("", stdout.getvalue())
                self.assertNotEqual("", stderr.getvalue())

    def test_timeout_is_nonzero_and_leaves_no_live_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_bytes(b"page")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = preview._serve(page, timeout_seconds=0.02)

        self.assertNotEqual(0, returncode)
        lines = stdout.getvalue().splitlines()
        self.assertEqual(1, len(lines))
        parsed = urllib.parse.urlsplit(json.loads(lines[0])["url"])
        self.assertIn("timed out", stderr.getvalue())
        with self.assertRaises(OSError):
            socket.create_connection((parsed.hostname, parsed.port), timeout=0.2)

    def test_connected_client_that_sends_no_request_is_bounded_by_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_bytes(b"page")
            command = (
                "import sys;"
                f"sys.path.insert(0,{str(SCRIPTS)!r});"
                "import preview;"
                f"raise SystemExit(preview._serve({str(page)!r},timeout_seconds=0.1))"
            )
            process = subprocess.Popen(
                [sys.executable, "-c", command], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8",
            )
            self.addCleanup(lambda: process.kill() if process.poll() is None else None)
            payload = json.loads(process.stdout.readline())
            parsed = urllib.parse.urlsplit(payload["url"])
            client = socket.create_connection((parsed.hostname, parsed.port), timeout=1)
            try:
                _, stderr = process.communicate(timeout=2)
            finally:
                client.close()
        self.assertNotEqual(0, process.returncode)
        self.assertTrue("timed out" in stderr or "failed" in stderr, stderr)

    def test_serving_error_is_nonzero_and_closes_server(self):
        class FailingServer:
            def __init__(self, _address, _handler):
                self.server_address = ("127.0.0.1", 43210)
                self.closed = False

            def handle_request(self):
                raise OSError("injected serving failure")

            def server_close(self):
                self.closed = True

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_bytes(b"page")
            server = FailingServer(None, None)
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = preview._serve(
                    page,
                    timeout_seconds=1,
                    server_factory=lambda _address, _handler: server,
                )

        self.assertNotEqual(0, returncode)
        self.assertTrue(server.closed)
        self.assertEqual(1, len(stdout.getvalue().splitlines()))
        self.assertIn("preview failed", stderr.getvalue())

    def test_accept_socket_error_is_immediate_and_closes_server(self):
        class SocketFailureServer:
            def __init__(self):
                self.server_address = ("127.0.0.1", 43210)
                self.socket_failed = False
                self.closed = False

            def handle_request(self):
                self.socket_failed = True

            def server_close(self):
                self.closed = True

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_bytes(b"page")
            server = SocketFailureServer()
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = preview._serve(
                    page,
                    timeout_seconds=0.02,
                    server_factory=lambda _address, _handler: server,
                )

        self.assertNotEqual(0, returncode)
        self.assertTrue(server.closed)
        self.assertIn("socket", stderr.getvalue())

    def test_response_error_is_nonzero_and_closes_server(self):
        class ResponseFailureServer:
            def __init__(self):
                self.server_address = ("127.0.0.1", 43210)
                self.response_failed = True
                self.closed = False

            def handle_request(self):
                pass

            def server_close(self):
                self.closed = True

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "page.html"
            page.write_bytes(b"page")
            server = ResponseFailureServer()
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = preview._serve(
                    page,
                    timeout_seconds=1,
                    server_factory=lambda _address, _handler: server,
                )

        self.assertNotEqual(0, returncode)
        self.assertTrue(server.closed)
        self.assertIn("writing a response", stderr.getvalue())


class TestPreviewSkillContract(unittest.TestCase):
    def test_visual_look_pass_uses_the_one_shot_http_preview(self):
        body = SKILL.read_text(encoding="utf-8")
        start = body.index("scripts/preview.py")
        readiness = body.index("JSON URL", start)
        opened = body.index("open that HTTP URL", readiness)
        successful_exit = body.index("successful exit", opened)
        self.assertLess(start, readiness)
        self.assertLess(readiness, opened)
        self.assertLess(opened, successful_exit)
        self.assertIn("forbid `file://`", body)
