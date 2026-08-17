"""Two social adapters, offline: Bluesky's AppView and X through FxTwitter.

Both read a public JSON surface and both have a way of failing that looks
exactly like having nothing to say, so most of this suite exists to keep those
apart.

The claim the Bluesky half defends is that a refusal about *who is asking* is
never an empty search. On this host, on 2026-08-17, ``searchPosts`` answered
403 with an HTML page from the CDN in front of the AppView while
``getAuthorFeed`` answered 200 on the same origin in the same minute. An
adapter that read that 403 as "no posts matched" would report a live platform
as silent, on a method that is documented keyless; one that read the *body*
rather than the status line would type an ordinary 400 the same way, because
both bodies say something about not being served. So the status line decides
and the body only speaks: the same bytes at 403 and at 400 are two different
answers, and that pair is asserted directly.

The claim the FxTwitter half defends is that a record which travelled through
an independent operator says so *on the record*. `third_party_archive` is the
descriptor's standing loss and it is asserted on every record of every page
this suite produces, not on the page — a caller holding one row cannot
correlate it back to a page to learn where it came from. Beside it sits this
origin's own oddity: it states a ``code`` inside a body it has already
answered 200 to, and a 404 there is an absence while anything else there is
the status the read got, one layer in. Neither is `schema_drift`, because the
envelope is exactly the shape this module declares and is being read
correctly.

Three smaller claims hold both halves up. Counts are the origin's own exact
integers under the origin's own names, so a ``null`` view count is absent
rather than zero and a ``bookmarkCount`` the module does not declare is
carried nowhere. A caller's window reaches Bluesky's search in that method's
own terms — ``since`` and ``until`` on the built address — and reaches the
author feed not at all, because that method takes no bound on time. And a
conversation's root is read once: the payload puts the root at the head of
its own ``thread`` as well as under ``status``, and an adapter reading both
would emit one status twice under one id.

Every test here runs offline against fixtures under ``fixtures/bluesky/`` and
``fixtures/x_fxtwitter/``, captured live from both origins on 2026-08-17.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from super_research import adapters, transport
from super_research.adapters import bluesky, x_fxtwitter
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
BLUESKY_DIR = FIXTURE_DIR / "bluesky"
FXTWITTER_DIR = FIXTURE_DIR / "x_fxtwitter"

SEARCH_ROUTE = transport.BLUESKY_SEARCH_POSTS_ROUTE
AUTHOR_ROUTE = transport.BLUESKY_AUTHOR_FEED_ROUTE
FXTWITTER_ROUTE = transport.FXTWITTER_API_ROUTE

JSON_TYPE = "application/json"
HTML_TYPE = "text/html"

# The two posts the search fixture carries, and the handle both are under.
BSKY_HANDLE = "bsky.app"
BSKY_ROOT_URI = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3msqpuobiwk2t"
BSKY_REPLY_URI = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3msqpusnigc2t"
BSKY_DID = "did:plc:z72i7hdynmk6r22z27h6tvur"
# The third row of the author feed is a repost: a post by somebody else that
# this actor passed on, so its author is the account that wrote it.
BSKY_REPOSTED_HANDLE = "buttondown.com"

# The statuses the X fixtures carry.
X_ROOT_ID = "2088841930813690331"
X_SELF_REPLY_ID = "2088847137115144643"
X_SEARCH_REPLY_ID = "2089361198391214168"
X_SEARCH_ROOT_ID = "2089361176186491316"
X_SEARCH_PARENT_ID = "2089083612171739470"
X_PROFILE_ID = "34743251"
X_HANDLE = "SpaceX"


def read_fixture(directory, name):
    return directory.joinpath(name).read_text(encoding="utf-8")


def payload_of(directory, name):
    return json.loads(read_fixture(directory, name))


def discovery(query, **bounds):
    return adapters.AdapterRequest(step_id="s1-social", query=query, **bounds)


def hydration(target, **bounds):
    return adapters.AdapterRequest(step_id="s1-social", target_ids=(target,), **bounds)


def answered(module, route_id, body, request, status=200, content_type=JSON_TYPE):
    """Run one adapter over one canned answer; return its page and the opener."""

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (status, body, content_type)}
    )
    return (module.fetch_native_page(carrier, request), opener)


def bluesky_page(name, request, route_id=SEARCH_ROUTE, status=200, content_type=JSON_TYPE):
    return answered(
        bluesky, route_id, read_fixture(BLUESKY_DIR, name), request, status, content_type
    )


def fxtwitter_page(name, request, status=200, content_type=JSON_TYPE):
    return answered(
        x_fxtwitter, FXTWITTER_ROUTE, read_fixture(FXTWITTER_DIR, name), request, status,
        content_type,
    )


def built_url(route_id, params):
    """The address the transport builds for these params — the one oracle for a url."""

    return transport.build_transport_request(route_id, params).url


def named(record):
    """One record's attributes as a mapping, for asserting one name at a time."""

    return dict(record.attributes)


