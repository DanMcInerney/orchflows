"""Transport request and opener cases."""

from .common import *

def outbound_blob(outbound):
    """Everything a urllib request would put on the wire, as one string."""

    return " ".join(
        [outbound.full_url, repr(sorted(outbound.header_items())), repr(outbound.data)]
    )




class WriteVerbRefusalTest(unittest.TestCase):
    """Read-only bar: no code path here can mutate a remote resource."""

    def _refusal_for(self, route_id, method):
        request = transport.TransportRequest(
            route_id=route_id, method=method, url="https://example.test/probe"
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError) as caught:
                transport.urlopen_read(request)

        return str(caught.exception)

    def test_every_write_verb_is_refused_on_every_route(self):
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS"):
            for route_id in sorted(transport.ROUTE_CONSTANTS):
                with self.subTest(method=method, route=route_id):
                    self.assertIn(
                        "refusing a write-capable method", self._refusal_for(route_id, method)
                    )

    def test_post_is_refused_on_every_route(self):
        declared = ()
        refused = []

        for route_id in sorted(transport.ROUTE_CONSTANTS):
            if route_id in declared:
                continue
            with self.subTest(route=route_id):
                self.assertIn(
                    "refusing a write-capable method", self._refusal_for(route_id, "POST")
                )
                refused.append(route_id)

        # Every retained route is read-only.
        self.assertEqual(len(refused), len(transport.ROUTE_CONSTANTS) - len(declared))
        self.assertGreater(len(refused), 0)

    def test_a_non_https_url_is_still_refused_before_any_socket(self):
        request = transport.TransportRequest(
            route_id=transport.HN_ALGOLIA_SEARCH_ROUTE,
            method="POST",
            url="http://8.8.8.8/feed.xml",
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError) as caught:
                transport.urlopen_read(request)

        self.assertIn("non-https", str(caught.exception))




class RaisingUrlopen:
    """Stand in for ``urllib.request.urlopen`` the way it really answers a non-2xx.

    ``FakeHTTPResponse`` returns every status, which no real ``urlopen`` does:
    urllib raises :class:`urllib.error.HTTPError` for every response outside
    2xx, and the opener's own ``except`` is what turns that back into a status,
    a body, a content type, and an answering address. Nothing in the suite
    constructed one, so every failure path in this package — `stale_identifier`,
    `auth_required`, `rate_limited`, `network_intercepted` — reached production
    through a branch no test executed. ``HTTPError`` is also a response object
    in its own right, which is why the branch can read it at all.
    """

    def __init__(self, status, body, content_type, url="", headers=()):
        self.status = status
        self.body = body
        self.content_type = content_type
        self.url = url
        self.headers = tuple(headers)
        self.requests = []

    def __call__(self, outbound, timeout=None):
        self.requests.append(outbound)
        raise urllib.error.HTTPError(
            self.url or outbound.full_url,
            self.status,
            "an origin's own refusal",
            sent_headers(self.content_type, self.headers),
            io.BytesIO(self.body.encode("utf-8")),
        )


