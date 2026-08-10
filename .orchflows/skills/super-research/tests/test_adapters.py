"""Adapter suite: X reaches its measured capability with no credential.

The claim this module exists to defend is that a stale vendor identifier is
never silence. X rotates its GraphQL query ids per web release, and the id
sits in the request path, so a rotated id answers 404 — the same status a
missing page answers, and one status away from the 401/403 a blocked
operation answers. An adapter that read that 404 as "no results" would turn
a scheduled outage into an empty answer nobody could attribute, and one that
read it as `auth_required` would report a keyless route as credentialed.
findings.md §1 measured both halves: `SearchTimeline` and `TweetDetail`
returned 404 from stale ids while the three operations whose ids were current
returned 200, and a guest-blocked operation returns 403 or 401.

Every test here runs offline against fixtures under `fixtures/x/`.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, runner, transport
from super_research.adapters import x_guest, x_syndication
from tests import helpers


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "x"
PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
GUEST_QUERY_ID = "V7H0Ap3_Hh2FyS75OCDO3Q"
MINTED_GUEST_TOKEN = "1804400000000000000"

# findings.md §1 (X): every field the syndication row records this route
# returning for each of its 100 timeline entries.
SYNDICATION_ROSTER_FIELDS = (
    "full_text",
    "created_at",
    "favorite_count",
    "retweet_count",
    "reply_count",
    "quote_count",
    "conversation_id_str",
)
SYNDICATION_METRICS = ("favorite_count", "retweet_count", "reply_count", "quote_count")

PROFILE_REQUEST = adapters.AdapterRequest(step_id="s1-x", target_ids=("simonw",))


def read_fixture(name):
    """Read one offline fixture."""

    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def stale_identifier_cases():
    """The measured case table: a status, a body, and the loss its evidence names."""

    return tuple(json.loads(read_fixture("stale_identifier_cases.json"))["cases"])


def adapters_named(path, own_id):
    """Every adapter id one source names that is not its own."""

    source = path.read_text(encoding="utf-8")
    return sorted(
        adapter_id
        for adapter_id in runner.ADAPTER_IDS
        if adapter_id != own_id and adapter_id in source
    )


def load_adapter_fixture(name):
    """Load one adapter written beside the tree, by path.

    These are not package modules: nothing in the package imports them and no
    discovery pattern matches them. They exist so the oracle below can be shown
    to reject a wrong result, without mutating the tree under test.
    """

    spec = importlib.util.spec_from_file_location(
        "adapter_fixture_" + name, FIXTURE_DIR / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def typed_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: adapter_page(
            module,
            row["status"],
            read_fixture(row["body_fixture"]),
            content_type="application/json",
            request=adapters.AdapterRequest(step_id="s1-x", target_ids=(row["target_id"],)),
        )[0]
        for row in stale_identifier_cases()
    }


def assert_stale_identifier_is_typed(case, adapter_id, pages):
    """The stale-identifier oracle: a rotated id is named, and named as itself.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. Three confusions are called out by name, because each one
    is a different wrong thing to believe: a stale id read as an empty result
    turns a scheduled rotation into silence, a stale id read as an
    authorization failure calls a keyless route credentialed, and a refusal
    read as a stale id sends a reader chasing a bundle over something the
    origin decided.
    """

    for row in stale_identifier_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if row["expected_loss"] == x_guest.STALE_IDENTIFIER:
            if not page.records and page.outcome != "failed":
                case.fail("a stale query id was recorded as an empty success:" + detail)
            if x_guest.AUTH_REQUIRED in loss:
                case.fail("a stale query id was recorded as an authorization failure:" + detail)
            if x_guest.STALE_IDENTIFIER not in loss:
                case.fail("a stale query id was not recorded as one:" + detail)
        elif x_guest.STALE_IDENTIFIER in loss:
            case.fail("a response naming no stale identifier was recorded as one:" + detail)
        case.assertEqual(
            page.outcome,
            row["expected_outcome"],
            "case {0} came back {1}, its evidence says {2}".format(
                name, page.outcome, row["expected_outcome"]
            ),
        )
        case.assertEqual(
            loss, (row["expected_loss"],) if row["expected_loss"] else (), detail
        )


def adapter_page(module, status, body, content_type="text/html", request=None):
    """Run one adapter over one canned response; return its page and the opener."""

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {module.DESCRIPTOR.route_id: (status, body, content_type)}
    )
    return (
        module.fetch_native_page(carrier, PROFILE_REQUEST if request is None else request),
        opener,
    )


class FakeHTTPResponse:
    """The little of an http response that ``urlopen_response`` reads."""

    def __init__(self, status, body, content_type):
        self.status = status
        self.headers = {"Content-Type": content_type}
        self._body = body.encode("utf-8")

    def read(self, limit):
        return self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


class RoutingUrlopen:
    """Stand in for ``urllib.request.urlopen``, answering by url and keeping the wire.

    Two answers are needed at once here, which is the whole point: minting a
    guest token and spending it are two different requests to two different
    endpoints, and only one of them is a route read.
    """

    def __init__(self, answers, default=(200, "{}", "application/json")):
        self.answers = list(answers)  # [(url_fragment, status, body, content_type)]
        self.default = default
        self.requests = []

    def __call__(self, outbound, timeout=None):
        self.requests.append(outbound)
        for fragment, status, body, content_type in self.answers:
            if fragment in outbound.full_url:
                return FakeHTTPResponse(status, body, content_type)
        return FakeHTTPResponse(*self.default)

    def urls(self):
        return [outbound.full_url for outbound in self.requests]

    def headers_of(self, index):
        return {name.lower(): value for name, value in self.requests[index].header_items()}


ACTIVATION_ANSWER = (
    "guest/activate",
    200,
    json.dumps({"guest_token": MINTED_GUEST_TOKEN}),
    "application/json",
)


def guest_read_request():
    return transport.build_transport_request(
        transport.X_GUEST_GRAPHQL_ROUTE,
        {
            "query_id": GUEST_QUERY_ID,
            "operation_name": "UserByScreenName",
            "variables": '{"screen_name":"simonw"}',
        },
    )


class XRouteConstantTest(unittest.TestCase):
    """Both X routes name a path the evidence measured, owned by transport."""

    def test_the_syndication_route_spends_the_handle_as_a_path_segment(self):
        request = transport.build_transport_request(
            transport.X_SYNDICATION_TIMELINE_ROUTE, {"screen_name": "simonw"}
        )

        # findings.md §1 (X): syndication.twitter.com/srv/timeline-profile/
        # screen-name/<u> returned 200 with 100 timeline entries.
        self.assertEqual(
            request.url,
            "https://syndication.twitter.com/srv/timeline-profile/screen-name/simonw",
        )
        self.assertEqual(request.method, "GET")

    def test_the_guest_graphql_route_spends_the_query_id_and_operation_as_segments(self):
        request = transport.build_transport_request(
            transport.X_GUEST_GRAPHQL_ROUTE,
            {
                "query_id": GUEST_QUERY_ID,
                "operation_name": "UserTweets",
                "variables": '{"userId":"44196397"}',
            },
        )

        # A rotating query id lives in the path, which is why a stale one is a
        # 404 rather than an error inside a 200 body.
        self.assertEqual(
            request.url,
            "https://api.twitter.com/graphql/"
            + GUEST_QUERY_ID
            + "/UserTweets?variables=%7B%22userId%22%3A%2244196397%22%7D",
        )
        self.assertEqual(request.method, "GET")

    def test_a_route_whose_path_segments_are_unsupplied_still_builds_its_base_url(self):
        request = transport.build_transport_request(transport.X_GUEST_GRAPHQL_ROUTE)

        self.assertEqual(request.url, "https://api.twitter.com/graphql")

    def test_both_x_routes_are_keyless_and_read_only(self):
        for route_id in (
            transport.X_SYNDICATION_TIMELINE_ROUTE,
            transport.X_GUEST_GRAPHQL_ROUTE,
        ):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertTrue(transport.route_admissions()[route_id])
                self.assertEqual(transport.admitted_methods(route_id), transport.READ_METHODS)
                self.assertEqual(route.operator_identity, "x")

    def test_the_guest_route_carries_the_public_bearer_and_the_syndication_route_none(self):
        self.assertIs(
            transport.route_credential(transport.X_GUEST_GRAPHQL_ROUTE),
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.X_GUEST_PUBLIC_BEARER],
        )
        self.assertIsNone(
            transport.route_credential(transport.X_SYNDICATION_TIMELINE_ROUTE)
        )


class GuestTokenMintTest(unittest.TestCase):
    """The two-call mint lives here, so an adapter stays a one-read shape.

    A guest token is a credential the origin issues rather than one the vendor
    publishes, so it is applied exactly where the published bearer is applied —
    at send time, by the opener — and never earlier. That keeps one adapter
    call at one ``carrier.fetch``, and keeps the token off every value the run
    keeps.
    """

    def setUp(self):
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def _sent(self, requests, answers):
        opener = RoutingUrlopen(answers)
        results = []
        with mock.patch.object(urllib.request, "urlopen", opener):
            for request in requests:
                results.append(transport.urlopen_response(request))
        return results, opener

    def test_a_guest_read_is_preceded_by_one_activation_and_carries_its_token(self):
        _, opener = self._sent([guest_read_request()], [ACTIVATION_ANSWER])

        self.assertEqual(len(opener.requests), 2)
        self.assertIn("guest/activate", opener.urls()[0])
        self.assertEqual(opener.requests[0].get_method(), "POST")
        self.assertIn("/graphql/", opener.urls()[1])
        self.assertEqual(
            opener.headers_of(1)[transport.GUEST_TOKEN_HEADER], MINTED_GUEST_TOKEN
        )

    def test_the_token_is_minted_once_and_spent_on_every_later_read(self):
        _, opener = self._sent(
            [guest_read_request(), guest_read_request()], [ACTIVATION_ANSWER]
        )

        activations = [url for url in opener.urls() if "guest/activate" in url]
        self.assertEqual(len(activations), 1)
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(
            opener.headers_of(2)[transport.GUEST_TOKEN_HEADER], MINTED_GUEST_TOKEN
        )

    def test_a_keyless_route_is_never_preceded_by_an_activation(self):
        _, opener = self._sent(
            [transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})],
            [ACTIVATION_ANSWER],
        )

        self.assertEqual(len(opener.requests), 1)
        self.assertNotIn(transport.GUEST_TOKEN_HEADER, opener.headers_of(0))

    def test_a_refused_mint_yields_no_token_rather_than_an_exception(self):
        # The read still goes out, unauthorized, and the origin answers 401 or
        # 403 — which the adapter records as the platform's own refusal.
        # Inventing a token, or turning a failed mint into a retry, are the two
        # wrong answers.
        refused = ("guest/activate", 403, "forbidden", "text/plain")

        results, opener = self._sent([guest_read_request()], [refused])

        self.assertEqual(len(opener.requests), 2)
        self.assertNotIn(transport.GUEST_TOKEN_HEADER, opener.headers_of(1))
        self.assertEqual(results[0][0], 200)

    def test_the_minted_token_reaches_no_request_the_run_records(self):
        opener = RoutingUrlopen([ACTIVATION_ANSWER])
        carrier = transport.Transport(now=lambda: "2026-08-10T09:00:00Z")

        with mock.patch.object(urllib.request, "urlopen", opener):
            response = carrier.fetch(guest_read_request())

        self.assertNotIn(MINTED_GUEST_TOKEN, repr(carrier.calls))
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(response))
        self.assertEqual(len(carrier.calls), 1)


class SyndicationTimelineTest(unittest.TestCase):
    """Criterion 1, K2 half: 100 entries, each carrying its whole roster row."""

    def setUp(self):
        self.page, self.opener = adapter_page(
            x_syndication, 200, read_fixture("syndication_timeline.html")
        )

    def test_one_page_carries_the_hundred_entries_the_evidence_measured(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(len(self.page.records), 100)
        self.assertEqual(len(self.opener.opened), 1)

    def test_every_entry_carries_every_field_its_roster_row_names(self):
        for record in self.page.records:
            with self.subTest(item=record.native_item_id):
                metrics = dict(record.engagement)

                self.assertTrue(record.body, "full_text")
                self.assertTrue(record.published_at, "created_at")
                self.assertTrue(record.native_parent_id, "conversation_id_str")
                self.assertEqual(sorted(metrics), sorted(SYNDICATION_METRICS))
                for name in SYNDICATION_METRICS:
                    self.assertIsInstance(metrics[name], int)
                self.assertEqual(record.loss, ())

    def test_a_record_names_the_tweet_its_author_and_its_conversation(self):
        first = self.page.records[0]
        reply = self.page.records[2]

        self.assertEqual(first.canonical_content_kind, "post")
        self.assertEqual(first.native_item_id, "1799990000000000001")
        self.assertEqual(first.author, "simonw")
        self.assertEqual(
            first.canonical_locator, "https://x.com/simonw/status/1799990000000000001"
        )
        self.assertEqual(first.published_at, "2026-08-09T07:00:00Z")
        self.assertEqual(first.native_position, 0)
        # X reports the thread a post belongs to as conversation_id_str: its own
        # id for a root, the root it answers for a reply. Both are the
        # platform's own statement, so both are carried as reported.
        self.assertEqual(first.native_parent_id, first.native_item_id)
        self.assertNotEqual(reply.native_parent_id, reply.native_item_id)

    def test_the_page_speaks_for_x_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "x_syndication")
        self.assertEqual(self.page.platform, "x")
        self.assertEqual(self.page.native_identity_namespace, "x")
        self.assertEqual(self.page.access_class, "K2")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.X_SYNDICATION_TIMELINE_ROUTE)

    def test_a_page_that_embeds_no_structured_data_is_drift_and_not_an_empty_profile(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_without_next_data.html")
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_a_timeline_that_moved_is_drift_and_not_an_empty_profile(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_drifted_container.html")
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_the_origins_own_failure_stays_the_origins(self):
        page, _ = adapter_page(x_syndication, 404, "<html><body>Not found</body></html>")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("404", " ".join(page.warnings))

    def test_the_handle_is_read_from_the_target_or_from_the_query(self):
        for request in (
            adapters.AdapterRequest(step_id="s1-x", target_ids=("@simonw",)),
            adapters.AdapterRequest(step_id="s1-x", query="simonw"),
        ):
            with self.subTest(request=request):
                _, opener = adapter_page(
                    x_syndication,
                    200,
                    read_fixture("syndication_timeline.html"),
                    request=request,
                )

                self.assertTrue(opener.opened[0].url.endswith("/simonw"), opener.opened[0].url)


class SyndicationDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metric."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # findings.md §1 (X): 2.5 s per request. No refusal was observed on
        # this route, so burst and cooldown keep the conservative defaults
        # rather than a number nobody measured.
        descriptor = x_syndication.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 2500)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.X_SYNDICATION_TIMELINE_ROUTE],
            runner.RouteBudget(min_interval_ms=2500, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_the_reply_metric_it_reports_and_no_comment_metric(self):
        # X reports one metric for replies and none named for comments.
        # Declaring the reply count under both names would make two of the five
        # named views silently identical on a number the platform reported once.
        self.assertEqual(x_syndication.DESCRIPTOR.reply_count_metric, "reply_count")
        self.assertEqual(x_syndication.DESCRIPTOR.comment_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("x_syndication", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("x_syndication"), x_syndication.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.X_SYNDICATION_TIMELINE_ROUTE: (
                    200,
                    read_fixture("syndication_timeline.html"),
                    "text/html",
                )
            },
        )
        page = runner.call_adapter("x_syndication", carrier, PROFILE_REQUEST)

        self.assertEqual(len(page.records), 100)
        self.assertEqual(len(opener.opened), 1)


def guest_page(body, status=200, target_id="tweet:1799990000000000001"):
    """Run ``x_guest`` over one canned answer for one named operation."""

    return adapter_page(
        x_guest,
        status,
        body,
        content_type="application/json",
        request=adapters.AdapterRequest(step_id="s1-x", target_ids=(target_id,)),
    )


class GuestOperationTest(unittest.TestCase):
    """Criterion 1, K1 half: the three operations a guest token authorizes."""

    def test_a_tweet_by_id_carries_the_platforms_own_counts(self):
        page, opener = guest_page(read_fixture("guest_tweet_result.json"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "post")
        self.assertEqual(record.native_item_id, "1799990000000000001")
        self.assertEqual(record.native_parent_id, "1799990000000000001")
        self.assertEqual(record.author, "simonw")
        self.assertEqual(record.published_at, "2026-08-09T07:00:00Z")
        self.assertEqual(
            record.canonical_locator, "https://x.com/simonw/status/1799990000000000001"
        )
        self.assertEqual(
            dict(record.engagement),
            {
                "favorite_count": 412,
                "retweet_count": 57,
                "reply_count": 23,
                "quote_count": 4,
            },
        )
        self.assertEqual(len(opener.opened), 1)

    def test_a_user_by_handle_carries_the_profile_the_route_returns(self):
        page, _ = guest_page(
            read_fixture("guest_user_by_screen_name.json"), target_id="user:simonw"
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 1)
        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "profile")
        self.assertEqual(record.native_item_id, "12497")
        self.assertEqual(record.author, "simonw")
        self.assertEqual(record.title, "Simon Willison")
        self.assertIn("local models", record.body)
        self.assertEqual(record.canonical_locator, "https://x.com/simonw")
        self.assertEqual(record.published_at, "2007-11-12T18:04:11Z")
        self.assertEqual(dict(record.engagement)["followers_count"], 61234)

    def test_a_user_timeline_carries_its_posts_and_surfaces_its_cursor(self):
        page, _ = guest_page(
            read_fixture("guest_user_tweets.json"), target_id="user_tweets:12497"
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(
            [record.native_item_id for record in page.records],
            ["1799990000000000001", "1799990000000000003"],
        )
        self.assertEqual([record.native_position for record in page.records], [0, 1])
        self.assertEqual(page.records[1].native_parent_id, "1799990000000000002")
        # The cursor is surfaced for the core to decide on. The adapter does
        # not follow it: one call, one page.
        self.assertEqual(page.cursor_out, "DAABCgABGel3Xxi2ZAAKAAIY6WOMSt-QAAgAAgAAAAI")

    def test_each_target_kind_names_its_own_operation_and_query_id(self):
        expected = {
            "tweet:1799990000000000001": ("TweetResultByRestId", "tweetId"),
            "user:simonw": ("UserByScreenName", "screen_name"),
            "user_tweets:12497": ("UserTweets", "userId"),
        }

        for target_id, (operation, variable) in sorted(expected.items()):
            with self.subTest(target=target_id):
                _, opener = guest_page(
                    read_fixture("guest_tweet_result.json"), target_id=target_id
                )
                url = opener.opened[0].url

                self.assertIn("/" + x_guest.GUEST_QUERY_IDS[operation] + "/", url)
                self.assertIn("/" + operation + "?", url)
                self.assertIn(variable, urllib.parse.unquote(url))

    def test_a_bare_target_id_is_a_tweet_id_and_never_a_guess_at_its_shape(self):
        _, opener = guest_page(
            read_fixture("guest_tweet_result.json"), target_id="1799990000000000001"
        )

        self.assertIn("/TweetResultByRestId?", opener.opened[0].url)

    def test_the_page_speaks_for_x_at_the_class_the_ladder_gives_it(self):
        page, _ = guest_page(read_fixture("guest_tweet_result.json"))

        self.assertEqual(page.adapter_id, "x_guest")
        self.assertEqual(page.platform, "x")
        self.assertEqual(page.native_identity_namespace, "x")
        self.assertEqual(page.access_class, "K1")
        self.assertEqual(page.representation_kind, "native")
        self.assertEqual(page.route_id, transport.X_GUEST_GRAPHQL_ROUTE)


class GuestDescriptorTest(unittest.TestCase):
    """Criterion 3: every rotating id names its way back, where a reader meets it."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        descriptor = x_guest.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 500)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.X_GUEST_GRAPHQL_ROUTE],
            runner.RouteBudget(min_interval_ms=500, burst=1, cooldown_ms=60000),
        )

    def test_every_operation_declares_its_query_id_with_a_recovery_procedure(self):
        declared = x_guest.DESCRIPTOR.volatile_identifiers

        self.assertEqual(len(declared), len(x_guest.GUEST_QUERY_IDS))
        for operation, query_id in sorted(x_guest.GUEST_QUERY_IDS.items()):
            with self.subTest(operation=operation):
                naming = [
                    identifier
                    for identifier in declared
                    if operation in identifier.name and query_id in identifier.name
                ]

                self.assertEqual(len(naming), 1)
                # The procedure travels with the identifier rather than living
                # somewhere a reader would have to already know to look.
                recovery = naming[0].recovery
                self.assertIn("import map", recovery)
                self.assertIn("queryId", recovery)

    def test_a_query_id_carries_the_shape_the_route_puts_in_its_path(self):
        for operation, query_id in sorted(x_guest.GUEST_QUERY_IDS.items()):
            with self.subTest(operation=operation):
                self.assertEqual(len(query_id), 22)
                self.assertEqual(query_id, urllib.parse.quote(query_id, safe="-_"))

    def test_it_declares_the_reply_metric_it_reports_and_no_comment_metric(self):
        self.assertEqual(x_guest.DESCRIPTOR.reply_count_metric, "reply_count")
        self.assertEqual(x_guest.DESCRIPTOR.comment_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("x_guest", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("x_guest"), x_guest.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.X_GUEST_GRAPHQL_ROUTE: (
                    200,
                    read_fixture("guest_tweet_result.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter(
            "x_guest",
            carrier,
            adapters.AdapterRequest(step_id="s1-x", target_ids=("tweet:1799990000000000001",)),
        )

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)


class StaleIdentifierTest(unittest.TestCase):
    """Criterion 2: a rotated query id is typed, and never mistaken for the other thing.

    This is the ticket's spine. X rotates these ids on its own release
    schedule, so the day one goes stale is a day this package must say what
    happened — not return nothing, and not blame a credential it does not use.
    """

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_stale_identifier_is_typed(self, "x_guest", typed_pages(x_guest))

    def test_a_stale_query_id_names_the_id_and_the_way_back_to_a_current_one(self):
        page, opener = guest_page(read_fixture("guest_stale_query_id.json"), status=404)
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, ("stale_identifier",))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn("TweetResultByRestId", warning)
        self.assertIn(x_guest.GUEST_QUERY_IDS["TweetResultByRestId"], warning)
        self.assertIn("import map", warning)
        # And it cost one call: a stale id is an answer, not a reason to look
        # somewhere else.
        self.assertEqual(len(opener.opened), 1)

    def test_a_refusal_is_the_platforms_and_never_a_rotated_id(self):
        page, _ = guest_page(read_fixture("guest_blocked_operation.json"), status=403)

        self.assertEqual(page.loss, ("auth_required",))
        self.assertNotIn("stale_identifier", page.loss)

    def test_no_x_route_returns_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. Both routes are keyless: the only way
        # `auth_required` can appear is the origin's own 401 or 403, never the
        # absence of something this package was supposed to have.
        for module, body, content_type in (
            (x_syndication, read_fixture("syndication_timeline.html"), "text/html"),
            (x_guest, read_fixture("guest_tweet_result.json"), "application/json"),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module,
                    200,
                    body,
                    content_type=content_type,
                    request=adapters.AdapterRequest(
                        step_id="s1-x", target_ids=("tweet:1799990000000000001",)
                    ),
                )

                self.assertNotIn("auth_required", page.loss)
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(transport.route_admissions()[module.DESCRIPTOR.route_id])


class StaleIdentifierOracleCanFailTest(unittest.TestCase):
    """Criterion 5: the oracle above rejects a wrong result, in either direction.

    Both adapters here are written beside the tree and loaded by path. Each is
    ``x_guest`` with exactly one status branch replaced, which is what makes a
    rejection attributable to that branch and to nothing else. Nothing in the
    package produces them and nothing under test is mutated to obtain them.
    """

    def _assert_oracle_rejects(self, name, reason):
        wrong = load_adapter_fixture(name)

        with self.assertRaises(AssertionError) as caught:
            assert_stale_identifier_is_typed(self, name, typed_pages(wrong))

        self.assertIn(reason, str(caught.exception))

    def test_an_adapter_that_answers_a_stale_id_with_nothing_fails_the_oracle(self):
        # Row 5's named case: the 404 comes back as a result set with no rows
        # in it, so a caller reads "this account has no posts" off a page the
        # origin never served.
        self._assert_oracle_rejects(
            "stale_id_as_empty_adapter",
            "a stale query id was recorded as an empty success",
        )

    def test_an_adapter_that_calls_a_stale_id_a_credential_problem_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "stale_id_as_auth_required_adapter",
            "a stale query id was recorded as an authorization failure",
        )

    def test_an_adapter_that_calls_every_refusal_a_stale_id_fails_the_oracle(self):
        # The opposite error. Without this side the oracle could be satisfied
        # by typing everything stale, which would send a reader after a bundle
        # walk over an operation the origin simply will not serve a guest.
        self._assert_oracle_rejects(
            "blocked_as_stale_adapter",
            "a response naming no stale identifier was recorded as one",
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_stale_identifier_is_typed(self, "x_guest", typed_pages(x_guest))


class OneCallOnePageTest(unittest.TestCase):
    """Criterion 4: one bounded call in, exactly one page out, whatever comes back.

    An adapter that retried, paged, or reached for a second route on a bad
    answer would spend an origin's budget without anyone having asked, and the
    ledger would stop describing the work. The proof is the carrier's own
    attempt log, over every case in the table and every failure shape either
    route can answer with.
    """

    def _every_case(self):
        for row in stale_identifier_cases():
            yield (
                "x_guest/" + row["case_name"],
                x_guest,
                row["status"],
                read_fixture(row["body_fixture"]),
                "application/json",
                adapters.AdapterRequest(step_id="s1-x", target_ids=(row["target_id"],)),
            )
        syndication = (
            ("timeline", 200, "syndication_timeline.html"),
            ("no_next_data", 200, "syndication_without_next_data.html"),
            ("drifted", 200, "syndication_drifted_container.html"),
        )
        for name, status, fixture in syndication:
            yield (
                "x_syndication/" + name,
                x_syndication,
                status,
                read_fixture(fixture),
                "text/html",
                PROFILE_REQUEST,
            )
        for status in (404, 500, 503):
            yield (
                "x_syndication/http_{0}".format(status),
                x_syndication,
                status,
                "<html><body>no</body></html>",
                "text/html",
                PROFILE_REQUEST,
            )

    def test_every_answer_costs_one_call_on_the_adapters_own_route(self):
        for name, module, status, body, content_type, request in self._every_case():
            with self.subTest(case=name):
                page, opener = adapter_page(
                    module, status, body, content_type=content_type, request=request
                )

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    [call.route_id for call in opener.opened], [module.DESCRIPTOR.route_id]
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertIsInstance(page, adapters.NativePage)

    def test_a_cursor_is_surfaced_for_the_core_and_never_followed(self):
        page, opener = guest_page(
            read_fixture("guest_user_tweets.json"), target_id="user_tweets:12497"
        )

        self.assertTrue(page.cursor_out)
        self.assertEqual(len(opener.opened), 1)

    def test_a_cursor_the_core_hands_back_is_spent_on_the_next_single_call(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.X_GUEST_GRAPHQL_ROUTE: (
                    200,
                    read_fixture("guest_user_tweets.json"),
                    "application/json",
                )
            },
        )

        x_guest.fetch_native_page(
            carrier,
            adapters.AdapterRequest(
                step_id="s1-x", target_ids=("user_tweets:12497",), cursor="DAABCgABGel3"
            ),
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertIn("DAABCgABGel3", urllib.parse.unquote(opener.opened[0].url))

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        # "Never calls another adapter" as a structure. Each module speaks to
        # the transport seam and the shared protocol, and to nothing else, so
        # no adapter can quietly become a fallback for a route it does not own.
        for module_name, own_id in (
            ("x_guest.py", "x_guest"),
            ("x_syndication.py", "x_syndication"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", (ADAPTER_DIR / module_name).read_text(encoding="utf-8")
                )

    def test_the_cross_adapter_scan_can_fail(self):
        # Which is what makes the case above worth anything: a module beside
        # the tree that does reach another adapter is named by the same scan.
        self.assertEqual(
            adapters_named(FIXTURE_DIR / "stale_id_as_empty_adapter.py", "stale_id_as_empty"),
            ["x_guest"],
        )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = [
            (x_syndication, read_fixture("syndication_timeline.html"), "text/html", PROFILE_REQUEST),
            (
                x_guest,
                read_fixture("guest_user_tweets.json"),
                "application/json",
                adapters.AdapterRequest(step_id="s1-x", target_ids=("user_tweets:12497",)),
            ),
        ]

        for module, body, content_type, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock, {module.DESCRIPTOR.route_id: (200, body, content_type)}
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_nothing_in_the_package_can_reach_a_wrong_x_adapter(self):
        wrong = (
            "stale_id_as_empty_adapter",
            "stale_id_as_auth_required_adapter",
            "blocked_as_stale_adapter",
        )
        named = [
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for name in wrong
            if name in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(named, [])


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