class BlueskyDescriptorTest(unittest.TestCase):
    """What this adapter declares about itself, against the routes it declares it for."""

    def test_two_surfaces_are_declared_and_the_search_is_the_primary(self):
        self.assertEqual(
            bluesky.SURFACE_DESCRIPTORS, (bluesky.DESCRIPTOR, bluesky.AUTHOR_FEED_DESCRIPTOR)
        )
        self.assertEqual(bluesky.DESCRIPTOR.route_id, SEARCH_ROUTE)
        self.assertEqual(bluesky.AUTHOR_FEED_DESCRIPTOR.route_id, AUTHOR_ROUTE)

    def test_every_surface_speaks_for_bluesky_at_the_class_its_route_declares(self):
        for descriptor in bluesky.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.adapter_id, "bluesky")
                self.assertEqual(descriptor.platform, "bluesky")
                self.assertEqual(descriptor.native_identity_namespace, "bluesky")
                self.assertEqual(descriptor.representation_kind, "native")
                self.assertEqual(descriptor.operator_identity, "bluesky")
                self.assertEqual(descriptor.standing_loss, ())
                self.assertEqual(descriptor.min_interval_ms, 1000)
                self.assertEqual(descriptor.burst, 5)
                self.assertEqual(descriptor.page_size, 100)
                # The class is the route's, not this module's opinion of it.
                self.assertEqual(
                    descriptor.access_class,
                    transport.ROUTE_CONSTANTS[descriptor.route_id].access_class,
                )

    def test_the_one_counted_metric_is_the_appviews_own_name_for_replies(self):
        # A name aliased across platforms would be this package inventing a
        # vocabulary; `replyCount` is what the payload calls it.
        for descriptor in bluesky.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.reply_count_metric, "replyCount")
                self.assertEqual(descriptor.comment_count_metric, "")


