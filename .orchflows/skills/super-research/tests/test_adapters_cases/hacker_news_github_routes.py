from tests.test_adapters_cases.youtube_ttl_and_artifact import *  # noqa: F401,F403

HN_ALGOLIA_ENDPOINTS = ("search", "search_by_date")
HN_COMMENT_TAG = "comment"
HN_STORY_ID = "44831234"
GITHUB_OWNER = "harbourlight"
GITHUB_REPO = "gpu-bench"
GITHUB_RESOURCES = ("issues", "releases")
GITHUB_SEARCH_INDEX = "repositories"

NEW_ROUTES = (
    "hn_algolia_search",
    "hn_firebase_item",
    "github_rest",
    "github_search",
)


class HackerNewsGithubRouteConstantTest(unittest.TestCase):
    """Four routes over three origins, every one of them a plain keyless read.

    Two adapters, four surfaces: HN publishes its search through Algolia and its
    item tree through Firebase, and GitHub spends its anonymous hour as two
    buckets — `core` and `code_search` — which `api.github.com/rate_limit`
    reported separately. Each bucket is a route because each is paced on its
    own, and `/repos/<owner>/<repo>` and `/search/<index>` do not share a path
    shape besides.

    The sharpest claim in this file is here rather than in an adapter: GitHub is
    the one origin in the roster with a large, well-known write surface, and
    nothing about that surface is reachable from this package. T07 widened the
    verb gate by one closed set for a route that has no GET form; all four of
    these are outside that widening, declare no body, and are refused every
    verb that is not a read.
    """

    def _routes(self):
        return NEW_ROUTES

    def test_the_algolia_route_spends_its_endpoint_as_a_path_segment(self):
        request = transport.build_transport_request(
            transport.HN_ALGOLIA_SEARCH_ROUTE,
            {"endpoint": "search_by_date", "query": "local models"},
        )

        # The 2026-08-10 probes, carry-over: `hn.algolia.com/api/v1/search_by_date`
        # answered 200 with full-text HN search — the capability the prior
        # spec's Firebase-only adapter did not have at all.
        self.assertEqual(
            request.url, "https://hn.algolia.com/api/v1/search_by_date?query=local+models"
        )
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.body, "")

    def test_each_algolia_endpoint_is_the_same_route_at_a_different_segment(self):
        for endpoint in HN_ALGOLIA_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                request = transport.build_transport_request(
                    transport.HN_ALGOLIA_SEARCH_ROUTE, {"endpoint": endpoint}
                )

                self.assertTrue(request.url.endswith("/api/v1/" + endpoint), request.url)

    def test_comment_search_is_that_endpoint_under_the_tag_the_evidence_measured(self):
        request = transport.build_transport_request(
            transport.HN_ALGOLIA_SEARCH_ROUTE,
            {"endpoint": "search", "query": "cuda", "tags": HN_COMMENT_TAG},
        )

        # The 2026-08-10 probes, carry-over: `hn.algolia.com/api/v1/search?tags=comment`
        # answered 200 for comment search.
        self.assertEqual(
            request.url, "https://hn.algolia.com/api/v1/search?query=cuda&tags=comment"
        )

    def test_the_firebase_route_names_an_item_and_spells_its_own_json_suffix(self):
        request = transport.build_transport_request(
            transport.HN_FIREBASE_ITEM_ROUTE, {"item_id": HN_STORY_ID}
        )

        # The 2026-08-10 probes, carry-over: `hacker-news.firebaseio.com/v0/item/<id>`
        # answered 200 with `by`, `descendants` and the `kids` tree. Firebase
        # spells a resource's representation as a path suffix rather than as an
        # Accept header, so the suffix is part of the endpoint's shape and is
        # owned here — an adapter that composed it would own the endpoint.
        self.assertEqual(
            request.url,
            "https://hacker-news.firebaseio.com/v0/item/" + HN_STORY_ID + ".json",
        )
        self.assertEqual(request.method, "GET")

    def test_a_request_naming_no_item_takes_neither_the_segment_nor_the_suffix(self):
        # A half-filled path must not become a different endpoint: `/v0/item`
        # with no id is not `/v0/item.json`, which is a resource of its own.
        request = transport.build_transport_request(transport.HN_FIREBASE_ITEM_ROUTE, {})

        self.assertEqual(request.url, "https://hacker-news.firebaseio.com/v0/item")

    def test_a_caller_cannot_choose_the_suffix_any_more_than_it_can_the_path(self):
        request = transport.build_transport_request(
            transport.HN_FIREBASE_ITEM_ROUTE, {"item_id": HN_STORY_ID, "path_suffix": ".xml"}
        )

        self.assertEqual(
            urllib.parse.urlsplit(request.url).path, "/v0/item/" + HN_STORY_ID + ".json"
        )
        # What the route never declared went where every undeclared parameter
        # goes: the query string, in the open, on a url this run records.
        self.assertIn("path_suffix=.xml", urllib.parse.unquote(request.url))

    def test_the_repo_route_spends_an_owner_a_repo_and_an_optional_resource(self):
        bare = transport.build_transport_request(
            transport.GITHUB_REST_ROUTE, {"owner": GITHUB_OWNER, "repo": GITHUB_REPO}
        )

        # The 2026-08-10 probes, carry-over: `api.github.com` answered anonymously.
        self.assertEqual(
            bare.url, "https://api.github.com/repos/" + GITHUB_OWNER + "/" + GITHUB_REPO
        )
        for resource in GITHUB_RESOURCES:
            with self.subTest(resource=resource):
                request = transport.build_transport_request(
                    transport.GITHUB_REST_ROUTE,
                    {"owner": GITHUB_OWNER, "repo": GITHUB_REPO, "resource": resource},
                )

                self.assertEqual(request.url, bare.url + "/" + resource)

    def test_the_search_route_asks_one_index_one_question(self):
        request = transport.build_transport_request(
            transport.GITHUB_SEARCH_ROUTE, {"index": GITHUB_SEARCH_INDEX, "q": "llama.cpp"}
        )

        # The 2026-08-10 probes, carry-over: `api.github.com/search/repositories`
        # answered 200 anonymously.
        self.assertEqual(
            request.url, "https://api.github.com/search/repositories?q=llama.cpp"
        )

    def test_all_four_are_documented_keyless_and_need_no_credential_of_any_kind(self):
        # protocol.md's access ladder places "HN Algolia + Firebase, GitHub
        # anon" in `K0`,
        # the documented-keyless class, and the spec's roster row repeats it.
        for route_id in self._routes():
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertEqual(route.access_class, "K0")
                self.assertTrue(transport.route_admissions()[route_id])
                self.assertIsNone(transport.route_credential(route_id))
                self.assertEqual(route.credential_id, "")

    def test_every_one_of_them_names_the_party_that_answers_it(self):
        # HN's own search is operated by Algolia and published by HN: the
        # platform's index of itself rather than an independent mirror of it,
        # which is why the evidence classes it `K0` and not `K3` and why no
        # record from it carries `third_party_archive`.
        self.assertEqual(
            [transport.route_constant(route_id).operator_identity for route_id in NEW_ROUTES],
            ["algolia", "hacker-news", "github", "github"],
        )

    def test_none_of_the_four_is_inside_the_verb_gates_one_widening(self):
        # T07 widened the gate by one closed set, for a route with no GET form.
        # These four are ordinary reads and stay entirely outside it.
        for route_id in self._routes():
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertIn(route.method, transport.READ_METHODS)
                self.assertNotIn(route_id, transport.TOKEN_ACTIVATION_ROUTES)
                self.assertNotIn(route_id, transport.QUERY_BODY_ROUTES)
                self.assertEqual(
                    transport.admitted_methods(route_id), transport.READ_METHODS
                )
                self.assertEqual(route.body_params, ())

    def test_no_request_any_of_them_builds_can_carry_a_body(self):
        # The body is how the one widened route asks its question. A caller
        # handing these the same parameters gets them in the open, on the url.
        for route_id in self._routes():
            with self.subTest(route=route_id):
                request = transport.build_transport_request(
                    route_id, {"query": "x", "context": "mine", "title": "new issue"}
                )

                self.assertEqual(request.body, "")

    def test_every_verb_that_is_not_a_read_is_refused_on_all_four(self):
        # GitHub is the one origin in the roster whose API has a large write
        # surface. None of it is reachable: the refusal happens in the opener,
        # before any socket, however the request was built.
        for route_id in self._routes():
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                with self.subTest(route=route_id, method=method):
                    request = transport.TransportRequest(
                        route_id=route_id, method=method, url="https://example.test/probe"
                    )

                    with helpers.forbid_io():
                        with self.assertRaises(transport.TransportError) as caught:
                            transport.urlopen_response(request)

                    self.assertIn("refusing a write-capable method", str(caught.exception))

    def test_an_hn_item_address_belongs_to_neither_of_its_routes_origins(self):
        # Why `hacker_news` composes an item's address instead of resolving it:
        # `origin_locator` resolves against the route's own origin, and an HN
        # item lives on HN's site, which is neither of these. Resolving one
        # here would state a confident wrong address.
        for route_id in ("hn_algolia_search", "hn_firebase_item"):
            with self.subTest(route=route_id):
                resolved = transport.origin_locator(route_id, "/item?id=" + HN_STORY_ID)

                self.assertNotIn("news.ycombinator.com", resolved)