class TheOpenerReadsARealHTTPErrorTest(unittest.TestCase):
    """Fidelity: the branch every non-2xx in production goes through, executed.

    Nothing under test changes here. This exists because the stand-in that
    every other row uses is more forgiving than urllib is, and the last time an
    offline stand-in was gentler than the real thing it hid the `final_url`
    credential leak for ten tickets.
    """

    def _read(self, status, body, content_type="text/html", route=None, headers=()):
        recorder = RaisingUrlopen(status, body, content_type, headers=headers)
        request = transport.build_transport_request(
            transport.HN_ALGOLIA_SEARCH_ROUTE if route is None else route, {"query": "probe"}
        )
        with mock.patch.object(urllib.request, "urlopen", recorder):
            return transport.urlopen_read(request), recorder.requests[0]

    def test_a_raised_status_comes_back_as_a_status_and_not_as_a_tool_failure(self):
        (status, body, content_type, final_url, _), outbound = self._read(
            404, "<html>not found</html>"
        )

        self.assertEqual(status, 404)
        self.assertIn("not found", body)
        self.assertEqual(content_type, "text/html")
        self.assertEqual(final_url, outbound.full_url)

    def test_the_channel_verdict_still_tells_this_network_from_the_origin(self):
        portal = read_fixture("captive_portal.html")
        blocked, _ = self._read(503, portal)
        refused, _ = self._read(503, "<html>Service Unavailable</html>")

        self.assertEqual(
            transport.channel_verdict(blocked[0], blocked[1]), transport.NETWORK_INTERCEPTED
        )
        self.assertEqual(
            transport.channel_verdict(refused[0], refused[1]), transport.ORIGIN_FAILURE
        )


    def test_the_headers_arrive_on_the_branch_that_raises(self):
        # Where `Retry-After` actually lives. A 429 is a raise, so headers read
        # only off the returning branch would be headers the scheduler never
        # sees on the one status it exists to answer.
        answered, _ = self._read(
            transport.RATE_LIMITED_STATUS,
            "slow down",
            headers=((transport.RETRY_AFTER_HEADER, "120"),),
        )

        self.assertEqual(
            transport.header_value(answered[4], transport.RETRY_AFTER_HEADER), "120"
        )

    def test_an_oserror_is_still_a_tool_failure_and_never_a_status(self):
        # The other half of the same try: a refused connection has no status to
        # report, so it must stay a `TransportError` rather than becoming one.
        def refuse(outbound, timeout=None):
            raise OSError("connection refused")

        request = transport.build_transport_request(transport.HN_ALGOLIA_SEARCH_ROUTE, {"query": "probe"})
        with mock.patch.object(urllib.request, "urlopen", refuse):
            with self.assertRaises(transport.TransportError):
                transport.urlopen_read(request)


class TheAnswerCarriesWhatTheOriginSaidTest(unittest.TestCase):
    """Criterion 1: an origin's own headers reach a caller, or say it sent none.

    Until they did, the one thing an origin can say about how long it wants to
    be left alone died inside the opener, and every wait this package took was
    a constant it had guessed rather than an interval it had been told.
    """

    def _fetched(self, answer):
        carrier, _ = offline_transport({transport.HN_ALGOLIA_SEARCH_ROUTE: answer})
        return carrier.fetch(
            transport.build_transport_request(transport.HN_ALGOLIA_SEARCH_ROUTE, {"query": "probe"})
        )

    def test_the_headers_an_opener_reports_reach_the_response(self):
        response = self._fetched(
            (
                transport.RATE_LIMITED_STATUS,
                "slow down",
                "text/plain",
                "https://asked.invalid/html/",
                ((transport.RETRY_AFTER_HEADER, "120"),),
            )
        )

        self.assertEqual(response.headers, ((transport.RETRY_AFTER_HEADER, "120"),))

    def test_an_opener_that_reports_no_headers_says_the_origin_sent_none(self):
        # The four-value opener contract every stand-in in this suite was
        # written against, unchanged: it reports no headers and gets an empty
        # set rather than an error.
        response = self._fetched((200, "<html></html>", "text/html"))

        self.assertEqual(response.headers, ())

    def test_a_header_is_found_whatever_case_the_origin_spelled_it_in(self):
        for spelling in ("Retry-After", "retry-after", "RETRY-AFTER", "ReTrY-aFtEr"):
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    transport.header_value(
                        ((spelling, "120"),), transport.RETRY_AFTER_HEADER
                    ),
                    "120",
                )

    def test_a_header_nobody_sent_reads_as_nothing_rather_than_raising(self):
        self.assertEqual(transport.header_value((), transport.RETRY_AFTER_HEADER), "")
        self.assertEqual(
            transport.header_value(
                (("Content-Type", "text/html"),), transport.RETRY_AFTER_HEADER
            ),
            "",
        )

    def test_the_real_opener_reports_what_the_origin_sent(self):
        recorder = RecordingUrlopen(
            200, "{}", "application/json", headers=(("x-ratelimit-remaining", "59"),)
        )
        request = transport.build_transport_request(
            transport.GITHUB_REST_ROUTE, {"owner": "o"}
        )

        with mock.patch.object(urllib.request, "urlopen", recorder):
            answered = transport.urlopen_read(request)

        self.assertEqual(
            transport.header_value(answered[4], "X-RateLimit-Remaining"), "59"
        )
