"""The transport's stated-encoding decode, proven at the seam that owns it.

Stack Exchange's API compresses every answer whether or not the request asked
(measured 2026-09-01: `Content-Encoding: gzip` on a request that sent no
`Accept-Encoding`), and gzip bytes decoded as UTF-8 are garbage an adapter
can only mis-type as `malformed_json`. These cases prove the three readings
`transport.decoded_body` can make: honored, absent, and refused.
"""

import gzip
import unittest
import urllib.request
from unittest import mock

from super_research import transport
from tests.test_transport_cases.common import sent_headers

GZIP_HEADERS = (("Content-Encoding", "gzip"),)
TRUNCATED_GZIP = gzip.compress(b"x" * 200000)[:-40]
GZIP_HEADER_OVER_GARBAGE = gzip.compress(b"x" * 200000)[:10] + b"not deflate at all" * 30


class GzipBytesResponse:
    """The little of an http response ``urlopen_read`` reads, answering raw bytes."""

    def __init__(self, raw):
        self.status = 200
        self.url = "https://api.stackexchange.com/2.3/search/advanced"
        self.headers = sent_headers("application/json", GZIP_HEADERS)
        self._raw = raw

    def read(self, limit):
        return self._raw[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


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

    def test_a_lying_gzip_header_is_a_transport_failure(self):
        # The body is not gzip: the read is refused rather than decoded raw
        # into something an adapter would mis-type.
        headers = sent_headers("application/json", (("Content-Encoding", "gzip"),))
        with self.assertRaises(transport.TransportError):
            transport.decoded_body(b'{"a": 1}', headers)

    def test_a_gzip_stream_cut_short_is_the_same_transport_failure(self):
        # A truncated member raises EOFError, not the gzip module's own error;
        # it is still a body that is not the gzip it declared.
        headers = sent_headers("application/json", GZIP_HEADERS)
        with self.assertRaises(transport.TransportError):
            transport.decoded_body(TRUNCATED_GZIP, headers)

    def test_a_gzip_header_over_garbage_is_the_same_transport_failure(self):
        # A valid header followed by bytes that are not deflate raises from
        # zlib itself; one typed failure covers all three.
        headers = sent_headers("application/json", GZIP_HEADERS)
        with self.assertRaises(transport.TransportError):
            transport.decoded_body(GZIP_HEADER_OVER_GARBAGE, headers)

    def test_a_bad_gzip_body_leaves_the_opener_as_a_typed_failure(self):
        # Through the real opener: the read raises the transport's own error,
        # which the runner types `unreachable`, rather than an exception that
        # escapes the step and discards every step already run.
        request = transport.build_transport_request(
            transport.STACKEXCHANGE_SEARCH_ROUTE, {"q": "probe"}
        )
        for raw in (TRUNCATED_GZIP, GZIP_HEADER_OVER_GARBAGE, b'{"a": 1}'):
            with self.subTest(raw=raw[:12]):
                with mock.patch.object(
                    urllib.request, "urlopen", lambda outbound, timeout=None, raw=raw: GzipBytesResponse(raw)
                ):
                    with self.assertRaises(transport.TransportError) as caught:
                        transport.urlopen_read(request)
                self.assertEqual(caught.exception.loss, transport.UNREACHABLE)

    def test_the_decompressed_body_is_bounded_by_the_same_ceiling(self):
        headers = sent_headers("text/plain", (("Content-Encoding", "gzip"),))
        inflated = gzip.compress(b"x" * (transport.MAX_RESPONSE_BYTES + 1024))
        decoded = transport.decoded_body(inflated, headers)
        self.assertEqual(len(decoded), transport.MAX_RESPONSE_BYTES)


if __name__ == "__main__":
    unittest.main()