class BlueskySearchTest(unittest.TestCase):
    """The search surface reading the shape the method documents and returns."""

    def setUp(self):
        self.page, self.opener = bluesky_page("search_posts.json", discovery("spacex"))

    def test_the_page_speaks_for_the_route_that_answered(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(self.page.route_id, SEARCH_ROUTE)
        self.assertEqual(self.page.access_class, "K0")
        self.assertEqual(self.page.native_order, "bluesky_search_latest_order")
        self.assertEqual(len(self.page.records), 2)

    def test_a_post_is_addressed_by_its_handle_and_its_record_key(self):
        first = self.page.records[0]

        self.assertEqual(first.canonical_content_kind, "post")
        # The identity is the `at://` URI; the address is composed from the
        # handle beside it and the URI's last segment, because the payload
        # publishes no web address at all.
        self.assertEqual(first.native_item_id, BSKY_ROOT_URI)
        self.assertEqual(
            first.canonical_locator,
            "https://bsky.app/profile/" + BSKY_HANDLE + "/post/3msqpuobiwk2t",
        )
        self.assertEqual(first.author, BSKY_HANDLE)
        self.assertEqual(first.published_at, "2026-08-10T18:23:59Z")
        self.assertEqual(first.native_position, 0)
        self.assertEqual(first.loss, ())
        self.assertTrue(first.body.startswith("v1.130 is live!"))

    def test_the_four_declared_counts_are_the_payloads_own_exact_integers(self):
        self.assertEqual(
            self.page.records[0].engagement,
            (
                ("likeCount", 9487),
                ("repostCount", 2388),
                ("replyCount", 494),
                ("quoteCount", 2368),
            ),
        )

    def test_a_count_this_module_does_not_declare_is_carried_nowhere(self):
        # The payload states `bookmarkCount: 600` on this row. It is not one of
        # the four declared metrics, so it is neither an engagement figure nor
        # an attribute: a name this module does not declare is a name it does
        # not carry.
        record = self.page.records[0]

        self.assertNotIn("bookmarkCount", dict(record.engagement))
        self.assertNotIn("bookmarkCount", named(record))

    def test_a_post_carries_the_appviews_own_named_facts(self):
        self.assertEqual(
            self.page.records[0].attributes,
            (
                ("did", BSKY_DID),
                ("cid", "bafyreia5giteuhei7im66w7yn3pldm7h7npkmuy73fvakrpsjsz5oejdgu"),
                ("indexedAt", "2026-08-10T18:24:05.869Z"),
            ),
        )

    def test_a_reply_names_the_post_it_answers_and_carries_its_root_apart(self):
        reply = self.page.records[1]

        self.assertEqual(reply.native_item_id, BSKY_REPLY_URI)
        self.assertEqual(reply.native_parent_id, BSKY_ROOT_URI)
        # The thread's root is a separate fact and never `native_parent_id`.
        self.assertEqual(named(reply)["root_uri"], BSKY_ROOT_URI)
        # And a reply never inherits the parent's counts.
        self.assertEqual(dict(reply.engagement)["likeCount"], 2378)

    def test_a_post_answering_nothing_names_no_parent_and_no_root(self):
        first = self.page.records[0]

        self.assertEqual(first.native_parent_id, "")
        self.assertNotIn("root_uri", named(first))

    def test_the_continuation_is_the_one_the_appview_published(self):
        self.assertEqual(
            self.page.cursor_out, payload_of(BLUESKY_DIR, "search_posts.json")["cursor"]
        )


class BlueskyAuthorFeedTest(unittest.TestCase):
    """One actor's feed: the same post view, wrapped one level deeper."""

    def setUp(self):
        self.page, self.opener = bluesky_page(
            "author_feed.json", discovery("author:" + BSKY_HANDLE), route_id=AUTHOR_ROUTE
        )

    def test_every_feed_entry_is_read_through_its_own_post(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.route_id, AUTHOR_ROUTE)
        self.assertEqual(self.page.native_order, "bluesky_author_feed_order")
        self.assertEqual(len(self.page.records), 3)
        self.assertEqual([record.native_position for record in self.page.records], [0, 1, 2])

    def test_a_reposted_row_is_authored_by_whoever_wrote_it(self):
        # A repost is somebody else's post carried in this actor's feed. Its
        # author is the account that wrote it, and its address is under that
        # account's handle — attributing it to the reposter would be this
        # module inventing an authorship the payload does not state.
        passed_on = self.page.records[2]

        self.assertEqual(passed_on.author, BSKY_REPOSTED_HANDLE)
        self.assertTrue(
            passed_on.canonical_locator.startswith(
                "https://bsky.app/profile/" + BSKY_REPOSTED_HANDLE + "/post/"
            ),
            passed_on.canonical_locator,
        )
        self.assertEqual(passed_on.published_at, "2026-08-01T20:08:00Z")
        self.assertEqual(dict(passed_on.engagement)["likeCount"], 574)

    def test_the_continuation_is_the_one_the_appview_published(self):
        self.assertEqual(
            self.page.cursor_out, payload_of(BLUESKY_DIR, "author_feed.json")["cursor"]
        )


class BlueskyAnswersWithNoPostsTest(unittest.TestCase):
    """The five ways these methods answer with no post, told apart.

    The one that matters is the 403. It is a refusal about who is asking,
    arriving from the party in front of the AppView, on a method the platform
    documents as keyless — and the 400 beside it, whose body also declines to
    serve, is an ordinary status. Only the status line may decide.
    """

    def test_an_empty_container_is_an_absence_and_says_so(self):
        for name, route_id, request, spoken in (
            ("search_posts_empty.json", SEARCH_ROUTE, discovery("nothing here"), "posts"),
            ("author_feed_empty.json", AUTHOR_ROUTE, discovery("author:nobody"), "feed"),
        ):
            with self.subTest(fixture=name):
                page, _ = bluesky_page(name, request, route_id=route_id)

                self.assertEqual(page.outcome, "empty")
                self.assertEqual(page.loss, ())
                self.assertEqual(page.records, ())
                self.assertIn(spoken, " ".join(page.warnings))

    def test_a_payload_whose_container_moved_is_drift_and_never_an_absence(self):
        for name, route_id, request in (
            ("search_posts_reshaped.json", SEARCH_ROUTE, discovery("spacex")),
            ("author_feed_reshaped.json", AUTHOR_ROUTE, discovery("author:" + BSKY_HANDLE)),
        ):
            with self.subTest(fixture=name):
                page, _ = bluesky_page(name, request, route_id=route_id)

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("schema_drift",))
                self.assertEqual(page.records, ())
                self.assertIn("changed shape", " ".join(page.warnings))

    def test_rows_that_name_no_post_are_drift_and_never_an_empty_feed(self):
        # The container is there and holds two entries, and neither of them
        # carries a post this adapter can identify. Reporting that as "this
        # actor has posted nothing" is the one thing a caller cannot tell from
        # a real absence.
        page, _ = bluesky_page(
            "author_feed_no_posts.json", discovery("author:" + BSKY_HANDLE), route_id=AUTHOR_ROUTE
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertIn("no uri on any of them", " ".join(page.warnings))

    def test_a_body_that_is_not_json_at_two_hundred_is_malformed_and_not_a_refusal(self):
        page, _ = answered(bluesky, SEARCH_ROUTE, "<html>not json", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("malformed_json",))
        self.assertNotIn(bluesky.AUTH_REQUIRED, page.loss)

    def test_the_cdns_own_refusal_is_typed_as_one_and_quoted(self):
        page, _ = bluesky_page(
            "forbidden_403.html", discovery("spacex"), status=403, content_type=HTML_TYPE
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("auth_required",))
        self.assertEqual(page.records, ())
        spoken = " ".join(page.warnings)
        self.assertIn("403", spoken)
        self.assertIn("who is asking", spoken)
        # The refusing party's own first readable sentence, so an operator
        # reads the CDN rather than this module's guess at it.
        self.assertIn("403 Forbidden", spoken)

    def test_the_same_body_at_two_statuses_is_two_different_answers(self):
        # The sharpest form of the rule. One body, twice: at 403 it is the
        # origin declining over who is asking, at 400 it is an ordinary status.
        # Nothing in the body moved, so nothing in the body decided.
        refused, _ = bluesky_page(
            "forbidden_403.html", discovery("spacex"), status=403, content_type=HTML_TYPE
        )
        ordinary, _ = bluesky_page(
            "forbidden_403.html", discovery("spacex"), status=400, content_type=HTML_TYPE
        )

        self.assertEqual(refused.loss, ("auth_required",))
        self.assertEqual(ordinary.loss, ("http_status",))

    def test_an_unauthorized_status_is_the_same_refusal_as_a_forbidden_one(self):
        page, _ = bluesky_page("forbidden_403.html", discovery("spacex"), status=401,
                              content_type=HTML_TYPE)

        self.assertEqual(page.loss, ("auth_required",))

    def test_an_appview_error_body_is_quoted_from_its_own_message(self):
        page, _ = bluesky_page(
            "profile_not_found_400.json",
            discovery("author:nobody"),
            route_id=AUTHOR_ROUTE,
            status=400,
        )

        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("Profile not found", " ".join(page.warnings))


class BlueskyGrammarTest(unittest.TestCase):
    """Which method a step reaches, and what a step that names none means."""

    def test_a_caller_names_the_operation_and_the_argument_survives_it(self):
        for named_step, expected in (
            ("search:spacex", (bluesky.SEARCH_OPERATION, "spacex")),
            ("author:" + BSKY_HANDLE, (bluesky.AUTHOR_OPERATION, BSKY_HANDLE)),
            # A decentralised identifier is full of colons and travels whole.
            ("author:" + BSKY_DID, (bluesky.AUTHOR_OPERATION, BSKY_DID)),
        ):
            with self.subTest(step=named_step):
                self.assertEqual(bluesky.operation_for(discovery(named_step)), expected)

    def test_absent_a_prefix_both_shapes_of_step_search(self):
        # An actor is a thing a caller names, never a thing inferred from the
        # characters in an argument.
        self.assertEqual(
            bluesky.operation_for(discovery("spacex")), (bluesky.SEARCH_OPERATION, "spacex")
        )
        self.assertEqual(
            bluesky.operation_for(hydration(BSKY_HANDLE)),
            (bluesky.SEARCH_OPERATION, BSKY_HANDLE),
        )

    def test_a_query_carrying_a_colon_this_module_does_not_name_stays_a_query(self):
        self.assertEqual(
            bluesky.operation_for(discovery("from:someone spacex")),
            (bluesky.SEARCH_OPERATION, "from:someone spacex"),
        )

    def test_a_search_asks_for_the_latest_and_states_the_page_it_wants(self):
        _, opener = bluesky_page("search_posts.json", discovery("spacex"))

        self.assertEqual(
            opener.opened[0].url,
            built_url(SEARCH_ROUTE, {"q": "spacex", "sort": "latest", "limit": "100"}),
        )

    def test_an_author_step_names_the_actor_and_no_sort_at_all(self):
        _, opener = bluesky_page(
            "author_feed.json", discovery("author:" + BSKY_DID), route_id=AUTHOR_ROUTE
        )

        self.assertEqual(
            opener.opened[0].url,
            built_url(AUTHOR_ROUTE, {"actor": BSKY_DID, "limit": "100"}),
        )

    def test_one_call_reads_one_page_and_nothing_else(self):
        _, opener = bluesky_page("search_posts.json", discovery("spacex"))

        self.assertEqual(len(opener.opened), 1)


class BlueskyWindowAndCursorTest(unittest.TestCase):
    """The step's bounds, in the method's own terms, and the page after this one."""

    def test_the_steps_window_reaches_the_search_as_since_and_until(self):
        _, opener = bluesky_page(
            "search_posts.json",
            discovery(
                "spacex",
                window_start="2026-08-01T00:00:00Z",
                window_end="2026-08-17T00:00:00Z",
            ),
        )

        self.assertEqual(
            opener.opened[0].url,
            built_url(
                SEARCH_ROUTE,
                {
                    "q": "spacex",
                    "sort": "latest",
                    "limit": "100",
                    "since": "2026-08-01T00:00:00Z",
                    "until": "2026-08-17T00:00:00Z",
                },
            ),
        )

    def test_a_half_open_window_sends_only_the_bound_it_has(self):
        _, opener = bluesky_page(
            "search_posts.json", discovery("spacex", window_start="2026-08-01T00:00:00Z")
        )

        self.assertIn("since=2026-08-01T00%3A00%3A00Z", opener.opened[0].url)
        self.assertNotIn("until", opener.opened[0].url)

    def test_the_author_feed_takes_no_bound_on_time_and_is_sent_none(self):
        # The method publishes no term for one, so the core's own filter is the
        # whole window there. Sending a parameter the method does not declare
        # would be this module inventing the origin's vocabulary.
        _, opener = bluesky_page(
            "author_feed.json",
            discovery(
                "author:" + BSKY_HANDLE,
                window_start="2026-08-01T00:00:00Z",
                window_end="2026-08-17T00:00:00Z",
            ),
            route_id=AUTHOR_ROUTE,
        )

        self.assertEqual(
            opener.opened[0].url,
            built_url(AUTHOR_ROUTE, {"actor": BSKY_HANDLE, "limit": "100"}),
        )

    def test_a_cursor_the_core_froze_is_spent_under_the_appviews_own_name(self):
        for route_id, name, request, params in (
            (
                SEARCH_ROUTE,
                "search_posts.json",
                discovery("spacex", ),
                {"q": "spacex", "sort": "latest", "limit": "100", "cursor": "25"},
            ),
            (
                AUTHOR_ROUTE,
                "author_feed.json",
                discovery("author:" + BSKY_HANDLE),
                {"actor": BSKY_HANDLE, "limit": "100", "cursor": "25"},
            ),
        ):
            with self.subTest(route=route_id):
                carried = adapters.AdapterRequest(
                    step_id=request.step_id,
                    query=request.query,
                    target_ids=request.target_ids,
                    cursor="25",
                )
                _, opener = bluesky_page(name, carried, route_id=route_id)

                self.assertEqual(opener.opened[0].url, built_url(route_id, params))


class BlueskyFieldOmittedTest(unittest.TestCase):
    """A row that arrived short of what this adapter declares says so."""

    def test_a_post_with_no_text_carries_the_loss_and_still_carries_its_counts(self):
        payload = payload_of(BLUESKY_DIR, "search_posts.json")
        del payload["posts"][0]["record"]["text"]
        page, _ = answered(bluesky, SEARCH_ROUTE, json.dumps(payload), discovery("spacex"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        self.assertEqual(page.records[0].body, "")
        self.assertEqual(dict(page.records[0].engagement)["likeCount"], 9487)
        # And the row beside it, which arrived whole, carries no loss at all.
        self.assertEqual(page.records[1].loss, ())

    def test_a_stamp_this_module_cannot_read_is_a_missing_time_and_not_a_guess(self):
        payload = payload_of(BLUESKY_DIR, "search_posts.json")
        payload["posts"][0]["record"]["createdAt"] = "yesterday"
        page, _ = answered(bluesky, SEARCH_ROUTE, json.dumps(payload), discovery("spacex"))

        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("field_omitted",))


class XFxtwitterDescriptorTest(unittest.TestCase):
    """What this adapter declares: an operator's identity, and the platform's namespace."""

    def test_the_descriptor_speaks_for_x_through_an_operator_that_is_not_x(self):
        descriptor = x_fxtwitter.DESCRIPTOR

        self.assertEqual(descriptor.adapter_id, "x_fxtwitter")
        self.assertEqual(descriptor.route_id, FXTWITTER_ROUTE)
        self.assertEqual(descriptor.platform, "x")
        self.assertEqual(descriptor.representation_kind, "native")
        self.assertEqual(descriptor.operator_identity, "fxtwitter")
        self.assertEqual(descriptor.min_interval_ms, 1000)
        self.assertEqual(descriptor.burst, 5)
        self.assertEqual(descriptor.page_size, 20)
        self.assertEqual(descriptor.reply_count_metric, "replies")
        self.assertEqual(descriptor.comment_count_metric, "")

    def test_the_class_is_the_routes_own_and_it_is_the_archive_class(self):
        self.assertEqual(x_fxtwitter.DESCRIPTOR.access_class, "K3")
        self.assertEqual(
            x_fxtwitter.DESCRIPTOR.access_class,
            transport.ROUTE_CONSTANTS[FXTWITTER_ROUTE].access_class,
        )

    def test_the_namespace_is_the_platforms_so_one_tweet_read_twice_is_one_tweet(self):
        # Read here and read off the syndication timeline, a status must group
        # by strong identity. A namespace naming the operator would make two
        # readings of one status two different things.
        self.assertEqual(x_fxtwitter.DESCRIPTOR.native_identity_namespace, "x")

    def test_the_standing_loss_is_declared_on_the_descriptor(self):
        self.assertEqual(x_fxtwitter.DESCRIPTOR.standing_loss, ("third_party_archive",))


class XFxtwitterStandingLossTest(unittest.TestCase):
    """`third_party_archive` on every record of every answer, never the page alone."""

    def test_every_record_of_every_answering_operation_carries_it(self):
        for name, request in (
            ("search.json", discovery("spacex")),
            ("statuses.json", discovery("timeline:" + X_HANDLE)),
            ("profile.json", discovery("user:" + X_HANDLE)),
            ("conversation.json", hydration(X_ROOT_ID)),
        ):
            page, _ = fxtwitter_page(name, request)
            with self.subTest(fixture=name):
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(page.records)
                for record in page.records:
                    self.assertIn("third_party_archive", record.loss)

    def test_the_fact_rides_on_the_record_rather_than_on_the_page(self):
        # A caller holding one row cannot correlate it back to a page to learn
        # where it came from, which is the whole reason the loss is standing.
        page, _ = fxtwitter_page("search.json", discovery("spacex"))

        self.assertEqual(page.loss, ())
        self.assertEqual(
            [record.loss for record in page.records],
            [("third_party_archive",), ("third_party_archive",)],
        )


class XFxtwitterSearchTest(unittest.TestCase):
    """The one keyless X search in the roster, read as the operator answers it."""

    def setUp(self):
        self.page, self.opener = fxtwitter_page("search.json", discovery("spacex"))

    def test_the_page_speaks_for_the_route_that_answered(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.route_id, FXTWITTER_ROUTE)
        self.assertEqual(self.page.access_class, "K3")
        self.assertEqual(self.page.operator_identity, "fxtwitter")
        self.assertEqual(self.page.native_order, "fxtwitter_search_latest_order")
        self.assertEqual(len(self.page.records), 2)

    def test_a_status_is_addressed_by_the_url_the_payload_published(self):
        reply = self.page.records[0]

        self.assertEqual(reply.canonical_content_kind, "post")
        self.assertEqual(reply.native_item_id, X_SEARCH_REPLY_ID)
        self.assertEqual(
            reply.canonical_locator,
            "https://x.com/Pre_Consensus/status/" + X_SEARCH_REPLY_ID,
        )
        self.assertEqual(reply.author, "Pre_Consensus")
        self.assertEqual(reply.published_at, "2026-08-17T14:38:22Z")
        self.assertEqual(reply.native_position, 0)

    def test_a_reply_names_the_status_it_answers(self):
        self.assertEqual(self.page.records[0].native_parent_id, X_SEARCH_PARENT_ID)
        self.assertEqual(self.page.records[1].native_parent_id, "")

    def test_a_view_count_nobody_reported_is_absent_and_never_zero(self):
        # `views` is `null` on the first row and an integer on the second. A
        # zero written for the first would be a number nobody reported.
        first = dict(self.page.records[0].engagement)
        second = dict(self.page.records[1].engagement)

        self.assertNotIn("views", first)
        self.assertEqual(second["views"], 20)

    def test_the_counts_are_the_operators_own_names_and_exact_integers(self):
        self.assertEqual(
            self.page.records[0].engagement,
            (("likes", 0), ("reposts", 0), ("replies", 0), ("quotes", 0), ("bookmarks", 0)),
        )

    def test_a_status_carries_the_operators_own_named_facts(self):
        carried = named(self.page.records[0])

        self.assertEqual(carried["lang"], "en")
        self.assertEqual(carried["source"], "Twitter for iPhone")
        # The platform's own spelling of the moment, beside the exact epoch the
        # record's instant was read from.
        self.assertEqual(carried["created_at"], "Mon Aug 17 14:38:22 +0000 2026")
        self.assertEqual(carried["is_note_tweet"], "true")
        self.assertEqual(carried["provider"], "twitter")
        self.assertEqual(carried["author.id"], "2073814671727968256")
        self.assertEqual(
            carried["replying_to.url"],
            "https://x.com/capybaraReborn/status/" + X_SEARCH_PARENT_ID,
        )

    def test_the_continuation_is_the_token_the_operator_published(self):
        self.assertEqual(
            self.page.cursor_out, payload_of(FXTWITTER_DIR, "search.json")["cursor"]["bottom"]
        )

    def test_the_two_rankings_are_two_operations_on_one_endpoint(self):
        top, opener = fxtwitter_page("search.json", discovery("search_top:spacex"))

        self.assertEqual(top.native_order, "fxtwitter_search_top_order")
        self.assertEqual(
            opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "search", "q": "spacex", "feed": "top"}),
        )
        self.assertEqual(
            self.opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "search", "q": "spacex", "feed": "latest"}),
        )


