"""Adapter suite: four platforms reach their measured capability, keyless.

Four platforms, and one shape of claim four times. Each has a way of failing
that looks exactly like having nothing to say, and each part of this suite
exists to keep those apart — for X a rotated identifier, for LinkedIn a page
whose structured block moved and beside it a page whose navigation chrome
merely looks like a wall, for YouTube a caption list withheld from a client
that cannot attest, and for Instagram a login page arriving where JSON was
asked for.

The claim the X half exists to defend is that a stale vendor identifier is
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

The claim the LinkedIn half exists to defend is that navigation chrome is not
an authwall. The superseded spec placed the whole platform outside the roster
on an assumed 999; measured, `linkedin.com/in/<slug>` answers 200 with a
complete `ld+json` Person block, and "Sign in to" and "Join now" sit in that
same page above the block and below it. An adapter that read those strings
would re-create exactly the false negative the measurement overturned. Its
counterweight is that a page which genuinely lost its block is `schema_drift`
and never a member with nothing to show — a `K2` route reads a shape the
vendor may rewrite without notice, and typed drift is the whole mitigation.
That pair is checked over its own case table and shown to be falsifiable by
three more wrong adapters, one per confusion, including one that types the
chrome as a refusal.

Two smaller claims hold it up. The capability is real: ten dated postings a
page with stable URNs, and a Person block whose every roster field reaches the
artifact. And the strings the ticket turns on are declared in the adapter and
read nowhere in it, which an AST scan states as a count of zero.

The claim the YouTube half exists to defend is that a caption list nobody was
served is never a video with no captions. Across five clients and three videos
`captionTracks` came back empty every time and playability degraded to
`UNPLAYABLE` after the first metadata call, and the evidence names the cause:
PoToken/BotGuard attestation. An adapter that read that as an absence would
assert something false about every video it ever touched, quietly, on a 200,
with title and view count and publish date looking perfectly healthy beside it.
The same half must not read "Sign in to confirm you're not a bot" as a
credential problem, which is the LinkedIn finding again at its sharpest — the
words are in the body, and only a status line decides. Three wrong adapters
beside the tree hold the oracle honest, including one that types every player
answer as withheld, without which the claim could be satisfied by never
distinguishing anything.

The claim the Instagram half exists to defend is the same one from the other
end: this route's origin serves a logged-out page saying "Log in" in plain
words, and at 200 that is a route which stopped answering in JSON, while the
same bytes at 401 are a refusal. Beside it, the roster row itself — a bio, a
follower count, and twelve posts each carrying its shortcode, the platform's
own timestamp, and two counts under the exact key paths the payload publishes
them at, because a name translated here would be a cross-platform vocabulary
this package invented.

Every test here runs offline against fixtures under `fixtures/x/`,
`fixtures/linkedin/`, `fixtures/youtube/` and `fixtures/instagram/`. Those
fixtures carry the shape and field set findings.md §1 records; the evidence
records no captured bodies, and this package may not reach the network to make
one, so what they prove is that this code reads that shape correctly.
Criterion 12's live smoke is what proves the shape.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, cache, normalize, runner, schema, transport
from super_research.adapters import instagram_public, linkedin_jobs, linkedin_public
from super_research.adapters import x_guest, x_syndication, youtube_innertube
from tests import helpers


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "x"
LINKEDIN_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "linkedin"
# T02's captive-portal body, read rather than copied: an adapter inherits
# interception typing from the protocol, and the proof has to be the same
# measured body the transport suite uses or it proves something else.
TRANSPORT_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "transport"
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


def load_adapter_fixture(name, directory=None):
    """Load one adapter written beside the tree, by path.

    These are not package modules: nothing in the package imports them and no
    discovery pattern matches them. They exist so the oracle below can be shown
    to reject a wrong result, without mutating the tree under test.
    """

    spec = importlib.util.spec_from_file_location(
        "adapter_fixture_" + name,
        (FIXTURE_DIR if directory is None else directory) / (name + ".py"),
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


SCHEMA_DRIFT = "schema_drift"

WRONG_LINKEDIN_ADAPTERS = (
    "chrome_as_authwall_adapter",
    "absent_block_as_empty_adapter",
    "every_page_as_drift_adapter",
)


def linkedin_chrome_cases():
    """The measured case table: a status, a body, and the loss its evidence names."""

    return tuple(json.loads(read_linkedin("authwall_chrome_cases.json"))["cases"])


def typed_profile_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: adapter_page(
            module,
            row["status"],
            read_linkedin(row["body_fixture"]),
            content_type="text/html",
            request=adapters.AdapterRequest(step_id="s1-li", target_ids=(row["slug"],)),
        )[0]
        for row in linkedin_chrome_cases()
    }


def names_read(path, name):
    """How many times one source reads a name, its own definition excluded.

    A constant a module declares and never reads is a statement that the module
    has seen the thing and does not act on it. That is exactly what
    ``NAVIGATION_CHROME`` is for, and a count is the only way to check it from
    outside — a string scan would count the module's own prose.

    Both ways of reaching it are counted: bare, as the declaring module would,
    and through its module, as anything else would. A scan that counted only
    the first would pass any module that imported the constant instead.
    """

    read = 0
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Name) and node.id == name:
            read += 1 if isinstance(node.ctx, ast.Load) else 0
        elif isinstance(node, ast.Attribute) and node.attr == name:
            read += 1
    return read


def assert_chrome_is_never_an_authwall(case, adapter_id, pages):
    """The row-2 and row-3 oracle: the chrome decides nothing, and drift is typed.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. Four confusions are called out by name, because each is a
    different wrong thing to believe. Chrome read as an authwall re-creates the
    999 assumption the measurement overturned and puts a keyless route back
    outside the roster. A populated block read as empty loses a profile the
    origin served. A missing block read as an authwall blames a credential
    nobody withheld, and read as an empty profile says a member has nothing on
    a page that never said so. And typing drift onto answers that carry no
    structural evidence sends an operator hunting a markup change that did not
    happen.
    """

    for row in linkedin_chrome_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if row["expected_outcome"] == "ok":
            if linkedin_public.AUTH_REQUIRED in loss:
                case.fail("navigation chrome was recorded as an authwall:" + detail)
            # Ordered most specific first: a good page typed as drift is also a
            # page with no records on it, and naming the cause beats naming the
            # symptom.
            if SCHEMA_DRIFT in loss:
                case.fail(
                    "a populated ld+json block was recorded as a page that changed"
                    " shape:" + detail
                )
            if not page.records:
                case.fail(
                    "a populated ld+json block was recorded as an empty profile:" + detail
                )
        elif row["expected_loss"] == SCHEMA_DRIFT:
            if linkedin_public.AUTH_REQUIRED in loss:
                case.fail("a missing ld+json block was recorded as an authwall:" + detail)
            if page.records or page.outcome != "failed":
                case.fail(
                    "a missing ld+json block was recorded as an empty profile:" + detail
                )
            if SCHEMA_DRIFT not in loss:
                case.fail("a missing ld+json block was not recorded as one:" + detail)
        elif SCHEMA_DRIFT in loss:
            case.fail(
                "an answer carrying no structural evidence was recorded as drift:" + detail
            )
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


class ChromeIsNotAnAuthwallTest(unittest.TestCase):
    """Criteria 2 and 3: this pair's spine, and the finding it exists to protect.

    The superseded spec placed LinkedIn entirely outside the roster on an
    assumed 999 authwall. Measured, ``linkedin.com/in/<slug>`` answers 200 with
    a complete Person block and the sign-in strings sit in that same page as
    navigation chrome. An adapter that reads them re-creates the false negative
    the evidence overturned; one that answers a missing block with silence
    loses the drift that a ``K2`` route is exposed to by construction.
    """

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_chrome_is_never_an_authwall(
            self, "linkedin_public", typed_profile_pages(linkedin_public)
        )

    def test_the_bodies_that_claim_to_carry_the_chrome_really_do(self):
        # Without this the whole table could be satisfied by fixtures that
        # quietly have no chrome in them, and the claim would be about nothing.
        carrying = 0
        for row in linkedin_chrome_cases():
            body = read_linkedin(row["body_fixture"]).lower()
            present = all(marker in body for marker in linkedin_public.NAVIGATION_CHROME)

            self.assertEqual(present, row["chrome_present"], row["body_fixture"])
            carrying += 1 if present else 0

        self.assertGreater(carrying, 1)

    def test_the_shipped_adapter_never_reads_the_chrome_it_names(self):
        # The structural half. The module declares the two strings so a reader
        # knows it has seen them, and reads the constant nowhere: no branch, no
        # filter, no warning. A count of zero is the statement.
        self.assertEqual(
            names_read(ADAPTER_DIR / "linkedin_public.py", "NAVIGATION_CHROME"), 0
        )

    def test_the_same_bytes_at_two_statuses_are_two_different_answers(self):
        # The sharpest form of the rule. One body, twice: at 200 it is a page
        # that changed shape, at 403 it is the origin refusing. Nothing in the
        # body moved, so nothing in the body decided.
        drifted, _ = profile_page("profile_chrome_only.html")
        refused, _ = profile_page("profile_chrome_only.html", status=403)

        self.assertEqual(drifted.loss, (SCHEMA_DRIFT,))
        self.assertEqual(refused.loss, (linkedin_public.AUTH_REQUIRED,))

    def test_a_refusal_carrying_no_chrome_at_all_still_fails(self):
        # The mirror of the first row: chrome does not make a refusal, and its
        # absence does not make an answer. Only the status did.
        page, _ = profile_page("profile_request_denied_999.html", status=999)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("999", " ".join(page.warnings))

    def test_a_reshaped_block_names_what_it_looked_for(self):
        page, _ = profile_page("profile_reshaped_graph.html")
        warning = " ".join(page.warnings)

        self.assertIn(linkedin_public.PERSON_TYPE, warning)
        self.assertIn(linkedin_public.NODE_TYPE_KEY, warning)

    def test_no_linkedin_route_returns_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. Both routes are keyless: the only way
        # `auth_required` can appear is the origin's own 401 or 403, never the
        # absence of something this package was supposed to have.
        for module, fixture, request in (
            (linkedin_public, "profile_person.html", LINKEDIN_PROFILE_REQUEST),
            (linkedin_jobs, "jobs_search_page.html", JOBS_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module,
                    200,
                    read_linkedin(fixture),
                    content_type="text/html",
                    request=request,
                )

                self.assertNotIn("auth_required", page.loss)
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(transport.route_admissions()[module.DESCRIPTOR.route_id])
                self.assertIsNone(transport.route_credential(module.DESCRIPTOR.route_id))


class ChromeOracleCanFailTest(unittest.TestCase):
    """Criterion 5: the oracle above rejects a wrong result, in every direction.

    All three adapters here are written beside the tree and loaded by path.
    Each is ``linkedin_public`` with exactly one branch replaced, which is what
    makes a rejection attributable to that branch and to nothing else. Nothing
    in the package produces them and nothing under test is mutated to obtain
    them.
    """

    def _assert_oracle_rejects(self, name, reason):
        wrong = load_adapter_fixture(name, directory=LINKEDIN_FIXTURE_DIR)

        with self.assertRaises(AssertionError) as caught:
            assert_chrome_is_never_an_authwall(self, name, typed_profile_pages(wrong))

        self.assertIn(reason, str(caught.exception))

    def test_an_adapter_that_reads_the_chrome_as_an_authwall_fails_the_oracle(self):
        # Row 5's named case: the strings the measurement called navigation
        # chrome are read as a refusal, so a keyless route with a complete
        # block on it comes back credentialed and LinkedIn drops out of the
        # roster again.
        self._assert_oracle_rejects(
            "chrome_as_authwall_adapter", "navigation chrome was recorded as an authwall"
        )

    def test_an_adapter_that_answers_a_missing_block_with_nothing_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "absent_block_as_empty_adapter",
            "a missing ld+json block was recorded as an empty profile",
        )

    def test_an_adapter_that_calls_every_page_drift_fails_the_oracle(self):
        # The opposite error. Without this side the oracle could be satisfied
        # by typing everything as drift, which would report a page that changed
        # shape every time a profile was read successfully.
        self._assert_oracle_rejects(
            "every_page_as_drift_adapter",
            "a populated ld+json block was recorded as a page that changed shape",
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_chrome_is_never_an_authwall(
            self, "linkedin_public", typed_profile_pages(linkedin_public)
        )

    def test_the_chrome_scan_can_fail(self):
        # Which is what makes the shipped adapter's count of zero worth
        # anything: a module beside the tree that does read the constant is
        # named by the same scan.
        self.assertGreater(
            names_read(
                LINKEDIN_FIXTURE_DIR / "chrome_as_authwall_adapter.py", "NAVIGATION_CHROME"
            ),
            0,
        )

    def test_nothing_in_the_package_can_reach_a_wrong_linkedin_adapter(self):
        named = [
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for name in WRONG_LINKEDIN_ADAPTERS
            if name in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(named, [])


class LinkedInOneCallOnePageTest(unittest.TestCase):
    """Criterion 4: one bounded call in, exactly one page out, whatever comes back."""

    def _every_case(self):
        for row in linkedin_chrome_cases():
            yield (
                "linkedin_public/" + row["case_name"],
                linkedin_public,
                row["status"],
                read_linkedin(row["body_fixture"]),
                adapters.AdapterRequest(step_id="s1-li", target_ids=(row["slug"],)),
            )
        jobs = (
            ("search_page", 200, "jobs_search_page.html"),
            ("empty_list", 200, "jobs_empty_list.html"),
            ("reshaped", 200, "jobs_reshaped_markup.html"),
            ("partial_card", 200, "jobs_partial_card.html"),
        )
        for name, status, fixture in jobs:
            yield (
                "linkedin_jobs/" + name,
                linkedin_jobs,
                status,
                read_linkedin(fixture),
                JOBS_REQUEST,
            )
        for status in (429, 503, 999):
            yield (
                "linkedin_jobs/http_{0}".format(status),
                linkedin_jobs,
                status,
                "<html><body>no</body></html>",
                JOBS_REQUEST,
            )

    def test_every_answer_costs_one_call_on_the_adapters_own_route(self):
        for name, module, status, body, request in self._every_case():
            with self.subTest(case=name):
                page, opener = adapter_page(
                    module, status, body, content_type="text/html", request=request
                )

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    [call.route_id for call in opener.opened], [module.DESCRIPTOR.route_id]
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertIsInstance(page, adapters.NativePage)

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("linkedin_jobs.py", "linkedin_jobs"),
            ("linkedin_public.py", "linkedin_public"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", (ADAPTER_DIR / module_name).read_text(encoding="utf-8")
                )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (linkedin_public, "profile_person.html", LINKEDIN_PROFILE_REQUEST),
            (linkedin_jobs, "jobs_search_page.html", JOBS_REQUEST),
        )

        for module, fixture, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock,
                    {module.DESCRIPTOR.route_id: (200, read_linkedin(fixture), "text/html")},
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing: `fetch_one_page`
        # reads the channel verdict ahead of any status test either adapter
        # runs, so a captive portal's 503 is `network_intercepted` and not a
        # LinkedIn authwall.
        portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
            encoding="utf-8"
        )

        for module, request in (
            (linkedin_public, LINKEDIN_PROFILE_REQUEST),
            (linkedin_jobs, JOBS_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module, 503, portal, content_type="text/html", request=request
                )

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")


class LinkedInRouteTtlTest(unittest.TestCase):
    """How long each LinkedIn route's answer may stand in for a fresh read.

    A TTL belongs to a route's own volatility, and `cache.py`'s default is
    deliberately short — a route nobody has measured is not one to trust for
    long. Both of these were measured, so both declare their own, and the proof
    is behavioral from both sides: a re-read inside the window that the default
    would have sent back to the origin, and one outside it that comes back.
    """

    def _paced(self, clock, route_id, body):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "text/html")}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return governor, opener

    def test_a_profile_reread_inside_the_window_is_answered_from_memory(self):
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.LINKEDIN_PUBLIC_PROFILE_ROUTE,
            read_linkedin("profile_person.html"),
        )

        first = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)
        clock.advance(600)
        held = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)
        clock.advance(400)
        expired = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read.
        self.assertEqual(held.observed_at, first.observed_at)
        self.assertEqual(len(held.records), 1)

    def test_the_route_serving_the_more_volatile_thing_holds_it_for_the_least_time(self):
        # A profile changes when a member edits it and its block carries no
        # counter, and it is the most expensive read in the roster per item —
        # 577 KB and 1.3 s. A jobs search changes as postings arrive and costs
        # 27 KB and 0.7 s, so holding it longer buys less and risks more.
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
            read_linkedin("jobs_search_page.html"),
        )

        linkedin_jobs.fetch_native_page(governor, JOBS_REQUEST)
        clock.advance(120)
        held = linkedin_jobs.fetch_native_page(governor, JOBS_REQUEST)
        clock.advance(240)
        expired = linkedin_jobs.fetch_native_page(governor, JOBS_REQUEST)

        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        self.assertLess(
            cache.ttl_seconds(transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE),
            cache.ttl_seconds(transport.LINKEDIN_PUBLIC_PROFILE_ROUTE),
        )

    def test_a_body_the_size_the_evidence_measured_is_served_through_and_never_held(self):
        # findings.md §1 measured this route at 577 KB, and the run cache holds
        # nothing over MAX_ENTRY_BYTES (512 KiB) — so a real profile page is
        # served through and the declared TTL never binds on it. The window
        # above is real, and it is real for a smaller page than the one the
        # evidence measured. Stated here rather than in prose so it cannot rot.
        clock = helpers.FakeClock()
        oversized = read_linkedin("profile_person.html") + "<!--{0}-->".format(
            "x" * cache.MAX_ENTRY_BYTES
        )
        governor, opener = self._paced(
            clock, transport.LINKEDIN_PUBLIC_PROFILE_ROUTE, oversized
        )

        first = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)
        clock.advance(1)
        second = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)

        self.assertGreater(len(oversized.encode("utf-8")), cache.MAX_ENTRY_BYTES)
        self.assertNotIn(cache.CACHE_HIT, second.loss)
        self.assertEqual(len(opener.opened), 2)
        # Served through, and still correct: the page is parsed both times.
        self.assertEqual(len(first.records), 1)
        self.assertEqual(len(second.records), 1)


def linkedin_manifest():
    """One dispatch reading LinkedIn through both of its routes."""

    return schema.AcquisitionManifest(
        manifest_id="m-li-pair",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-jobs",
                kind="discovery",
                adapter_id="linkedin_jobs",
                query="reliability engineer",
                max_items=25,
            ),
            schema.AcquisitionStep(
                step_id="s2-profile",
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


class LinkedInArtifactSeamTest(unittest.TestCase):
    """The widest seam: the record a caller keeps, after normalize has run.

    Every test above reads a ``NativePage``, which is an intermediate value.
    "LinkedIn reaches its measured capability" is a claim about the artifact,
    so it is closed here — including the part where the whole Person block
    survives normalization under the block's own names.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE: (
                    200,
                    read_linkedin("jobs_search_page.html"),
                    "text/html",
                ),
                transport.LINKEDIN_PUBLIC_PROFILE_ROUTE: (
                    200,
                    read_linkedin("profile_person.html"),
                    "text/html",
                ),
            },
        )
        self.artifact = runner.run_acquisition(
            linkedin_manifest(), carrier, clock=clock.monotonic
        )
        self.jobs = [
            record
            for record in self.artifact.records
            if record.canonical_content_kind == "job_posting"
        ]

    def test_the_artifact_holds_every_row_both_routes_returned(self):
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())
        self.assertEqual(len(self.artifact.records), 11)
        self.assertEqual([step.records_kept for step in self.artifact.steps], [10, 1])
        self.assertEqual(len(self.opener.opened), 2)

    def test_a_profile_record_keeps_its_whole_roster_row_where_a_caller_reads_it(self):
        profile = self.artifact.records[-1]
        carried = profile_roster_row(profile)

        for name in LINKEDIN_PROFILE_ROSTER_FIELDS:
            self.assertTrue(carried[name], name)
        self.assertEqual(profile.access_class, "K2")
        self.assertEqual(profile.platform, "linkedin")
        # The page states no publication time, so the record claims none and
        # says so rather than borrowing the moment it was read.
        self.assertEqual(profile.time_confidence, "unknown")
        self.assertEqual(profile.usable_basis_time, "")

    def test_a_job_record_says_both_what_it_knows_and_how_precisely(self):
        first = self.jobs[0]

        self.assertEqual(first.access_class, "K0")
        self.assertEqual(first.published_at, "2026-08-05T00:00:00Z")
        self.assertEqual(first.usable_basis_time, "2026-08-05T00:00:00Z")
        # LinkedIn's own date, so the day is authoritative — and the midnight
        # is this package's form for a day, which the record says out loud
        # rather than leaving a reader to assume a posting appeared at 00:00.
        self.assertEqual(first.time_confidence, "authoritative")
        self.assertEqual(first.loss, ("date_precision_only",))

    def test_one_platform_read_at_two_access_classes_stays_eleven_records(self):
        # wrong_merge_law rule 1: a strong identity is namespace, item id and
        # content kind together. Ten postings and one profile share a platform
        # and a namespace and nothing else, so nothing here may fold.
        multiples = [
            group for group in self.artifact.groups if len(group.member_record_ids) > 1
        ]

        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K0", "K2"]
        )
        self.assertEqual(len(self.artifact.groups), 11)
        self.assertEqual(multiples, [])
        self.assertEqual(
            sorted({group.key_kind for group in self.artifact.groups}), ["strong"]
        )

    def test_two_postings_from_one_company_are_two_records_and_never_one(self):
        # Three of these ten are Northwind Analytics. A grouping that keyed on
        # anything the cards share rather than on the posting's own id would
        # collapse them, and a caller would lose two open roles.
        northwind = [
            record for record in self.jobs if record.author == "Northwind Analytics"
        ]

        self.assertEqual(len(northwind), 3)
        self.assertEqual(len({record.record_id for record in northwind}), 3)
        self.assertEqual(len({record.canonical_locator for record in northwind}), 3)

    def test_a_route_reporting_no_count_ranks_on_nothing_it_did_not_report(self):
        # Neither descriptor declares a comment or reply metric, so the two
        # metric orders have no eligible snapshot to rank on and fall through
        # to time. That is the point of an unset metric name: the view still
        # answers, and it answers with what the route actually reported.
        by_metric = runner.order_records(
            self.jobs, "most_commented", self.artifact.as_of
        )
        by_time = runner.order_records(self.jobs, "newest", self.artifact.as_of)

        for record in self.jobs:
            self.assertIsNone(
                runner.eligible_snapshot(record, "comment_count", self.artifact.as_of)
            )
        self.assertEqual(
            [record.native_item_id for record in by_metric],
            [record.native_item_id for record in by_time],
        )

    def test_newest_orders_day_precision_postings_by_the_day_the_origin_reported(self):
        ranked = runner.order_records(self.jobs, "newest", self.artifact.as_of)

        self.assertEqual(
            [record.native_item_id for record in ranked],
            [
                "3971120007",
                "3971120001",
                "3971120002",
                "3971120003",
                "3971120004",
                "3971120005",
                "3971120006",
                "3971120008",
                "3971120009",
                "3971120010",
            ],
        )


