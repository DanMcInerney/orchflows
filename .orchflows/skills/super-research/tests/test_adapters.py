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
from super_research.adapters import github_rest, hacker_news, instagram_public
from super_research.adapters import public_page, reddit_archive, reddit_feed, rss_atom
from super_research.adapters import linkedin_jobs
from super_research.adapters import linkedin_public
from super_research.adapters import x_guest, x_syndication, youtube_innertube
from tests import helpers, test_pipeline


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


HN_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "hacker_news"

# findings.md §1 (carry-over routes): the three fields the evidence names the
# Firebase item route returning, named as the evidence names them rather than
# as a record spells them.
HN_ITEM_ROSTER_FIELDS = ("by", "descendants", "kids")
HN_COMMENT_ID = "44831402"
HN_ABSENT_ID = "44899999"
HN_PERMALINK = "https://news.ycombinator.com/item?id="


def read_hacker_news(name):
    """Read one offline Hacker News fixture."""

    return HN_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def hacker_news_cases():
    """The measured case table: a request, a status, a body, and what it means."""

    return tuple(json.loads(read_hacker_news("item_cases.json"))["cases"])


def hn_request(query="", target_id="", cursor=""):
    return adapters.AdapterRequest(
        step_id="s1-hn",
        query=query,
        target_ids=(target_id,) if target_id else (),
        cursor=cursor,
    )


def hn_page(
    fixture,
    status=200,
    query="",
    target_id="",
    cursor="",
    content_type="application/json",
    module=None,
):
    """Run the adapter over one canned answer, with both surfaces seeded.

    Both routes answer, so a call that reached the wrong one is a wrong url
    rather than a missing fixture, and a call that reached both is two entries
    in one opener — which is what "two surfaces, never fused" is checked
    against.
    """

    clock = helpers.FakeClock()
    answer = (status, read_hacker_news(fixture), content_type)
    carrier, opener = helpers.offline_transport(
        clock,
        {
            transport.HN_ALGOLIA_SEARCH_ROUTE: answer,
            transport.HN_FIREBASE_ITEM_ROUTE: answer,
        },
    )
    reading = hacker_news if module is None else module
    return (
        reading.fetch_native_page(carrier, hn_request(query, target_id, cursor)),
        opener,
    )


def attribute_pairs(record, name):
    """Every value one record carries under one attribute name, in its own order."""

    return tuple(value for carried, value in record.attributes if carried == name)


class HackerNewsSearchTest(unittest.TestCase):
    """The half the prior spec did not have: HN, searchable.

    Firebase v0 lists and hydrates and cannot search at all, which is why the
    superseded spec's `hacker_news` adapter could only walk ids it was already
    given. Algolia is HN's own index of itself, and it is what makes a query
    answerable — so these checks read a query's answer, row by row, in the
    order the index listed them.
    """

    def test_a_step_naming_only_a_query_asks_the_endpoint_the_evidence_measured(self):
        _, opener = hn_page("algolia_search_by_date.json", query="local models")

        # findings.md §1: `hn.algolia.com/api/v1/search_by_date` answered 200
        # with full-text HN search. A caller wanting relevance names `search:`.
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, transport.HN_ALGOLIA_SEARCH_ROUTE)
        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path, "/api/v1/search_by_date"
        )

    def test_comment_search_is_that_endpoint_asked_under_the_tag_that_selects_them(self):
        _, opener = hn_page("algolia_comment_search.json", query="comments:kv cache")
        asked = urllib.parse.urlsplit(opener.opened[0].url)

        # findings.md §1: `.../search?tags=comment` answered 200 for comments.
        self.assertEqual(asked.path, "/api/v1/search")
        self.assertEqual(
            sorted(urllib.parse.parse_qsl(asked.query)),
            [("query", "kv cache"), ("tags", "comment")],
        )

    def test_the_index_rows_arrive_in_the_order_the_index_listed_them(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(
            [record.native_item_id for record in page.records],
            ["44831234", "44830011", "44829903", "44829502"],
        )
        self.assertEqual(
            [record.canonical_content_kind for record in page.records],
            ["story", "story", "comment", "story"],
        )
        self.assertEqual([record.native_position for record in page.records], [0, 1, 2, 3])

    def test_a_story_hit_carries_its_own_address_and_the_link_it_points_at(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")
        story = page.records[0]

        # Two different things, and conflating them would merge every story
        # that ever linked to one article: the item's address is on HN, and the
        # link it points at is the story's own reported field.
        self.assertEqual(story.canonical_locator, HN_PERMALINK + "44831234")
        self.assertEqual(
            attribute_pairs(story, "url"), ("https://harbourlight.example/70b-two-gpus",)
        )
        self.assertEqual(story.title, "Running a 70B locally on two consumer GPUs")
        self.assertEqual(story.author, "kessel_run")
        self.assertEqual(story.published_at, "2026-08-09T16:41:52Z")

    def test_a_story_that_links_to_nothing_carries_its_own_text_and_no_link(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")
        ask = page.records[1]

        self.assertEqual(attribute_pairs(ask, "url"), ())
        self.assertEqual(
            ask.body, "Mine was a cache key that stopped including the lockfile."
        )

    def test_a_comment_hit_names_the_parent_it_answers_and_no_title_of_its_own(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")
        comment = page.records[2]

        self.assertEqual(comment.native_parent_id, "44829870")
        self.assertEqual(
            comment.body,
            "The two settings that mattered were batch size and the KV cache dtype.",
        )
        # Algolia reports the parent story's title on a comment. It is a fact
        # about the story, so it is not this record's title.
        self.assertEqual(comment.title, "")
        self.assertEqual(comment.engagement, ())

    def test_the_counts_a_hit_reports_travel_under_algolias_own_names(self):
        page, _ = hn_page("algolia_search_by_date.json", query="local models")

        self.assertEqual(counts_of(page.records[0]), {"points": 412, "num_comments": 233})
        self.assertEqual(counts_of(page.records[3]), {"points": 58, "num_comments": 12})

    def test_the_next_page_is_surfaced_for_the_core_and_never_followed(self):
        page, opener = hn_page("algolia_search_by_date.json", query="local models")

        # The index states how many pages it has, so the next one is its claim
        # and not this adapter's arithmetic about whether more exist.
        self.assertEqual(page.cursor_out, "1")
        self.assertEqual(len(opener.opened), 1)

    def test_the_last_page_the_index_states_surfaces_no_next_one(self):
        page, _ = hn_page("algolia_comment_search.json", query="comments:kv cache")

        self.assertEqual(page.cursor_out, "")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(
            [record.canonical_content_kind for record in page.records],
            ["comment", "comment"],
        )

    def test_a_reply_names_the_comment_it_answers_and_the_story_it_sits_under(self):
        # Two different facts, and only one of them is `native_parent_id`: this
        # reply hangs off another comment, and the story it belongs to is the
        # index's own separate field.
        page, _ = hn_page("algolia_comment_search.json", query="comments:kv cache")
        reply = page.records[0]

        self.assertEqual(reply.native_parent_id, HN_COMMENT_ID)
        self.assertEqual(attribute_pairs(reply, "story_id"), (HN_STORY_ID,))

    def test_a_cursor_the_core_hands_back_is_spent_as_the_index_own_page(self):
        _, opener = hn_page(
            "algolia_search_by_date.json", query="local models", cursor="3"
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertIn(("page", "3"), urllib.parse.parse_qsl(opener.opened[0].url.split("?")[1]))

    def test_rows_this_adapter_cannot_type_are_not_a_query_that_matched_nothing(self):
        # Two answers with no records and two different reasons. An index that
        # returned nothing matched nothing; an index that returned rows this
        # adapter cannot identify matched something it could not read, and
        # saying "matched nothing" there would hide a shape this package does
        # not handle behind an ordinary empty.
        unreadable, _ = hn_page("algolia_untypable_only.json", query="front page")
        matched, _ = hn_page("algolia_no_matches.json", query="a phrase")

        self.assertEqual(unreadable.outcome, "empty")
        self.assertEqual(unreadable.records, ())
        self.assertIn("2", " ".join(unreadable.warnings))
        self.assertNotIn("matched nothing", " ".join(unreadable.warnings))
        self.assertIn("matched nothing", " ".join(matched.warnings))

    def test_a_row_short_of_its_fields_says_so_and_a_row_of_no_type_is_not_a_row(self):
        page, _ = hn_page("algolia_partial_hit.json", query="short row")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        # Zero is a count the index reported, not a field it left out.
        self.assertEqual(counts_of(page.records[0]), {"points": 0, "num_comments": 0})
        self.assertEqual(page.outcome, "ok")
        self.assertIn("1", " ".join(page.warnings))
        self.assertIn("no item type", " ".join(page.warnings))


class HackerNewsItemTest(unittest.TestCase):
    """The other surface: one item, its counts, and the tree under it.

    Firebase v0 is where a story's comment tree lives — `kids` is the only
    field in either surface that says which items hang off this one. The
    traversal itself is the core's: this adapter reads one item per call and
    hands back the ids, because walking them here would make one call a crawl.
    """

    def test_an_item_answer_carries_every_field_the_evidence_names(self):
        page, opener = hn_page("firebase_story.json", target_id=HN_STORY_ID)
        story = page.records[0]

        # findings.md §1: `by`, `descendants`, and the `kids` tree.
        self.assertEqual(len(page.records), 1)
        self.assertEqual(story.author, "kessel_run")
        self.assertEqual(counts_of(story)["descendants"], 233)
        self.assertEqual(
            attribute_pairs(story, hacker_news.KIDS_KEY),
            ("44831402", "44831377", "44831301"),
        )
        self.assertEqual(len(opener.opened), 1)

    def test_the_item_is_asked_for_on_the_route_that_has_the_tree(self):
        _, opener = hn_page("firebase_story.json", target_id=HN_STORY_ID)

        self.assertEqual(opener.opened[0].route_id, transport.HN_FIREBASE_ITEM_ROUTE)
        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path,
            "/v0/item/" + HN_STORY_ID + ".json",
        )

    def test_an_item_states_its_kind_its_time_and_its_own_address(self):
        page, _ = hn_page("firebase_story.json", target_id=HN_STORY_ID)
        story = page.records[0]

        self.assertEqual(story.canonical_content_kind, "story")
        self.assertEqual(story.native_item_id, HN_STORY_ID)
        self.assertEqual(story.published_at, "2026-08-09T16:41:52Z")
        self.assertEqual(story.canonical_locator, HN_PERMALINK + HN_STORY_ID)
        self.assertEqual(counts_of(story)["score"], 412)

    def test_a_kid_read_by_its_own_id_names_the_item_it_hangs_off(self):
        page, _ = hn_page("firebase_comment.json", target_id="item:" + HN_COMMENT_ID)
        comment = page.records[0]

        self.assertEqual(comment.canonical_content_kind, "comment")
        self.assertEqual(comment.native_item_id, HN_COMMENT_ID)
        self.assertEqual(comment.native_parent_id, HN_STORY_ID)
        self.assertEqual(attribute_pairs(comment, hacker_news.KIDS_KEY), ("44831500",))
        # A comment reports no score and no descendant count, and neither is
        # invented as a zero here.
        self.assertEqual(counts_of(comment), {})

    def test_a_stamp_no_clock_can_hold_is_a_missing_time_and_not_a_crash(self):
        # Every wrong shape this route can send has to arrive as an answer,
        # because an adapter that raised would cost the core its one page and
        # the run its typed outcome. An epoch second past what a clock can
        # represent is the one value here that is not a string to be parsed.
        page, _ = hn_page("firebase_absurd_time.json", target_id="44831999")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(page.records[0].published_at, "")
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        self.assertEqual(page.outcome, "ok")

    def test_one_story_seen_on_both_surfaces_states_one_identity(self):
        # What makes the two surfaces one adapter: Algolia's `objectID` is HN's
        # own item id, so a search hit and an item read name the same thing and
        # will group on it rather than being two unrelated rows.
        found, _ = hn_page("algolia_search_by_date.json", query="local models")
        read, _ = hn_page("firebase_story.json", target_id=HN_STORY_ID)

        self.assertEqual(found.records[0].native_item_id, read.records[0].native_item_id)
        self.assertEqual(
            found.records[0].canonical_content_kind, read.records[0].canonical_content_kind
        )
        self.assertEqual(
            found.records[0].canonical_locator, read.records[0].canonical_locator
        )
        self.assertNotEqual(found.route_id, read.route_id)


def typed_hacker_news_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: hn_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            content_type=(
                "text/html" if row["body_fixture"].endswith(".txt") else "application/json"
            ),
            module=module,
        )[0]
        for row in hacker_news_cases()
    }


def assert_an_absence_is_never_a_moved_payload(case, adapter_id, pages):
    """The oracle: nothing here is both an answer of no rows and a shape change.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. Two confusions, one per direction. HN answers a request
    for an item it does not have with 200 and `null`, and Algolia answers a
    query nothing matched with 200 and an empty list; typing either as
    `schema_drift` sends a reader hunting a payload change over an ordinary
    answer. And a payload that really did move must never arrive as one of
    those, because then the platform looks quiet while this package reads the
    wrong keys.
    """

    for row in hacker_news_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if row["answer_kind"] in ("absent", "no_matches"):
            if hacker_news.SCHEMA_DRIFT in loss:
                case.fail(
                    "an answer stating there is nothing there was recorded as a payload"
                    " that moved:" + detail
                )
            if page.records:
                case.fail("an answer stating there is nothing there carried rows:" + detail)
            if not page.warnings:
                case.fail("an empty answer was returned with nothing said about it:" + detail)
        elif row["answer_kind"] == "drifted":
            if page.outcome != "failed":
                case.fail("a payload that moved was recorded as an answer:" + detail)
            if page.records:
                case.fail("a payload that moved still produced rows:" + detail)
        elif row["answer_kind"] == "records" and not page.records:
            case.fail("an answer carrying rows produced none:" + detail)
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


class HackerNewsAbsenceIsNotDriftTest(unittest.TestCase):
    """Criterion 1's other half: an answer of nothing is an answer."""

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_an_absence_is_never_a_moved_payload(
            self, "hacker_news", typed_hacker_news_pages(hacker_news)
        )

    def test_an_item_hn_does_not_have_is_an_answer_and_never_a_failure(self):
        page, _ = hn_page("firebase_absent_item.json", target_id=HN_ABSENT_ID)

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn(HN_ABSENT_ID, " ".join(page.warnings))

    def test_a_query_that_matched_nothing_is_not_an_index_that_moved(self):
        matched, _ = hn_page("algolia_no_matches.json", query="a phrase")
        moved, _ = hn_page("algolia_reshaped.json", query="local models")

        self.assertEqual(matched.outcome, "empty")
        self.assertEqual(matched.loss, ())
        self.assertEqual(moved.outcome, "failed")
        self.assertEqual(moved.loss, (hacker_news.SCHEMA_DRIFT,))
        # The drift names the container it looked for, so a reader knows which
        # shape to go and check.
        self.assertIn(hacker_news.HITS_KEY, " ".join(moved.warnings))

    def test_neither_surface_calls_a_keyless_route_credentialed(self):
        # Criterion 1: with no credential store anywhere in this run, no answer
        # either surface can give is `auth_required`.
        typed = typed_hacker_news_pages(hacker_news)

        for name, page in sorted(typed.items()):
            with self.subTest(case=name):
                self.assertNotIn("auth_required", page.loss)


WRONG_HN_ADAPTERS = ("absent_item_as_drift_adapter", "drift_as_no_matches_adapter")


class HackerNewsOracleCanFailTest(unittest.TestCase):
    """The oracle above rejects each confusion, and accepts the shipped adapter.

    Each wrong adapter is the shipped one with a single conclusion changed,
    written beside the tree and loaded by path, so a rejection is attributable
    to that conclusion and nothing under test was mutated to produce it.
    """

    def _pages(self, name):
        return typed_hacker_news_pages(load_adapter_fixture(name, directory=HN_FIXTURE_DIR))

    def test_an_absent_item_read_as_a_moved_payload_fails_the_oracle(self):
        with self.assertRaisesRegex(AssertionError, "recorded as a payload that moved"):
            assert_an_absence_is_never_a_moved_payload(
                self, "absent_item_as_drift_adapter", self._pages(WRONG_HN_ADAPTERS[0])
            )

    def test_a_moved_payload_read_as_a_search_with_no_matches_fails_the_oracle(self):
        with self.assertRaisesRegex(AssertionError, "recorded as an answer"):
            assert_an_absence_is_never_a_moved_payload(
                self, "drift_as_no_matches_adapter", self._pages(WRONG_HN_ADAPTERS[1])
            )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_an_absence_is_never_a_moved_payload(
            self, "hacker_news", typed_hacker_news_pages(hacker_news)
        )

    def test_nothing_in_the_package_can_reach_either_wrong_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for wrong in WRONG_HN_ADAPTERS
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


class HackerNewsDescriptorTest(unittest.TestCase):
    """One adapter, two surfaces, and a budget for each route it can reach."""

    def test_each_surface_declares_the_route_it_reads_under_one_adapter_id(self):
        self.assertEqual(
            [descriptor.route_id for descriptor in hacker_news.SURFACE_DESCRIPTORS],
            [transport.HN_FIREBASE_ITEM_ROUTE, transport.HN_ALGOLIA_SEARCH_ROUTE],
        )
        for descriptor in hacker_news.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.adapter_id, "hacker_news")
                self.assertEqual(descriptor.access_class, "K0")
                self.assertEqual(descriptor.platform, "hackernews")
                self.assertEqual(descriptor.native_identity_namespace, "hackernews")
                self.assertEqual(descriptor.representation_kind, "native")
                # `K3` carries `third_party_archive`; this is HN's own index of
                # itself and HN's own item store, so neither surface does.
                self.assertEqual(descriptor.standing_loss, ())
                self.assertEqual(descriptor.volatile_identifiers, ())

    def test_nothing_was_measured_here_so_nothing_is_declared(self):
        # findings.md §1 records "no throttle observed" and no latency for
        # either surface. An unmeasured ceiling is not one to spend, so both
        # keep the protocol's conservative defaults rather than a number this
        # ticket would have had to invent.
        for descriptor in hacker_news.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(
                    runner.route_budgets()[descriptor.route_id],
                    runner.RouteBudget(
                        min_interval_ms=adapters.DEFAULT_MIN_INTERVAL_MS,
                        burst=adapters.DEFAULT_BURST,
                        cooldown_ms=adapters.DEFAULT_COOLDOWN_MS,
                    ),
                )

    def test_each_surface_declares_the_comment_count_its_own_route_reports(self):
        # The same quantity under two surfaces' own names: Firebase calls a
        # story's comment count `descendants` and Algolia calls it
        # `num_comments`. Declaring either under the other's name would be this
        # package inventing a vocabulary; declaring neither would leave
        # `most_commented` ranking on a number nobody reported.
        by_route = {
            descriptor.route_id: descriptor for descriptor in hacker_news.SURFACE_DESCRIPTORS
        }

        self.assertEqual(
            by_route[transport.HN_FIREBASE_ITEM_ROUTE].comment_count_metric,
            hacker_news.DESCENDANTS_METRIC,
        )
        self.assertEqual(
            by_route[transport.HN_ALGOLIA_SEARCH_ROUTE].comment_count_metric,
            hacker_news.NUM_COMMENTS_METRIC,
        )
        for descriptor in hacker_news.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.reply_count_metric, "")

    def test_the_core_reaches_it_by_both_literal_branches_and_sees_both_surfaces(self):
        self.assertIn("hacker_news", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("hacker_news"), hacker_news.DESCRIPTOR)
        self.assertEqual(
            runner.surface_descriptors("hacker_news"), hacker_news.SURFACE_DESCRIPTORS
        )

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.HN_FIREBASE_ITEM_ROUTE: (
                    200,
                    read_hacker_news("firebase_story.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter("hacker_news", carrier, hn_request(target_id=HN_STORY_ID))

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)


GITHUB_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "github"

GITHUB_TARGET = GITHUB_OWNER + "/" + GITHUB_REPO
# The roster row's four capabilities, named as the spec names them. The
# enumeration in the next section reads this tuple: an operation set that
# covers fewer of them is a capability this ticket did not deliver, and one
# that covers more is a surface nobody measured.
GITHUB_ROSTER_CAPABILITIES = ("repo", "issues", "releases", "search")


def read_github(name):
    """Read one offline GitHub fixture."""

    return GITHUB_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def github_cases():
    """The measured case table: a request, a status, a body, and what it means."""

    return tuple(json.loads(read_github("github_cases.json"))["cases"])


def gh_request(query="", target_id="", cursor=""):
    return adapters.AdapterRequest(
        step_id="s1-gh",
        query=query,
        target_ids=(target_id,) if target_id else (),
        cursor=cursor,
    )


def gh_page(fixture, status=200, query="", target_id="", cursor="", module=None):
    """Run the adapter over one canned answer, with both buckets seeded."""

    clock = helpers.FakeClock()
    answer = (status, read_github(fixture), "application/json")
    carrier, opener = helpers.offline_transport(
        clock,
        {transport.GITHUB_REST_ROUTE: answer, transport.GITHUB_SEARCH_ROUTE: answer},
    )
    reading = github_rest if module is None else module
    return (
        reading.fetch_native_page(carrier, gh_request(query, target_id, cursor)),
        opener,
    )


class GithubReadTest(unittest.TestCase):
    """Four capabilities out of one anonymous client, and the row each returns.

    findings.md §1 measured `api.github.com` answering anonymously and
    `rate_limit` reporting the ceiling that answer costs. The roster row names
    repos, issues, releases and search, and each is read here at the field set
    GitHub publishes it with — under GitHub's own names, because a name
    translated here would be a vocabulary this package invented.
    """

    def test_a_repository_is_asked_for_at_the_path_that_names_it(self):
        _, opener = gh_page("repo.json", target_id=GITHUB_TARGET)

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].route_id, transport.GITHUB_REST_ROUTE)
        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path, "/repos/" + GITHUB_TARGET
        )

    def test_a_repository_answer_carries_the_row_the_route_publishes(self):
        page, _ = gh_page("repo.json", target_id=GITHUB_TARGET)
        repository = page.records[0]

        self.assertEqual(len(page.records), 1)
        self.assertEqual(repository.canonical_content_kind, "repository")
        self.assertEqual(repository.native_item_id, "704212099")
        self.assertEqual(repository.title, GITHUB_TARGET)
        self.assertEqual(repository.author, GITHUB_OWNER)
        self.assertEqual(
            repository.canonical_locator, "https://github.com/" + GITHUB_TARGET
        )
        self.assertEqual(repository.published_at, "2024-11-03T09:14:22Z")
        self.assertEqual(
            counts_of(repository),
            {"stargazers_count": 8241, "forks_count": 512, "open_issues_count": 47},
        )
        self.assertEqual(attribute_pairs(repository, "language"), ("Python",))
        self.assertEqual(
            attribute_pairs(repository, "topics"), ("benchmarks", "inference", "gpu")
        )

    def test_issues_arrive_in_the_order_the_route_listed_them(self):
        page, opener = gh_page("issues.json", target_id="issues:" + GITHUB_TARGET)

        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path,
            "/repos/" + GITHUB_TARGET + "/issues",
        )
        self.assertEqual(
            [record.native_item_id for record in page.records],
            ["2411900731", "2411004488", "2409776610"],
        )
        self.assertEqual(
            sorted({record.canonical_content_kind for record in page.records}), ["issue"]
        )
        self.assertEqual([record.native_position for record in page.records], [0, 1, 2])

    def test_an_issue_carries_its_own_comment_count_and_a_zero_is_one(self):
        page, _ = gh_page("issues.json", target_id="issues:" + GITHUB_TARGET)

        self.assertEqual(
            [counts_of(record)["comments"] for record in page.records], [23, 31, 0]
        )
        # Nobody has commented on the third, and that is a count GitHub
        # reported rather than a field it left out.
        self.assertEqual(page.records[2].loss, ())
        self.assertEqual(page.records[0].author, "bramble")
        self.assertEqual(attribute_pairs(page.records[0], "number"), ("812",))
        self.assertEqual(attribute_pairs(page.records[0], "state"), ("open",))

    def test_an_issue_names_its_repository_only_the_way_the_route_does(self):
        # A listed issue states its repository as an api address and never as
        # the numeric id this package identifies a repository by. The address
        # is carried verbatim so a caller can tie the two, and no id is
        # recovered from a url — that would be this adapter inventing an
        # identity out of a string it was handed.
        page, _ = gh_page("issues.json", target_id="issues:" + GITHUB_TARGET)
        issue = page.records[0]

        self.assertEqual(issue.native_parent_id, "")
        self.assertEqual(
            attribute_pairs(issue, "repository_url"),
            ("https://api.github.com/repos/" + GITHUB_TARGET,),
        )

    def test_releases_carry_their_tag_and_the_moment_they_were_published(self):
        page, opener = gh_page("releases.json", target_id="releases:" + GITHUB_TARGET)
        first = page.records[0]

        self.assertEqual(
            urllib.parse.urlsplit(opener.opened[0].url).path,
            "/repos/" + GITHUB_TARGET + "/releases",
        )
        self.assertEqual(len(page.records), 2)
        self.assertEqual(first.canonical_content_kind, "release")
        self.assertEqual(first.title, "v0.9.0 — split-GPU runs")
        self.assertEqual(attribute_pairs(first, "tag_name"), ("v0.9.0",))
        # The release's own publication moment, not the commit's creation one.
        self.assertEqual(first.published_at, "2026-08-05T10:44:19Z")
        self.assertEqual(first.engagement, ())

    def test_search_yields_repositories_at_the_index_the_evidence_measured(self):
        page, opener = gh_page("search_repositories.json", query="gpu benchmark")
        asked = urllib.parse.urlsplit(opener.opened[0].url)

        # findings.md §1: `api.github.com/search/repositories` answered 200
        # anonymously, and `rate_limit` counts it against its own bucket.
        self.assertEqual(opener.opened[0].route_id, transport.GITHUB_SEARCH_ROUTE)
        self.assertEqual(asked.path, "/search/repositories")
        self.assertEqual(urllib.parse.parse_qsl(asked.query), [("q", "gpu benchmark")])
        self.assertEqual(len(page.records), 2)
        self.assertEqual(
            [record.native_item_id for record in page.records], ["704212099", "512900744"]
        )
        self.assertEqual(
            sorted({record.canonical_content_kind for record in page.records}),
            ["repository"],
        )

    def test_a_search_hit_and_a_repository_read_name_the_same_thing(self):
        # One adapter, two buckets, one id space: a hit and a read of the same
        # repository will group rather than stand as two unrelated rows.
        found, _ = gh_page("search_repositories.json", query="gpu benchmark")
        read, _ = gh_page("repo.json", target_id=GITHUB_TARGET)

        self.assertEqual(found.records[0].native_item_id, read.records[0].native_item_id)
        self.assertEqual(
            found.records[0].canonical_locator, read.records[0].canonical_locator
        )
        self.assertNotEqual(found.route_id, read.route_id)

    def test_the_index_states_a_total_and_no_next_page_so_none_is_invented(self):
        # GitHub states how many repositories matched and never how many pages
        # it split them into. Turning a total into a next page needs a page
        # size this adapter did not send, so the cursor stays the caller's.
        page, _ = gh_page("search_repositories.json", query="gpu benchmark")

        self.assertEqual(page.cursor_out, "")

    def test_a_page_the_core_hands_back_is_spent_as_the_routes_own_page(self):
        _, opener = gh_page(
            "search_repositories.json", query="gpu benchmark", cursor="4"
        )
        asked = urllib.parse.urlsplit(opener.opened[0].url)

        self.assertEqual(len(opener.opened), 1)
        self.assertIn(("page", "4"), urllib.parse.parse_qsl(asked.query))

    def test_a_row_short_of_its_fields_says_so_and_a_star_count_of_zero_is_one(self):
        page, _ = gh_page("repo_partial.json", target_id="quilling/kvcache-notes")
        repository = page.records[0]

        self.assertEqual(repository.loss, ("field_omitted",))
        self.assertEqual(repository.author, "")
        self.assertEqual(repository.published_at, "")
        self.assertEqual(
            counts_of(repository),
            {"stargazers_count": 0, "forks_count": 0, "open_issues_count": 0},
        )


