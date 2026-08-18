from tests.test_adapters_cases.hacker_news_github_artifact import *  # noqa: F401,F403

REDDIT_SUBREDDIT = "LocalLLaMA"
REDDIT_FEED_FIELDS = ("title", "link", "author", "updated")
# The 2026-08-10 probes, carry-over: `feeds/videos.xml?channel_id=` answered 200 with
# 39 KB in 0.35 s — the one RSS/Atom document in the evidence.
FEED_CHANNEL_ID = "UCharbourlight0000000000"
# the captive-portal caveat, control probes: `example.com` and `wikipedia.org` answered
# 200 with genuine origin content from this host, while the appliance answered
# `tiktok.com` and `ecosia.org` with a 503 login portal. Those two are the only
# static documents the evidence measures, and they are what `public_page` may
# select between.
ARTICLE_TITLE = "Rate_limiting"

FEED_PAGE_ROUTES = (
    "public_page_article",
    "public_page_control",
    "reddit_feed",
    "youtube_channel_feed",
)

# Every way a caller could try to name an address instead of a document. Each
# is refused, and the transport-level half of that claim is here: a value the
# route declares as a path segment is percent-quoted into it, so no string a
# caller supplies can move the host the request goes to.
ADDRESS_SHAPED_VALUES = (
    "https://evil.example/x",
    "//evil.example/x",
    "http://127.0.0.1:8080/admin",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "../../etc/passwd",
    "en.wikipedia.org/wiki/Rate_limiting",
)