YOUTUBE_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "youtube"
INSTAGRAM_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "instagram"

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

        # findings.md §1 (YouTube): `youtubei/v1/search` with the public web key
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

        # findings.md §1 (Instagram): `api/v1/users/web_profile_info/?username=`
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
                    route_id, {"query": "x", "video_id": "y", "context": "z"}
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

# findings.md §1 (Instagram): every field the roster row records this route
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


class InstagramAnswersWithNoProfileTest(unittest.TestCase):
    """The four ways this route answers with no profile, told apart.

    The one that matters is the login page. It arrives at HTTP 200 saying "Log
    in" in plain words, and reading that as a refusal is exactly the false
    negative the LinkedIn measurement overturned. Only a status line may make
    this route `auth_required`; a body may not, whatever it says.
    """

    def _typed(self, case_name):
        row = next(case for case in instagram_cases() if case["case_name"] == case_name)
        page, _ = instagram_page(
            row["body_fixture"],
            status=row["status"],
            request=adapters.AdapterRequest(step_id="s1-ig", target_ids=(row["username"],)),
        )
        return page, row

    def test_a_username_nobody_holds_is_empty_and_says_so(self):
        page, _ = self._typed("no_such_username_200")

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("nobody.holds.this.name", " ".join(page.warnings))

    def test_a_payload_whose_container_moved_is_drift_and_not_an_absent_profile(self):
        page, _ = self._typed("payload_container_moved_200")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())
        # Names what was looked for, so an operator learns the shape changed
        # rather than only that nothing came back.
        self.assertIn(
            ".".join(instagram_public.PROFILE_PATH), " ".join(page.warnings)
        )

    def test_a_login_page_at_two_hundred_is_not_read_as_a_refusal(self):
        page, _ = self._typed("login_page_at_200")

        self.assertEqual(page.loss, ("malformed_json",))
        self.assertNotIn(instagram_public.AUTH_REQUIRED, page.loss)

    def test_the_same_bytes_at_two_statuses_are_two_different_answers(self):
        # The sharpest form of the rule. One body, twice: at 200 it is a route
        # that stopped answering in JSON, at 401 it is the origin refusing.
        # Nothing in the body moved, so nothing in the body decided.
        at_two_hundred, _ = self._typed("login_page_at_200")
        refused, _ = self._typed("origin_refused_401")

        self.assertEqual(at_two_hundred.loss, ("malformed_json",))
        self.assertEqual(refused.loss, (instagram_public.AUTH_REQUIRED,))
        self.assertIn("401", " ".join(refused.warnings))

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        for row in instagram_cases():
            with self.subTest(case=row["case_name"]):
                page, _ = self._typed(row["case_name"])

                self.assertEqual(page.outcome, row["expected_outcome"])
                self.assertEqual(
                    tuple(page.loss),
                    (row["expected_loss"],) if row["expected_loss"] else (),
                )

    def test_the_route_returns_no_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. The route carries a vendor-published app
        # id, which is not a user credential and is never asked of anyone: the
        # only way `auth_required` appears is the origin's own status line.
        page, _ = instagram_page("web_profile_info.json")

        self.assertNotIn(instagram_public.AUTH_REQUIRED, page.loss)
        self.assertEqual(page.outcome, "ok")
        self.assertTrue(
            transport.route_admissions()[transport.INSTAGRAM_WEB_PROFILE_ROUTE]
        )


class InstagramDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metric."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # findings.md §1 (Instagram): 2.9 s per request, the slowest read in
        # the roster. Nothing here was measured refusing, so burst and cooldown
        # keep the conservative defaults rather than a ceiling nobody observed.
        descriptor = instagram_public.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 2900)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.INSTAGRAM_WEB_PROFILE_ROUTE],
            runner.RouteBudget(min_interval_ms=2900, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_the_comment_metric_it_reports_and_no_reply_metric(self):
        # Instagram reports a count of comments on a post and nothing named for
        # replies. Declaring the one under both names would make two of the
        # five views silently identical on a number reported once.
        self.assertEqual(
            instagram_public.DESCRIPTOR.comment_count_metric,
            instagram_public.COMMENT_METRIC,
        )
        self.assertEqual(instagram_public.DESCRIPTOR.reply_count_metric, "")

    def test_it_declares_no_rotating_identifier_because_it_depends_on_none(self):
        # The app id is a vendor-published constant, not a rotating one: it is
        # the same value every client sends and the evidence records it in
        # full. Declaring it volatile would attach a recovery procedure to
        # something that has not been observed to move.
        self.assertEqual(instagram_public.DESCRIPTOR.volatile_identifiers, ())

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("instagram_public", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("instagram_public"), instagram_public.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.INSTAGRAM_WEB_PROFILE_ROUTE: (
                    200,
                    read_instagram("web_profile_info.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter("instagram_public", carrier, INSTAGRAM_REQUEST)

        self.assertEqual(len(page.records), 13)
        self.assertEqual(len(opener.opened), 1)


YOUTUBE_VIDEO_ID = "dQw4w9WgXcQ"
YOUTUBE_SEARCH_TARGET = "search:local models"
YOUTUBE_COMMENT_CURSOR = "Eg0SC2RRdzR3OVdnWGNRGAYyJSIRIgtkUXc0dzlXZ1hjUTAA"

# findings.md §1 (YouTube): the roster row records a field set for `player` and
# names only the capability for the other two. These are the three the evidence
# enumerates, named as it names them.
YOUTUBE_PLAYER_ROSTER_FIELDS = ("title", "viewCount", "publishDate")


def read_youtube(name):
    """Read one offline YouTube fixture."""

    return YOUTUBE_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def youtube_cases():
    """The measured case table: a status, a body, and the loss its evidence names."""

    return tuple(json.loads(read_youtube("attestation_cases.json"))["cases"])


def youtube_request(target_id, cursor=""):
    return adapters.AdapterRequest(step_id="s1-yt", target_ids=(target_id,), cursor=cursor)


def youtube_page(fixture, status=200, target_id=None, cursor=""):
    """Run ``youtube_innertube`` over one canned answer for one named operation."""

    return adapter_page(
        youtube_innertube,
        status,
        read_youtube(fixture),
        content_type="application/json",
        request=youtube_request(
            "player:" + YOUTUBE_VIDEO_ID if target_id is None else target_id, cursor=cursor
        ),
    )


def attributes_of(record):
    """One record's named string facts, grouped under the names the route used."""

    named = {}
    for name, value in record.attributes:
        named.setdefault(name, []).append(value)
    return named


class InnerTubeSearchTest(unittest.TestCase):
    """Criterion 1, search: the platform's own results, keyless.

    The prior spec priced YouTube search behind an API key. Measured, one
    request under the web key youtube.com embeds in its own page source
    answers with the results themselves.
    """

    def setUp(self):
        self.page, self.opener = youtube_page(
            "search_results.json", target_id=YOUTUBE_SEARCH_TARGET
        )

    def test_one_page_carries_the_results_the_section_listed(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(len(self.page.records), 5)
        self.assertEqual(len(self.opener.opened), 1)

    def test_a_result_names_the_video_its_channel_and_the_address_youtube_published(self):
        first = self.page.records[0]

        self.assertEqual(first.canonical_content_kind, "video")
        self.assertEqual(first.native_item_id, YOUTUBE_VIDEO_ID)
        self.assertEqual(first.title, "Running a 70B locally on two consumer GPUs")
        self.assertEqual(first.author, "Harbourlight Optics")
        # The address the payload published, resolved against the origin that
        # published it. YouTube writes it relative, so it is resolved where
        # hosts are spelled rather than composed here.
        self.assertEqual(
            first.canonical_locator, "https://www.youtube.com/watch?v=" + YOUTUBE_VIDEO_ID
        )
        self.assertEqual(first.native_position, 0)

    def test_a_row_that_is_not_a_video_is_not_read_as_one(self):
        # The section carries a shelf between the results. A parser that took
        # every row would report a heading as a video.
        self.assertEqual(
            [record.canonical_content_kind for record in self.page.records],
            ["video"] * 5,
        )
        self.assertEqual(
            [record.native_position for record in self.page.records], [0, 1, 2, 3, 4]
        )

    def test_a_count_the_route_wrote_for_a_reader_is_carried_and_never_parsed(self):
        # "1,284,553 views" and "2 weeks ago" are strings YouTube formatted for
        # a person. Turning either into a number or an instant would be this
        # package inventing a fact: the separators are locale-shaped, "1.2M" is
        # lossy, and "2 weeks ago" is only an instant if you read a clock. So
        # they travel verbatim, under the route's own names, and the record
        # states no engagement and no publication time at all.
        first = self.page.records[0]
        named = attributes_of(first)

        self.assertEqual(named[youtube_innertube.VIEW_COUNT_TEXT_KEY], ["1,284,553 views"])
        self.assertEqual(named[youtube_innertube.PUBLISHED_TIME_TEXT_KEY], ["2 weeks ago"])
        self.assertEqual(first.engagement, ())
        self.assertEqual(first.published_at, "")

    def test_the_continuation_is_surfaced_for_the_core_and_never_followed(self):
        self.assertEqual(
            self.page.cursor_out, "EpcDEgxsb2NhbCBtb2RlbHMaggNTQlNDQVE"
        )
        self.assertEqual(len(self.opener.opened), 1)

    def test_a_result_the_payload_left_incomplete_is_marked_and_never_filled(self):
        page, _ = youtube_page(
            "search_partial_result.json", target_id=YOUTUBE_SEARCH_TARGET
        )
        complete, partial = page.records

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(complete.loss, ())
        self.assertEqual(partial.loss, ("field_omitted",))
        self.assertEqual(partial.author, "")
        self.assertEqual(attributes_of(partial), {})

    def test_a_row_the_payload_gave_no_video_id_is_not_a_result_at_all(self):
        # The third row of that fixture has a title and a channel and no id, so
        # it can be neither identified nor addressed. Keeping it would put a
        # record in the artifact that names nothing.
        page, _ = youtube_page(
            "search_partial_result.json", target_id=YOUTUBE_SEARCH_TARGET
        )

        self.assertEqual(len(page.records), 2)
        self.assertTrue(all(record.native_item_id for record in page.records))

    def test_the_query_is_read_from_the_target_or_from_the_step_that_searched(self):
        # A step naming a target is hydrating one; a step naming only a query
        # is searching. Neither is inferred from the argument's characters.
        for request in (
            adapters.AdapterRequest(step_id="s1-yt", target_ids=(YOUTUBE_SEARCH_TARGET,)),
            adapters.AdapterRequest(step_id="s1-yt", query="local models"),
        ):
            with self.subTest(request=request):
                page, opener = adapter_page(
                    youtube_innertube,
                    200,
                    read_youtube("search_results.json"),
                    content_type="application/json",
                    request=request,
                )

                self.assertTrue(opener.opened[0].url.endswith("/search"), opener.opened[0].url)
                self.assertEqual(
                    json.loads(opener.opened[0].body)["query"], "local models"
                )
                self.assertEqual(len(page.records), 5)


class InnerTubeCommentThreadTest(unittest.TestCase):
    """Criterion 1, next: comment threads, and the token that reaches them.

    The first call names a video and comes back with the watch page, whose
    comment section holds a token and no thread yet. The token is surfaced for
    the core to spend, exactly as a timeline cursor is: following it here would
    make one adapter call two reads.
    """

    def test_a_call_spending_the_token_carries_the_threads_it_returned(self):
        page, opener = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertEqual(len(page.records), 3)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(
            json.loads(opener.opened[0].body)["continuation"], YOUTUBE_COMMENT_CURSOR
        )

    def test_a_comment_names_itself_its_author_the_video_and_its_reply_count(self):
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )
        first = page.records[0]

        self.assertEqual(first.canonical_content_kind, "comment")
        self.assertEqual(first.native_item_id, "UgxK1rTn9pQwLmXaZ4h4AaABAg")
        self.assertEqual(first.native_parent_id, YOUTUBE_VIDEO_ID)
        self.assertEqual(first.author, "@northsea.dev")
        # The runs are one text the route split at its own formatting, so they
        # join back into the comment rather than into a list of fragments.
        self.assertEqual(
            first.body,
            "The two settings were n_batch and rope scaling, not the quantisation.",
        )
        self.assertEqual(dict(first.engagement), {youtube_innertube.REPLY_COUNT_METRIC: 14})
        self.assertEqual(first.native_position, 0)

    def test_a_vote_count_the_route_abbreviated_is_carried_and_never_parsed(self):
        # "1.2K" is not a number this route reported; it is a number it
        # rounded for a reader. Reading 1200 off it would be a count nobody
        # published, and the record would rank against exact ones.
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )
        named = attributes_of(page.records[0])

        self.assertEqual(named[youtube_innertube.VOTE_COUNT_TEXT_KEY], ["1.2K"])
        self.assertEqual(named[youtube_innertube.PUBLISHED_TIME_TEXT_KEY], ["3 days ago"])
        self.assertNotIn(
            youtube_innertube.VOTE_COUNT_TEXT_KEY, dict(page.records[0].engagement)
        )

    def test_a_comment_carries_no_publication_time_because_the_route_states_none(self):
        # "3 days ago" is an interval from a moment this package did not
        # observe. Turning it into an instant needs a wall clock, and a record
        # dated from the read would look exactly as fresh as the read.
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        for record in page.records:
            with self.subTest(item=record.native_item_id):
                self.assertEqual(record.published_at, "")

    def test_a_comment_carries_no_address_because_the_payload_publishes_none(self):
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual([record.canonical_locator for record in page.records], [""] * 3)

    def test_the_next_continuation_is_surfaced_for_the_core(self):
        page, _ = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(page.cursor_out, YOUTUBE_COMMENT_CURSOR)

    def test_the_first_call_names_the_video_and_comes_back_holding_only_the_token(self):
        page, opener = youtube_page(
            "next_watch_page.json", target_id="next:" + YOUTUBE_VIDEO_ID
        )

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertEqual(page.cursor_out, YOUTUBE_COMMENT_CURSOR)
        self.assertIn("comment", " ".join(page.warnings))
        self.assertEqual(json.loads(opener.opened[0].body)["videoId"], YOUTUBE_VIDEO_ID)
        self.assertEqual(len(opener.opened), 1)


class InnerTubePlayerTest(unittest.TestCase):
    """Criterion 1, player: the three fields the evidence measured, and no fourth."""

    def setUp(self):
        self.page, self.opener = youtube_page("player_metadata.json")

    def test_one_page_carries_the_one_video_this_operation_asks_for(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 1)
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_record_carries_every_field_its_roster_row_names(self):
        record = self.page.records[0]
        carried = {
            "title": record.title,
            "viewCount": dict(record.engagement).get(youtube_innertube.VIEW_COUNT_METRIC),
            "publishDate": record.published_at,
        }

        self.assertEqual(sorted(carried), sorted(YOUTUBE_PLAYER_ROSTER_FIELDS))
        for name in YOUTUBE_PLAYER_ROSTER_FIELDS:
            self.assertTrue(carried[name], name)
        self.assertEqual(carried["title"], "Running a 70B locally on two consumer GPUs")
        # An exact count the route published as digits, read as the integer it
        # is. "1,284,553 views" on the search row is a different thing and
        # stays a string.
        self.assertEqual(carried["viewCount"], 1284553)
        self.assertIsInstance(carried["viewCount"], int)
        self.assertEqual(carried["publishDate"], "2026-07-26T00:00:00Z")

    def test_a_video_nobody_has_watched_reported_a_count_and_it_is_zero(self):
        # The other direction of `field_omitted`, and the whole reason the mark
        # exists: the route reported the view count and it is zero. Marking
        # that omitted would say the payload was short when it was complete.
        # The same answer carries a full instant rather than a bare day, so
        # this record claims no precision it does not have and says nothing
        # about precision it does.
        page, _ = youtube_page("player_zero_views.json", target_id="player:Zk5xD1nQ9pL")
        record = page.records[0]

        self.assertEqual(dict(record.engagement), {youtube_innertube.VIEW_COUNT_METRIC: 0})
        self.assertEqual(record.published_at, "2026-08-10T08:55:00Z")
        self.assertEqual(record.loss, (youtube_innertube.ATTESTATION_REQUIRED,))

    def test_a_day_the_route_reported_is_a_day_and_the_record_says_so(self):
        # The route states a date and the artifact's instant carries seconds,
        # so the record reads midnight UTC and carries the precision it has
        # rather than letting a reader assume a video appeared at 00:00.
        record = self.page.records[0]

        self.assertIn("date_precision_only", record.loss)

    def test_the_record_names_the_video_and_the_address_the_payload_published(self):
        record = self.page.records[0]

        self.assertEqual(record.canonical_content_kind, "video")
        self.assertEqual(record.native_item_id, YOUTUBE_VIDEO_ID)
        self.assertEqual(record.author, "Harbourlight Optics")
        # The player payload publishes one address for the video and it is
        # already absolute, so it is carried as published rather than rebuilt.
        self.assertEqual(
            record.canonical_locator, "https://www.youtube.com/embed/" + YOUTUBE_VIDEO_ID
        )
        self.assertIn("benchmarks", record.body)

    def test_the_page_speaks_for_youtube_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "youtube_innertube")
        self.assertEqual(self.page.platform, "youtube")
        self.assertEqual(self.page.native_identity_namespace, "youtube")
        self.assertEqual(self.page.access_class, "K1")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.YOUTUBE_INNERTUBE_ROUTE)

    def test_a_bare_target_id_names_a_video_and_never_a_guess_at_its_shape(self):
        _, opener = youtube_page("player_metadata.json", target_id=YOUTUBE_VIDEO_ID)

        self.assertTrue(opener.opened[0].url.endswith("/player"), opener.opened[0].url)
        self.assertEqual(json.loads(opener.opened[0].body)["videoId"], YOUTUBE_VIDEO_ID)


class InnerTubeDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads, and the identifier that rotates under it."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # findings.md §1 (YouTube): 1.4 s for search, which is the roster row's
        # declared ceiling. `next` at 2.2 s and `player` at 0.3 s are those
        # operations' latencies and not second ceilings: one route, one budget.
        descriptor = youtube_innertube.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 1400)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.YOUTUBE_INNERTUBE_ROUTE],
            runner.RouteBudget(min_interval_ms=1400, burst=1, cooldown_ms=60000),
        )

    def test_the_client_version_is_declared_rotating_with_a_way_back_to_a_current_one(self):
        declared = youtube_innertube.DESCRIPTOR.volatile_identifiers

        self.assertEqual(len(declared), 1)
        self.assertIn(youtube_innertube.CLIENT_VERSION, declared[0].name)
        self.assertIn(youtube_innertube.CLIENT_NAME, declared[0].name)
        # The procedure travels with the identifier rather than living
        # somewhere a reader would have to already know to look.
        recovery = declared[0].recovery
        self.assertIn("ytcfg", recovery)
        self.assertIn("INNERTUBE_CLIENT_VERSION", recovery)

    def test_the_client_version_goes_out_in_the_body_the_route_shapes(self):
        _, opener = youtube_page("player_metadata.json")
        client = json.loads(opener.opened[0].body)["context"]["client"]

        self.assertEqual(client["clientName"], youtube_innertube.CLIENT_NAME)
        self.assertEqual(client["clientVersion"], youtube_innertube.CLIENT_VERSION)

    def test_it_declares_the_reply_metric_it_reports_and_no_comment_metric(self):
        # A comment carries a count of its replies; nothing in these three
        # operations reports a count of comments on a video. Declaring the one
        # under both names would make two of the five views identical.
        self.assertEqual(
            youtube_innertube.DESCRIPTOR.reply_count_metric,
            youtube_innertube.REPLY_COUNT_METRIC,
        )
        self.assertEqual(youtube_innertube.DESCRIPTOR.comment_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("youtube_innertube", runner.ADAPTER_IDS)
        self.assertIs(
            runner.descriptor_for("youtube_innertube"), youtube_innertube.DESCRIPTOR
        )

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_INNERTUBE_ROUTE: (
                    200,
                    read_youtube("player_metadata.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter(
            "youtube_innertube", carrier, youtube_request("player:" + YOUTUBE_VIDEO_ID)
        )

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)


WRONG_YOUTUBE_ADAPTERS = (
    "empty_captions_as_absence_adapter",
    "stale_version_as_empty_adapter",
    "every_player_as_attested_adapter",
)


def typed_youtube_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: adapter_page(
            module,
            row["status"],
            read_youtube(row["body_fixture"]),
            content_type="application/json",
            request=youtube_request(row["target_id"], cursor=row["cursor"]),
        )[0]
        for row in youtube_cases()
    }