def typed_github_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: gh_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            module=module,
        )[0]
        for row in github_cases()
    }


def assert_a_spent_hour_is_never_a_missing_credential(case, adapter_id, pages):
    """The oracle: nothing this route answers says a credential was needed.

    GitHub's documented answer to an anonymous client that has spent its 60/hr
    is 403 with a message about rate limits. An adapter that read that as
    `auth_required` would report the roster's tightest budget as a missing
    credential — a keyless capability recorded as a credentialed one, which is
    the exact false claim the measured access ladder exists to prevent. The
    same rule holds in the other direction for the empties: a repository with
    nothing open and a search that matched nothing are answers, not shape
    changes.
    """

    for row in github_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if github_rest.AUTH_REQUIRED in loss:
            case.fail("a keyless route was recorded as needing a credential:" + detail)
        if row["answer_kind"] == "no_matches":
            if github_rest.SCHEMA_DRIFT in loss:
                case.fail(
                    "an answer stating there is nothing there was recorded as a payload"
                    " that moved:" + detail
                )
            if page.records:
                case.fail("an answer stating there is nothing there carried rows:" + detail)
        elif row["answer_kind"] == "drifted" and page.outcome != "failed":
            case.fail("a payload that moved was recorded as an answer:" + detail)
        elif row["answer_kind"] == "records" and not page.records:
            case.fail("an answer carrying rows produced none:" + detail)
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


class GithubIsNeverCredentialedTest(unittest.TestCase):
    """Criterion 1 at its sharpest: the tightest budget in the roster is not a wall."""

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_a_spent_hour_is_never_a_missing_credential(
            self, "github_rest", typed_github_pages(github_rest)
        )

    def test_an_hour_spent_is_the_status_it_is_and_never_a_credential_problem(self):
        page, _ = gh_page("rate_limit_exceeded.json", status=403, target_id=GITHUB_TARGET)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertNotIn(github_rest.AUTH_REQUIRED, page.loss)
        # The warning says which two things GitHub documents this status as, so
        # a reader is not left to parse the body for it.
        self.assertIn("403", " ".join(page.warnings))
        self.assertIn("60", " ".join(page.warnings))

    def test_a_repository_with_nothing_open_is_not_a_route_that_moved(self):
        empty, _ = gh_page("issues_none_open.json", target_id="issues:" + GITHUB_TARGET)
        moved, _ = gh_page("repo_reshaped.json", target_id=GITHUB_TARGET)

        self.assertEqual(empty.outcome, "empty")
        self.assertEqual(empty.loss, ())
        self.assertTrue(empty.warnings)
        self.assertEqual(moved.outcome, "failed")
        self.assertEqual(moved.loss, (github_rest.SCHEMA_DRIFT,))


