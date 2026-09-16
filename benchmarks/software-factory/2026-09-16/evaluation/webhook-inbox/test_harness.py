"""Evaluator unit calibration; no reference product implementation."""

import hashlib
import hmac
import tempfile
import unittest
from pathlib import Path

from harness import signed_headers


class SigningCalibration(unittest.TestCase):
    def test_rfc4231_hmac_sha256_vector(self):
        digest = hmac.new(b"\x0b" * 20, b"Hi There", hashlib.sha256).hexdigest()
        self.assertEqual(digest, "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7")

    def test_header_helper_composes_exact_bytes(self):
        body = b'{ "unicode": "\xc3\xa9", "x": 1 }'
        stamp = "1789512345"
        headers = signed_headers("alpha", "one", body, timestamp=stamp, secret="key")
        expected = hmac.digest(b"key", b"1789512345." + body, "sha256").hex()
        self.assertEqual(headers, {"X-Event-ID": "one", "X-Timestamp": stamp, "X-Signature": expected})
        normalized = signed_headers("alpha", "one", b'{"unicode":"\xc3\xa9","x":1}', timestamp=stamp, secret="key")
        self.assertNotEqual(headers["X-Signature"], normalized["X-Signature"])

    def test_signature_uses_timestamp_and_secret(self):
        base = signed_headers("alpha", "one", b'{}', timestamp=100)
        later = signed_headers("alpha", "one", b'{}', timestamp=101)
        other_tenant = signed_headers("beta", "one", b'{}', timestamp=100)
        self.assertNotEqual(base["X-Signature"], later["X-Signature"])
        self.assertNotEqual(base["X-Signature"], other_tenant["X-Signature"])


if __name__ == "__main__":
    unittest.main()