def assert_captions_are_never_reported_absent(case, adapter_id, pages):
    """Row 3's oracle: a withheld caption list is named, and named as itself.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. Four confusions are called out by name, because each is a
    different wrong thing to believe.

    A player answer listing no caption track, read as a video with no captions,
    asserts something false about the video rather than about the read — and it
    is the one findings.md §1 measured on every client and every video, so it
    is the answer this adapter will meet every single time.

    A player answer that did list tracks, read as withheld, is the mirror: it
    would make the claim above satisfiable by typing every player answer the
    same way, and this package would report attestation on a video it could
    have read.

    A request the origin refused, read as an empty result, turns a scheduled
    client-version rotation into silence nobody can attribute; read as an
    authorization failure, it calls a keyless route credentialed.
    """

    for row in youtube_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if row["captions_withheld"] is True:
            if youtube_innertube.ATTESTATION_REQUIRED not in loss:
                case.fail(
                    "a player answer listing no caption track was recorded as a"
                    " video with no captions:" + detail
                )
        elif row["captions_withheld"] is False:
            if youtube_innertube.ATTESTATION_REQUIRED in loss:
                case.fail(
                    "a player answer that did list caption tracks was recorded as"
                    " withheld:" + detail
                )
        if row["expected_loss"] == youtube_innertube.STALE_IDENTIFIER:
            if not page.records and page.outcome != "failed":
                case.fail("a refused request was recorded as an empty success:" + detail)
            if youtube_innertube.AUTH_REQUIRED in loss:
                case.fail(
                    "a refused request was recorded as an authorization failure:" + detail
                )
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