class GithubDescriptorTest(unittest.TestCase):
    """Two buckets, measured apart, declared apart, and paced apart."""

    def test_the_core_bucket_declares_the_ceiling_the_evidence_measured(self):
        # findings.md §1: `api.github.com/rate_limit` reported the anonymous
        # ceiling as 60/hr. GitHub spends that as one hourly bucket, so sixty
        # reads may leave at once and one refills per minute. T04 seeded these
        # three numbers as a replay constant before this route existed; the
        # shipped descriptor is that seed, which is what ties the scheduler's
        # arithmetic to the route it paces.
        self.assertEqual(
            runner.route_budgets()[transport.GITHUB_REST_ROUTE],
            runner.RouteBudget(min_interval_ms=60000, burst=60, cooldown_ms=3600000),
        )
        self.assertEqual(
            runner.route_budgets()[transport.GITHUB_REST_ROUTE],
            test_pipeline.GITHUB_REST_BUDGET,
        )

    def test_the_search_bucket_declares_its_own_hour(self):
        # `rate_limit` reported core and code_search separately, at 60/hr each.
        # Two buckets, so a search never spends a repository read's budget.
        self.assertEqual(
            runner.route_budgets()[transport.GITHUB_SEARCH_ROUTE],
            runner.route_budgets()[transport.GITHUB_REST_ROUTE],
        )
        self.assertNotEqual(transport.GITHUB_SEARCH_ROUTE, transport.GITHUB_REST_ROUTE)

    def test_each_surface_declares_the_route_it_reads_under_one_adapter_id(self):
        self.assertEqual(
            [descriptor.route_id for descriptor in github_rest.SURFACE_DESCRIPTORS],
            [transport.GITHUB_REST_ROUTE, transport.GITHUB_SEARCH_ROUTE],
        )
        for descriptor in github_rest.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.adapter_id, "github_rest")
                self.assertEqual(descriptor.access_class, "K0")
                self.assertEqual(descriptor.platform, "github")
                self.assertEqual(descriptor.operator_identity, "github")
                self.assertEqual(descriptor.representation_kind, "native")
                self.assertEqual(descriptor.standing_loss, ())
                self.assertEqual(descriptor.volatile_identifiers, ())

    def test_it_declares_the_comment_count_an_issue_reports_and_no_reply_count(self):
        # An issue reports an exact count of its comments and nothing here
        # reports a count of replies, so one name is declared and one is not.
        self.assertEqual(github_rest.DESCRIPTOR.comment_count_metric, "comments")
        for descriptor in github_rest.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.reply_count_metric, "")

    def test_the_core_reaches_it_by_both_literal_branches_and_sees_both_surfaces(self):
        self.assertIn("github_rest", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("github_rest"), github_rest.DESCRIPTOR)
        self.assertEqual(
            runner.surface_descriptors("github_rest"), github_rest.SURFACE_DESCRIPTORS
        )

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {transport.GITHUB_REST_ROUTE: (200, read_github("repo.json"), "application/json")},
        )
        page = runner.call_adapter("github_rest", carrier, gh_request(target_id=GITHUB_TARGET))

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)


WRITE_VERBS = ("POST", "PUT", "PATCH", "DELETE")
WRONG_GITHUB_ADAPTERS = ("issue_write_adapter", "no_operations_adapter")


