from tests.test_adapters_cases.hacker_news_github_artifact import *  # noqa: F401,F403

FEED_CHANNEL_ID = "UCharbourlight0000000000"
FEED_PAGE_ROUTES = ("youtube_channel_feed",)


class FeedPageRouteConstantTest(unittest.TestCase):
    """The retained YouTube channel feed uses a declared anonymous read."""

    def _routes(self):
        return FEED_PAGE_ROUTES


    def test_the_channel_feed_route_asks_by_the_id_the_evidence_measured(self):
        request = transport.build_transport_request(
            transport.YOUTUBE_CHANNEL_FEED_ROUTE, {"channel_id": FEED_CHANNEL_ID}
        )

        # The 2026-08-10 probes: `feeds/videos.xml?channel_id=` answered 200 with
        # 39 KB in 0.35 s. The channel is a query parameter, which is how the
        # measured url spells it, and not a path segment.
        self.assertEqual(
            request.url,
            "https://www.youtube.com/feeds/videos.xml?channel_id=" + FEED_CHANNEL_ID,
        )
        self.assertEqual(request.method, "GET")


    def test_feed_route_declares_keyless_access(self):
        for route_id in sorted(self._routes()):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertEqual(route.access_class, "K0")


    def test_every_one_of_them_names_the_party_that_answers_it(self):
        for route_id in sorted(self._routes()):
            with self.subTest(route=route_id):
                self.assertNotEqual(
                    transport.route_constant(route_id).operator_identity, ""
                )


    def test_no_request_any_of_them_builds_can_carry_a_body(self):
        for route_id in sorted(self._routes()):
            with self.subTest(route=route_id):

                request = transport.build_transport_request(
                    route_id, {"query": "x", "body": "y", "data": "z"}
                )

                self.assertEqual(request.body, "")

    def test_every_verb_that_is_not_a_read_is_refused(self):
        for route_id in sorted(self._routes()):
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                with self.subTest(route=route_id, method=method):
                    request = transport.TransportRequest(
                        route_id=route_id,
                        method=method,
                        url="https://example.test/probe",
                    )

                    with helpers.forbid_io():
                        with self.assertRaises(transport.TransportError) as caught:
                            transport.urlopen_read(request)

                    self.assertIn("write-capable method", str(caught.exception))