class AttestationIsNotAnAbsenceTest(unittest.TestCase):
    """Criteria 2 and 3: this half's spine, and the false capability it prevents.

    Across five clients and three videos, ``captionTracks`` came back empty
    every time and playability degraded to ``UNPLAYABLE`` after the first
    metadata call. That is attestation, not a property of the videos. An
    adapter that reported it as "no captions" would assert something false
    about every video it ever read, and it would do so quietly, on a 200, with
    the rest of the metadata looking perfectly healthy beside it.
    """

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_captions_are_never_reported_absent(
            self, "youtube_innertube", typed_youtube_pages(youtube_innertube)
        )

    def test_a_withheld_caption_list_names_where_it_looked_and_why_it_is_empty(self):
        page, _ = youtube_page("player_metadata.json")
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, (youtube_innertube.ATTESTATION_REQUIRED,))
        self.assertEqual(page.outcome, "ok")
        self.assertIn(".".join(youtube_innertube.CAPTION_TRACKS_PATH), warning)
        self.assertIn("attestation", warning)
        # The record a caller keeps carries it too: a caller reading one record
        # would otherwise have to correlate back to a step to learn that the
        # captions were withheld rather than absent.
        self.assertIn(
            youtube_innertube.ATTESTATION_REQUIRED, page.records[0].loss
        )

    def test_a_video_that_does_list_tracks_is_not_reported_as_withheld(self):
        # Without this the claim above is satisfiable by typing every player
        # answer the same way, and the oracle would be checking nothing.
        page, _ = youtube_page(
            "player_with_caption_tracks.json", target_id="player:7pQm3nXkT2a"
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertNotIn(youtube_innertube.ATTESTATION_REQUIRED, page.records[0].loss)

    def test_an_unplayable_answer_is_attestation_and_never_a_credential_problem(self):
        page, _ = youtube_page("player_unplayable.json")
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, (youtube_innertube.ATTESTATION_REQUIRED,))
        self.assertEqual(page.outcome, "failed")
        self.assertNotIn(youtube_innertube.AUTH_REQUIRED, page.loss)
        self.assertIn("UNPLAYABLE", warning)
        self.assertIn("bot", warning)

    def test_a_degraded_answer_is_not_mined_for_the_metadata_it_still_carries(self):
        # That fixture carries a complete videoDetails. The origin said it was
        # not serving this client, so reporting its contents as a successful
        # read would make a degraded response indistinguishable from a healthy
        # one at exactly the moment a caller needs to tell them apart.
        page, _ = youtube_page("player_unplayable.json")

        self.assertEqual(page.records, ())
        self.assertIn(
            "Running a 70B locally", read_youtube("player_unplayable.json")
        )

    def test_a_refused_request_names_the_rotating_part_and_the_way_back(self):
        page, opener = youtube_page("innertube_invalid_argument.json", status=400)
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, (youtube_innertube.STALE_IDENTIFIER,))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn(youtube_innertube.CLIENT_VERSION, warning)
        self.assertIn("ytcfg", warning)
        # And it cost one call: a refused request is an answer, not a reason to
        # look somewhere else.
        self.assertEqual(len(opener.opened), 1)

    def test_the_same_bytes_at_two_statuses_are_two_different_answers(self):
        refused_request, _ = youtube_page("innertube_invalid_argument.json", status=400)
        refused_read, _ = youtube_page("innertube_invalid_argument.json", status=403)

        self.assertEqual(refused_request.loss, (youtube_innertube.STALE_IDENTIFIER,))
        self.assertEqual(refused_read.loss, (youtube_innertube.AUTH_REQUIRED,))

    def test_a_results_section_that_moved_is_drift_and_not_a_search_with_no_matches(self):
        page, _ = youtube_page("search_reshaped.json", target_id=YOUTUBE_SEARCH_TARGET)
        warning = " ".join(page.warnings)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertIn(".".join(youtube_innertube.SEARCH_RESULTS_PATH), warning)

    def test_the_shipped_adapter_never_reads_the_field_a_caption_fetcher_needs(self):
        # Caption retrieval is deferred by the spec with a named reopen
        # condition. The module declares the field a fetcher would need so a
        # reader knows it has seen it, and reads it nowhere: a count of zero is
        # the statement, and `test_the_caption_scan_can_fail` is what makes the
        # count worth anything.
        source = ADAPTER_DIR / "youtube_innertube.py"

        self.assertEqual(names_read(source, "CAPTION_FETCH_FIELD"), 0)
        self.assertIn("baseUrl", source.read_text(encoding="utf-8"))

    def test_no_youtube_route_returns_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. The web key is a vendor-published constant,
        # not a user credential: the only way `auth_required` appears is the
        # origin's own 401 or 403.
        for fixture, target in (
            ("search_results.json", YOUTUBE_SEARCH_TARGET),
            ("player_metadata.json", "player:" + YOUTUBE_VIDEO_ID),
        ):
            with self.subTest(fixture=fixture):
                page, _ = youtube_page(fixture, target_id=target)

                self.assertNotIn(youtube_innertube.AUTH_REQUIRED, page.loss)
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(
                    transport.route_admissions()[transport.YOUTUBE_INNERTUBE_ROUTE]
                )