def code_strings(path):
    """Every string one source spells in its code, docstrings excluded.

    A module's prose may name a verb — this one's says out loud that a POST is
    refused before any socket — and prose cannot be put on a wire. A string
    constant can, so the two are counted apart: the scan below is about what
    the code can send, not about what the file can say.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"))
    prose = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            prose.add(id(first.value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in prose
    }


def any_route_transport(body):
    """A carrier that will answer on any route at all, and record which one.

    Seeding only the routes an adapter is supposed to use would turn "it
    reached somewhere else" into a missing fixture. Every declared route
    answers here, so reaching a fourth one is a recorded call the enumeration
    can name rather than an error it trips over.
    """

    clock = helpers.FakeClock()
    answer = (200, body, "application/json")
    return helpers.offline_transport(
        clock, {route_id: answer for route_id in transport.ROUTE_CONSTANTS}
    )


def assert_no_write_verb_is_reachable(case, adapter_id, module):
    """Row 2's oracle: the reachable operation set, enumerated, and read-only.

    Not "no test tried a write". The set of operations this adapter can perform
    is a declared tuple; each one is run, and each is checked at four seams —
    the operation set covers the roster's capabilities and nothing wider, every
    operation's route is one this adapter declares, every route declares a read
    and admits nothing else, and every operation's single recorded call left
    with a read verb and no body.

    The coverage clause is what stops the whole thing being vacuous: an adapter
    that declared no operation would reach no write verb by reaching nothing,
    and would satisfy every other clause here perfectly.
    """

    declared = tuple(module.GITHUB_OPERATIONS)
    surfaces = tuple(
        descriptor.route_id for descriptor in module.SURFACE_DESCRIPTORS
    )
    uncovered = [
        capability
        for capability in GITHUB_ROSTER_CAPABILITIES
        if capability not in declared
    ]
    if uncovered:
        case.fail(
            "{0} enumerates an operation set that reaches none of the roster's"
            " capabilities {1}: nothing was proven read-only by proving nothing"
            " is reachable".format(adapter_id, uncovered)
        )

    for operation in declared:
        route_id, _ = (
            module.OPERATION_SURFACES[operation][0].route_id,
            module.OPERATION_SURFACES[operation][1],
        )
        detail = " {0} operation {1} on route {2}".format(adapter_id, operation, route_id)
        if route_id not in surfaces:
            case.fail("an operation reaches a route this adapter never declared:" + detail)
        route = transport.route_constant(route_id)
        if route.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is declared by the route behind:{1}".format(
                    route.method, detail
                )
            )
        if transport.admitted_methods(route_id) != transport.READ_METHODS:
            case.fail(
                "a route this adapter reads admits a verb that is not a read:" + detail
            )
        if route.body_params:
            case.fail("a route this adapter reads carries a request body:" + detail)

        carrier, opener = any_route_transport(read_github("repo.json"))
        module.fetch_native_page(
            carrier, gh_request(target_id=operation + ":" + GITHUB_TARGET)
        )
        if len(opener.opened) != 1:
            case.fail(
                "one operation cost {0} calls rather than one:{1}".format(
                    len(opener.opened), detail
                )
            )
        sent = opener.opened[0]
        if sent.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is reachable through:{1}".format(sent.method, detail)
            )
        if sent.body:
            case.fail("a request this adapter sent carried a body:" + detail)
        if sent.route_id not in surfaces:
            case.fail(
                "a call left on a route this adapter never declared: {0} through{1}".format(
                    sent.route_id, detail
                )
            )


class GithubNoWriteVerbIsReachableTest(unittest.TestCase):
    """Row 2: the largest write surface in the roster, and none of it reachable.

    GitHub's REST API creates issues, opens pull requests, pushes files and
    deletes repositories, all on paths that look like the ones this adapter
    reads — the difference is the verb, and the verb belongs to the route. So
    the claim is made by enumerating what this adapter can do rather than by
    the absence of a test that tried something.
    """

    def test_the_reachable_operation_set_is_read_only_by_enumeration(self):
        assert_no_write_verb_is_reachable(self, "github_rest", github_rest)

    def test_the_operation_set_is_exactly_the_roster_row_and_nothing_wider(self):
        self.assertEqual(
            sorted(github_rest.GITHUB_OPERATIONS), sorted(GITHUB_ROSTER_CAPABILITIES)
        )
        self.assertEqual(
            sorted(github_rest.OPERATION_SURFACES), sorted(GITHUB_ROSTER_CAPABILITIES)
        )

    def test_the_module_spells_no_write_verb_anywhere_in_its_code(self):
        # The verb is the route's, and this module never names one: there is no
        # string here that could become a method on a wire.
        spelled = sorted(
            verb
            for verb in WRITE_VERBS
            if verb in code_strings(ADAPTER_DIR / "github_rest.py")
        )

        self.assertEqual(spelled, [])

    def test_the_same_scan_finds_a_verb_where_one_is_spelled(self):
        # Shown to discriminate rather than to match nothing: the wrong adapter
        # beside the tree spells the one this module does not.
        spelled = sorted(
            verb
            for verb in WRITE_VERBS
            if verb in code_strings(GITHUB_FIXTURE_DIR / "issue_write_adapter.py")
        )

        self.assertEqual(spelled, ["POST"])

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        # Declared so this module can say what it never says. A count of zero
        # reads is the statement: no branch here can reach it.
        self.assertEqual(github_rest.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "github_rest.py", "AUTH_REQUIRED"), 0)


class GithubWriteVerbOracleCanFailTest(unittest.TestCase):
    """Row 4: the oracle above rejects a write verb, and rejects an empty claim."""

    def _wrong(self, name):
        return load_adapter_fixture(name, directory=GITHUB_FIXTURE_DIR)

    def test_an_adapter_that_can_open_an_issue_fails_the_oracle(self):
        with self.assertRaisesRegex(
            AssertionError, "write-capable verb POST is reachable"
        ):
            assert_no_write_verb_is_reachable(
                self, WRONG_GITHUB_ADAPTERS[0], self._wrong(WRONG_GITHUB_ADAPTERS[0])
            )

    def test_an_adapter_that_reaches_nothing_at_all_fails_the_oracle(self):
        # The vacuity direction. Without this clause the oracle would be
        # perfectly satisfied by an adapter with no capability whatsoever,
        # which is the cheapest way to pass a read-only check.
        with self.assertRaisesRegex(AssertionError, "reaches none of the roster's"):
            assert_no_write_verb_is_reachable(
                self, WRONG_GITHUB_ADAPTERS[1], self._wrong(WRONG_GITHUB_ADAPTERS[1])
            )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_no_write_verb_is_reachable(self, "github_rest", github_rest)

    def test_the_write_adapter_would_really_have_left_with_a_write_verb(self):
        # The rejection above is not a technicality about a declaration: the
        # call this fixture makes is recorded on the carrier with the verb on
        # it, which is what an adapter opening an issue would actually do.
        wrong = self._wrong(WRONG_GITHUB_ADAPTERS[0])
        carrier, opener = any_route_transport(read_github("repo.json"))

        wrong.fetch_native_page(carrier, gh_request(target_id="create_issue:" + GITHUB_TARGET))

        self.assertEqual([call.method for call in opener.opened], ["POST"])
        self.assertIn("title", opener.opened[0].body)
        # And the transport would refuse it before any socket, which is the
        # second line of defence rather than the first.
        with helpers.forbid_io():
            with self.assertRaises(transport.TransportError):
                transport.urlopen_response(opener.opened[0])

    def test_nothing_in_the_package_can_reach_either_wrong_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for wrong in WRONG_GITHUB_ADAPTERS
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


HN_ROUTES = (transport.HN_FIREBASE_ITEM_ROUTE, transport.HN_ALGOLIA_SEARCH_ROUTE)
GITHUB_ROUTES = (transport.GITHUB_REST_ROUTE, transport.GITHUB_SEARCH_ROUTE)


def assert_one_answer_costs_one_call(case, adapter_id, rows, run, routes):
    """Row 3's oracle: one bounded call in, exactly one page out, on one route.

    ``run`` answers one case with the page an adapter produced and the opener
    that saw what left. Two adapters here read two origins each, so "one page
    per call" is not only about pagination and retries: an adapter that
    answered a search by also reading the item it found would be two reads
    charged to one page, on two budgets, with one observation time — and the
    core, which owns pacing and sequence, would never see the second.
    """

    for row in rows:
        name = row["case_name"]
        page, opener = run(row)
        detail = " {0} case {1}".format(adapter_id, name)
        if not isinstance(page, adapters.NativePage):
            case.fail("an answer was not one NativePage:" + detail)
        if len(opener.opened) != 1:
            case.fail(
                "one answer cost {0} calls rather than one:{1}".format(
                    len(opener.opened), detail
                )
            )
        if opener.opened[0].route_id != page.route_id:
            case.fail(
                "the page names route {0} and the call went to {1}:{2}".format(
                    page.route_id, opener.opened[0].route_id, detail
                )
            )
        if page.route_id not in routes:
            case.fail(
                "an answer came back on a route this adapter never declared: {0}{1}".format(
                    page.route_id, detail
                )
            )


def hn_status_rows():
    """The four statuses every route can answer with, as case rows."""

    return tuple(
        {
            "case_name": "http_{0}".format(status),
            "query": "",
            "target_id": HN_STORY_ID,
            "cursor": "",
            "status": status,
            "body_fixture": "firebase_reshaped.json",
        }
        for status in (404, 429, 500, 503)
    )


def github_status_rows():
    return tuple(
        {
            "case_name": "http_{0}".format(status),
            "query": "",
            "target_id": GITHUB_TARGET,
            "cursor": "",
            "status": status,
            "body_fixture": "not_found.json",
        }
        for status in (404, 429, 500, 503)
    )


def run_hn_case(module=None):
    def run(row):
        return hn_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            content_type=(
                "text/html" if row["body_fixture"].endswith(".txt") else "application/json"
            ),
            module=module,
        )

    return run


def run_github_case(module=None):
    def run(row):
        return gh_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            module=module,
        )

    return run


def portal_page(module, request, seeded):
    """One captive-portal 503 through an adapter, on every route it can reach."""

    portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
        encoding="utf-8"
    )
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (503, portal, "text/html") for route_id in seeded}
    )
    return (module.fetch_native_page(carrier, request), opener)


class HackerNewsGithubOneCallOnePageTest(unittest.TestCase):
    """Row 3: one call, one page, one route, whatever comes back."""

    def test_every_hacker_news_answer_costs_one_call_on_one_of_its_two_routes(self):
        assert_one_answer_costs_one_call(
            self,
            "hacker_news",
            hacker_news_cases() + hn_status_rows(),
            run_hn_case(),
            HN_ROUTES,
        )

    def test_every_github_answer_costs_one_call_on_one_of_its_two_routes(self):
        assert_one_answer_costs_one_call(
            self,
            "github_rest",
            github_cases() + github_status_rows(),
            run_github_case(),
            GITHUB_ROUTES,
        )

    def test_a_search_reads_the_index_and_an_item_read_reads_the_item_store(self):
        # The two surfaces are two calls: a search never also hydrates what it
        # found, and an item read never also searches for it. Which to do next
        # is the core's decision, and it can only make it if it sees both.
        _, searched = hn_page("algolia_search_by_date.json", query="local models")
        _, read = hn_page("firebase_story.json", target_id=HN_STORY_ID)

        self.assertEqual(
            [call.route_id for call in searched.opened], [transport.HN_ALGOLIA_SEARCH_ROUTE]
        )
        self.assertEqual(
            [call.route_id for call in read.opened], [transport.HN_FIREBASE_ITEM_ROUTE]
        )

    def test_a_github_search_and_a_repository_read_spend_their_own_buckets(self):
        _, searched = gh_page("search_repositories.json", query="gpu benchmark")
        _, read = gh_page("repo.json", target_id=GITHUB_TARGET)

        self.assertEqual(
            [call.route_id for call in searched.opened], [transport.GITHUB_SEARCH_ROUTE]
        )
        self.assertEqual([call.route_id for call in read.opened], [transport.GITHUB_REST_ROUTE])

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("hacker_news.py", "hacker_news"),
            ("github_rest.py", "github_rest"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", (ADAPTER_DIR / module_name).read_text(encoding="utf-8")
                )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (hacker_news, transport.HN_FIREBASE_ITEM_ROUTE,
             read_hacker_news("firebase_story.json"), hn_request(target_id=HN_STORY_ID)),
            (github_rest, transport.GITHUB_REST_ROUTE,
             read_github("repo.json"), gh_request(target_id=GITHUB_TARGET)),
        )

        for module, route_id, body, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock, {route_id: (200, body, "application/json")}
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing: `fetch_one_page`
        # reads the channel verdict ahead of any status test either adapter
        # runs, so a captive portal's 503 is `network_intercepted` and never an
        # absent item, a search with no matches, or a spent GitHub hour.
        cases = (
            (hacker_news, hn_request(target_id=HN_STORY_ID), HN_ROUTES),
            (hacker_news, hn_request(query="local models"), HN_ROUTES),
            (github_rest, gh_request(target_id=GITHUB_TARGET), GITHUB_ROUTES),
            (github_rest, gh_request(query="gpu benchmark"), GITHUB_ROUTES),
        )

        for module, request, seeded in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id, request=request):
                page, opener = portal_page(module, request, seeded)

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.records, ())
                self.assertEqual(len(opener.opened), 1)

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        # 429 is the one refusal the protocol types for every adapter, and it
        # is never answered by trying the other surface: an origin asking for
        # fewer requests is not an invitation to spend a different budget.
        cases = (
            (hacker_news, run_hn_case(), HN_STORY_ID, "firebase_reshaped.json"),
            (github_rest, run_github_case(), GITHUB_TARGET, "not_found.json"),
        )

        for module, run, target, fixture in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = run(
                    {
                        "case_name": "rate_limited",
                        "query": "",
                        "target_id": target,
                        "cursor": "",
                        "status": transport.RATE_LIMITED_STATUS,
                        "body_fixture": fixture,
                    }
                )

                self.assertEqual(page.loss, (transport.RATE_LIMITED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(len(opener.opened), 1)


class FusedSurfaceOracleCanFailTest(unittest.TestCase):
    """The oracle rejects an adapter that answers one call with two reads."""

    def test_an_adapter_that_hydrates_what_it_found_fails_the_oracle(self):
        fused = load_adapter_fixture("fused_surfaces_adapter", directory=HN_FIXTURE_DIR)

        with self.assertRaisesRegex(AssertionError, "cost 2 calls rather than one"):
            assert_one_answer_costs_one_call(
                self,
                "fused_surfaces_adapter",
                hacker_news_cases(),
                run_hn_case(module=fused),
                HN_ROUTES,
            )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_one_answer_costs_one_call(
            self, "hacker_news", hacker_news_cases(), run_hn_case(), HN_ROUTES
        )

    def test_nothing_in_the_package_can_reach_the_fused_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            if "fused_surfaces_adapter" in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


class SecondSurfaceIsPacedTest(unittest.TestCase):
    """Every route an adapter can reach has a budget, and the governor spends it.

    A two-surface adapter is the first thing in this package that could reach a
    route no descriptor declares a ceiling for. The governor refuses to pace
    such a route rather than reading it freely, so the failure would be loud —
    but it would be loud at the first live search, which is too late.
    """

    def _paced(self, route_id, body):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "application/json")}
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)
        return (governor, opener, clock)

    def test_every_route_any_adapter_can_reach_declares_a_budget(self):
        budgets = runner.route_budgets()
        reachable = sorted(
            descriptor.route_id
            for adapter_id in runner.ADAPTER_IDS
            for descriptor in runner.surface_descriptors(adapter_id)
        )

        self.assertEqual([route for route in reachable if route not in budgets], [])
        # And the second surfaces are really in there rather than the primaries
        # being counted twice.
        self.assertIn(transport.HN_ALGOLIA_SEARCH_ROUTE, budgets)
        self.assertIn(transport.GITHUB_SEARCH_ROUTE, budgets)
        self.assertEqual(len(reachable), len(set(reachable)))

    def test_a_search_on_the_second_surface_is_paced_and_never_refused(self):
        governor, opener, _ = self._paced(
            transport.HN_ALGOLIA_SEARCH_ROUTE, read_hacker_news("algolia_search_by_date.json")
        )
        request = hn_request(query="local models")

        with helpers.forbid_sleep():
            hacker_news.fetch_native_page(governor, request)
            hacker_news.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            adapters.DEFAULT_MIN_INTERVAL_MS * 1000,
        )

    def test_githubs_hour_leaves_sixty_at_once_and_then_refills_one_a_minute(self):
        # findings.md §1: 60/hr anonymous, spent as one bucket. The declared
        # burst is what lets a run do useful work at all under a ceiling that
        # tight, and the interval is what stops it doing so twice.
        governor, opener, _ = self._paced(
            transport.GITHUB_REST_ROUTE, read_github("repo.json")
        )
        budget = runner.route_budgets()[transport.GITHUB_REST_ROUTE]
        request = gh_request(target_id=GITHUB_TARGET)

        with helpers.forbid_sleep():
            for _ in range(budget.burst):
                github_rest.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), budget.burst)
        self.assertEqual([read.waited_us for read in governor.log], [0] * budget.burst)

        github_rest.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), budget.burst + 1)
        self.assertGreater(governor.log[budget.burst].waited_us, 0)


class HackerNewsGithubRouteTtlTest(unittest.TestCase):
    """How long each of the four answers may stand in for a fresh read.

    A TTL belongs to a route's own volatility, and `cache.py`'s default is
    deliberately short — a route nobody has measured is not one to trust for
    long. So every window declared here is proven from both sides: a re-read
    inside it that the inherited default would have sent back to the origin,
    and one outside it that goes back.

    The GitHub pair is the one where the argument is not only volatility.
    findings.md §1 measured the anonymous ceiling at 60/hr per bucket — the
    tightest in the roster after Reddit's feed — so a repeat read there costs a
    minute of the hour rather than a second of latency, and that is a different
    kind of expensive from the 2.9 s Instagram profile.
    """

    def _served(self, clock, route_id, body):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "application/json")}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return (governor, opener)

    def _window(self, route_id, body, module, request, inside, outside):
        """Read, re-read inside the window, re-read past it."""

        clock = helpers.FakeClock()
        governor, opener = self._served(clock, route_id, body)

        first = module.fetch_native_page(governor, request)
        clock.advance(inside)
        held = module.fetch_native_page(governor, request)
        clock.advance(outside - inside)
        expired = module.fetch_native_page(governor, request)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read.
        self.assertEqual(held.observed_at, first.observed_at)
        self.assertEqual(len(held.records), len(first.records))
        # And the window it was held for is longer than the one an undeclared
        # route would have got, so the hit above is this table's doing.
        self.assertGreater(inside, cache.DEFAULT_TTL_SECONDS)
        self.assertLess(inside, cache.ttl_seconds(route_id))
        self.assertGreater(outside, cache.ttl_seconds(route_id))

    def test_a_search_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.HN_ALGOLIA_SEARCH_ROUTE,
            read_hacker_news("algolia_search_by_date.json"),
            hacker_news,
            hn_request(query="local models"),
            inside=120,
            outside=200,
        )

    def test_an_item_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.HN_FIREBASE_ITEM_ROUTE,
            read_hacker_news("firebase_story.json"),
            hacker_news,
            hn_request(target_id=HN_STORY_ID),
            inside=90,
            outside=150,
        )

    def test_a_repository_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.GITHUB_REST_ROUTE,
            read_github("repo.json"),
            github_rest,
            gh_request(target_id=GITHUB_TARGET),
            inside=500,
            outside=700,
        )

    def test_a_repository_search_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.GITHUB_SEARCH_ROUTE,
            read_github("search_repositories.json"),
            github_rest,
            gh_request(query="gpu benchmark"),
            inside=240,
            outside=400,
        )

    def test_the_list_of_each_pair_is_held_for_less_time_than_the_thing_it_lists(self):
        # An item's counts move while nobody edits anything, and an index's
        # answer changes as stories arrive: within HN the store is the one that
        # cannot be held long. Within GitHub it is the other way round, because
        # a repository's own row changes on a human timescale while a ranked
        # search moves whenever anything in it does.
        self.assertLess(
            cache.ttl_seconds(transport.HN_FIREBASE_ITEM_ROUTE),
            cache.ttl_seconds(transport.HN_ALGOLIA_SEARCH_ROUTE),
        )
        self.assertLess(
            cache.ttl_seconds(transport.GITHUB_SEARCH_ROUTE),
            cache.ttl_seconds(transport.GITHUB_REST_ROUTE),
        )

    def test_the_tightest_budget_in_the_roster_earns_the_longest_of_these_four(self):
        # Not a preference: at 60/hr one repeat read costs a full minute of the
        # hour, where the roster's other routes cost seconds of latency. Every
        # other window here is shorter, and every one of the four is longer
        # than the window a route nobody has measured gets.
        declared = {
            route_id: cache.ttl_seconds(route_id)
            for route_id in (HN_ROUTES + GITHUB_ROUTES)
        }

        self.assertEqual(
            max(declared, key=lambda route_id: declared[route_id]),
            transport.GITHUB_REST_ROUTE,
        )
        for route_id, window in sorted(declared.items()):
            with self.subTest(route=route_id):
                self.assertGreater(window, cache.DEFAULT_TTL_SECONDS)

    def test_all_four_answers_are_small_enough_for_a_window_to_mean_anything(self):
        # The LinkedIn profile route declares a window that never binds because
        # its measured body is over the entry cap. These four answer in
        # kilobytes, so nothing here is served through — and the cap itself is
        # untouched: this ticket declares windows, not a run footprint.
        for fixture, read in (
            ("algolia_search_by_date.json", read_hacker_news),
            ("firebase_story.json", read_hacker_news),
            ("repo.json", read_github),
            ("search_repositories.json", read_github),
        ):
            with self.subTest(body=fixture):
                self.assertLess(
                    len(read(fixture).encode("utf-8")), cache.MAX_ENTRY_BYTES
                )
        self.assertEqual(cache.MAX_ENTRY_BYTES, 512 * 1024)


HN_KID_ID = "44831402"


def hacker_news_github_manifest():
    """One dispatch reading four surfaces, and HN twice about one story."""

    return schema.AcquisitionManifest(
        manifest_id="m-hn-gh",
        mode="staged",
        # After the reads this dispatch makes, because a frozen horizon that
        # fell before its own observations would replay to nothing.
        as_of="2026-08-10T09:05:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-search",
                kind="discovery",
                adapter_id="hacker_news",
                query="local models",
                max_items=20,
            ),
            schema.AcquisitionStep(
                step_id="s2-story",
                kind="hydration",
                adapter_id="hacker_news",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator=HN_PERMALINK + HN_STORY_ID,
                        target_id=HN_STORY_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s3-kid",
                kind="hydration",
                adapter_id="hacker_news",
                # One id out of the story's own `kids`, chosen by the caller.
                # The traversal is the core's: the adapter handed back the ids
                # and made no second call of its own.
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator=HN_PERMALINK + HN_KID_ID,
                        target_id=HN_KID_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s4-repository",
                kind="hydration",
                adapter_id="github_rest",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://github.com/" + GITHUB_TARGET,
                        target_id=GITHUB_TARGET,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s5-issues",
                kind="hydration",
                adapter_id="github_rest",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://github.com/" + GITHUB_TARGET + "/issues",
                        target_id="issues:" + GITHUB_TARGET,
                    ),
                ),
                max_items=20,
            ),
            schema.AcquisitionStep(
                step_id="s6-search",
                kind="discovery",
                adapter_id="github_rest",
                query="gpu benchmark",
                max_items=20,
            ),
        ),
    )


class HackerNewsGithubArtifactSeamTest(unittest.TestCase):
    """The widest seam: the records a caller keeps, after normalize has run.

    Every check above reads a ``NativePage``, which is an intermediate value.
    "These two reach their measured capability" is a claim about the artifact,
    and the two-surface question only becomes real here: one story read on two
    origins has to arrive as two records that group, ranked on the name each
    surface itself reported.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                transport.HN_ALGOLIA_SEARCH_ROUTE: (
                    200,
                    read_hacker_news("algolia_search_by_date.json"),
                    "application/json",
                ),
                # One route, two items, in the order the steps read them.
                transport.HN_FIREBASE_ITEM_ROUTE: [
                    (200, read_hacker_news("firebase_story.json"), "application/json"),
                    (200, read_hacker_news("firebase_comment.json"), "application/json"),
                ],
                transport.GITHUB_REST_ROUTE: [
                    (200, read_github("repo.json"), "application/json"),
                    (200, read_github("issues.json"), "application/json"),
                ],
                transport.GITHUB_SEARCH_ROUTE: (
                    200,
                    read_github("search_repositories.json"),
                    "application/json",
                ),
            },
        )
        self.artifact = runner.run_acquisition(
            hacker_news_github_manifest(), carrier, clock=clock.monotonic
        )
        self.by_step = {}
        for record in self.artifact.records:
            self.by_step.setdefault(record.step_id, []).append(record)

    def test_the_artifact_holds_every_row_all_six_steps_returned(self):
        self.assertEqual(len(self.artifact.records), 12)
        self.assertEqual(
            [step.records_kept for step in self.artifact.steps], [4, 1, 1, 1, 3, 2]
        )
        self.assertEqual(len(self.opener.opened), 6)
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())

    def test_neither_platform_reports_needing_a_credential_anywhere_in_the_run(self):
        # Criterion 1 at the artifact, with no credential store in the process:
        # both of these are documented keyless, and nothing in the run says
        # otherwise.
        self.assertNotIn(github_rest.AUTH_REQUIRED, self.artifact.loss)
        for record in self.artifact.records:
            with self.subTest(record=record.record_id):
                self.assertNotIn(github_rest.AUTH_REQUIRED, record.loss)
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K0"]
        )

    def test_one_story_read_on_two_origins_is_two_records_held_together(self):
        # wrong_merge_law rule 1: Algolia's `objectID` is HN's own item id, so
        # the hit and the item share a namespace, an id and a kind. One group
        # of two, never one record — and they disagree about nothing here,
        # which is not why they are kept apart.
        seen = [
            record
            for record in self.artifact.records
            if record.native_item_id == HN_STORY_ID
        ]
        grouped = [
            group for group in self.artifact.groups if len(group.member_record_ids) > 1
        ]

        self.assertEqual([record.step_id for record in seen], ["s1-search", "s2-story"])
        self.assertEqual(
            [record.route_id for record in seen],
            [transport.HN_ALGOLIA_SEARCH_ROUTE, transport.HN_FIREBASE_ITEM_ROUTE],
        )
        # Two origins answered, and each record says which one did.
        self.assertEqual(
            [record.operator_identity for record in seen], ["algolia", "hacker-news"]
        )
        # Two folds in this run, both the same shape: one story read on HN's
        # two origins, and one repository both found by GitHub's search and
        # read from GitHub's core. Each is one group of two.
        folded = [sorted(group.member_record_ids) for group in grouped]
        repository = [
            record for record in self.artifact.records if record.native_item_id == "704212099"
        ]

        self.assertEqual(len(grouped), 2)
        self.assertEqual(sorted({group.key_kind for group in grouped}), ["strong"])
        self.assertIn(sorted(record.record_id for record in seen), folded)
        self.assertEqual(
            [record.step_id for record in repository], ["s4-repository", "s6-search"]
        )
        self.assertIn(sorted(record.record_id for record in repository), folded)

    def test_the_tree_is_walked_by_the_core_one_call_per_item(self):
        # The story hands back the ids of what hangs off it; the caller chose
        # one and the core spent one call on it. The adapter walked nothing:
        # six steps, six calls, and the kid names the story it came from.
        story = self.by_step["s2-story"][0]
        kid = self.by_step["s3-kid"][0]

        self.assertEqual(
            [value for name, value in story.attributes if name == hacker_news.KIDS_KEY],
            ["44831402", "44831377", "44831301"],
        )
        self.assertEqual(kid.native_item_id, HN_KID_ID)
        self.assertEqual(kid.native_parent_id, HN_STORY_ID)
        self.assertEqual(kid.canonical_content_kind, "comment")
        self.assertEqual(len(self.opener.opened), 6)

    def test_each_step_names_the_route_it_actually_read(self):
        # A two-surface adapter is the first thing here that could record a
        # step against a route it never touched: the descriptor the core routes
        # by names one surface, and the step may have read the other.
        self.assertEqual(
            [step.route_id for step in self.artifact.steps],
            [
                transport.HN_ALGOLIA_SEARCH_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_SEARCH_ROUTE,
            ],
        )

    def test_the_work_ledger_charges_each_read_to_the_route_it_left_on(self):
        # The same fact one seam lower: a run's accounting of what it consumed
        # is per route, and two surfaces are two budgets.
        run = runner.run_scheduled(
            hacker_news_github_manifest(),
            helpers.offline_transport(
                helpers.FakeClock(),
                {
                    transport.HN_ALGOLIA_SEARCH_ROUTE: (
                        200,
                        read_hacker_news("algolia_search_by_date.json"),
                        "application/json",
                    ),
                    transport.HN_FIREBASE_ITEM_ROUTE: (
                        200,
                        read_hacker_news("firebase_story.json"),
                        "application/json",
                    ),
                    transport.GITHUB_REST_ROUTE: (
                        200,
                        read_github("repo.json"),
                        "application/json",
                    ),
                    transport.GITHUB_SEARCH_ROUTE: (
                        200,
                        read_github("search_repositories.json"),
                        "application/json",
                    ),
                },
            )[0],
        )

        self.assertEqual(
            [event.route_id for event in runner.planned_operations(run.ledger)],
            [
                transport.HN_ALGOLIA_SEARCH_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_SEARCH_ROUTE,
            ],
        )

    def test_two_surfaces_rank_together_on_the_name_each_one_reported(self):
        # The payoff of one descriptor per surface. Algolia calls a story's
        # comment count `num_comments` and Firebase calls the same quantity
        # `descendants`; each record is ranked by the name its own surface
        # published, so a view over both is one ranking rather than a list with
        # half of it unranked at the bottom.
        stories = [
            record
            for record in self.artifact.records
            if record.canonical_content_kind == "story"
        ]
        ranked = runner.order_records(stories, "most_commented", self.artifact.as_of)
        counts = []
        for record in ranked:
            named = {snapshot.metric_name: snapshot.value for snapshot in record.engagement}
            counts.append(named.get("num_comments", named.get("descendants")))

        self.assertEqual(len(stories), 4)
        self.assertEqual(counts, [311, 233, 233, 12])
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_an_issue_list_ranks_on_the_count_github_reported(self):
        issues = self.by_step["s5-issues"]
        ranked = runner.order_records(issues, "most_commented", self.artifact.as_of)
        counts = [
            runner.eligible_snapshot(record, "comments", self.artifact.as_of).value
            for record in ranked
        ]

        self.assertEqual(counts, [31, 23, 0])
        # And that is a different view from the newest one, so the ranking is
        # the count's doing rather than the order they arrived in.
        self.assertNotEqual(
            [record.native_item_id for record in ranked],
            [
                record.native_item_id
                for record in runner.order_records(issues, "newest", self.artifact.as_of)
            ],
        )

    def test_every_row_is_the_platform_speaking_for_itself(self):
        # Neither of these is an archive and neither is an index-mediated hit:
        # HN's own search of HN and GitHub's own search of GitHub are both the
        # platform reporting its own items, so nothing carries
        # `third_party_archive` and no discovery edge is drawn.
        self.assertEqual(
            sorted({record.representation_kind for record in self.artifact.records}),
            ["native"],
        )
        self.assertEqual(self.artifact.edges, ())
        for record in self.artifact.records:
            with self.subTest(record=record.record_id):
                self.assertNotIn("third_party_archive", record.loss)
                self.assertEqual(record.time_confidence, "authoritative")

    def test_a_named_fact_each_route_reported_survives_normalization(self):
        story = self.by_step["s2-story"][0]
        repository = self.by_step["s4-repository"][0]

        self.assertIn(("url", "https://harbourlight.example/70b-two-gpus"), story.attributes)
        self.assertIn(("language", "Python"), repository.attributes)
        self.assertEqual(
            [value for name, value in repository.attributes if name == "topics"],
            ["benchmarks", "inference", "gpu"],
        )

    def test_both_platforms_keep_their_own_moments_and_their_own_addresses(self):
        story = self.by_step["s2-story"][0]
        release_free = self.by_step["s6-search"][0]

        self.assertEqual(story.usable_basis_time, "2026-08-09T16:41:52Z")
        self.assertEqual(story.canonical_locator, HN_PERMALINK + HN_STORY_ID)
        self.assertEqual(
            story.normalized_locator, normalize.normalized_locator(story.canonical_locator)
        )
        self.assertEqual(release_free.canonical_locator, "https://github.com/" + GITHUB_TARGET)
        self.assertEqual(release_free.usable_basis_time, "2024-11-03T09:14:22Z")


