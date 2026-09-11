"""Transport request and opener cases."""

from .common import *

def outbound_blob(outbound):
    """Everything a urllib request would put on the wire, as one string."""

    return " ".join(
        [outbound.full_url, repr(sorted(outbound.header_items())), repr(outbound.data)]
    )


class GuestActivationRouteTest(unittest.TestCase):
    """The two non-read operations, and the gate that keeps them two.

    Minting an anonymous guest token needs a POST, and so does asking InnerTube
    a question it only takes in a JSON body. Neither creates anything at an
    origin: they are reads spelled in an awkward verb. What separates that from
    a write-capable channel is not the verb but the enumeration — each is named
    by route id in one of two closed sets, asserted below in both directions,
    and no route anywhere reaches PUT, PATCH or DELETE.
    """

    def test_the_activation_route_carries_the_shape_the_evidence_measured(self):
        route = transport.route_constant(transport.X_GUEST_ACTIVATE_ROUTE)

        # The 2026-08-10 probes (X): POST api.twitter.com/1.1/guest/activate.json
        # returned 200 with a guest token, keylessly.
        self.assertEqual(route.access_class, "K1")
        self.assertEqual(route.method, "POST")
        self.assertEqual(route.origin, "https://api.twitter.com")
        self.assertEqual(route.path, "/1.1/guest/activate.json")
        self.assertEqual(route.credential_id, transport.X_GUEST_PUBLIC_BEARER)

    def test_the_activation_route_needs_no_user_credential(self):
        self.assertTrue(transport.route_admissions()[transport.X_GUEST_ACTIVATE_ROUTE])

    def test_the_routes_declaring_a_non_read_method_are_exactly_the_declared_exceptions(self):
        # Both directions. A route declaring a non-read method and named in
        # neither set fails here; a route named in a set while declaring a read
        # fails here too, because an exception nothing needs must not be held.
        declared = sorted(transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES)
        non_read = sorted(
            route_id
            for route_id, route in transport.ROUTE_CONSTANTS.items()
            if route.method not in transport.READ_METHODS
        )

        self.assertEqual(non_read, declared)
        # Spelled as well as derived: an allowlist compared only against itself
        # would admit a third member silently.
        self.assertEqual(
            declared, [transport.X_GUEST_ACTIVATE_ROUTE, transport.YOUTUBE_INNERTUBE_ROUTE]
        )
        # Two exceptions, one verb between them, and no route in both.
        self.assertEqual(transport.TOKEN_ACTIVATION_METHODS, ("POST",))
        self.assertEqual(transport.QUERY_BODY_METHODS, ("POST",))
        self.assertEqual(
            sorted(set(transport.TOKEN_ACTIVATION_ROUTES) & set(transport.QUERY_BODY_ROUTES)),
            [],
        )

    def test_only_a_declared_exception_route_may_use_a_method_that_is_not_a_read(self):
        declared = transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES

        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                admitted = transport.admitted_methods(route_id)

                if route_id in declared:
                    self.assertEqual(admitted, transport.READ_METHODS + ("POST",))
                else:
                    self.assertEqual(admitted, transport.READ_METHODS)
                # Unconditional, and true of the exceptions too: the widening
                # is one more way to ask, never a way to change anything.
                for method in ("PUT", "PATCH", "DELETE"):
                    self.assertNotIn(method, admitted)


class WriteVerbRefusalTest(unittest.TestCase):
    """Read-only bar: no code path here can mutate a remote resource."""

    def _refusal_for(self, route_id, method):
        request = transport.TransportRequest(
            route_id=route_id, method=method, url="https://example.test/probe"
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError) as caught:
                transport.urlopen_response(request)

        return str(caught.exception)

    def test_every_write_verb_is_refused_on_every_route(self):
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS"):
            for route_id in sorted(transport.ROUTE_CONSTANTS):
                with self.subTest(method=method, route=route_id):
                    self.assertIn(
                        "refusing a write-capable method", self._refusal_for(route_id, method)
                    )

    def test_post_is_refused_on_every_route_but_the_two_declared_exceptions(self):
        declared = transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES
        refused = []

        for route_id in sorted(transport.ROUTE_CONSTANTS):
            if route_id in declared:
                continue
            with self.subTest(route=route_id):
                self.assertIn(
                    "refusing a write-capable method", self._refusal_for(route_id, "POST")
                )
                refused.append(route_id)

        # The skip list is what a widening grows, so the loop states how much
        # it still covers: every route but the two, and never zero.
        self.assertEqual(len(refused), len(transport.ROUTE_CONSTANTS) - len(declared))
        self.assertGreater(len(refused), 0)

    def test_a_non_https_url_is_still_refused_before_any_socket(self):
        request = transport.TransportRequest(
            route_id=transport.X_GUEST_ACTIVATE_ROUTE,
            method="POST",
            url="http://api.twitter.com/1.1/guest/activate.json",
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError) as caught:
                transport.urlopen_response(request)

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
            transport.DDG_HTML_ROUTE if route is None else route, {"q": "local model"}
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

    def test_a_credential_placed_in_the_query_does_not_ride_out_on_the_error(self):
        # T02, on the path that raises. `HTTPError.url` is the address the
        # request actually went out on — credential and all — so this is the
        # one branch where the answering address could carry one back out.
        route = transport.YOUTUBE_INNERTUBE_ROUTE
        (_, _, _, final_url, _), outbound = self._read(
            401, "{}", "application/json", route=route
        )

        for _, value in credential_strings():
            with self.subTest(secret=value):
                self.assertNotIn(value, final_url)
        self.assertTrue(outbound.full_url)

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

        request = transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "x"})
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
        carrier, _ = offline_transport({transport.DDG_HTML_ROUTE: answer})
        return carrier.fetch(
            transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "local model"})
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

    def test_the_three_value_view_is_still_three_values(self):
        recorder = RecordingUrlopen(200, "{}", "application/json")
        request = transport.build_transport_request(
            transport.GITHUB_REST_ROUTE, {"owner": "o"}
        )

        with mock.patch.object(urllib.request, "urlopen", recorder):
            self.assertEqual(len(transport.urlopen_response(request)), 3)


class OutboundRequestTest(unittest.TestCase):
    """What the default opener would put on the wire, captured without a socket."""

    def _sent(self, request, recorder):
        with mock.patch.object(urllib.request, "urlopen", recorder):
            result = transport.urlopen_response(request)
        return result, recorder.requests[0]

    def test_the_activation_post_carries_the_public_bearer_and_no_body(self):
        recorder = RecordingUrlopen(200, '{"guest_token": "1234567890"}', "application/json")
        request = transport.build_transport_request(transport.X_GUEST_ACTIVATE_ROUTE)

        (status, body, content_type), outbound = self._sent(request, recorder)

        bearer = transport.PUBLIC_CLIENT_CREDENTIALS[transport.X_GUEST_PUBLIC_BEARER].value
        self.assertEqual(outbound.get_method(), "POST")
        self.assertIsNone(outbound.data)
        self.assertIn(bearer, outbound_blob(outbound))
        self.assertEqual(status, 200)
        self.assertIn("guest_token", body)
        self.assertEqual(content_type, "application/json")

    def test_a_keyless_route_sends_no_credential_at_all(self):
        recorder = RecordingUrlopen(200, "<html></html>", "text/html")
        request = transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})

        _, outbound = self._sent(request, recorder)

        blob = outbound_blob(outbound)
        for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values():
            self.assertNotIn(credential.value, blob)
        self.assertEqual(outbound.get_method(), "GET")
        self.assertIn(transport.USER_AGENT, blob)
