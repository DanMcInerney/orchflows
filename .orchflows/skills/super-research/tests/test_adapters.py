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
returned 200, and a guest-blocked operation returns 403 or 401. That claim is
checked over a case table and shown to be falsifiable by three wrong adapters
written beside the tree, one per confusion.

Three smaller claims hold it up. The first is that the capability is real:
100 timeline entries carrying the platform's own engagement out of a public
page, and three operations out of a token anyone can mint. The second is that
the token stays a transport concern — one mint per process, applied at send
time, absent from every value the run keeps — so an adapter that needs
authorization is still exactly one read. The third is that a structured page
that moved is `schema_drift` and never an empty profile, which is the same
distinction as the first claim at the other access class.

Every test here runs offline against fixtures under `fixtures/x/`. Those
fixtures carry the shape and field set findings.md §1 records; the evidence
records no captured bodies, and this package may not reach the network to
make one, so what they prove is that this code reads that shape correctly.
Criterion 12's live smoke is what proves the shape.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, cache, normalize, runner, schema, transport
from super_research.adapters import linkedin_jobs, linkedin_public, x_guest, x_syndication
from tests import helpers


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "x"
LINKEDIN_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "linkedin"
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
                carried = dict(record.engagement)
                carried["full_text"] = record.body
                carried["created_at"] = record.published_at
                carried["conversation_id_str"] = record.native_parent_id

                self.assertEqual(sorted(carried), sorted(SYNDICATION_ROSTER_FIELDS))
                for name in SYNDICATION_ROSTER_FIELDS:
                    self.assertTrue(carried[name], name)
                for name in SYNDICATION_METRICS:
                    self.assertIsInstance(carried[name], int)
                self.assertEqual(record.loss, ())

    def test_an_entry_missing_a_roster_field_arrives_marked_and_never_zero_filled(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_partial_entry.html")
        )
        complete, partial = page.records

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(complete.loss, ())
        self.assertEqual(partial.loss, ("field_omitted",))
        # Marked, and absent rather than invented: no quote count at all, and
        # no time, instead of a zero and a moment nobody observed.
        self.assertNotIn("quote_count", dict(partial.engagement))
        self.assertEqual(partial.published_at, "")
        self.assertEqual(dict(partial.engagement)["favorite_count"], 96)

    def test_an_entry_that_is_not_a_post_is_not_read_as_one(self):
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_partial_entry.html")
        )

        self.assertEqual(len(page.records), 2)
        self.assertEqual(
            [record.canonical_content_kind for record in page.records], ["post", "post"]
        )

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

    def test_the_one_legitimate_empty_says_why_it_is_empty(self):
        # A result the graph holds but has no profile in it is a real empty —
        # a suspended account, not a rotated id and not a page that moved. It
        # still may not be silent: an empty nobody explained is the shape every
        # other case here exists to keep this adapter out of.
        page, _ = guest_page(
            read_fixture("guest_user_unavailable.json"), target_id="user:simonw"
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("UserUnavailable", " ".join(page.warnings))
        self.assertIn("UserByScreenName", " ".join(page.warnings))

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


class RouteTtlTest(unittest.TestCase):
    """How long each X route's answer may stand in for a fresh read.

    A TTL belongs to a route's own volatility, and `cache.py`'s default is
    deliberately short — a route nobody has measured is not one to trust for
    long. Both of these were measured, so both declare their own, and the
    proof is behavioral: a re-read ninety seconds later, which the default
    would have sent back to the origin.
    """

    def _paced(self, clock, route_id, body, content_type):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, content_type)}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return governor, opener

    def test_a_timeline_reread_inside_the_window_is_answered_from_memory(self):
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.X_SYNDICATION_TIMELINE_ROUTE,
            read_fixture("syndication_timeline.html"),
            "text/html",
        )

        first = x_syndication.fetch_native_page(governor, PROFILE_REQUEST)
        clock.advance(90)
        second = x_syndication.fetch_native_page(governor, PROFILE_REQUEST)

        self.assertEqual(len(opener.opened), 1)
        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertIn(cache.CACHE_HIT, second.loss)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read, which is what makes the saving free
        # rather than a quiet loss of freshness.
        self.assertEqual(second.observed_at, first.observed_at)
        self.assertEqual(len(second.records), 100)

    def test_the_route_serving_the_most_volatile_thing_holds_it_for_the_least_time(self):
        # One TTL per route, and the guest route serves three operations at
        # once, so it takes the volatility of the most volatile of them — a
        # tweet's counts — rather than the least. It is also the cheap read:
        # 0.5 s against 2.5 s and 378 KB, so holding an answer longer buys
        # less here than anywhere else on X.
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.X_GUEST_GRAPHQL_ROUTE,
            read_fixture("guest_tweet_result.json"),
            "application/json",
        )
        request = adapters.AdapterRequest(
            step_id="s1-x", target_ids=("tweet:1799990000000000001",)
        )

        x_guest.fetch_native_page(governor, request)
        clock.advance(90)
        held = x_guest.fetch_native_page(governor, request)
        clock.advance(90)
        expired = x_guest.fetch_native_page(governor, request)

        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        self.assertLess(
            cache.ttl_seconds(transport.X_GUEST_GRAPHQL_ROUTE),
            cache.ttl_seconds(transport.X_SYNDICATION_TIMELINE_ROUTE),
        )