# The last three adapters, and the four routes they read. Named here as the
# evidence names them, so a route check reads against the roster row rather
# than against an adapter's own constants.
#
# findings.md §1, Reddit: `www.reddit.com/r/<sub>.rss` answered 200 with 32 KB
# in 1.4 s carrying title, link, author and updated, at a ceiling of 1–2
# requests per ~30 s per IP. Every `.json` form answered 403 to three unrelated
# User-Agents.
REDDIT_SUBREDDIT = "LocalLLaMA"
REDDIT_FEED_FIELDS = ("title", "link", "author", "updated")
# findings.md §1, carry-over: `feeds/videos.xml?channel_id=` answered 200 with
# 39 KB in 0.35 s — the one RSS/Atom document in the evidence.
FEED_CHANNEL_ID = "UCharbourlight0000000000"
# findings.md §0, control probes: `example.com` and `wikipedia.org` answered
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
    surface here. findings.md §1 measured `.json` answering 403 to three
    unrelated User-Agents from three hosts, which is IP-class blocking no
    header set changes, so it is not a route and not a fallback.
    """

    def _routes(self):
        return FEED_PAGE_ROUTES

    def test_the_reddit_feed_route_is_the_rss_endpoint_the_evidence_measured(self):
        request = transport.build_transport_request(
            transport.REDDIT_FEED_ROUTE, {"subreddit": REDDIT_SUBREDDIT}
        )

        # findings.md §1, Reddit: `www.reddit.com/r/<sub>.rss`, 200, 32 KB,
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

        self.assertEqual(sorted(reddit_routes), [transport.REDDIT_FEED_ROUTE])
        for route_id, route in sorted(reddit_routes.items()):
            with self.subTest(route=route_id):
                self.assertEqual(route.path_suffix, ".rss")
                self.assertNotIn(".json", route.path)
                self.assertNotIn(".json", route.path_suffix)

    def test_the_channel_feed_route_asks_by_the_id_the_evidence_measured(self):
        request = transport.build_transport_request(
            transport.YOUTUBE_CHANNEL_FEED_ROUTE, {"channel_id": FEED_CHANNEL_ID}
        )

        # findings.md §1: `feeds/videos.xml?channel_id=` answered 200 with
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


REDDIT_FEED_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "reddit_feed"
REDDIT_PERMALINK = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)
REDDIT_POST_ID = "t3_1abc234"


def read_reddit_feed(name):
    return REDDIT_FEED_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def reddit_feed_cases():
    return tuple(json.loads(read_reddit_feed("feed_cases.json"))["cases"])


def feed_request(subreddit=REDDIT_SUBREDDIT):
    return adapters.AdapterRequest(step_id="s1-feed", target_ids=(subreddit,))


def feed_page(fixture, status=200, subreddit=REDDIT_SUBREDDIT, module=None):
    """Run the feed adapter over one canned answer; return its page and the opener."""

    reader = reddit_feed if module is None else module
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock,
        {
            transport.REDDIT_FEED_ROUTE: (
                status,
                read_reddit_feed(fixture),
                "application/atom+xml",
            )
        },
    )
    return (reader.fetch_native_page(carrier, feed_request(subreddit)), opener)


def feed_roster_row(record):
    """One entry's roster row, named as findings.md §1 names it."""

    return {
        "title": record.title,
        "link": record.canonical_locator,
        "author": record.author,
        "updated": record.published_at,
    }


class RedditFeedTest(unittest.TestCase):
    """The freshness probe, and the four fields it is allowed to have.

    findings.md §1 measured `www.reddit.com/r/<sub>.rss` at 200, 32 KB, 1.4 s,
    returning title, link, author and updated — and nothing else. Reddit's own
    `.json` surfaces answered 403 to three unrelated User-Agents from three
    hosts, which is IP-class blocking rather than a header problem, so this is
    the only Reddit surface in the package and there is nothing to fall back to.

    What this half exists to prevent is an engagement number nobody reported.
    Every other Reddit route in the roster carries `score`, `num_comments` and
    `upvote_ratio`, and this one carries none: a caller ranking a feed entry on
    a zero would be ranking on a fact this package made up, which is the defect
    T07's craft pass caught in the other direction.
    """

    def test_one_page_carries_the_entries_the_feed_listed(self):
        page, opener = feed_page("subreddit_new.xml")

        self.assertEqual(len(page.records), 3)
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(opener.opened), 1)

    def test_every_entry_carries_every_field_its_roster_row_names(self):
        page, _ = feed_page("subreddit_new.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                row = feed_roster_row(record)

                for name in REDDIT_FEED_FIELDS:
                    self.assertNotEqual(row[name], "", name)

    def test_an_entry_names_the_post_its_author_and_the_moment_reddit_reported(self):
        page, _ = feed_page("subreddit_new.xml")
        first = page.records[0]

        self.assertEqual(first.title, "What is the best local model right now?")
        self.assertEqual(first.canonical_locator, REDDIT_PERMALINK)
        # The handle, not the path fragment Reddit writes it inside. The `/u/`
        # prefix addresses a page; the handle is who wrote the post, and it is
        # what Reddit's other surface in this roster reports.
        self.assertEqual(first.author, "harbourlight")
        self.assertEqual(first.published_at, "2026-08-10T08:41:03Z")
        self.assertEqual(first.canonical_content_kind, "post")
        self.assertEqual(first.native_position, 0)

    def test_a_post_keeps_the_fullname_reddit_identifies_it_by(self):
        # wrong_merge_law rule 6: the `t3_` prefix is part of platform
        # identity, so it stays where the `/u/` prefix goes — one is an
        # identifier and the other is a path. This is also the exact spelling
        # the archive adapter produces, which is what lets a caller tie a
        # freshness hit to a hydration of the same post.
        page, _ = feed_page("subreddit_new.xml")

        self.assertEqual(
            [record.native_item_id for record in page.records],
            [REDDIT_POST_ID, "t3_1abc999", "t3_1abd001"],
        )
        self.assertEqual(
            page.native_identity_namespace, reddit_archive.DESCRIPTOR.native_identity_namespace
        )

    def test_the_entries_arrive_in_the_order_the_feed_listed_them(self):
        page, _ = feed_page("subreddit_new.xml")

        self.assertEqual(
            [record.native_position for record in page.records], [0, 1, 2]
        )
        self.assertEqual(
            [record.published_at for record in page.records],
            ["2026-08-10T08:41:03Z", "2026-08-10T07:12:44Z", "2026-08-09T23:05:00Z"],
        )

    def test_no_entry_carries_an_engagement_number_of_any_kind(self):
        # The roster row is four fields and this route publishes no fifth. A
        # zero here would be indistinguishable from a post nobody has voted on,
        # which is a different and checkable thing on the archive route.
        page, _ = feed_page("subreddit_new.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertEqual(record.engagement, ())
        self.assertEqual(reddit_feed.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(reddit_feed.DESCRIPTOR.reply_count_metric, "")
        self.assertIn("engagement_unavailable", reddit_feed.DESCRIPTOR.standing_loss)

    def test_the_absence_of_a_count_is_stated_on_every_record_it_is_true_of(self):
        # Standing rather than per-record, because it is true of every entry
        # this route will ever return.
        page, _ = feed_page("subreddit_new.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertIn("engagement_unavailable", record.loss)

    def test_a_subreddit_that_published_nothing_is_empty_and_not_a_feed_that_moved(self):
        page, _ = feed_page("subreddit_empty.xml", subreddit="EmptyPlaceHolder")

        self.assertEqual(page.records, ())
        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertIn("no entry", " ".join(page.warnings))

    def test_a_body_carrying_no_feed_at_all_is_drift_and_not_a_quiet_subreddit(self):
        page, _ = feed_page("subreddit_reshaped.xml")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_an_entry_short_of_a_roster_field_says_so_and_is_never_dated_from_the_read(self):
        page, _ = feed_page("entry_missing_updated.xml")
        complete, short = page.records

        self.assertEqual(short.published_at, "")
        self.assertIn("field_omitted", short.loss)
        self.assertNotIn("field_omitted", complete.loss)
        # And the moment it was read is not quietly promoted into the moment it
        # was published: an entry with no time has no time.
        self.assertNotEqual(short.published_at, page.observed_at)

    def test_the_subreddit_is_read_from_the_target_or_from_the_query(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.REDDIT_FEED_ROUTE: (
                    200,
                    read_reddit_feed("subreddit_new.xml"),
                    "application/atom+xml",
                )
            },
        )

        reddit_feed.fetch_native_page(
            carrier, adapters.AdapterRequest(step_id="s1", query=REDDIT_SUBREDDIT)
        )

        self.assertEqual(
            opener.opened[0].url,
            "https://www.reddit.com/r/" + REDDIT_SUBREDDIT + ".rss",
        )

    def test_the_page_speaks_for_reddit_at_the_class_the_ladder_gives_it(self):
        page, _ = feed_page("subreddit_new.xml")

        self.assertEqual(page.adapter_id, "reddit_feed")
        self.assertEqual(page.access_class, "K0")
        self.assertEqual(page.platform, "reddit")
        self.assertEqual(page.operator_identity, "reddit")
        # A syndication feed is its own representation. It is not the platform's
        # full native record — it carries four fields and no engagement — and
        # `REPRESENTATION_KINDS` has had a name for that all along.
        self.assertEqual(page.representation_kind, "feed")
        self.assertEqual(page.route_id, transport.REDDIT_FEED_ROUTE)


class RedditFeedDescriptorTest(unittest.TestCase):
    """The tightest ceiling in the roster, declared where the scheduler reads it."""

    def test_the_route_declares_the_ceiling_the_evidence_measured(self):
        budget = runner.route_budgets()[transport.REDDIT_FEED_ROUTE]

        # findings.md §1: four requests back to back answered 1x 200 then
        # 3x 429; after a thirty-second cooldown, paced one per six seconds, it
        # answered 2x 200 and then 429ed again; a custom UA changed nothing.
        # The effective ceiling is 1–2 per ~30 s per IP, and a client that
        # respects a limit takes the floor of a measured range.
        self.assertEqual(budget.min_interval_ms, 30000)
        self.assertEqual(budget.burst, 1)
        self.assertEqual(budget.cooldown_ms, 30000)
        # T04 seeded these three numbers as a replay constant before this route
        # existed. Asserting the identity rather than the values a second time
        # is what stops the seed and the shipped descriptor drifting apart.
        self.assertEqual(budget, test_pipeline.REDDIT_FEED_BUDGET)

    def test_it_admits_fewer_reads_in_a_minute_than_any_other_route_in_the_roster(self):
        # "Tightest ceiling" is not the longest interval — GitHub's is twice as
        # long — it is how few reads a route admits at all. GitHub spends its
        # hour as one bucket of sixty, so a minute buys sixty-one reads there
        # and three here. That factor of twenty is the whole reason the cache
        # is a correctness requirement rather than an optimization, and it is
        # what a budget of 30 s at a burst of one actually means.
        budgets = runner.route_budgets()
        admitted = {
            route_id: budget.burst + 60000 // budget.min_interval_ms
            for route_id, budget in budgets.items()
        }
        ranked = sorted(admitted.items(), key=lambda pair: (pair[1], pair[0]))

        self.assertEqual(ranked[0], (transport.REDDIT_FEED_ROUTE, 3))
        # Unique, and not merely equal-lowest: the runner-up admits at least
        # seven times as many reads in the same minute.
        self.assertGreaterEqual(ranked[1][1], ranked[0][1] * 7)
        self.assertGreater(ranked[1][1], ranked[0][1])

    def test_it_declares_neither_engagement_metric_because_the_route_reports_none(self):
        self.assertEqual(reddit_feed.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(reddit_feed.DESCRIPTOR.reply_count_metric, "")

    def test_it_declares_no_rotating_identifier_because_it_depends_on_none(self):
        self.assertEqual(reddit_feed.DESCRIPTOR.volatile_identifiers, ())

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.REDDIT_FEED_ROUTE: (
                    200,
                    read_reddit_feed("subreddit_new.xml"),
                    "application/atom+xml",
                )
            },
        )

        self.assertIn("reddit_feed", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("reddit_feed"), reddit_feed.DESCRIPTOR)
        page = runner.call_adapter("reddit_feed", carrier, feed_request())

        self.assertEqual(len(page.records), 3)
        self.assertEqual(len(opener.opened), 1)

    def test_the_only_reddit_surface_this_adapter_can_reach_is_the_feed(self):
        # There is no `.json` branch to find, because there is no `.json`
        # route: the one route this adapter names is the measured one, and a
        # refusal on it is never answered by asking somewhere else.
        self.assertEqual(
            [descriptor.route_id for descriptor in runner.surface_descriptors("reddit_feed")],
            [transport.REDDIT_FEED_ROUTE],
        )
        # Code strings, not prose: this module's docstring says out loud that
        # `.json` is blocked and why, and a paragraph cannot be put on a wire.
        # What matters is that no string constant here could become one.
        spelled = sorted(
            blocked
            for blocked in (".json", "old.reddit", "api.reddit")
            for spelling in code_strings(ADAPTER_DIR / "reddit_feed.py")
            if blocked in spelling
        )

        self.assertEqual(spelled, [])

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        # A 403 from a private community is Reddit declining this read, and
        # waiting or asking about a public community clears it. Typing it as a
        # missing credential would report a documented keyless route as one
        # this package cannot use without an account.
        self.assertEqual(reddit_feed.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "reddit_feed.py", "AUTH_REQUIRED"), 0)


def typed_reddit_feed_pages(module):
    return {
        row["case_name"]: feed_page(
            row["body_fixture"],
            status=row["status"],
            subreddit=row["subreddit"],
            module=module,
        )[0]
        for row in reddit_feed_cases()
    }


def assert_a_freshness_probe_reports_only_freshness(case, adapter_id, pages):
    """Row 3's oracle: four fields, no fifth, and no route but the measured one.

    Three confusions, each a different wrong thing to believe. An engagement
    number on a feed entry is a fact nobody reported. A refusal read as a
    missing credential turns the roster's tightest budget into a capability
    this package does not have. And an answer typed as anything other than
    what its own evidence names sends a reader to the wrong place entirely.
    """

    for row in reddit_feed_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )

        for record in page.records:
            if record.engagement:
                case.fail(
                    "a freshness probe reported engagement {0} the route does not"
                    " publish:{1}".format(record.engagement, detail)
                )
        if reddit_feed.AUTH_REQUIRED in loss:
            case.fail("a documented keyless route was called credentialed:" + detail)
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