class XFxtwitterTimelineAndProfileTest(unittest.TestCase):
    """One handle's statuses, and the account itself."""

    def test_a_timeline_reads_the_profiles_statuses_collection(self):
        page, opener = fxtwitter_page("statuses.json", discovery("timeline:" + X_HANDLE))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.native_order, "fxtwitter_timeline_order")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(page.records[0].native_item_id, X_ROOT_ID)
        self.assertEqual(page.records[1].native_parent_id, X_ROOT_ID)
        self.assertEqual(dict(page.records[0].engagement)["views"], 1169817)
        self.assertEqual(
            opener.opened[0].url,
            built_url(
                FXTWITTER_ROUTE,
                {"endpoint": "profile", "subject": X_HANDLE, "collection": "statuses"},
            ),
        )

    def test_a_timeline_surfaces_the_operators_own_continuation(self):
        page, _ = fxtwitter_page("statuses.json", discovery("timeline:" + X_HANDLE))

        self.assertEqual(
            page.cursor_out, payload_of(FXTWITTER_DIR, "statuses.json")["cursor"]["bottom"]
        )

    def test_an_account_is_a_profile_record_with_the_accounts_own_counts(self):
        page, opener = fxtwitter_page("profile.json", discovery("user:" + X_HANDLE))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.native_order, "fxtwitter_profile_order")
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "profile")
        self.assertEqual(record.native_item_id, X_PROFILE_ID)
        self.assertEqual(record.canonical_locator, "https://x.com/" + X_HANDLE)
        self.assertEqual(record.author, X_HANDLE)
        self.assertEqual(record.title, X_HANDLE)
        self.assertEqual(
            record.engagement,
            (
                ("followers", 41906741),
                ("following", 127),
                ("likes", 528),
                ("media_count", 4593),
                ("statuses", 11649),
            ),
        )
        self.assertEqual(
            opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "profile", "subject": X_HANDLE}),
        )

    def test_an_account_states_one_moment_and_it_is_read_without_a_locale(self):
        # `Thu Apr 23 21:53:30 +0000 2009` — the month is numbered before the
        # format is read, so a process that set `LC_TIME` still gets the time.
        page, _ = fxtwitter_page("profile.json", discovery("user:" + X_HANDLE))

        self.assertEqual(page.records[0].published_at, "2009-04-23T21:53:30Z")
        self.assertEqual(
            named(page.records[0])["joined"], "Thu Apr 23 21:53:30 +0000 2009"
        )

    def test_an_account_carries_its_own_named_facts_under_their_key_paths(self):
        page, _ = fxtwitter_page("profile.json", discovery("user:" + X_HANDLE))
        carried = named(page.records[0])

        self.assertEqual(carried["location"], "Earth")
        self.assertEqual(carried["protected"], "false")
        self.assertEqual(carried["website.url"], "http://spacex.com")
        self.assertEqual(carried["verification.verified"], "true")
        self.assertEqual(carried["verification.type"], "organization")


