"""The transport's stated-encoding decode, proven at the seam that owns it.

Stack Exchange's API compresses every answer whether or not the request asked
(measured 2026-09-01: `Content-Encoding: gzip` on a request that sent no
`Accept-Encoding`), and gzip bytes decoded as UTF-8 are garbage an adapter
can only mis-type as `malformed_json`. These cases prove the three readings
`transport.decoded_body` can make: honored, absent, and lied about.
"""

import gzip
import unittest

from super_research import transport
from tests.test_transport_cases.common import sent_headers


class DecodedBodyTest(unittest.TestCase):
    def test_a_stated_gzip_encoding_is_honored(self):
        body = '{"items": [{"question_id": 1}]}'
        headers = sent_headers("application/json", (("Content-Encoding", "gzip"),))
        self.assertEqual(
            transport.decoded_body(gzip.compress(body.encode("utf-8")), headers), body
        )

    def test_the_origins_own_casing_does_not_matter(self):
        body = "plain"
        headers = sent_headers("text/plain", (("content-encoding", "GZIP"),))
        self.assertEqual(
            transport.decoded_body(gzip.compress(body.encode("utf-8")), headers), body
        )

    def test_an_unstated_encoding_decodes_raw(self):
        headers = sent_headers("application/json", ())
        self.assertEqual(transport.decoded_body(b'{"a": 1}', headers), '{"a": 1}')
        self.assertEqual(transport.decoded_body(b"", None), "")

    def test_a_lying_gzip_header_degrades_to_the_raw_decode(self):
        # The body is not gzip: the typed parse failure downstream is the
        # honest reading, not a raised read that discards the whole step.
        headers = sent_headers("application/json", (("Content-Encoding", "gzip"),))
        self.assertEqual(transport.decoded_body(b'{"a": 1}', headers), '{"a": 1}')

    def test_the_decompressed_body_is_bounded_by_the_same_ceiling(self):
        headers = sent_headers("text/plain", (("Content-Encoding", "gzip"),))
        inflated = gzip.compress(b"x" * (transport.MAX_RESPONSE_BYTES + 1024))
        decoded = transport.decoded_body(inflated, headers)
        self.assertEqual(len(decoded), transport.MAX_RESPONSE_BYTES)


if __name__ == "__main__":
    unittest.main()