class RedditFeedIsOnlyAFreshnessProbeTest(unittest.TestCase):
    """Row 3, over every answer this route can give."""

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_a_freshness_probe_reports_only_freshness(
            self, "reddit_feed", typed_reddit_feed_pages(None)
        )

    def test_the_two_rows_the_evidence_measured_are_marked_as_measured(self):
        # The case table mixes a measurement with this adapter's own declared
        # handling, and which is which has to survive being read later.
        measured = sorted(row["case_name"] for row in reddit_feed_cases() if row["measured"])

        self.assertEqual(measured, ["asked_for_fewer_requests", "newest_entries"])

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        # The measurement that made the run-local cache a correctness
        # requirement. An origin asking for fewer requests is an outcome, not
        # an invitation to ask a different Reddit host — and there is no other
        # Reddit host here to ask.
        page, opener = feed_page(
            "too_many_requests.txt", status=transport.RATE_LIMITED_STATUS
        )

        self.assertEqual(page.loss, (transport.RATE_LIMITED,))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertEqual(
            [call.route_id for call in opener.opened], [transport.REDDIT_FEED_ROUTE]
        )


RSS_ATOM_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "rss_atom"
FEED_VIDEO_ID = "yt:video:dQw4w9WgXcQ"
FEED_VIDEO_LOCATOR = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
PODCAST_GUID = "harbourlight-tape-014"


def read_rss_atom(name):
    return RSS_ATOM_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def rss_atom_cases():
    return tuple(json.loads(read_rss_atom("feed_cases.json"))["cases"])


def syndication_request(channel_id=FEED_CHANNEL_ID):
    return adapters.AdapterRequest(step_id="s1-rss", target_ids=(channel_id,))


def rss_atom_page(fixture, status=200, channel_id=FEED_CHANNEL_ID, module=None):
    reader = rss_atom if module is None else module
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock,
        {
            transport.YOUTUBE_CHANNEL_FEED_ROUTE: (
                status,
                read_rss_atom(fixture),
                "application/atom+xml",
            )
        },
    )
    return (reader.fetch_native_page(carrier, syndication_request(channel_id)), opener)