class XFxtwitterConversationTest(unittest.TestCase):
    """One status and everything under it, with the root read exactly once."""

    def setUp(self):
        self.page, self.opener = fxtwitter_page("conversation.json", hydration(X_ROOT_ID))

    def test_the_root_is_carried_once_though_the_payload_states_it_twice(self):
        # The payload puts the root under `status` and again at the head of its
        # own `thread`. Reading both would emit one status twice under one id.
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 3)
        self.assertEqual(
            [record.native_item_id for record in self.page.records].count(X_ROOT_ID), 1
        )
        self.assertEqual(self.page.records[0].native_item_id, X_ROOT_ID)

    def test_every_reply_names_the_root_it_answers_and_keeps_its_own_counts(self):
        replies = self.page.records[1:]

        for reply in replies:
            with self.subTest(status=reply.native_item_id):
                self.assertEqual(reply.native_parent_id, X_ROOT_ID)
        # A reply never inherits the root's counts.
        self.assertEqual(dict(self.page.records[0].engagement)["likes"], 8505)
        self.assertEqual(dict(replies[0].engagement)["likes"], 27)
        self.assertEqual(dict(replies[1].engagement)["likes"], 26)

    def test_a_conversation_surfaces_no_continuation_and_spends_none(self):
        # The payload states a `cursor.bottom` here too, and spending it under
        # the name the two listing operations take answered 404 three times out
        # of three on 2026-08-17. A token whose spelling nobody proved is not
        # surfaced, so the core never spends a call of its own on a refusal.
        self.assertEqual(self.page.cursor_out, "")

        carried = adapters.AdapterRequest(
            step_id="s1-social", target_ids=(X_ROOT_ID,), cursor="whatever-the-payload-said"
        )
        _, opener = fxtwitter_page("conversation.json", carried)

        self.assertEqual(
            opener.opened[0].url,
            built_url(FXTWITTER_ROUTE, {"endpoint": "conversation", "subject": X_ROOT_ID}),
        )

    def test_a_conversation_with_no_thread_is_read_from_its_status_alone(self):
        payload = payload_of(FXTWITTER_DIR, "conversation.json")
        payload["thread"] = None
        page, _ = answered(
            x_fxtwitter, FXTWITTER_ROUTE, json.dumps(payload), hydration(X_ROOT_ID)
        )

        self.assertEqual(len(page.records), 3)
        self.assertEqual(page.records[0].native_item_id, X_ROOT_ID)