class AttestationOracleCanFailTest(unittest.TestCase):
    """Criterion 6: the oracle above rejects a wrong result, in every direction.

    All three adapters here are written beside the tree and loaded by path.
    Each runs the shipped adapter and then draws exactly one wrong conclusion
    from what it returned, which is what makes a rejection attributable to that
    conclusion and to nothing else. Nothing in the package produces them and
    nothing under test is mutated to obtain them.
    """

    def _assert_oracle_rejects(self, name, reason):
        wrong = load_adapter_fixture(name, directory=YOUTUBE_FIXTURE_DIR)

        with self.assertRaises(AssertionError) as caught:
            assert_captions_are_never_reported_absent(
                self, name, typed_youtube_pages(wrong)
            )

        self.assertIn(reason, str(caught.exception))

    def test_an_adapter_that_calls_a_withheld_caption_list_an_absence_fails_the_oracle(self):
        # Row 6's named case: the empty list becomes a successful answer
        # asserting that the video has no captions, which is a claim about the
        # video that this package is in no position to make.
        self._assert_oracle_rejects(
            "empty_captions_as_absence_adapter",
            "a player answer listing no caption track was recorded as a video with"
            " no captions",
        )

    def test_an_adapter_that_calls_every_player_answer_attested_fails_the_oracle(self):
        # The opposite error. Without this side the oracle could be satisfied
        # by typing every player answer as withheld, and the package would
        # report attestation on a video it could have read.
        self._assert_oracle_rejects(
            "every_player_as_attested_adapter",
            "a player answer that did list caption tracks was recorded as withheld",
        )

    def test_an_adapter_that_answers_a_refused_request_with_nothing_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "stale_version_as_empty_adapter",
            "a refused request was recorded as an empty success",
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_captions_are_never_reported_absent(
            self, "youtube_innertube", typed_youtube_pages(youtube_innertube)
        )

    def test_the_caption_scan_can_fail(self):
        # Which is what makes the shipped adapter's count of zero worth
        # anything: a module beside the tree that does read the constant is
        # named by the same scan.
        self.assertGreater(
            names_read(
                YOUTUBE_FIXTURE_DIR / "empty_captions_as_absence_adapter.py",
                "CAPTION_FETCH_FIELD",
            ),
            0,
        )

    def test_nothing_in_the_package_can_reach_a_wrong_youtube_adapter(self):
        named = [
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for name in WRONG_YOUTUBE_ADAPTERS
            if name in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(named, [])


class YoutubeInstagramOneCallOnePageTest(unittest.TestCase):
    """Criterion 5: one bounded call in, exactly one page out, whatever comes back."""

    def _every_case(self):
        for row in youtube_cases():
            yield (
                "youtube_innertube/" + row["case_name"],
                youtube_innertube,
                row["status"],
                read_youtube(row["body_fixture"]),
                youtube_request(row["target_id"], cursor=row["cursor"]),
            )
        for row in instagram_cases():
            yield (
                "instagram_public/" + row["case_name"],
                instagram_public,
                row["status"],
                read_instagram(row["body_fixture"]),
                adapters.AdapterRequest(step_id="s1-ig", target_ids=(row["username"],)),
            )
        for status in (404, 429, 500, 503):
            yield (
                "youtube_innertube/http_{0}".format(status),
                youtube_innertube,
                status,
                '{"error": "no"}',
                youtube_request("player:" + YOUTUBE_VIDEO_ID),
            )
            yield (
                "instagram_public/http_{0}".format(status),
                instagram_public,
                status,
                '{"error": "no"}',
                INSTAGRAM_REQUEST,
            )

    def test_every_answer_costs_one_call_on_the_adapters_own_route(self):
        for name, module, status, body, request in self._every_case():
            with self.subTest(case=name):
                page, opener = adapter_page(
                    module, status, body, content_type="application/json", request=request
                )

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    [call.route_id for call in opener.opened], [module.DESCRIPTOR.route_id]
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertIsInstance(page, adapters.NativePage)

    def test_a_continuation_the_core_hands_back_is_spent_on_the_next_single_call(self):
        page, opener = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertTrue(page.cursor_out)

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("youtube_innertube.py", "youtube_innertube"),
            ("instagram_public.py", "instagram_public"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", (ADAPTER_DIR / module_name).read_text(encoding="utf-8")
                )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (youtube_innertube, "player_metadata.json", read_youtube,
             youtube_request("player:" + YOUTUBE_VIDEO_ID)),
            (instagram_public, "web_profile_info.json", read_instagram, INSTAGRAM_REQUEST),
        )

        for module, fixture, reader, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock,
                    {module.DESCRIPTOR.route_id: (200, reader(fixture), "application/json")},
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing: `fetch_one_page`
        # reads the channel verdict ahead of any status test either adapter
        # runs, so a captive portal's 503 is `network_intercepted` and never a
        # YouTube attestation or an Instagram refusal.
        portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
            encoding="utf-8"
        )

        for module, request in (
            (youtube_innertube, youtube_request("player:" + YOUTUBE_VIDEO_ID)),
            (instagram_public, INSTAGRAM_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module, 503, portal, content_type="text/html", request=request
                )

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        for module, request in (
            (youtube_innertube, youtube_request("player:" + YOUTUBE_VIDEO_ID)),
            (instagram_public, INSTAGRAM_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = adapter_page(
                    module,
                    transport.RATE_LIMITED_STATUS,
                    "slow down",
                    content_type="text/plain",
                    request=request,
                )

                self.assertEqual(page.loss, (transport.RATE_LIMITED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(len(opener.opened), 1)


# findings.md §1 (Instagram): 455 KB per answer. Held against `MAX_ENTRY_BYTES`
# below, because whether a route's declared window can ever bind depends on it.
MEASURED_INSTAGRAM_BYTES = 455 * 1024


class YoutubeInstagramRouteTtlTest(unittest.TestCase):
    """How long each route's answer may stand in for a fresh read.

    One of these two declares a window and one cannot have one, and the
    difference is not a preference. A TTL belongs to a route's own volatility,
    and `cache.py`'s default is deliberately short — a route nobody has
    measured is not one to trust for long — so a declared window is proven from
    both sides here: a re-read inside it that the default would have sent back
    to the origin, and one outside it that comes back.
    """

    def _paced(self, clock, route_id, body):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "application/json")}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return governor, opener

    def test_a_profile_reread_inside_the_window_is_answered_from_memory(self):
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.INSTAGRAM_WEB_PROFILE_ROUTE,
            read_instagram("web_profile_info.json"),
        )

        first = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)
        clock.advance(120)
        held = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)
        clock.advance(240)
        expired = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        # Two minutes, which the inherited default would have sent back to the
        # origin at a cost of 2.9 s — the slowest read in the roster.
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read.
        self.assertEqual(held.observed_at, first.observed_at)
        self.assertEqual(len(held.records), 13)

    def test_the_route_carrying_counts_holds_them_for_less_time_than_a_block_with_none(self):
        # A profile page's ld+json block carries no counter at all and changes
        # when a member edits it, so LinkedIn's window is the roster's longest.
        # This payload carries a follower count and twelve pairs of like and
        # comment counts, all of which move while nobody edits anything, so it
        # cannot hold them that long however expensive the read is.
        self.assertLess(
            cache.ttl_seconds(transport.INSTAGRAM_WEB_PROFILE_ROUTE),
            cache.ttl_seconds(transport.LINKEDIN_PUBLIC_PROFILE_ROUTE),
        )
        self.assertGreater(
            cache.ttl_seconds(transport.INSTAGRAM_WEB_PROFILE_ROUTE),
            cache.DEFAULT_TTL_SECONDS,
        )

    def test_a_body_the_size_the_evidence_measured_is_held_rather_than_served_through(self):
        # The mirror of the LinkedIn profile route, and the reason that check
        # exists: at 577 KB that one exceeds `MAX_ENTRY_BYTES` and its window
        # never binds. At 455 KB this one fits, so the window above is real at
        # the size the evidence actually measured — with 57 KB of headroom, and
        # not a byte more.
        clock = helpers.FakeClock()
        payload = read_instagram("web_profile_info.json")
        measured = payload + " " * (MEASURED_INSTAGRAM_BYTES - len(payload.encode("utf-8")))
        governor, opener = self._paced(
            clock, transport.INSTAGRAM_WEB_PROFILE_ROUTE, measured
        )

        first = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)
        clock.advance(60)
        held = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)

        self.assertEqual(len(measured.encode("utf-8")), MEASURED_INSTAGRAM_BYTES)
        self.assertLess(MEASURED_INSTAGRAM_BYTES, cache.MAX_ENTRY_BYTES)
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(len(first.records), 13)
        self.assertEqual(len(held.records), 13)

    def test_an_innertube_answer_is_never_held_because_the_read_is_not_a_get(self):
        # The InnerTube route declares no window, and the reason is structural
        # rather than a judgment about volatility: `cache.cacheable` holds only
        # what came back from a read method, and this route asks its question
        # in a POST body. A second identical read one second later still
        # reaches the origin, so no window it could declare would ever bind.
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock, transport.YOUTUBE_INNERTUBE_ROUTE, read_youtube("player_metadata.json")
        )
        request = youtube_request("player:" + YOUTUBE_VIDEO_ID)

        first = youtube_innertube.fetch_native_page(governor, request)
        clock.advance(1)
        second = youtube_innertube.fetch_native_page(governor, request)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertNotIn(cache.CACHE_HIT, second.loss)
        self.assertEqual(len(opener.opened), 2)
        self.assertNotIn(
            transport.route_constant(transport.YOUTUBE_INNERTUBE_ROUTE).method,
            transport.READ_METHODS,
        )
        self.assertNotIn(transport.YOUTUBE_INNERTUBE_ROUTE, cache.ROUTE_TTL_SECONDS)

    def test_two_of_the_three_innertube_answers_are_too_large_to_hold_anyway(self):
        # And the window would not bind even if the verb changed: findings.md
        # §1 measured search at 2.27 MB and next at 1.12 MB against a 512 KiB
        # entry cap, so only the 21 KB player answer could ever be held.
        for measured_bytes in (2270 * 1024, 1120 * 1024):
            with self.subTest(body_bytes=measured_bytes):
                self.assertGreater(measured_bytes, cache.MAX_ENTRY_BYTES)
        self.assertLess(21 * 1024, cache.MAX_ENTRY_BYTES)