class RssAtomReaderTest(unittest.TestCase):
    """One parser over both syndication vocabularies, on one selected route.

    The roster row's "generic" is the parser and not the route. findings.md §1
    measured one RSS/Atom document — `feeds/videos.xml?channel_id=`, 200, 39 KB,
    0.35 s — and that is the one route this adapter declares. The RSS 2.0 half
    of the row, enclosures and transcript links, is proven against a document of
    that shape rather than against a route known to send one, which is a real
    limit and is stated in `## Risks` rather than papered over.

    The claim this half defends is that a generic reader stays generic. The
    measured feed carries `media:statistics views=` in a vendor namespace, and
    reading it would make this adapter quietly YouTube-aware — a second opinion
    about a count `youtube_innertube` already reports, under a name this row
    does not name. It is left where it is, and that is checked.
    """

    def test_an_atom_feed_yields_the_entries_it_listed(self):
        page, opener = rss_atom_page("youtube_channel_feed.xml")

        self.assertEqual(len(page.records), 2)
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(
            opener.opened[0].url,
            "https://www.youtube.com/feeds/videos.xml?channel_id=" + FEED_CHANNEL_ID,
        )

    def test_an_atom_entry_carries_its_identity_its_date_and_its_address(self):
        page, _ = rss_atom_page("youtube_channel_feed.xml")
        first = page.records[0]

        self.assertEqual(first.native_item_id, FEED_VIDEO_ID)
        self.assertEqual(first.title, "70B on two 3090s: the numbers")
        self.assertEqual(first.canonical_locator, FEED_VIDEO_LOCATOR)
        self.assertEqual(first.author, "Harbourlight Benchmarks")
        # `published` is when the entry appeared; `updated` is when it last
        # changed. A feed that states both states a publication time, and that
        # is the one a caller ordering by recency means.
        self.assertEqual(first.published_at, "2026-08-09T15:30:12Z")

    def test_an_rss_two_item_carries_the_same_row_out_of_a_different_vocabulary(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        first = page.records[0]

        self.assertEqual(len(page.records), 3)
        self.assertEqual(first.native_item_id, PODCAST_GUID)
        self.assertEqual(first.title, "Measuring what a rate limit actually is")
        self.assertEqual(first.canonical_locator, "https://harbourlight.example/podcast/014")
        # RFC 822, which is what RSS 2.0 dates are, parsed rather than pattern
        # matched: `pubDate` is a different grammar from Atom's RFC 3339 and
        # reading one as the other would drop every RSS date in existence.
        self.assertEqual(first.published_at, "2026-08-10T08:41:03Z")

    def test_an_enclosure_travels_with_the_media_type_the_feed_declared(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        first = page.records[0]

        self.assertEqual(
            attribute_pairs(first, rss_atom.ENCLOSURE_ATTRIBUTE),
            ("https://cdn.harbourlight.example/tape/014.mp3",),
        )
        self.assertEqual(
            attribute_pairs(first, rss_atom.ENCLOSURE_TYPE_ATTRIBUTE), ("audio/mpeg",)
        )

    def test_a_transcript_link_is_carried_for_every_one_the_feed_published(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        first, second, _ = page.records

        # Two transcripts on one episode, in the feed's own order, each with
        # the type it was declared under. This is the half of the roster row no
        # route in this package is known to send, and it is why the parser is
        # generic rather than shaped to one document.
        self.assertEqual(
            attribute_pairs(first, rss_atom.TRANSCRIPT_ATTRIBUTE),
            (
                "https://cdn.harbourlight.example/tape/014.vtt",
                "https://cdn.harbourlight.example/tape/014.srt",
            ),
        )
        self.assertEqual(
            attribute_pairs(first, rss_atom.TRANSCRIPT_TYPE_ATTRIBUTE),
            ("text/vtt", "application/x-subrip"),
        )
        # An episode that published none carries none, rather than an empty
        # string standing in for a transcript nobody offered.
        self.assertEqual(attribute_pairs(second, rss_atom.TRANSCRIPT_ATTRIBUTE), ())

    def test_a_media_pair_stays_paired_when_the_feed_declared_no_type(self):
        # The two names repeat in step, one pair per enclosure, so a caller can
        # read them by position. A feed that declared a url and no type still
        # contributes to both, with the type empty — an absence stated in its
        # own slot rather than a pairing that silently slips by one.
        page, _ = rss_atom_page("podcast_rss.xml")
        undated = page.records[2]

        self.assertEqual(attribute_pairs(undated, rss_atom.ENCLOSURE_ATTRIBUTE), ())
        self.assertEqual(attribute_pairs(undated, rss_atom.ENCLOSURE_TYPE_ATTRIBUTE), ())
        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertEqual(
                    len(attribute_pairs(record, rss_atom.ENCLOSURE_ATTRIBUTE)),
                    len(attribute_pairs(record, rss_atom.ENCLOSURE_TYPE_ATTRIBUTE)),
                )

    def test_an_item_the_feed_dated_in_no_grammar_at_all_carries_no_date(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        undated = page.records[2]

        self.assertEqual(undated.published_at, "")
        self.assertIn("field_omitted", undated.loss)
        self.assertNotEqual(undated.published_at, page.observed_at)

    def test_a_vendor_extension_the_feed_carries_is_left_where_it_is(self):
        # `media:statistics views="128455"` is in the measured document. A
        # generic reader that mined it would be publishing a count under a name
        # this roster row does not name, about a platform it does not know it
        # is reading, beside an adapter that reports the same quantity from the
        # platform's own API.
        page, _ = rss_atom_page("youtube_channel_feed.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertEqual(record.engagement, ())
                self.assertEqual(
                    [name for name, _ in record.attributes if "statistic" in name], []
                )
                self.assertNotIn("128455", repr(record))
        self.assertEqual(rss_atom.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(rss_atom.DESCRIPTOR.reply_count_metric, "")

    def test_a_syndication_identity_is_recorded_and_never_used_to_merge(self):
        # A `guid` is unique inside its own feed and nowhere else, and this
        # adapter cannot say which identity space it belongs to. So the id is
        # carried — it is the roster row's "identity" — and the namespace is
        # left unstated, which is exactly what makes `strong_identity` decline
        # to fold two entries that happened to be named the same thing.
        page, _ = rss_atom_page("podcast_rss.xml")
        records = normalize.normalize_page(
            page,
            schema.AcquisitionStep(
                step_id="s1-rss", kind="discovery", adapter_id="rss_atom", max_items=10
            ),
            "artifact:t", "m-t",
        )

        self.assertEqual(page.native_identity_namespace, "")
        for record in records:
            with self.subTest(entry=record.native_item_id):
                self.assertNotEqual(record.native_item_id, "")
                self.assertIsNone(normalize.strong_identity(record))

    def test_a_channel_that_published_nothing_is_empty_and_not_a_feed_that_moved(self):
        page, _ = rss_atom_page("channel_with_no_entries.xml")

        self.assertEqual(page.records, ())
        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())

    def test_a_document_that_is_not_a_feed_is_drift_and_not_a_quiet_channel(self):
        page, _ = rss_atom_page("not_a_feed.html")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_the_channel_is_read_from_the_target_or_from_the_query(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_CHANNEL_FEED_ROUTE: (
                    200,
                    read_rss_atom("youtube_channel_feed.xml"),
                    "application/atom+xml",
                )
            },
        )

        rss_atom.fetch_native_page(
            carrier, adapters.AdapterRequest(step_id="s1", query=FEED_CHANNEL_ID)
        )

        self.assertIn("channel_id=" + FEED_CHANNEL_ID, opener.opened[0].url)

    def test_the_page_speaks_for_the_route_at_the_class_the_ladder_gives_it(self):
        page, _ = rss_atom_page("youtube_channel_feed.xml")

        self.assertEqual(page.adapter_id, "rss_atom")
        self.assertEqual(page.access_class, "K0")
        self.assertEqual(page.representation_kind, "feed")
        self.assertEqual(page.route_id, transport.YOUTUBE_CHANNEL_FEED_ROUTE)
        # An entry in a feed is an entry in a feed. A generic reader does not
        # know whether the thing behind it is a video, an episode or an
        # article, and naming one would be a guess this adapter cannot support.
        self.assertEqual(
            sorted({record.canonical_content_kind for record in page.records}),
            ["feed_entry"],
        )


class RssAtomDescriptorTest(unittest.TestCase):
    """One route, its measured cost, and the seam a second feed would use."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        budget = runner.route_budgets()[transport.YOUTUBE_CHANNEL_FEED_ROUTE]

        # findings.md §1: 0.35 s per request, the cheapest read in the roster.
        # Nothing on this route was measured refusing, so `burst` and
        # `cooldown_ms` keep the protocol's conservative defaults rather than a
        # ceiling nobody observed.
        self.assertEqual(budget.min_interval_ms, 350)
        self.assertEqual(budget.burst, adapters.DEFAULT_BURST)
        self.assertEqual(budget.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)

    def test_it_is_the_cheapest_read_the_roster_declares(self):
        budgets = runner.route_budgets()
        cheapest = min(budgets, key=lambda route_id: budgets[route_id].min_interval_ms)

        self.assertEqual(cheapest, transport.YOUTUBE_CHANNEL_FEED_ROUTE)

    def test_it_declares_no_rotating_identifier_because_it_depends_on_none(self):
        self.assertEqual(rss_atom.DESCRIPTOR.volatile_identifiers, ())

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_CHANNEL_FEED_ROUTE: (
                    200,
                    read_rss_atom("youtube_channel_feed.xml"),
                    "application/atom+xml",
                )
            },
        )

        self.assertIn("rss_atom", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("rss_atom"), rss_atom.DESCRIPTOR)
        page = runner.call_adapter("rss_atom", carrier, syndication_request())

        self.assertEqual(len(page.records), 2)
        self.assertEqual(len(opener.opened), 1)

    def test_one_route_today_and_the_seam_a_second_feed_would_arrive_through(self):
        # A second measured feed is a second route constant and a second
        # descriptor under this same id, reachable through `surface_descriptors`
        # — not a second adapter and not a caller-supplied address.
        self.assertEqual(
            [descriptor.route_id for descriptor in runner.surface_descriptors("rss_atom")],
            [transport.YOUTUBE_CHANNEL_FEED_ROUTE],
        )

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        self.assertEqual(rss_atom.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "rss_atom.py", "AUTH_REQUIRED"), 0)


class RssAtomCaseTableTest(unittest.TestCase):
    """Every answer this route can give, typed as its own evidence names it."""

    def test_every_case_is_typed_as_its_evidence_says(self):
        for row in rss_atom_cases():
            with self.subTest(case=row["case_name"]):
                page, _ = rss_atom_page(row["body_fixture"], status=row["status"])

                self.assertEqual(page.outcome, row["expected_outcome"])
                self.assertEqual(
                    tuple(page.loss),
                    (row["expected_loss"],) if row["expected_loss"] else (),
                )
                self.assertNotIn(rss_atom.AUTH_REQUIRED, page.loss)

    def test_the_one_row_the_evidence_measured_is_marked_as_measured(self):
        measured = sorted(row["case_name"] for row in rss_atom_cases() if row["measured"])

        self.assertEqual(measured, ["an_atom_channel_feed"])


PUBLIC_PAGE_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "public_page"
ARTICLE_TARGET = "article:" + ARTICLE_TITLE
ARTICLE_LOCATOR = "https://en.wikipedia.org/wiki/" + ARTICLE_TITLE
CONTROL_LOCATOR = "https://example.com/"
# The roster row's capability, as the spec's own table names it. The oracle
# refuses an adapter that reaches none of it, because an adapter that can do
# nothing satisfies "reaches no host a caller chose" perfectly.
PAGE_ROSTER_SELECTIONS = ("article", "control")
WRONG_PAGE_ADAPTERS = ("any_url_adapter", "no_selection_adapter")

# Every shape a caller could use to try to name an address instead of a
# document, plus the same shapes behind a valid selection prefix. None of them
# reaches the network.
UNSELECTABLE_TARGETS = ADDRESS_SHAPED_VALUES + tuple(
    "article:" + value for value in ADDRESS_SHAPED_VALUES
) + (
    "",
    "article",
    "control:something",
    "shell:rm -rf /",
    "not_a_selection:x",
)


def read_public_page(name):
    return PUBLIC_PAGE_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def page_cases():
    return tuple(json.loads(read_public_page("page_cases.json"))["cases"])


def page_request(target):
    return adapters.AdapterRequest(step_id="s1-page", target_ids=(target,))


def selected_page(fixture, status=200, target=ARTICLE_TARGET, module=None, final_url=None):
    """Run the page adapter over one canned answer; return its page and the opener.

    A four-part answer is how an offline read reports that the origin answered
    from an address other than the one asked for. The carrier treats a
    three-part answer as a read that was not redirected, so every existing
    seeding in this suite keeps meaning what it meant.
    """

    reader = public_page if module is None else module
    body = read_public_page(fixture)
    answer = (status, body, "text/html")
    if final_url is not None:
        answer = answer + (final_url,)
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: answer for route_id in transport.ROUTE_CONSTANTS}
    )
    return (reader.fetch_native_page(carrier, page_request(target)), opener)


class PublicPageReadTest(unittest.TestCase):
    """One selected document, read as a document.

    The roster row is body, hash, links, media type, redirects and observed
    time — everything a caller needs to say "this is the document I read, here
    is its fingerprint, and here is where it actually came from". The body is
    the bytes the origin served rather than text extracted from them, because
    the hash has to be of something exact and an extraction is this package's
    reading rather than the origin's document.
    """

    def test_one_page_carries_the_one_document_it_selected(self):
        page, opener = selected_page("article.html")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].url, ARTICLE_LOCATOR)

    def test_the_record_carries_every_field_its_roster_row_names(self):
        page, _ = selected_page("article.html")
        record = page.records[0]
        named = dict(record.attributes)

        # body, as served
        self.assertEqual(record.body, read_public_page("article.html"))
        # media type
        self.assertEqual(named[public_page.CONTENT_TYPE_ATTRIBUTE], "text/html")
        # links
        self.assertGreater(len(attribute_pairs(record, public_page.LINK_ATTRIBUTE)), 1)
        # redirects: what was asked, and what answered
        self.assertEqual(named[public_page.REQUESTED_URL_ATTRIBUTE], ARTICLE_LOCATOR)
        self.assertEqual(named[public_page.FINAL_URL_ATTRIBUTE], ARTICLE_LOCATOR)
        # observed time, which a page states and every record built from it
        # inherits: the moment the origin was read, not the moment it was
        # normalized.
        self.assertEqual(page.observed_at, helpers.FROZEN_START)

    def test_the_hash_is_of_the_document_that_was_read(self):
        # The hash is derived by the one module that owns hashing rather than
        # computed a second time here, which is why the body is the bytes the
        # origin served: an extraction would fingerprint this package's reading
        # of a document instead of the document.
        page, _ = selected_page("article.html")
        records = normalize.normalize_page(
            page,
            schema.AcquisitionStep(
                step_id="s1-page", kind="discovery", adapter_id="public_page", max_items=5
            ),
            "artifact:t", "m-t",
        )

        self.assertEqual(
            records[0].exact_content_hash,
            normalize.content_hash(read_public_page("article.html")),
        )
        self.assertEqual(len(records[0].exact_content_hash), 64)

    def test_the_links_are_the_ones_the_document_published_exactly_as_published(self):
        page, _ = selected_page("article.html")
        links = attribute_pairs(page.records[0], public_page.LINK_ATTRIBUTE)

        # In the document's own order, and relative where the document was
        # relative: resolving one here would mean guessing the base a page
        # states elsewhere, and the record already carries the address the
        # origin answered from for a caller that wants to resolve them.
        self.assertEqual(
            links,
            (
                "/wiki/Denial-of-service_attack",
                "/wiki/Bandwidth_throttling",
                "/wiki/Token_bucket",
                "/wiki/Project_Shield",
                "https://www.rfc-editor.org/rfc/rfc6585",
                "https://foundation.wikimedia.org/wiki/Policy:Privacy_policy",
            ),
        )

    def test_a_read_that_was_redirected_says_what_it_asked_and_what_answered(self):
        answered_from = "https://en.wikipedia.org/wiki/Rate_limiting_(computing)"
        page, _ = selected_page("article.html", final_url=answered_from)
        record = page.records[0]
        named = dict(record.attributes)

        # One hop's worth of truth: "I asked X and read the document at Y".
        self.assertEqual(named[public_page.REQUESTED_URL_ATTRIBUTE], ARTICLE_LOCATOR)
        self.assertEqual(named[public_page.FINAL_URL_ATTRIBUTE], answered_from)
        # And the locator is where the document actually came from, so two
        # requests that land on one document name one thing.
        self.assertEqual(record.canonical_locator, answered_from)

    def test_a_read_that_was_not_redirected_names_one_address_twice(self):
        page, _ = selected_page("control.html", target="control")
        record = page.records[0]
        named = dict(record.attributes)

        self.assertEqual(named[public_page.REQUESTED_URL_ATTRIBUTE], CONTROL_LOCATOR)
        self.assertEqual(named[public_page.FINAL_URL_ATTRIBUTE], CONTROL_LOCATOR)
        self.assertEqual(record.canonical_locator, CONTROL_LOCATOR)

    def test_the_control_selection_takes_no_argument_and_reads_one_document(self):
        page, opener = selected_page("control.html", target="control")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(opener.opened[0].url, CONTROL_LOCATOR)
        self.assertEqual(
            attribute_pairs(page.records[0], public_page.LINK_ATTRIBUTE),
            ("https://www.iana.org/domains/example",),
        )

    def test_a_page_the_origin_does_not_have_is_the_status_it_is(self):
        page, _ = selected_page("article_absent.html", status=404)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertEqual(page.records, ())
        self.assertNotIn(public_page.AUTH_REQUIRED, page.loss)

    def test_the_page_speaks_for_the_document_at_the_class_the_ladder_gives_it(self):
        page, _ = selected_page("article.html")

        self.assertEqual(page.adapter_id, "public_page")
        self.assertEqual(page.access_class, "K0")
        self.assertEqual(page.representation_kind, "page")
        self.assertEqual(page.route_id, transport.PUBLIC_PAGE_ARTICLE_ROUTE)
        self.assertEqual(page.operator_identity, "wikimedia")
        self.assertEqual(page.records[0].canonical_content_kind, "web_page")
        # A document has no platform identity to be qualified against, so
        # nothing here can be folded with anything by strong identity.
        self.assertEqual(page.native_identity_namespace, "")

    def test_every_case_is_typed_as_its_evidence_says(self):
        for row in page_cases():
            with self.subTest(case=row["case_name"]):
                page, _ = selected_page(
                    row["body_fixture"], status=row["status"], target=row["target"]
                )

                self.assertEqual(page.outcome, row["expected_outcome"])
                self.assertEqual(
                    tuple(page.loss),
                    (row["expected_loss"],) if row["expected_loss"] else (),
                )


def assert_the_target_set_is_selected_and_enumerable(case, adapter_id, module):
    """Row 2's oracle: what this adapter can read is a list, and it is closed.

    Not "no test pointed it somewhere else". Every other adapter in this roster
    is pinned to a vendor's endpoint shape and could not be pointed anywhere if
    it tried; this one takes an argument, and an argument is one bad branch away
    from being an address. So the claim is made by enumerating what the adapter
    can reach and then trying to escape it.

    Four clauses. The selection set covers the roster's capability and is
    therefore not empty — without which an adapter that reads nothing at all
    passes perfectly. Every selection resolves to a route this module declares,
    which `transport.py` owns, which declares a read and admits nothing else.
    Every selection actually run leaves exactly one call, on that route, at that
    origin. And every caller string shaped like an address reaches the network
    zero times.
    """

    selections = dict(module.PAGE_SELECTIONS)
    surfaces = tuple(descriptor.route_id for descriptor in module.SURFACE_DESCRIPTORS)
    uncovered = [name for name in PAGE_ROSTER_SELECTIONS if name not in selections]
    if uncovered:
        case.fail(
            "{0} enumerates a selection set that reaches none of the roster's"
            " capability {1}: nothing was proven closed by proving nothing is"
            " reachable".format(adapter_id, uncovered)
        )

    origins = set()
    for name in sorted(selections):
        descriptor, _ = selections[name]
        route_id = descriptor.route_id
        detail = " {0} selection {1} on route {2}".format(adapter_id, name, route_id)
        if route_id not in surfaces:
            case.fail("a selection reaches a route this adapter never declared:" + detail)
        route = transport.route_constant(route_id)
        origins.add(urllib.parse.urlsplit(route.origin).netloc)
        if route.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is declared by the route behind:{1}".format(
                    route.method, detail
                )
            )
        if transport.admitted_methods(route_id) != transport.READ_METHODS:
            case.fail("a route this adapter reads admits a verb that is not a read:" + detail)
        if route.body_params:
            case.fail("a route this adapter reads carries a request body:" + detail)

    for row in page_cases():
        if row["status"] != 200:
            continue
        name = row["case_name"]
        _, opener = selected_page(row["body_fixture"], target=row["target"], module=module)
        detail = " {0} case {1}".format(adapter_id, name)
        if len(opener.opened) != 1:
            case.fail(
                "one selected read cost {0} calls rather than one:{1}".format(
                    len(opener.opened), detail
                )
            )
        sent = opener.opened[0]
        if sent.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is reachable through:{1}".format(sent.method, detail)
            )
        if sent.body:
            case.fail("a request this adapter sent carried a body:" + detail)
        if urllib.parse.urlsplit(sent.url).netloc not in origins:
            case.fail(
                "a read left for a host outside the selection set: {0}{1}".format(
                    sent.url, detail
                )
            )

    for target in UNSELECTABLE_TARGETS:
        page, opener = selected_page("article.html", target=target, module=module)
        detail = " {0} target {1!r}".format(adapter_id, target)
        if opener.opened:
            reached = urllib.parse.urlsplit(opener.opened[0].url).netloc
            if reached not in origins:
                case.fail(
                    "a caller chose the host a read went to: {0} reached {1}{2}".format(
                        target, opener.opened[0].url, detail
                    )
                )
            case.fail(
                "an arbitrary caller-supplied target reached the network:" + detail
            )
        if page.outcome != "refused":
            case.fail(
                "a target naming no selection was answered rather than refused:"
                " outcome {0}{1}".format(page.outcome, detail)
            )
        if page.records:
            case.fail("a refused target still produced records:" + detail)


# Everything a module would have to reach to run something rather than read
# something. None of it is imported here, named here, or read here.
EXECUTION_MODULES = (
    "subprocess",
    "os",
    "sys",
    "shlex",
    "shutil",
    "pty",
    "socket",
    "urllib.request",
    "http.client",
    "ssl",
    "importlib",
    "ctypes",
)
EXECUTION_NAMES = (
    "eval",
    "exec",
    "compile",
    "__import__",
    "getattr",
    "setattr",
    "system",
    "popen",
    "spawn",
    "fork",
    "execv",
    "run",
    "call",
    "check_output",
)


class PublicPageIsSelectedNotGenericTest(unittest.TestCase):
    """Row 2: the one adapter that could have been an HTTP primitive, and is not.

    The spec's non-goals forbid "any generic HTTP/CLI/exec primitive". Every
    other adapter here honours that by construction — a caller cannot point
    `github_rest` at Wikipedia because the route shape is GitHub's. This one is
    the only one where the constraint had to be built rather than inherited,
    and if it leaked, every other constraint in this package would be
    decorative: any route at all could be reached through it.
    """

    def test_the_reachable_target_set_is_selected_and_enumerable(self):
        assert_the_target_set_is_selected_and_enumerable(self, "public_page", public_page)

    def test_the_selection_set_is_exactly_the_roster_row_and_nothing_wider(self):
        self.assertEqual(sorted(public_page.PAGE_SELECTIONS), sorted(PAGE_ROSTER_SELECTIONS))
        self.assertEqual(
            sorted(
                descriptor.route_id
                for descriptor in runner.surface_descriptors("public_page")
            ),
            [transport.PUBLIC_PAGE_ARTICLE_ROUTE, transport.PUBLIC_PAGE_CONTROL_ROUTE],
        )

    def test_the_manifest_can_name_a_selection_and_can_express_nothing_else(self):
        # "Constrained by the manifest" from the other end: a caller writes a
        # manifest, so the manifest cannot be what limits it — what limits it is
        # that every string a manifest can carry resolves to a selection or to
        # a refusal, and a refusal costs the origin nothing.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                route_id: (200, read_public_page("article.html"), "text/html")
                for route_id in transport.ROUTE_CONSTANTS
            },
        )
        manifest = schema.AcquisitionManifest(
            manifest_id="m-page",
            mode="staged",
            as_of="2026-08-10T09:05:00Z",
            steps=(
                schema.AcquisitionStep(
                    step_id="s1-selected",
                    kind="hydration",
                    adapter_id="public_page",
                    selected_hits=(
                        schema.SelectedHit(
                            discovery_locator=ARTICLE_LOCATOR, target_id=ARTICLE_TARGET
                        ),
                        schema.SelectedHit(
                            discovery_locator="https://evil.example/x",
                            target_id="https://evil.example/x",
                        ),
                    ),
                    max_items=10,
                ),
            ),
        )

        artifact = runner.run_acquisition(manifest, carrier, clock=clock.monotonic)

        # Two hits, one document: the one that named a selection was read and
        # the one that named an address was refused before any socket.
        self.assertEqual(len(artifact.records), 1)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(artifact.records[0].canonical_locator, ARTICLE_LOCATOR)
        self.assertEqual(artifact.steps[0].outcome, "partial")

    def test_no_cli_shell_or_exec_surface_is_reachable_through_it(self):
        source = ADAPTER_DIR / "public_page.py"
        imported = helpers.imported_names(source)
        attributes = helpers.attribute_names(source)
        strings = code_strings(source)

        for module_name in EXECUTION_MODULES:
            with self.subTest(module=module_name):
                self.assertNotIn(module_name, imported)
        for name in EXECUTION_NAMES:
            with self.subTest(name=name):
                self.assertEqual(
                    [spelled for spelled in attributes if spelled.endswith("." + name)], []
                )
        # And no string here could become a command, an argument vector, or a
        # scheme that runs something.
        for dangerous in ("sh -c", "/bin/", "cmd.exe", "javascript:", "data:", "file:"):
            with self.subTest(spelling=dangerous):
                self.assertEqual(
                    [spelling for spelling in strings if dangerous in spelling], []
                )

    def test_it_runs_to_completion_with_every_file_socket_and_wait_forbidden(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {
                transport.PUBLIC_PAGE_ARTICLE_ROUTE: (
                    200,
                    read_public_page("article.html"),
                    "text/html",
                )
            },
        )

        with helpers.forbid_io():
            with helpers.forbid_sleep():
                page = public_page.fetch_native_page(carrier, page_request(ARTICLE_TARGET))

        self.assertEqual(page.outcome, "ok")

    def test_a_refused_target_is_a_refusal_and_never_a_missing_credential(self):
        page, opener = selected_page("article.html", target="https://evil.example/x")

        self.assertEqual(page.outcome, "refused")
        self.assertEqual(page.loss, (public_page.UNSELECTED_TARGET,))
        self.assertEqual(opener.opened, [])
        self.assertNotIn(public_page.AUTH_REQUIRED, page.loss)
        self.assertIn("selection", " ".join(page.warnings))

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        self.assertEqual(public_page.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "public_page.py", "AUTH_REQUIRED"), 0)


class PublicPageOracleCanFailTest(unittest.TestCase):
    """Row 5: the oracle above rejects an adapter a caller can point anywhere."""

    def _wrong(self, name):
        return load_adapter_fixture(name, directory=PUBLIC_PAGE_FIXTURE_DIR)

    def test_an_adapter_that_takes_a_url_from_its_caller_fails_the_oracle(self):
        with self.assertRaisesRegex(AssertionError, "caller chose the host a read went to"):
            assert_the_target_set_is_selected_and_enumerable(
                self, WRONG_PAGE_ADAPTERS[0], self._wrong(WRONG_PAGE_ADAPTERS[0])
            )

    def test_an_adapter_that_selects_nothing_at_all_fails_the_oracle(self):
        # The vacuity direction. Without this clause the oracle would be
        # perfectly satisfied by an adapter with no capability whatsoever,
        # which is the cheapest way to pass a "cannot be pointed anywhere"
        # check.
        with self.assertRaisesRegex(AssertionError, "reaches none of the roster's"):
            assert_the_target_set_is_selected_and_enumerable(
                self, WRONG_PAGE_ADAPTERS[1], self._wrong(WRONG_PAGE_ADAPTERS[1])
            )

    def test_the_url_adapter_would_really_have_read_a_host_nobody_selected(self):
        # The rejection above is not a technicality about a declaration: the
        # call this fixture makes is recorded on the carrier with a host no
        # route in this package declares, which is exactly what a generic HTTP
        # primitive is.
        wrong = self._wrong(WRONG_PAGE_ADAPTERS[0])
        _, opener = selected_page(
            "article.html", target="https://evil.example/x", module=wrong
        )

        self.assertEqual([call.url for call in opener.opened], ["https://evil.example/x"])
        self.assertEqual(
            sorted(
                {
                    urllib.parse.urlsplit(route.origin).netloc
                    for route in transport.ROUTE_CONSTANTS.values()
                    if urllib.parse.urlsplit(route.origin).netloc == "evil.example"
                }
            ),
            [],
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_the_target_set_is_selected_and_enumerable(self, "public_page", public_page)

    def test_nothing_in_the_package_can_reach_either_wrong_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for wrong in WRONG_PAGE_ADAPTERS
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


PAGE_ROUTES = (
    transport.PUBLIC_PAGE_ARTICLE_ROUTE,
    transport.PUBLIC_PAGE_CONTROL_ROUTE,
)
FEED_PAGE_ADAPTERS = ("public_page", "reddit_feed", "rss_atom")
HTTP_STATUSES_EVERY_ROUTE_CAN_ANSWER = (404, 429, 500, 503)


def status_rows(body_fixture, extra):
    """The four statuses every route can answer with, as case rows."""

    return tuple(
        dict(extra, case_name="http_{0}".format(status), status=status,
             body_fixture=body_fixture)
        for status in HTTP_STATUSES_EVERY_ROUTE_CAN_ANSWER
    )


def run_feed_case(module=None):
    def run(row):
        return feed_page(
            row["body_fixture"],
            status=row["status"],
            subreddit=row["subreddit"],
            module=module,
        )

    return run


def run_rss_case(module=None):
    def run(row):
        return rss_atom_page(row["body_fixture"], status=row["status"], module=module)

    return run


def run_page_case(module=None):
    def run(row):
        return selected_page(
            row["body_fixture"], status=row["status"], target=row["target"], module=module
        )

    return run


def feed_page_portal(module, request, seeded):
    """One captive-portal 503 through an adapter, on every route it can reach."""

    portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
        encoding="utf-8"
    )
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (503, portal, "text/html") for route_id in seeded}
    )
    return (module.fetch_native_page(carrier, request), opener)


class FeedPageOneCallOnePageTest(unittest.TestCase):
    """Row 4: one bounded call in, exactly one page out, on one declared route.

    The three adapters here are the roster's last, and two of them are the kind
    that invites a second read. A feed states a window onto recent entries and a
    caller always wants the next one; a page carries links and a page reader is
    one loop away from being a crawler. Neither happens: the core owns
    pagination and stop, so a caller that wants more says so, and an adapter
    that followed a link would turn one bounded call into a walk whose size
    nobody declared.
    """

    def test_every_reddit_feed_answer_costs_one_call_on_its_own_route(self):
        assert_one_answer_costs_one_call(
            self,
            "reddit_feed",
            reddit_feed_cases()
            + status_rows("refused.html", {"subreddit": REDDIT_SUBREDDIT}),
            run_feed_case(),
            (transport.REDDIT_FEED_ROUTE,),
        )

    def test_every_rss_atom_answer_costs_one_call_on_its_own_route(self):
        assert_one_answer_costs_one_call(
            self,
            "rss_atom",
            rss_atom_cases() + status_rows("not_a_feed.html", {}),
            run_rss_case(),
            (transport.YOUTUBE_CHANNEL_FEED_ROUTE,),
        )

    def test_every_public_page_answer_costs_one_call_on_one_of_its_selections(self):
        assert_one_answer_costs_one_call(
            self,
            "public_page",
            page_cases() + status_rows("article_absent.html", {"target": ARTICLE_TARGET}),
            run_page_case(),
            PAGE_ROUTES,
        )

    def test_none_of_the_three_paginates_or_surfaces_a_cursor_to_follow(self):
        # None of these three documents states a next page, so none is derived.
        # A feed publishes a window and a page is one document; inventing a
        # cursor from either would make the adapter the thing that decides
        # there is more.
        answers = (
            feed_page("subreddit_new.xml")[0],
            rss_atom_page("youtube_channel_feed.xml")[0],
            selected_page("article.html")[0],
        )

        for page in answers:
            with self.subTest(adapter=page.adapter_id):
                self.assertEqual(page.cursor_out, "")

    def test_none_of_the_three_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("public_page.py", "public_page"),
            ("reddit_feed.py", "reddit_feed"),
            ("rss_atom.py", "rss_atom"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", (ADAPTER_DIR / module_name).read_text(encoding="utf-8")
                )

    def test_none_of_the_three_touches_the_carrier_itself(self):
        # The channel verdict is read in one place for every adapter there will
        # ever be, and these three inherit it by calling `fetch_one_page`
        # instead of the carrier. An adapter that called `carrier.fetch` would
        # be the one adapter a local block could be recorded as a platform gap
        # through.
        for module_name in ("public_page.py", "reddit_feed.py", "rss_atom.py"):
            with self.subTest(module=module_name):
                source = ADAPTER_DIR / module_name
                attributes = helpers.attribute_names(source)
                imported = helpers.imported_names(source)

                self.assertNotIn("carrier.fetch", attributes)
                self.assertEqual(
                    sorted(name for name in attributes if name.endswith(".fetch")), []
                )
                # And the thing it calls instead is really imported, so the
                # absence above is a delegation rather than an adapter that
                # never reads at all.
                self.assertTrue(
                    any(name.endswith("fetch_one_page") for name in imported),
                    sorted(imported),
                )

    def test_the_same_scan_finds_the_carrier_where_one_is_touched(self):
        # Shown to discriminate rather than to match nothing: the wrong adapter
        # beside the tree reaches the carrier directly, which is exactly how an
        # adapter would end up reading a local block as a platform gap.
        attributes = helpers.attribute_names(
            PUBLIC_PAGE_FIXTURE_DIR / "any_url_adapter.py"
        )

        self.assertIn("carrier.fetch", attributes)

    def test_none_of_the_three_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (reddit_feed, transport.REDDIT_FEED_ROUTE,
             read_reddit_feed("subreddit_new.xml"), feed_request()),
            (rss_atom, transport.YOUTUBE_CHANNEL_FEED_ROUTE,
             read_rss_atom("youtube_channel_feed.xml"), syndication_request()),
            (public_page, transport.PUBLIC_PAGE_ARTICLE_ROUTE,
             read_public_page("article.html"), page_request(ARTICLE_TARGET)),
        )

        for module, route_id, body, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock, {route_id: (200, body, "text/html")}
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing. It matters most on
        # this trio: a 503 login portal answering a feed looks exactly like a
        # subreddit with nothing in it, and answering a page read it looks
        # exactly like a document that moved.
        cases = (
            (reddit_feed, feed_request(), (transport.REDDIT_FEED_ROUTE,)),
            (rss_atom, syndication_request(), (transport.YOUTUBE_CHANNEL_FEED_ROUTE,)),
            (public_page, page_request(ARTICLE_TARGET), PAGE_ROUTES),
            (public_page, page_request("control"), PAGE_ROUTES),
        )

        for module, request, seeded in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id, request=request):
                page, opener = feed_page_portal(module, request, seeded)

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.records, ())
                self.assertEqual(len(opener.opened), 1)

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        # The one refusal the protocol types for every adapter, and the one
        # this trio meets most: Reddit's feed refuses at the second read inside
        # thirty seconds. It is an outcome, never an invitation to ask a
        # different host — and for Reddit there is no other host to ask.
        cases = (
            (reddit_feed, feed_request(), (transport.REDDIT_FEED_ROUTE,)),
            (rss_atom, syndication_request(), (transport.YOUTUBE_CHANNEL_FEED_ROUTE,)),
            (public_page, page_request(ARTICLE_TARGET), PAGE_ROUTES),
        )

        for module, request, seeded in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, opener = helpers.offline_transport(
                    clock,
                    {
                        route_id: (transport.RATE_LIMITED_STATUS, "slow down", "text/plain")
                        for route_id in seeded
                    },
                )

                page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.loss, (transport.RATE_LIMITED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(len(opener.opened), 1)

    def test_every_route_all_three_can_reach_declares_a_budget(self):
        # T08's seam, inherited: `public_page` is the second two-surface
        # adapter, and a surface the core cannot see here is a route the
        # governor refuses to pace — loudly, but at the first live read rather
        # than here.
        budgets = runner.route_budgets()
        reachable = sorted(
            descriptor.route_id
            for adapter_id in FEED_PAGE_ADAPTERS
            for descriptor in runner.surface_descriptors(adapter_id)
        )

        self.assertEqual([route for route in reachable if route not in budgets], [])
        self.assertEqual(len(reachable), len(set(reachable)))
        self.assertEqual(len(reachable), 4)

    def test_the_second_selection_is_paced_rather_than_refused(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.PUBLIC_PAGE_CONTROL_ROUTE: (
                    200,
                    read_public_page("control.html"),
                    "text/html",
                )
            },
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)
        request = page_request("control")

        with helpers.forbid_sleep():
            public_page.fetch_native_page(governor, request)
            public_page.fetch_native_page(governor, request)

        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            adapters.DEFAULT_MIN_INTERVAL_MS * 1000,
        )

    def test_the_reddit_feeds_second_read_waits_the_measured_thirty_seconds(self):
        # The pacing proof that matters, in microseconds of real time rather
        # than in thirty real seconds: a fake clock's sleep moves time without
        # spending any.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.REDDIT_FEED_ROUTE: (
                    200,
                    read_reddit_feed("subreddit_new.xml"),
                    "application/atom+xml",
                )
            },
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        with helpers.forbid_sleep():
            reddit_feed.fetch_native_page(governor, feed_request("LocalLLaMA"))
            reddit_feed.fetch_native_page(governor, feed_request("MachineLearning"))

        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(governor.log[0].waited_us, 0)
        self.assertEqual(
            governor.log[1].at_us - governor.log[0].at_us,
            test_pipeline.REDDIT_FEED_BUDGET.min_interval_ms * 1000,
        )


class FeedPageRouteTtlTest(unittest.TestCase):
    """How long each of the four answers may stand in for a fresh read.

    This is the ticket where the cache stops being an optimization. Reddit's
    feed admits three reads a minute, so a run that asks twice does not run
    slowly — it spends a third of its minute on a question it already asked.
    Every window here is argued from that route's own measured cost and its own
    volatility, and proven from both sides: a re-read inside it that the
    inherited default would have sent back to the origin, and one outside it
    that goes back.

    The control is the interesting one, and it is argued the other way. Its
    whole job is to answer "is this network answering for the origin right
    now", and an answer from a run's own memory cannot answer that about now.
    So it declares a window of zero and is never served from memory — the only
    route in the table where holding an answer would defeat the read.
    """

    def _served(self, clock, route_id, body, content_type="text/html"):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, content_type)}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return (governor, opener)

    def _window(self, route_id, body, module, request, inside, outside):
        """Read, re-read inside the window, re-read past it."""

        clock = helpers.FakeClock()
        governor, opener = self._served(clock, route_id, body)

        first = module.fetch_native_page(governor, request)
        clock.advance(inside)
        held = module.fetch_native_page(governor, request)
        clock.advance(outside - inside)
        expired = module.fetch_native_page(governor, request)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read.
        self.assertEqual(held.observed_at, first.observed_at)
        self.assertEqual(len(held.records), len(first.records))
        # And the window it was held for is longer than the one an undeclared
        # route would have got, so the hit above is this table's doing.
        self.assertGreater(inside, cache.DEFAULT_TTL_SECONDS)
        self.assertLess(inside, cache.ttl_seconds(route_id))
        self.assertGreater(outside, cache.ttl_seconds(route_id))

    def test_a_subreddit_feed_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.REDDIT_FEED_ROUTE,
            read_reddit_feed("subreddit_new.xml"),
            reddit_feed,
            feed_request(),
            inside=120,
            outside=200,
        )

    def test_a_channel_feed_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.YOUTUBE_CHANNEL_FEED_ROUTE,
            read_rss_atom("youtube_channel_feed.xml"),
            rss_atom,
            syndication_request(),
            inside=200,
            outside=400,
        )

    def test_an_article_reread_inside_its_window_is_answered_from_memory(self):
        self._window(
            transport.PUBLIC_PAGE_ARTICLE_ROUTE,
            read_public_page("article.html"),
            public_page,
            page_request(ARTICLE_TARGET),
            inside=700,
            outside=1000,
        )

    def test_the_channel_control_is_never_answered_from_memory(self):
        # Not a short window: no window. A control read exists to say whether
        # the channel is answering, and memory cannot answer that about now. It
        # is the one route in the table where a hit would be a wrong answer
        # rather than a stale one.
        clock = helpers.FakeClock()
        governor, opener = self._served(
            clock, transport.PUBLIC_PAGE_CONTROL_ROUTE, read_public_page("control.html")
        )
        request = page_request("control")

        first = public_page.fetch_native_page(governor, request)
        again = public_page.fetch_native_page(governor, request)

        self.assertEqual(cache.ttl_seconds(transport.PUBLIC_PAGE_CONTROL_ROUTE), 0.0)
        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertNotIn(cache.CACHE_HIT, again.loss)
        self.assertEqual(len(opener.opened), 2)
        # And it is the shortest declared window in the whole table, by
        # construction rather than by comparison.
        self.assertEqual(min(cache.ROUTE_TTL_SECONDS.values()), 0.0)

    def test_the_freshness_probe_is_held_longer_than_the_interval_that_paces_it(self):
        # A window shorter than a route's interval could never bind: the
        # governor would already have made the caller wait longer than the
        # window before the second read arrived. Reddit's is the only route
        # where the two numbers are close enough for that to be a real risk.
        window_ms = cache.ttl_seconds(transport.REDDIT_FEED_ROUTE) * 1000

        self.assertGreater(
            window_ms, runner.route_budgets()[transport.REDDIT_FEED_ROUTE].min_interval_ms
        )
        # Six intervals: enough that a run polling several subreddits never
        # pays twice for one, and short enough that a freshness probe is still
        # about now. It is the window the roster's other "a list that has moved
        # on" route holds, for the same reason.
        self.assertEqual(
            cache.ttl_seconds(transport.REDDIT_FEED_ROUTE),
            cache.ttl_seconds(transport.HN_ALGOLIA_SEARCH_ROUTE),
        )

    def test_the_document_that_changes_only_when_edited_is_held_longest_of_the_four(self):
        # Volatility, not cost. An article carries no counter at all and
        # changes when somebody edits it, so nothing in it goes stale on a
        # run's timescale — which is the argument the roster's other
        # counter-free document is held for the same length of time on.
        declared = {
            route_id: cache.ttl_seconds(route_id) for route_id in FEED_PAGE_ROUTES
        }

        self.assertEqual(
            max(declared, key=lambda route_id: declared[route_id]),
            transport.PUBLIC_PAGE_ARTICLE_ROUTE,
        )
        self.assertEqual(
            cache.ttl_seconds(transport.PUBLIC_PAGE_ARTICLE_ROUTE),
            cache.ttl_seconds(transport.LINKEDIN_PUBLIC_PROFILE_ROUTE),
        )

    def test_three_of_the_four_are_longer_than_a_route_nobody_measured_gets(self):
        held = [
            route_id
            for route_id in FEED_PAGE_ROUTES
            if cache.ttl_seconds(route_id) > cache.DEFAULT_TTL_SECONDS
        ]

        self.assertEqual(
            sorted(held),
            [
                transport.PUBLIC_PAGE_ARTICLE_ROUTE,
                transport.REDDIT_FEED_ROUTE,
                transport.YOUTUBE_CHANNEL_FEED_ROUTE,
            ],
        )

    def test_the_bodies_these_routes_answer_with_fit_inside_the_run_footprint(self):
        # A window on a body over the entry cap never binds — the LinkedIn
        # profile route is the roster's example. These fixtures fit, so the
        # windows above bind on them. The cap itself is untouched: this ticket
        # declares windows, not a run footprint.
        for fixture, read in (
            ("subreddit_new.xml", read_reddit_feed),
            ("youtube_channel_feed.xml", read_rss_atom),
            ("article.html", read_public_page),
            ("control.html", read_public_page),
        ):
            with self.subTest(body=fixture):
                self.assertLess(len(read(fixture).encode("utf-8")), cache.MAX_ENTRY_BYTES)
        self.assertEqual(cache.MAX_ENTRY_BYTES, 512 * 1024)

    def test_every_route_this_ticket_declares_has_a_window_argued_for_it(self):
        for route_id in sorted(FEED_PAGE_ROUTES):
            with self.subTest(route=route_id):
                self.assertIn(route_id, cache.ROUTE_TTL_SECONDS)


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