def x_manifest():
    """One dispatch reading the same author through both X routes."""

    return schema.AcquisitionManifest(
        manifest_id="m-x",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-timeline",
                kind="hydration",
                adapter_id="x_syndication",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://x.com/simonw", target_id="simonw"
                    ),
                ),
                max_items=200,
            ),
            schema.AcquisitionStep(
                step_id="s2-tweet",
                kind="hydration",
                adapter_id="x_guest",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://x.com/simonw",
                        target_id="tweet:1799990000000000001",
                    ),
                ),
                max_items=1,
            ),
        ),
    )


class ArtifactSeamTest(unittest.TestCase):
    """The widest seam: the record a caller keeps, after normalize has run.

    Every test above reads a ``NativePage``, which is an intermediate value.
    "X reaches its measured capability" is a claim about the artifact, so it
    is closed here — including the part where one tweet observed twice, at two
    access classes, stays two records.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                transport.X_SYNDICATION_TIMELINE_ROUTE: (
                    200,
                    read_fixture("syndication_timeline.html"),
                    "text/html",
                ),
                transport.X_GUEST_GRAPHQL_ROUTE: (
                    200,
                    read_fixture("guest_tweet_result.json"),
                    "application/json",
                ),
            },
        )
        self.artifact = runner.run_acquisition(x_manifest(), carrier, clock=clock.monotonic)

    def test_the_artifact_holds_every_entry_both_routes_returned(self):
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())
        self.assertEqual(len(self.artifact.records), 101)
        self.assertEqual([step.records_kept for step in self.artifact.steps], [100, 1])
        self.assertEqual(len(self.opener.opened), 2)

    def test_a_record_keeps_the_platforms_own_counts_at_the_moment_they_were_read(self):
        record = self.artifact.records[0]
        snapshots = {snapshot.metric_name: snapshot for snapshot in record.engagement}

        self.assertEqual(sorted(snapshots), sorted(SYNDICATION_METRICS))
        self.assertEqual(snapshots["favorite_count"].value, 412)
        self.assertEqual(snapshots["favorite_count"].observed_at, record.observed_at)
        # The platform's own page, so its times are authoritative rather than
        # reported: nothing here is an archive speaking for X.
        self.assertEqual(record.time_confidence, "authoritative")
        self.assertEqual(record.access_class, "K2")
        self.assertEqual(record.usable_basis_time, "2026-08-09T07:00:00Z")

    def test_one_tweet_seen_at_two_access_classes_is_two_records_held_together(self):
        # wrong_merge_law rule 1: the same native identity observed twice is
        # one group of two, never one record. The K1 read and the K2 read
        # disagree about nothing here, and they would still not be folded if
        # they did.
        shared = "1799990000000000001"
        seen = [record for record in self.artifact.records if record.native_item_id == shared]
        groups = [
            group
            for group in self.artifact.groups
            if len(group.member_record_ids) > 1
        ]

        self.assertEqual([record.access_class for record in seen], ["K2", "K1"])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].key_kind, "strong")
        self.assertEqual(
            sorted(groups[0].member_record_ids), sorted(record.record_id for record in seen)
        )


class LinkedInRouteConstantTest(unittest.TestCase):
    """Both LinkedIn routes name a surface the evidence measured, owned by transport."""

    def test_the_jobs_guest_route_is_the_search_endpoint_the_evidence_measured(self):
        request = transport.build_transport_request(
            transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
            {"keywords": "reliability engineer", "location": "Seattle", "start": "10"},
        )

        # findings.md §1 (LinkedIn): linkedin.com/jobs-guest/jobs/api/
        # seeMoreJobPostings/search returned 200 with 10 jobs, start= paginating.
        self.assertEqual(
            request.url,
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=reliability+engineer&location=Seattle&start=10",
        )
        self.assertEqual(request.method, "GET")

    def test_the_public_profile_route_spends_the_slug_as_a_path_segment(self):
        request = transport.build_transport_request(
            transport.LINKEDIN_PUBLIC_PROFILE_ROUTE, {"slug": "avery-lindqvist-8a41b207"}
        )

        # findings.md §1 (LinkedIn): linkedin.com/in/<slug> returned 200 with a
        # complete ld+json Person block. The slug is a path segment, so the
        # endpoint's shape stays transport's and only the value is the caller's.
        self.assertEqual(
            request.url, "https://www.linkedin.com/in/avery-lindqvist-8a41b207"
        )
        self.assertEqual(request.method, "GET")

    def test_both_linkedin_routes_are_keyless_and_read_only(self):
        for route_id in (
            transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
            transport.LINKEDIN_PUBLIC_PROFILE_ROUTE,
        ):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertTrue(transport.route_admissions()[route_id])
                self.assertEqual(transport.admitted_methods(route_id), transport.READ_METHODS)
                self.assertEqual(route.operator_identity, "linkedin")
                # Neither route carries a credential of any kind. The whole
                # claim this pair defends is that LinkedIn is readable without
                # one, so a credential here would contradict the finding.
                self.assertIsNone(transport.route_credential(route_id))


JOBS_REQUEST = adapters.AdapterRequest(step_id="s1-li", query="reliability engineer")

# findings.md §1 (LinkedIn): every field the jobs row records this route
# returning per card, named as the evidence names them rather than as the
# record spells them, so the check reads against the roster row.
LINKEDIN_JOBS_ROSTER_FIELDS = ("urn_id", "title", "company", "posted_date")


def read_linkedin(name):
    """Read one offline LinkedIn fixture."""

    return LINKEDIN_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def jobs_roster_row(record):
    """One job card's roster row, keyed by the names the evidence uses."""

    return {
        "urn_id": record.native_item_id,
        "title": record.title,
        "company": record.author,
        "posted_date": record.published_at,
    }