class KeylessCredentialTest(unittest.TestCase):
    """Criterion 4: the two K1 credentials live in one module and reach no record.

    Both are vendor-published client credentials rather than user secrets —
    the key youtube.com embeds in its own page source, and the app id
    Instagram's own web client sends — so the question is not whether they are
    kept safe but whether they stay route constants. A credential that reached
    a manifest or an artifact would make a keyless route look credentialed to
    everything downstream, which is the same false capability this pair's
    other checks defend from the opposite direction.
    """

    def _values(self):
        return (
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.YOUTUBE_INNERTUBE_WEB_KEY].value,
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.INSTAGRAM_WEB_APP_ID].value,
        )

    def test_neither_credential_is_spelled_in_any_package_module_but_transport(self):
        named = sorted(
            (path.name, value)
            for path in PACKAGE_DIR.rglob("*.py")
            if path.name != "transport.py"
            for value in self._values()
            if value in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])

    def test_neither_credential_reaches_an_artifact_either_route_produced(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_INNERTUBE_ROUTE: [
                    (200, read_youtube("search_results.json"), "application/json"),
                    (200, read_youtube("player_metadata.json"), "application/json"),
                ],
                transport.INSTAGRAM_WEB_PROFILE_ROUTE: (
                    200,
                    read_instagram("web_profile_info.json"),
                    "application/json",
                ),
            },
        )

        artifact = runner.run_acquisition(
            youtube_instagram_manifest(), carrier, clock=clock.monotonic
        )

        self.assertTrue(artifact.records)
        for value in self._values():
            with self.subTest(credential=value[:8]):
                self.assertNotIn(value, repr(artifact))
                self.assertNotIn(value, repr(carrier.calls))
                self.assertNotIn(value, repr(youtube_instagram_manifest()))