class XFxtwitterAnswersWithNoStatusTest(unittest.TestCase):
    """The six ways this operator answers with nothing, told apart.

    Two of them arrive at HTTP 200 with a code of the operator's own inside
    the body. A 404 there is a subject it holds nothing for, which is an
    absence; anything else there is the status the read got, one layer in.
    Neither is drift: the envelope is the shape this module declares.
    """

    def test_an_empty_results_list_is_an_absence_and_says_so(self):
        page, _ = fxtwitter_page("search_empty.json", discovery("nothing matches this"))

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("results", " ".join(page.warnings))

    def test_an_empty_answer_surfaces_no_continuation_it_did_not_earn(self):
        # This envelope states a token on every answer and states no "there is
        # more" of its own, so relaying one off an answer with nothing in it
        # would be this module claiming a next page the operator never claimed.
        page, _ = fxtwitter_page("search_empty.json", discovery("nothing matches this"))

        self.assertTrue(payload_of(FXTWITTER_DIR, "search_empty.json")["cursor"]["bottom"])
        self.assertEqual(page.cursor_out, "")

    def test_every_container_that_moved_is_drift_and_never_an_absence(self):
        for name, request, spoken in (
            ("search_reshaped.json", discovery("spacex"), "results"),
            ("profile_reshaped.json", discovery("user:" + X_HANDLE), "user"),
            ("conversation_reshaped.json", hydration(X_ROOT_ID), "status"),
        ):
            with self.subTest(fixture=name):
                page, _ = fxtwitter_page(name, request)

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("schema_drift",))
                self.assertEqual(page.records, ())
                self.assertIn(spoken, " ".join(page.warnings))
                self.assertIn("changed shape", " ".join(page.warnings))

    def test_rows_that_name_no_id_are_drift_and_never_an_empty_search(self):
        page, _ = fxtwitter_page("search_unidentified.json", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertIn("no id on any of them", " ".join(page.warnings))

    def test_a_body_that_is_not_json_at_two_hundred_is_malformed(self):
        page, _ = answered(x_fxtwitter, FXTWITTER_ROUTE, "<html>nope", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("malformed_json",))

    def test_a_status_line_that_is_not_two_hundred_is_the_status_it_is(self):
        for name, status, request in (
            ("bad_request_400.json", 400, hydration("abc")),
            ("not_found_404.json", 404, discovery("user:nobody")),
            ("statuses_not_found_404.json", 404, discovery("timeline:nobody")),
            ("conversation_not_found_404.json", 404, hydration(X_ROOT_ID)),
        ):
            with self.subTest(fixture=name):
                page, _ = fxtwitter_page(name, request, status=status)

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("http_status",))
                self.assertIn(str(status), " ".join(page.warnings))

    def test_a_not_found_inside_a_two_hundred_is_an_absence_in_the_operators_words(self):
        page, _ = fxtwitter_page("code_404_in_200.json", discovery("user:nobody"))

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("code 404", " ".join(page.warnings))
        self.assertIn("User not found", " ".join(page.warnings))

    def test_any_other_code_inside_a_two_hundred_is_the_status_it_names(self):
        page, _ = fxtwitter_page("code_500_in_200.json", discovery("spacex"))

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("code 500", " ".join(page.warnings))
        self.assertIn("Upstream error", " ".join(page.warnings))

    def test_the_same_body_at_two_layers_is_typed_the_same_way_twice(self):
        # `not_found_404.json` and `code_404_in_200.json` are the same bytes.
        # At HTTP 404 the read never arrived, and at HTTP 200 the operator
        # answered about a subject it holds nothing for. Both are honest
        # readings, and neither is drift.
        outer, _ = fxtwitter_page("not_found_404.json", discovery("user:nobody"), status=404)
        inner, _ = fxtwitter_page("code_404_in_200.json", discovery("user:nobody"))

        self.assertEqual(outer.loss, ("http_status",))
        self.assertEqual(inner.outcome, "empty")
        self.assertNotIn("schema_drift", outer.loss + inner.loss)


