from tests.test_adapters_cases.linkedin_ttl_and_artifact import *  # noqa: F401,F403

YOUTUBE_FIXTURE_DIR = TEST_DIR / "fixtures" / "youtube"
INSTAGRAM_FIXTURE_DIR = TEST_DIR / "fixtures" / "instagram"

# The client this package presents to InnerTube, and the endpoint each of the
# three roster operations is spelled by. Named here so the route checks read
# against the roster row rather than against the adapter's own constants.
INNERTUBE_CLIENT = ("WEB", "2.20260808.00.00")
INNERTUBE_ENDPOINTS = ("search", "next", "player")


class YoutubeInstagramRouteConstantTest(unittest.TestCase):
    """Both routes name a surface the evidence measured, owned by transport.

    One of them is the first read in this package spelled ``POST``. InnerTube
    takes its query as a JSON body and has no GET form, so a route that could
    only be a read on the wire could not be this route at all. The widening is
    the guest activation's shape exactly — a second closed exception, named by
    route id, for an operation that creates nothing at the origin — and the
    checks below are the ones that keep it closed.
    """

    def _routes(self):
        return (transport.YOUTUBE_INNERTUBE_ROUTE, transport.INSTAGRAM_WEB_PROFILE_ROUTE)

    def test_the_innertube_route_spends_its_endpoint_as_a_path_segment(self):
        client_name, client_version = INNERTUBE_CLIENT
        request = transport.build_transport_request(
            transport.YOUTUBE_INNERTUBE_ROUTE,
            {
                "endpoint": "search",
                "client_name": client_name,
                "client_version": client_version,
                "query": "local models",
            },
        )

        # The 2026-08-10 probes (YouTube): `youtubei/v1/search` with the public web key
        # answered 200 with 2.27 MB of keyless search. The endpoint is a path
        # segment, so one route serves all three operations and only the
        # segment's value comes from the caller.
        self.assertEqual(request.url, "https://www.youtube.com/youtubei/v1/search")
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            json.loads(request.body),
            {
                "context": {
                    "client": {"clientName": client_name, "clientVersion": client_version}
                },
                "query": "local models",
            },
        )

    def test_each_innertube_endpoint_is_the_same_route_at_a_different_segment(self):
        for endpoint in INNERTUBE_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                request = transport.build_transport_request(
                    transport.YOUTUBE_INNERTUBE_ROUTE, {"endpoint": endpoint}
                )

                self.assertTrue(request.url.endswith("/youtubei/v1/" + endpoint), request.url)

    def test_the_instagram_route_asks_by_username_and_carries_no_body(self):
        request = transport.build_transport_request(
            transport.INSTAGRAM_WEB_PROFILE_ROUTE, {"username": "nasa"}
        )

        # The 2026-08-10 probes (Instagram): `api/v1/users/web_profile_info/?username=`
        # under `x-ig-app-id` answered 200 with 455 KB of profile and 12 posts.
        self.assertEqual(
            request.url,
            "https://www.instagram.com/api/v1/users/web_profile_info/?username=nasa",
        )
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.body, "")

    def test_both_routes_are_keyless_and_neither_needs_a_user_credential(self):
        for route_id in self._routes():
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertTrue(transport.route_admissions()[route_id])
                self.assertEqual(route.access_class, "K1")

    def test_each_route_names_the_vendor_published_credential_the_evidence_records(self):
        self.assertIs(
            transport.route_credential(transport.YOUTUBE_INNERTUBE_ROUTE),
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.YOUTUBE_INNERTUBE_WEB_KEY],
        )
        self.assertIs(
            transport.route_credential(transport.INSTAGRAM_WEB_PROFILE_ROUTE),
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.INSTAGRAM_WEB_APP_ID],
        )

    def test_neither_credential_rides_on_a_request_the_run_holds(self):
        # A K1 credential is attached at send time and nowhere earlier, which
        # is what keeps it out of every manifest and artifact: everything above
        # the transport seam sees only these two values.
        for route_id in self._routes():
            with self.subTest(route=route_id):
                request = transport.build_transport_request(route_id, {"endpoint": "player"})
                credential = transport.route_credential(route_id)

                self.assertNotIn(credential.value, repr(request))

    def test_only_the_two_declared_exceptions_may_use_a_method_that_is_not_a_read(self):
        # The verb gate, from both sides. A JSON-body read is admitted on the
        # one route that has no other form, and the set of routes that may
        # leave a read is exactly the two this module declares.
        declared = sorted(transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES)
        non_read = sorted(
            route_id
            for route_id, route in transport.ROUTE_CONSTANTS.items()
            if route.method not in transport.READ_METHODS
        )

        self.assertEqual(non_read, declared)
        self.assertEqual(
            declared,
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.YOUTUBE_INNERTUBE_ROUTE],
        )
        self.assertEqual(
            transport.admitted_methods(transport.YOUTUBE_INNERTUBE_ROUTE),
            transport.READ_METHODS + ("POST",),
        )
        self.assertEqual(
            transport.admitted_methods(transport.INSTAGRAM_WEB_PROFILE_ROUTE),
            transport.READ_METHODS,
        )

    def test_no_route_admits_a_verb_that_can_mutate_a_remote_resource(self):
        # The widening admits one more read, spelled POST. It admits nothing
        # that could change anything at an origin, on any route.
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            with self.subTest(route=route_id):
                admitted = transport.admitted_methods(route_id)

                for method in ("PUT", "DELETE", "PATCH", "OPTIONS"):
                    self.assertNotIn(method, admitted)

    def test_post_cannot_be_reached_on_a_route_this_module_did_not_name(self):
        # The other direction of the same gate, at the opener rather than at
        # the table: a route outside both declared sets is refused a POST
        # before any socket, however the request was built.
        declared = transport.TOKEN_ACTIVATION_ROUTES + transport.QUERY_BODY_ROUTES

        for route_id in sorted(transport.ROUTE_CONSTANTS):
            if route_id in declared:
                continue
            with self.subTest(route=route_id):
                request = transport.TransportRequest(
                    route_id=route_id, method="POST", url="https://example.test/probe"
                )

                with helpers.forbid_io():
                    with self.assertRaises(transport.TransportError) as caught:
                        transport.urlopen_response(request)

                self.assertIn("refusing a write-capable method", str(caught.exception))

    def test_a_caller_cannot_put_in_the_body_anything_the_route_did_not_declare(self):
        # The body is the endpoint's shape with the caller's values in it, the
        # same division `path_params` makes for a path segment. A caller that
        # could choose the body outright would hold the generic HTTP primitive
        # the spec's non-goals forbid, on the one route that has a body at all.
        request = transport.build_transport_request(
            transport.YOUTUBE_INNERTUBE_ROUTE,
            {
                "endpoint": "search",
                "query": "local models",
                "context": "mine",
                "trackingParams": "AAA",
            },
        )

        self.assertEqual(json.loads(request.body), {"query": "local models"})
        # What the route never declared went where every undeclared parameter
        # goes: the query string, in the open, on a url this run records.
        self.assertIn("context=mine", request.url)
        self.assertIn("trackingParams=AAA", request.url)

    def test_a_route_declaring_no_body_param_carries_no_body_whatever_it_is_handed(self):
        for route_id in sorted(transport.ROUTE_CONSTANTS):
            if transport.route_constant(route_id).body_params:
                continue
            with self.subTest(route=route_id):
                request = transport.build_transport_request(
                    route_id,
                    dict(
                        helpers.probe_params(route_id),
                        **{"query": "x", "video_id": "y", "context": "z"}
                    ),
                )

                self.assertEqual(request.body, "")

    def test_the_body_reaches_the_wire_with_the_key_on_the_url_beside_it(self):
        recorder = RoutingUrlopen([])
        client_name, client_version = INNERTUBE_CLIENT
        request = transport.build_transport_request(
            transport.YOUTUBE_INNERTUBE_ROUTE,
            {
                "endpoint": "player",
                "client_name": client_name,
                "client_version": client_version,
                "video_id": "dQw4w9WgXcQ",
            },
        )

        with mock.patch.object(urllib.request, "urlopen", recorder):
            transport.urlopen_response(request)

        outbound = recorder.requests[0]
        key = transport.PUBLIC_CLIENT_CREDENTIALS[transport.YOUTUBE_INNERTUBE_WEB_KEY]
        self.assertEqual(outbound.get_method(), "POST")
        self.assertEqual(
            json.loads(outbound.data.decode("utf-8"))["videoId"], "dQw4w9WgXcQ"
        )
        self.assertIn("key=" + key.value, outbound.full_url)
        self.assertEqual(recorder.headers_of(0)["content-type"], "application/json")

    def test_the_app_id_rides_the_headers_and_never_the_url(self):
        recorder = RoutingUrlopen([])
        request = transport.build_transport_request(
            transport.INSTAGRAM_WEB_PROFILE_ROUTE, {"username": "nasa"}
        )

        with mock.patch.object(urllib.request, "urlopen", recorder):
            transport.urlopen_response(request)

        outbound = recorder.requests[0]
        app_id = transport.PUBLIC_CLIENT_CREDENTIALS[transport.INSTAGRAM_WEB_APP_ID]
        self.assertEqual(recorder.headers_of(0)["x-ig-app-id"], app_id.value)
        self.assertNotIn(app_id.value, outbound.full_url)
        self.assertIsNone(outbound.data)

    def test_an_address_the_origin_published_is_resolved_where_hosts_are_spelled(self):
        # Both platforms publish an item's address relative to themselves, or
        # not at all — a `/watch?v=` path, a bare shortcode. An adapter may not
        # name a route host, so the resolution happens here or the record
        # carries no address at all.
        self.assertEqual(
            transport.origin_locator(transport.YOUTUBE_INNERTUBE_ROUTE, "/watch?v=dQw4w9WgXcQ"),
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        self.assertEqual(
            transport.origin_locator(transport.INSTAGRAM_WEB_PROFILE_ROUTE, "/p/CxYzAbCdEfG/"),
            "https://www.instagram.com/p/CxYzAbCdEfG/",
        )

    def test_an_address_already_absolute_is_handed_back_unchanged(self):
        # The player payload publishes one. Resolving an address somebody else
        # already resolved would be this package rewriting what it was told.
        published = "https://www.youtube.com/embed/dQw4w9WgXcQ"

        self.assertEqual(
            transport.origin_locator(transport.YOUTUBE_INNERTUBE_ROUTE, published), published
        )
        self.assertEqual(transport.origin_locator(transport.YOUTUBE_INNERTUBE_ROUTE, ""), "")


INSTAGRAM_USERNAME = "harbourlight.optics"
INSTAGRAM_REQUEST = adapters.AdapterRequest(step_id="s1-ig", target_ids=(INSTAGRAM_USERNAME,))

# The 2026-08-10 probes (Instagram): every field the roster row records this route
# returning, for the profile and for each of the 12 recent posts, named as the
# evidence names them rather than as a record spells them.
INSTAGRAM_PROFILE_ROSTER_FIELDS = ("username", "biography", "followers", "post_count")
INSTAGRAM_POST_ROSTER_FIELDS = (
    "shortcode",
    "taken_at_timestamp",
    "like_count",
    "comment_count",
)


def read_instagram(name):
    """Read one offline Instagram fixture."""

    return INSTAGRAM_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def instagram_cases():
    """The measured case table: a status, a body, and the loss its evidence names."""

    return tuple(json.loads(read_instagram("profile_cases.json"))["cases"])


def counts_of(record):
    """One record's metrics by name, on whichever side of normalize it sits.

    A native record carries pairs and an artifact record carries snapshots. The
    roster row is the same row either way, and reading it at both ends is how
    "the route reaches its capability" stops being a claim about an
    intermediate value.
    """

    named = {}
    for metric in record.engagement:
        if isinstance(metric, schema.EngagementSnapshot):
            named[metric.metric_name] = metric.value
        else:
            named[metric[0]] = metric[1]
    return named


def instagram_profile_row(record):
    """One profile's roster row exactly as a caller reads it off the record."""

    counts = counts_of(record)
    return {
        "username": record.author,
        "biography": record.body,
        "followers": counts.get(instagram_public.FOLLOWERS_METRIC, 0),
        "post_count": counts.get(instagram_public.POST_COUNT_METRIC, 0),
    }


def instagram_post_row(record):
    """One post's roster row exactly as a caller reads it off the record."""

    counts = counts_of(record)
    return {
        "shortcode": record.native_item_id,
        "taken_at_timestamp": record.published_at,
        "like_count": counts.get(instagram_public.LIKE_METRIC, 0),
        "comment_count": counts.get(instagram_public.COMMENT_METRIC, 0),
    }


def instagram_page(fixture, status=200, request=None):
    """Run ``instagram_public`` over one canned answer."""

    return adapter_page(
        instagram_public,
        status,
        read_instagram(fixture),
        content_type="application/json",
        request=INSTAGRAM_REQUEST if request is None else request,
    )


def instagram_posts(page):
    return [record for record in page.records if record.canonical_content_kind == "post"]


class InstagramProfileTest(unittest.TestCase):
    """Criterion 1, Instagram half: a profile and its twelve posts, keyless.

    The prior synthesis listed Instagram as a flat gap. Measured, one request
    under a vendor-published app id returns the bio, the follower count, and
    twelve recent posts each carrying the platform's own engagement and its own
    timestamp — which is the whole roster row, at zero cost and with no account.
    """

    def setUp(self):
        self.page, self.opener = instagram_page("web_profile_info.json")

    def test_one_page_carries_the_profile_and_the_twelve_posts_measured(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(len(self.page.records), 13)
        self.assertEqual(len(instagram_posts(self.page)), 12)
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_profile_record_carries_every_field_its_roster_row_names(self):
        carried = instagram_profile_row(self.page.records[0])

        self.assertEqual(sorted(carried), sorted(INSTAGRAM_PROFILE_ROSTER_FIELDS))
        for name in INSTAGRAM_PROFILE_ROSTER_FIELDS:
            self.assertTrue(carried[name], name)
        self.assertEqual(carried["username"], INSTAGRAM_USERNAME)
        self.assertIn("north Atlantic", carried["biography"])
        self.assertEqual(carried["followers"], 104262608)
        self.assertEqual(carried["post_count"], 4231)

    def test_every_post_carries_every_field_its_roster_row_names(self):
        for record in instagram_posts(self.page):
            with self.subTest(item=record.native_item_id):
                carried = instagram_post_row(record)

                self.assertEqual(sorted(carried), sorted(INSTAGRAM_POST_ROSTER_FIELDS))
                for name in INSTAGRAM_POST_ROSTER_FIELDS:
                    self.assertTrue(carried[name], name)
                for name in ("like_count", "comment_count"):
                    self.assertIsInstance(carried[name], int)
                self.assertEqual(record.loss, ())

    def test_a_post_names_itself_its_author_and_the_moment_the_platform_reported(self):
        first = instagram_posts(self.page)[0]

        self.assertEqual(first.canonical_content_kind, "post")
        # The shortcode is what Instagram addresses a post by, so it is the
        # record's own id and the address is built from it where hosts are
        # spelled — the payload publishes no address of its own.
        self.assertEqual(first.native_item_id, "C9xR2mQLpQz")
        self.assertEqual(
            first.canonical_locator, "https://www.instagram.com/p/C9xR2mQLpQz/"
        )
        self.assertEqual(first.native_parent_id, "528817151")
        self.assertEqual(first.author, INSTAGRAM_USERNAME)
        self.assertIn("blue hour", first.body)
        self.assertEqual(first.published_at, "2026-08-09T18:20:00Z")
        self.assertEqual(first.native_position, 0)
        self.assertEqual(
            counts_of(first),
            {
                instagram_public.LIKE_METRIC: 412873,
                instagram_public.COMMENT_METRIC: 1904,
            },
        )

    def test_the_profile_record_names_the_account_and_its_published_address(self):
        profile = self.page.records[0]

        self.assertEqual(profile.canonical_content_kind, "profile")
        self.assertEqual(profile.native_item_id, "528817151")
        self.assertEqual(profile.title, "Harbourlight Optics")
        self.assertEqual(
            profile.canonical_locator, "https://www.instagram.com/harbourlight.optics/"
        )
        # A profile states no publication time, so the record states none
        # rather than borrowing the moment it was read.
        self.assertEqual(profile.published_at, "")

    def test_the_posts_arrive_in_the_order_the_payload_listed_them(self):
        posts = instagram_posts(self.page)

        self.assertEqual([record.native_position for record in posts], list(range(12)))
        self.assertEqual(
            [record.published_at for record in posts[:3]],
            ["2026-08-09T18:20:00Z", "2026-08-08T15:05:00Z", "2026-08-07T12:00:00Z"],
        )

    def test_a_post_the_payload_left_incomplete_is_marked_and_never_zero_filled(self):
        page, _ = instagram_page(
            "web_profile_info_partial_post.json",
            request=adapters.AdapterRequest(
                step_id="s1-ig", target_ids=("kestrel.field.notes",)
            ),
        )
        complete, partial, quiet = instagram_posts(page)

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(complete.loss, ())
        self.assertEqual(partial.loss, ("field_omitted",))
        # Absent, not invented: no comment count at all and no time, instead of
        # a zero that reads as "nobody commented" and a moment nobody observed.
        self.assertNotIn(instagram_public.COMMENT_METRIC, counts_of(partial))
        self.assertEqual(partial.published_at, "")
        self.assertEqual(counts_of(partial)[instagram_public.LIKE_METRIC], 611)
        # And the other direction, which is the whole reason the mark exists:
        # a post nobody has liked or commented on reported both counts, and
        # both are zero. A row marked omitted for that would say the payload
        # was short when the payload was complete.
        self.assertEqual(quiet.loss, ())
        self.assertEqual(
            counts_of(quiet),
            {instagram_public.LIKE_METRIC: 0, instagram_public.COMMENT_METRIC: 0},
        )

    def test_the_metric_names_are_the_ones_the_payload_publishes_them_under(self):
        # A metric name is never inferred and never translated. Instagram
        # reports these three at these exact key paths; spelling them
        # `like_count` and `comment_count` would be this package inventing a
        # cross-platform vocabulary the spec's non-goals forbid.
        self.assertEqual(instagram_public.LIKE_METRIC, "edge_liked_by.count")
        self.assertEqual(instagram_public.COMMENT_METRIC, "edge_media_to_comment.count")
        self.assertEqual(instagram_public.FOLLOWERS_METRIC, "edge_followed_by.count")
        self.assertEqual(
            instagram_public.POST_COUNT_METRIC, "edge_owner_to_timeline_media.count"
        )

    def test_the_page_speaks_for_instagram_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "instagram_public")
        self.assertEqual(self.page.platform, "instagram")
        self.assertEqual(self.page.native_identity_namespace, "instagram")
        self.assertEqual(self.page.access_class, "K1")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.INSTAGRAM_WEB_PROFILE_ROUTE)

    def test_the_username_is_read_from_the_target_or_from_the_query(self):
        for request in (
            adapters.AdapterRequest(step_id="s1-ig", target_ids=(INSTAGRAM_USERNAME,)),
            adapters.AdapterRequest(step_id="s1-ig", query="@" + INSTAGRAM_USERNAME),
        ):
            with self.subTest(request=request):
                _, opener = instagram_page("web_profile_info.json", request=request)

                self.assertTrue(
                    opener.opened[0].url.endswith("username=harbourlight.optics"),
                    opener.opened[0].url,
                )