def youtube_instagram_manifest():
    """One dispatch reading both platforms, and YouTube twice about one video."""

    return schema.AcquisitionManifest(
        manifest_id="m-yt-ig",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-search",
                kind="discovery",
                adapter_id="youtube_innertube",
                query="local models",
                max_items=25,
            ),
            schema.AcquisitionStep(
                step_id="s2-video",
                kind="hydration",
                adapter_id="youtube_innertube",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.youtube.com/watch?v=" + YOUTUBE_VIDEO_ID,
                        target_id="player:" + YOUTUBE_VIDEO_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s3-profile",
                kind="hydration",
                adapter_id="instagram_public",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.instagram.com/" + INSTAGRAM_USERNAME + "/",
                        target_id=INSTAGRAM_USERNAME,
                    ),
                ),
                max_items=25,
            ),
        ),
    )


class YoutubeInstagramArtifactSeamTest(unittest.TestCase):
    """The widest seam: the record a caller keeps, after normalize has run.

    Every test above reads a ``NativePage``, which is an intermediate value.
    "These two reach their measured capability" is a claim about the artifact,
    so it is closed here — including the part where the one thing this half
    must never say quietly stays said, on the record and on the artifact.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                # One route, two operations, in the order the steps run them.
                transport.YOUTUBE_INNERTUBE_ROUTE: [
                    (200, read_youtube("search_results.json"), "application/json"),
                    (200, read_youtube("player_metadata.json"), "application/json"),
                ],
                transport.INSTAGRAM_WEB_PROFILE_ROUTE: (
                    200,
                    read_instagram("web_profile_info.json"),
                    "application/json",
                ),
            },
        )
        self.artifact = runner.run_acquisition(
            youtube_instagram_manifest(), carrier, clock=clock.monotonic
        )
        self.posts = [
            record
            for record in self.artifact.records
            if record.adapter_id == "instagram_public"
            and record.canonical_content_kind == "post"
        ]

    def test_the_artifact_holds_every_row_all_three_steps_returned(self):
        self.assertEqual(len(self.artifact.records), 19)
        self.assertEqual([step.records_kept for step in self.artifact.steps], [5, 1, 13])
        self.assertEqual(len(self.opener.opened), 3)
        self.assertEqual(self.artifact.outcome, "ok")

    def test_the_one_thing_this_half_must_never_say_reaches_the_artifact_unsaid(self):
        # The whole ticket, at the value a caller keeps: nothing anywhere in
        # this artifact states that the video has no captions, and the reason
        # the captions are missing is on the record and on the run.
        video = [
            record
            for record in self.artifact.records
            if record.step_id == "s2-video"
        ][0]

        self.assertEqual(self.artifact.loss, (youtube_innertube.ATTESTATION_REQUIRED,))
        self.assertIn(youtube_innertube.ATTESTATION_REQUIRED, video.loss)
        self.assertEqual(video.title, "Running a 70B locally on two consumer GPUs")
        self.assertEqual(video.usable_basis_time, "2026-07-26T00:00:00Z")
        self.assertEqual(video.time_confidence, "authoritative")
        self.assertIn("date_precision_only", video.loss)

    def test_one_video_seen_twice_is_two_records_held_together(self):
        # wrong_merge_law rule 1: a search hit and a player read of one video
        # share a namespace, an item id and a content kind, so they are one
        # group of two and never one record. They disagree about nothing here,
        # and they would still not be folded if they did.
        seen = [
            record
            for record in self.artifact.records
            if record.native_item_id == YOUTUBE_VIDEO_ID
        ]
        grouped = [
            group for group in self.artifact.groups if len(group.member_record_ids) > 1
        ]

        self.assertEqual([record.step_id for record in seen], ["s1-search", "s2-video"])
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0].key_kind, "strong")
        self.assertEqual(
            sorted(grouped[0].member_record_ids), sorted(record.record_id for record in seen)
        )

    def test_a_search_hit_is_the_platform_speaking_and_not_an_index_entry(self):
        # Which is why the pair above groups instead of linking: an edge joins
        # an index hit to the target it discovered, and every operation on this
        # route is YouTube reporting its own items. The `K4` index-mediated
        # pattern is `web_search`'s, and it is not what happened here.
        self.assertEqual(
            sorted({record.representation_kind for record in self.artifact.records}),
            ["native"],
        )
        self.assertEqual(self.artifact.edges, ())

    def test_a_named_fact_the_route_wrote_for_a_reader_survives_normalization(self):
        first = [
            record for record in self.artifact.records if record.step_id == "s1-search"
        ][0]

        self.assertEqual(
            first.attributes,
            (
                (youtube_innertube.VIEW_COUNT_TEXT_KEY, "1,284,553 views"),
                (youtube_innertube.PUBLISHED_TIME_TEXT_KEY, "2 weeks ago"),
            ),
        )
        # And the record states no time at all, rather than one derived from
        # the words beside it.
        self.assertEqual(first.usable_basis_time, "")
        self.assertEqual(first.time_confidence, "unknown")

    def test_a_post_keeps_the_platforms_own_counts_at_the_moment_they_were_read(self):
        first = self.posts[0]
        snapshots = {snapshot.metric_name: snapshot for snapshot in first.engagement}

        self.assertEqual(
            sorted(snapshots),
            sorted((instagram_public.LIKE_METRIC, instagram_public.COMMENT_METRIC)),
        )
        self.assertEqual(snapshots[instagram_public.LIKE_METRIC].value, 412873)
        self.assertEqual(
            snapshots[instagram_public.LIKE_METRIC].observed_at, first.observed_at
        )
        # The platform's own payload, so its times are authoritative rather
        # than reported: nothing here is an archive speaking for Instagram.
        self.assertEqual(first.time_confidence, "authoritative")
        self.assertEqual(first.access_class, "K1")

    def test_a_route_that_declares_a_comment_metric_ranks_on_the_one_it_reported(self):
        # The counterpart to LinkedIn's fall-through: there, no metric was
        # declared and `most_commented` ranked on time. Here the descriptor
        # names the exact key path the payload publishes the count at, so the
        # view ranks on the count itself — and on nothing this package named.
        ranked = runner.order_records(self.posts, "most_commented", self.artifact.as_of)
        counts = [
            runner.eligible_snapshot(
                record, instagram_public.COMMENT_METRIC, self.artifact.as_of
            ).value
            for record in ranked
        ]

        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(ranked[0].native_item_id, "C9xR2mQLpQz")
        self.assertNotEqual(
            [record.native_item_id for record in ranked],
            [
                record.native_item_id
                for record in runner.order_records(
                    self.posts, "newest", self.artifact.as_of
                )
            ],
        )

    def test_two_platforms_at_one_access_class_stay_nineteen_records(self):
        # Both of these are `K1`, and nothing about sharing a class makes two
        # platforms' rows comparable. Nineteen records, nineteen strong
        # identities, and exactly one fold — the video read twice, above.
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K1"]
        )
        self.assertEqual(
            sorted({record.platform for record in self.artifact.records}),
            ["instagram", "youtube"],
        )
        self.assertEqual(len(self.artifact.groups), 18)
        self.assertEqual(
            sorted({group.key_kind for group in self.artifact.groups}), ["strong"]
        )


# findings.md §1, carry-over routes: the four surfaces this ticket reads, named
# here as the evidence names them so the route checks read against the roster
# row rather than against an adapter's own constants.
HN_ALGOLIA_ENDPOINTS = ("search", "search_by_date")
HN_COMMENT_TAG = "comment"
HN_STORY_ID = "44831234"
GITHUB_OWNER = "ggml-org"
GITHUB_REPO = "llama.cpp"
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

        # findings.md §1, carry-over: `hn.algolia.com/api/v1/search_by_date`
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

        # findings.md §1, carry-over: `hn.algolia.com/api/v1/search?tags=comment`
        # answered 200 for comment search.
        self.assertEqual(
            request.url, "https://hn.algolia.com/api/v1/search?query=cuda&tags=comment"
        )

    def test_the_firebase_route_names_an_item_and_spells_its_own_json_suffix(self):
        request = transport.build_transport_request(
            transport.HN_FIREBASE_ITEM_ROUTE, {"item_id": HN_STORY_ID}
        )

        # findings.md §1, carry-over: `hacker-news.firebaseio.com/v0/item/<id>`
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

        # findings.md §1, carry-over: `api.github.com` answered anonymously.
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

        # findings.md §1, carry-over: `api.github.com/search/repositories`
        # answered 200 anonymously.
        self.assertEqual(
            request.url, "https://api.github.com/search/repositories?q=llama.cpp"
        )

    def test_all_four_are_documented_keyless_and_need_no_credential_of_any_kind(self):
        # findings.md §3 places "HN Algolia + Firebase, GitHub anon" in `K0`,
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


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