class XFxtwitterGrammarTest(unittest.TestCase):
    """Which of five operations a step reaches, and what a step naming none means."""

    def test_a_caller_names_the_operation_and_the_argument_survives_it(self):
        for named_step, expected in (
            ("search:spacex", (x_fxtwitter.SEARCH_OPERATION, "spacex")),
            ("search_top:spacex", (x_fxtwitter.SEARCH_TOP_OPERATION, "spacex")),
            ("timeline:" + X_HANDLE, (x_fxtwitter.TIMELINE_OPERATION, X_HANDLE)),
            ("user:" + X_HANDLE, (x_fxtwitter.USER_OPERATION, X_HANDLE)),
            ("conversation:" + X_ROOT_ID, (x_fxtwitter.CONVERSATION_OPERATION, X_ROOT_ID)),
        ):
            with self.subTest(step=named_step):
                self.assertEqual(x_fxtwitter.operation_for(discovery(named_step)), expected)
                # A conversation is reachable from either shape of step, which
                # is what freezing a hit and asking for it again means.
                self.assertEqual(x_fxtwitter.operation_for(hydration(named_step)), expected)

    def test_absent_a_prefix_the_steps_own_shape_decides(self):
        self.assertEqual(
            x_fxtwitter.operation_for(discovery("spacex")),
            (x_fxtwitter.SEARCH_OPERATION, "spacex"),
        )
        self.assertEqual(
            x_fxtwitter.operation_for(hydration(X_ROOT_ID)),
            (x_fxtwitter.CONVERSATION_OPERATION, X_ROOT_ID),
        )

    def test_nothing_is_inferred_from_the_characters_in_an_argument(self):
        # A query of digits is a query, not a status id; a handle written as a
        # query is a query, not a timeline.
        self.assertEqual(
            x_fxtwitter.operation_for(discovery(X_ROOT_ID)),
            (x_fxtwitter.SEARCH_OPERATION, X_ROOT_ID),
        )
        self.assertEqual(
            x_fxtwitter.operation_for(discovery("https://x.com/SpaceX")),
            (x_fxtwitter.SEARCH_OPERATION, "https://x.com/SpaceX"),
        )

    def test_a_cursor_is_spent_only_on_the_operations_that_proved_one(self):
        for step, params in (
            (
                "search:spacex",
                {"endpoint": "search", "q": "spacex", "feed": "latest", "cursor": "NEXT"},
            ),
            (
                "search_top:spacex",
                {"endpoint": "search", "q": "spacex", "feed": "top", "cursor": "NEXT"},
            ),
            (
                "timeline:" + X_HANDLE,
                {
                    "endpoint": "profile",
                    "subject": X_HANDLE,
                    "collection": "statuses",
                    "cursor": "NEXT",
                },
            ),
            ("user:" + X_HANDLE, {"endpoint": "profile", "subject": X_HANDLE}),
        ):
            with self.subTest(step=step):
                request = adapters.AdapterRequest(
                    step_id="s1-social", query=step, cursor="NEXT"
                )
                _, opener = fxtwitter_page("search_empty.json", request)

                self.assertEqual(opener.opened[0].url, built_url(FXTWITTER_ROUTE, params))

    def test_one_call_reads_one_page_and_nothing_else(self):
        _, opener = fxtwitter_page("search.json", discovery("spacex"))

        self.assertEqual(len(opener.opened), 1)