class FeedPageRouteConstantTest(unittest.TestCase):
    """Four routes, four origins, every one a plain keyless read.

    Three adapters: a feed reader, a selected-document reader, and a freshness
    probe. What separates the middle one from the generic HTTP primitive the
    spec's non-goals forbid begins here, one seam below the adapter: a selected
    page's host and endpoint are declared in the route table like every other
    route's, and the caller fills one declared segment. There is no route in
    this package whose host a caller supplies, and these three do not become
    the first.

    The Reddit route carries the second claim: `.rss` is the only Reddit
    surface here. The 2026-08-10 probes recorded `.json` answering 403 to three
    unrelated User-Agents from three hosts, which is IP-class blocking no
    header set changes, so it is not a route and not a fallback.
    """

    def _routes(self):
        return FEED_PAGE_ROUTES

    def test_the_reddit_feed_route_is_the_rss_endpoint_the_evidence_measured(self):
        request = transport.build_transport_request(
            transport.REDDIT_FEED_ROUTE, {"subreddit": REDDIT_SUBREDDIT}
        )

        # The 2026-08-10 probes, Reddit: `www.reddit.com/r/<sub>.rss`, 200, 32 KB,
        # 1.4 s. Reddit names the representation with a path suffix the way
        # Firebase does, so the suffix is part of the endpoint's shape and is
        # owned in the route table rather than composed by an adapter.
        self.assertEqual(
            request.url, "https://www.reddit.com/r/" + REDDIT_SUBREDDIT + ".rss"
        )
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.body, "")

    def test_a_request_naming_no_subreddit_takes_neither_the_segment_nor_the_suffix(self):
        # `/r.rss` is a different resource from `/r`, and guessing which was
        # meant is not the transport's to do.
        request = transport.build_transport_request(transport.REDDIT_FEED_ROUTE, {})

        self.assertEqual(request.url, "https://www.reddit.com/r")

    def test_no_route_in_this_package_reaches_reddits_json_surface(self):
        # The measurement that decided this: `.json` on `www.`, `old.` and
        # `api.` all answered 403, to a curl UA, a custom app UA and a browser
        # UA alike. A fallback to any of them would be a route this package
        # knows is blocked, dressed as a second chance.
        # Reddit's own hosts, by host rather than by substring: the `K3`
        # archive lives at `arctic-shift.photon-reddit.com`, which is somebody
        # else's machine with Reddit's name in it, and the whole point of that
        # route is that it is not Reddit answering.
        reddit_routes = {
            route_id: route
            for route_id, route in transport.ROUTE_CONSTANTS.items()
            if urllib.parse.urlsplit(route.origin).netloc.endswith(".reddit.com")
        }

        # Five routes on Reddit's own host since 2026-08-17: the RSS feed, and
        # the four `/svc/shreddit/` HTML partials Reddit's own web client loads
        # — measured 200 to the package identity that day, on a bucket of two
        # hundred reads per window. Not one of them names `.json`. The
        # `more-comments` continuation is a sixth partial and is deliberately
        # not declared: it asks for a POST, which this package admits on two
        # named routes and nowhere else.
        self.assertEqual(
            sorted(reddit_routes),
            sorted([
                transport.REDDIT_FEED_ROUTE,
                transport.REDDIT_SHREDDIT_COMMENTS_ROUTE,
                transport.REDDIT_SHREDDIT_LISTING_ROUTE,
                transport.REDDIT_SHREDDIT_SEARCH_ROUTE,
                transport.REDDIT_SHREDDIT_SUBREDDIT_SEARCH_ROUTE,
            ]),
        )
        self.assertEqual(reddit_routes[transport.REDDIT_FEED_ROUTE].path_suffix, ".rss")
        for route_id, route in sorted(reddit_routes.items()):
            with self.subTest(route=route_id):
                self.assertNotIn(".json", route.path)
                self.assertNotIn(".json", route.path_suffix)
                if route_id != transport.REDDIT_FEED_ROUTE:
                    self.assertTrue(route.path.startswith("/svc/shreddit/"), route.path)

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

    def test_the_two_selected_documents_are_the_ones_the_control_probes_measured(self):
        article = transport.build_transport_request(
            transport.PUBLIC_PAGE_ARTICLE_ROUTE, {"title": ARTICLE_TITLE}
        )
        control = transport.build_transport_request(transport.PUBLIC_PAGE_CONTROL_ROUTE, {})

        self.assertEqual(
            article.url, "https://en.wikipedia.org/wiki/" + ARTICLE_TITLE
        )
        # The control takes no argument at all: it is one document, and its
        # whole job is that its answer is known before it is asked.
        self.assertEqual(control.url, "https://example.com/")
        self.assertEqual(
            transport.route_constant(transport.PUBLIC_PAGE_CONTROL_ROUTE).path_params, ()
        )

    def test_no_string_a_caller_supplies_can_move_the_host_a_read_goes_to(self):
        # The transport half of row 2. A declared segment is percent-quoted
        # into the path, so a value shaped like an address becomes a nonsense
        # document name on the selected origin rather than a different origin.
        # The adapter refuses these outright and never gets here; this is the
        # floor under that, and it holds for every route in the table.
        for route_id in sorted(FEED_PAGE_ROUTES):
            route = transport.route_constant(route_id)
            if not route.path_params:
                continue
            expected = urllib.parse.urlsplit(route.origin).netloc
            for value in ADDRESS_SHAPED_VALUES:
                with self.subTest(route=route_id, value=value):
                    request = transport.build_transport_request(
                        route_id, {route.path_params[0]: value}
                    )

                    self.assertEqual(
                        urllib.parse.urlsplit(request.url).netloc, expected
                    )

    def test_all_four_are_documented_keyless_and_need_no_credential_of_any_kind(self):
        admissions = transport.route_admissions()

        for route_id in sorted(self._routes()):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertEqual(route.access_class, "K0")
                self.assertEqual(route.credential_id, "")
                self.assertIsNone(transport.route_credential(route_id))
                self.assertEqual(route.token_route_id, "")
                self.assertTrue(admissions[route_id])

    def test_every_one_of_them_names_the_party_that_answers_it(self):
        for route_id in sorted(self._routes()):
            with self.subTest(route=route_id):
                self.assertNotEqual(
                    transport.route_constant(route_id).operator_identity, ""
                )

    def test_none_of_the_four_is_inside_the_verb_gates_one_widening(self):
        widened = transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES

        for route_id in sorted(self._routes()):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertNotIn(route_id, widened)
                self.assertIn(route.method, transport.READ_METHODS)
                self.assertEqual(
                    transport.admitted_methods(route_id), transport.READ_METHODS
                )

    def test_no_request_any_of_them_builds_can_carry_a_body(self):
        for route_id in sorted(self._routes()):
            with self.subTest(route=route_id):
                self.assertEqual(transport.route_constant(route_id).body_params, ())
                request = transport.build_transport_request(
                    route_id, {"query": "x", "body": "y", "data": "z"}
                )

                self.assertEqual(request.body, "")

    def test_every_verb_that_is_not_a_read_is_refused_on_all_four(self):
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
                            transport.urlopen_response(request)

                    self.assertIn("write-capable method", str(caught.exception))