def jobs_page(fixture, status=200, request=None):
    """Run ``linkedin_jobs`` over one canned answer."""

    return adapter_page(
        linkedin_jobs,
        status,
        read_linkedin(fixture),
        content_type="text/html",
        request=JOBS_REQUEST if request is None else request,
    )


class LinkedInJobsPageTest(unittest.TestCase):
    """Criterion 1, K0 half: ten jobs a page, each carrying its whole roster row."""

    def setUp(self):
        self.page, self.opener = jobs_page("jobs_search_page.html")

    def test_one_page_carries_the_ten_jobs_the_evidence_measured(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 10)
        self.assertEqual(len(self.opener.opened), 1)

    def test_every_card_carries_every_field_its_roster_row_names(self):
        for record in self.page.records:
            with self.subTest(item=record.native_item_id):
                carried = jobs_roster_row(record)

                self.assertEqual(sorted(carried), sorted(LINKEDIN_JOBS_ROSTER_FIELDS))
                for name in LINKEDIN_JOBS_ROSTER_FIELDS:
                    self.assertTrue(carried[name], name)
                # The route reports a day and no time of day, so every record
                # from it says so and none of them says anything else.
                self.assertEqual(record.loss, linkedin_jobs.DESCRIPTOR.standing_loss)

    def test_a_record_names_the_posting_its_company_and_the_day_it_appeared(self):
        first = self.page.records[0]

        self.assertEqual(first.canonical_content_kind, "job_posting")
        self.assertEqual(first.native_item_id, "3971120001")
        # The address the card itself published, with its per-response tracking
        # parameters dropped and nothing else touched. Two reads of one posting
        # therefore normalize to one locator and group; and no adapter spells a
        # route's host, which is transport.py's alone.
        self.assertEqual(
            first.canonical_locator,
            "https://www.linkedin.com/jobs/view/"
            "staff-data-engineer-at-northwind-analytics-3971120001",
        )
        self.assertNotIn("refId", first.canonical_locator)
        self.assertEqual(first.title, "Staff Data Engineer")
        self.assertEqual(first.author, "Northwind Analytics")
        self.assertEqual(first.published_at, "2026-08-05T00:00:00Z")
        self.assertEqual(first.native_position, 0)
        self.assertEqual(first.engagement, ())

    def test_a_company_the_origin_pretty_printed_is_the_name_and_not_the_whitespace(self):
        self.assertEqual(self.page.records[2].author, "Harborline Freight")

    def test_the_posted_day_is_read_from_the_time_element_and_not_from_a_class(self):
        # Card 7 carries LinkedIn's listdate--new variant, which it puts on a
        # recent posting. A parser keyed to the class name would lose the date
        # the day a posting became new.
        self.assertEqual(self.page.records[6].published_at, "2026-08-09T00:00:00Z")

    def test_a_card_without_a_posted_date_is_marked_and_never_dated_from_the_read(self):
        page, _ = jobs_page("jobs_partial_card.html")
        complete, partial = page.records

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(complete.loss, linkedin_jobs.DESCRIPTOR.standing_loss)
        self.assertEqual(
            partial.loss, linkedin_jobs.DESCRIPTOR.standing_loss + ("field_omitted",)
        )
        # Absent, not derived: a posting dated from the moment it was found
        # would look exactly as fresh as the search that found it.
        self.assertEqual(partial.published_at, "")
        self.assertEqual(partial.native_item_id, "3971120012")

    def test_a_search_that_matched_nothing_is_empty_and_not_a_page_that_moved(self):
        # The container is there and holds no card, which is the origin saying
        # "no jobs" — a search past the last result, or a keyword nobody posted
        # against. Typing it as drift would send an operator hunting a markup
        # change every time a query came up short.
        page, _ = jobs_page("jobs_empty_list.html")

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn(linkedin_jobs.RESULTS_LIST_CLASS, " ".join(page.warnings))

    def test_markup_carrying_no_card_at_all_is_drift_and_not_an_empty_search(self):
        page, _ = jobs_page("jobs_reshaped_markup.html")
        warning = " ".join(page.warnings)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())
        # Names both declared markers, so an operator learns what was looked
        # for rather than only that nothing was found.
        self.assertIn(linkedin_jobs.RESULTS_LIST_CLASS, warning)
        self.assertIn(linkedin_jobs.JOB_URN_PREFIX, warning)

    def test_an_answer_with_no_markup_at_all_is_empty_and_not_a_page_that_moved(self):
        # Nothing arrived, so nothing changed shape. A body with no markup in
        # it is the route declining to send a list, which is the same fact as
        # an empty list and a different fact from markup that moved.
        page, _ = adapter_page(linkedin_jobs, 200, "   \n", content_type="text/html",
                               request=JOBS_REQUEST)

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())

    def test_the_origins_own_failure_stays_the_origins(self):
        page, _ = adapter_page(
            linkedin_jobs, 503, "<html><body>no</body></html>",
            content_type="text/html", request=JOBS_REQUEST,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("503", " ".join(page.warnings))

    def test_the_page_speaks_for_linkedin_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "linkedin_jobs")
        self.assertEqual(self.page.platform, "linkedin")
        self.assertEqual(self.page.native_identity_namespace, "linkedin")
        self.assertEqual(self.page.access_class, "K0")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE)

    def test_the_start_offset_is_the_callers_and_the_adapter_derives_none(self):
        # Row 4: `start=` pagination is the core's. The caller's cursor is
        # spent on the wire, and the page hands back no next offset — this
        # fragment states none, and inventing one from the count returned would
        # make the adapter the thing that decides there is another page.
        page, opener = jobs_page(
            "jobs_search_page.html",
            request=adapters.AdapterRequest(
                step_id="s1-li", query="reliability engineer", cursor="10"
            ),
        )

        self.assertIn("start=10", opener.opened[0].url)
        self.assertEqual(page.cursor_out, "")
        self.assertEqual(len(opener.opened), 1)

    def test_a_first_page_asks_for_no_offset_at_all(self):
        self.assertNotIn("start=", self.opener.opened[0].url)
        self.assertIn("keywords=reliability+engineer", self.opener.opened[0].url)


class LinkedInJobsDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metrics."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # findings.md §1 (LinkedIn): 0.7 s per request. Nothing on this route
        # was measured refusing, so burst and cooldown keep the conservative
        # defaults rather than a ceiling nobody observed.
        descriptor = linkedin_jobs.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 700)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE],
            runner.RouteBudget(min_interval_ms=700, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_neither_engagement_metric_because_the_route_reports_none(self):
        # A metric name is never inferred. With `comment_count_metric` unset a
        # snapshot named `comment_count` would be a missing comment count, and
        # this route reports no count of any kind.
        self.assertEqual(linkedin_jobs.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(linkedin_jobs.DESCRIPTOR.reply_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("linkedin_jobs", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("linkedin_jobs"), linkedin_jobs.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE: (
                    200,
                    read_linkedin("jobs_search_page.html"),
                    "text/html",
                )
            },
        )
        page = runner.call_adapter("linkedin_jobs", carrier, JOBS_REQUEST)

        self.assertEqual(len(page.records), 10)
        self.assertEqual(len(opener.opened), 1)


PROFILE_SLUG = "avery-lindqvist-8a41b207"
LINKEDIN_PROFILE_REQUEST = adapters.AdapterRequest(
    step_id="s1-li", target_ids=(PROFILE_SLUG,)
)

# findings.md §1 (LinkedIn): every field the profile row records the ld+json
# Person block carrying, named as the evidence names them.
LINKEDIN_PROFILE_ROSTER_FIELDS = (
    "name",
    "jobTitle",
    "addressLocality",
    "description",
    "worksFor",
    "alumniOf",
)


def profile_page(fixture, status=200, request=None):
    """Run ``linkedin_public`` over one canned answer."""

    return adapter_page(
        linkedin_public,
        status,
        read_linkedin(fixture),
        content_type="text/html",
        request=LINKEDIN_PROFILE_REQUEST if request is None else request,
    )


def profile_roster_row(record):
    """One profile's roster row exactly as a caller reads it off the record.

    Deliberately assembled from the record and never from the adapter's own
    parse: the claim is that the fields reach the value a caller keeps, and a
    helper that read the block again would be checking the parser twice.
    """

    repeated = {}
    for name, value in record.attributes:
        repeated.setdefault(name, []).append(value)
    return {
        "name": record.title,
        "jobTitle": repeated.get("jobTitle", []),
        "addressLocality": "".join(repeated.get("addressLocality", [])),
        "description": record.body,
        "worksFor": repeated.get("worksFor", []),
        "alumniOf": repeated.get("alumniOf", []),
    }


class LinkedInPublicProfileTest(unittest.TestCase):
    """Criterion 1, K2 half: the whole Person block out of a page anyone can read."""

    def setUp(self):
        self.page, self.opener = profile_page("profile_person.html")

    def test_one_page_carries_the_one_profile_this_route_serves(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(len(self.page.records), 1)
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_record_carries_every_field_its_roster_row_names(self):
        carried = profile_roster_row(self.page.records[0])

        self.assertEqual(sorted(carried), sorted(LINKEDIN_PROFILE_ROSTER_FIELDS))
        for name in LINKEDIN_PROFILE_ROSTER_FIELDS:
            self.assertTrue(carried[name], name)
        self.assertEqual(carried["name"], "Avery Lindqvist")
        # Repeated facts arrive repeated, in the order the block listed them.
        # Joining them into one string would invent a separator the origin
        # never sent and make two positions unreadable as two.
        self.assertEqual(
            carried["jobTitle"], ["Principal Reliability Engineer", "Board Advisor"]
        )
        self.assertEqual(
            carried["addressLocality"], "Gothenburg, Vastra Gotaland County, Sweden"
        )
        self.assertIn("distributed storage", carried["description"])
        self.assertEqual(carried["worksFor"], ["Northwind Analytics", "Kestrel Systems"])
        self.assertEqual(
            carried["alumniOf"],
            ["Chalmers University of Technology", "Lund University"],
        )
        self.assertEqual(self.page.records[0].loss, ())

    def test_the_record_names_the_profile_and_the_address_the_origin_published(self):
        record = self.page.records[0]

        self.assertEqual(record.canonical_content_kind, "profile")
        # Identity is the slug this run read, which is the route's own path
        # segment and LinkedIn's own public name for a member. The address is
        # the one the block published, so no adapter spells a route host.
        self.assertEqual(record.native_item_id, PROFILE_SLUG)
        self.assertEqual(record.author, PROFILE_SLUG)
        self.assertEqual(
            record.canonical_locator,
            "https://www.linkedin.com/in/avery-lindqvist-8a41b207",
        )
        # A profile page states no publication time, so the record states none
        # rather than borrowing the moment it was read.
        self.assertEqual(record.published_at, "")
        self.assertEqual(record.engagement, ())
        self.assertEqual(record.native_position, 0)

    def test_the_person_is_found_by_its_declared_type_and_never_by_position(self):
        # The page carries two ld+json scripts and the Person is in neither
        # first position: not the first script, and not the first node of the
        # graph inside it. A parser keyed to position would read a
        # BreadcrumbList and report a profile named "LinkedIn".
        self.assertEqual(self.page.records[0].title, "Avery Lindqvist")

    def test_a_profile_the_origin_populated_in_part_is_marked_and_never_filled(self):
        page, _ = profile_page(
            "profile_partial_person.html",
            request=adapters.AdapterRequest(
                step_id="s1-li", target_ids=("mira-okonkwo-4d90c113",)
            ),
        )
        carried = profile_roster_row(page.records[0])

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        # Marked, and absent rather than invented: no locality and no summary
        # at all, instead of an empty string that reads as "wrote nothing".
        self.assertEqual(carried["addressLocality"], "")
        self.assertEqual(carried["description"], "")
        self.assertEqual(carried["jobTitle"], [])
        self.assertEqual(carried["alumniOf"], [])
        self.assertEqual(carried["name"], "Mira Okonkwo")
        self.assertEqual(carried["worksFor"], ["Kestrel Systems"])

    def test_the_slug_is_read_from_the_target_or_from_the_query(self):
        for request in (
            adapters.AdapterRequest(step_id="s1-li", target_ids=(PROFILE_SLUG,)),
            adapters.AdapterRequest(step_id="s1-li", query=PROFILE_SLUG),
        ):
            with self.subTest(request=request):
                _, opener = profile_page("profile_person.html", request=request)

                self.assertTrue(
                    opener.opened[0].url.endswith("/" + PROFILE_SLUG), opener.opened[0].url
                )

    def test_the_page_speaks_for_linkedin_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "linkedin_public")
        self.assertEqual(self.page.platform, "linkedin")
        self.assertEqual(self.page.native_identity_namespace, "linkedin")
        self.assertEqual(self.page.access_class, "K2")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.LINKEDIN_PUBLIC_PROFILE_ROUTE)


class LinkedInPublicDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metrics."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # findings.md §1 (LinkedIn): 1.3 s per request. Nothing on this route
        # was measured refusing, so burst and cooldown keep the conservative
        # defaults rather than a ceiling nobody observed.
        descriptor = linkedin_public.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 1300)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.LINKEDIN_PUBLIC_PROFILE_ROUTE],
            runner.RouteBudget(min_interval_ms=1300, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_neither_engagement_metric_because_the_block_reports_none(self):
        self.assertEqual(linkedin_public.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(linkedin_public.DESCRIPTOR.reply_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("linkedin_public", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("linkedin_public"), linkedin_public.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_PUBLIC_PROFILE_ROUTE: (
                    200,
                    read_linkedin("profile_person.html"),
                    "text/html",
                )
            },
        )
        page = runner.call_adapter("linkedin_public", carrier, LINKEDIN_PROFILE_REQUEST)

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)


def profile_manifest():
    """One dispatch reading one public profile."""

    return schema.AcquisitionManifest(
        manifest_id="m-li",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-profile",
                kind="hydration",
                adapter_id="linkedin_public",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.linkedin.com/in/" + PROFILE_SLUG,
                        target_id=PROFILE_SLUG,
                    ),
                ),
                max_items=5,
            ),
        ),
    )