class XFxtwitterFieldOmittedTest(unittest.TestCase):
    """A row short of what this adapter declares says so, beside its standing loss."""

    def test_a_status_with_no_stamp_carries_both_losses(self):
        payload = payload_of(FXTWITTER_DIR, "search.json")
        del payload["results"][0]["created_timestamp"]
        page, _ = answered(
            x_fxtwitter, FXTWITTER_ROUTE, json.dumps(payload), discovery("spacex")
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("third_party_archive", "field_omitted"))
        # The standing half never depends on what the row carried.
        self.assertEqual(page.records[1].loss, ("third_party_archive",))

    def test_a_profile_with_no_join_stamp_carries_both_losses(self):
        payload = payload_of(FXTWITTER_DIR, "profile.json")
        payload["user"]["joined"] = "some time in 2009"
        page, _ = answered(
            x_fxtwitter, FXTWITTER_ROUTE, json.dumps(payload), discovery("user:" + X_HANDLE)
        )

        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("third_party_archive", "field_omitted"))


class BothAdaptersRefuseToInventNumbersTest(unittest.TestCase):
    """Engagement admits only what the origin published as an exact integer."""

    def test_neither_module_reads_a_float_a_bool_or_a_formatted_string_as_a_count(self):
        for module in (bluesky, x_fxtwitter):
            for value in (1.5, True, False, "21,068", "1.2K", None, [], {}):
                with self.subTest(module=module.__name__, value=value):
                    self.assertIsNone(module.exact_count(value))

    def test_a_json_integer_is_a_count_and_zero_is_one_too(self):
        for module in (bluesky, x_fxtwitter):
            with self.subTest(module=module.__name__):
                self.assertEqual(module.exact_count(0), 0)
                self.assertEqual(module.exact_count(9487), 9487)


if __name__ == "__main__":
    unittest.main()