class NamedAttributeCarrierTest(unittest.TestCase):
    """The one protocol extension this pair needed, and the law it carries.

    Four of `linkedin_public`'s six roster fields are named string facts, three
    of them repeated, and no other record field means any of them. Forcing them
    into `community` or `title` would alias a field that means a subreddit on
    one adapter into meaning a city on another, which is the same error the
    descriptor's metric law forbids for engagement counts. So they travel under
    their own names, and nothing else about a record moves.
    """

    def _artifact(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_PUBLIC_PROFILE_ROUTE: (
                    200,
                    read_linkedin("profile_person.html"),
                    "text/html",
                )
            },
        )
        return runner.run_acquisition(profile_manifest(), carrier, clock=clock.monotonic)

    def test_a_repeated_named_fact_reaches_the_artifact_in_the_blocks_own_order(self):
        # The claim closes where a caller keeps it. A page-level assertion
        # would leave the artifact free to drop the whole family.
        artifact = self._artifact()
        carried = profile_roster_row(artifact.records[0])

        self.assertEqual(len(artifact.records), 1)
        self.assertEqual(
            carried["jobTitle"], ["Principal Reliability Engineer", "Board Advisor"]
        )
        self.assertEqual(carried["worksFor"], ["Northwind Analytics", "Kestrel Systems"])
        self.assertEqual(artifact.records[0].time_confidence, "unknown")
        self.assertEqual(artifact.records[0].access_class, "K2")

    def test_a_record_from_a_route_reporting_no_named_fact_carries_none(self):
        # Defaulted and additive: every adapter that reported nothing under a
        # name still reports nothing, and no existing record grew a field with
        # something in it.
        page, _ = adapter_page(
            x_syndication, 200, read_fixture("syndication_timeline.html")
        )

        self.assertEqual(page.records[0].attributes, ())

    def test_a_named_fact_that_is_not_a_string_is_refused_rather_than_coerced(self):
        # Same bar as an engagement snapshot: the exact value as reported, or
        # nothing. A number stringified here would be a fact this package made.
        native = adapters.NativeRecord(
            canonical_content_kind="profile",
            canonical_locator="https://example.test/x",
            attributes=(("jobTitle", 7),),
        )

        with self.assertRaises(normalize.NormalizeError):
            normalize.normalize_page(
                adapters.build_native_page(linkedin_public.DESCRIPTOR, (native,)),
                profile_manifest().steps[0],
                "artifact:m-li",
                "m-li",
            )


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
