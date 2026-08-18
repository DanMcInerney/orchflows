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
The 2026-08-10 probes recorded both halves: `SearchTimeline` and `TweetDetail`
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
fixtures carry the shape and field set the 2026-08-10 probes record; the evidence
records no captured bodies, and this package may not reach the network to make
one, so what they prove is that this code reads that shape correctly.
Criterion 12's live smoke is what proves the shape.

One of those shapes has since been measured wrong, and the correction is
`CAPTURED_SYNDICATION_INSTANT` below — the only literal in this file taken off
a live origin. Every `created_at` in `fixtures/x/` is spelled
`2026-08-09T07:00:00.000Z`, which is what this package assumed; the route sends
`Sun Jul 13 04:58:11 +0000 2025`. Reading the route's spelling back off the
corpus is how `D1` was written, so read it off the capture instead.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import locale
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, cache, normalize, probes, runner, schema, smoke, transport
from super_research.adapters import fake
from super_research.adapters import github_rest, hacker_news, instagram_public
from super_research.adapters import public_page, reddit_archive, reddit_feed, rss_atom
from super_research.adapters import linkedin_jobs
from super_research.adapters import linkedin_public
from super_research.adapters import x_guest, x_syndication, youtube_innertube
from tests import helpers, test_pipeline
from tests.test_transport import ROUTE_OWNING_MODULES


TEST_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TEST_DIR / "fixtures" / "x"
LINKEDIN_FIXTURE_DIR = TEST_DIR / "fixtures" / "linkedin"
# T02's captive-portal body, read rather than copied: an adapter inherits
# interception typing from the protocol, and the proof has to be the same
# measured body the transport suite uses or it proves something else.
TRANSPORT_FIXTURE_DIR = TEST_DIR / "fixtures" / "transport"
PACKAGE_DIR = TEST_DIR.parent / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
GUEST_QUERY_ID = "V7H0Ap3_Hh2FyS75OCDO3Q"
MINTED_GUEST_TOKEN = "1804400000000000000"

# The 2026-08-10 probes (X): every field the syndication row records this route
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

    source = adapter_owner_source(path)
    return sorted(
        adapter_id
        for adapter_id in runner.ADAPTER_IDS
        if adapter_id != own_id and adapter_id in source
    )


def adapter_owner_paths(path):
    """One facade and the private support modules it imports directly."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    helpers = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level != 1:
            continue
        parts = (node.module or "").split(".")
        if not parts or parts[0] != "_support":
            continue
        helper = path.parent.joinpath(*parts).with_suffix(".py")
        if helper.is_file():
            helpers.append(helper)
    return (path,) + tuple(sorted(set(helpers)))


def adapter_owner_source(path):
    """The source read as one logical adapter owner, never as dispatch modules."""

    return "\n".join(
        owner.read_text(encoding="utf-8") for owner in adapter_owner_paths(path)
    )


def _next_data(entries):
    """One `__NEXT_DATA__` page holding exactly the timeline entries given."""

    payload = {"props": {"pageProps": {"timeline": {"entries": entries}}}}
    return (
        '<html><body><script id="__NEXT_DATA__">'
        + json.dumps(payload)
        + "</script></body></html>"
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



# Test classes stay discoverable through this structural facade.
from tests.test_adapters_cases.x_routes import *  # noqa: F401,F403
from tests.test_adapters_cases.x_stamps import *  # noqa: F401,F403
from tests.test_adapters_cases.x_stale_and_artifact import *  # noqa: F401,F403
from tests.test_adapters_cases.linkedin_jobs_and_profile import *  # noqa: F401,F403
from tests.test_adapters_cases.linkedin_claims import *  # noqa: F401,F403
from tests.test_adapters_cases.linkedin_ttl_and_artifact import *  # noqa: F401,F403
from tests.test_adapters_cases.youtube_instagram_routes import *  # noqa: F401,F403
from tests.test_adapters_cases.instagram_behavior import *  # noqa: F401,F403
from tests.test_adapters_cases.youtube_search_and_comments import *  # noqa: F401,F403
from tests.test_adapters_cases.youtube_viewmodels_and_player import *  # noqa: F401,F403
from tests.test_adapters_cases.youtube_attestation import *  # noqa: F401,F403
from tests.test_adapters_cases.youtube_oracles_and_calls import *  # noqa: F401,F403
from tests.test_adapters_cases.youtube_ttl_and_artifact import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_github_routes import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_read import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_claims import *  # noqa: F401,F403
from tests.test_adapters_cases.github_read import *  # noqa: F401,F403
from tests.test_adapters_cases.github_write_safety import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_github_calls import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_github_ttl import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_github_artifact import *  # noqa: F401,F403
from tests.test_adapters_cases.feed_page_routes import *  # noqa: F401,F403
from tests.test_adapters_cases.reddit_feed import *  # noqa: F401,F403
from tests.test_adapters_cases.rss_atom import *  # noqa: F401,F403
from tests.test_adapters_cases.public_page_read import *  # noqa: F401,F403
from tests.test_adapters_cases.public_page_claims import *  # noqa: F401,F403
from tests.test_adapters_cases.feed_page_calls_and_ttl import *  # noqa: F401,F403
from tests.test_adapters_cases.feed_page_artifact import *  # noqa: F401,F403
from tests.test_adapters_cases.unrecognized_and_roster import *  # noqa: F401,F403
from tests.test_adapters_cases.fake_attributes import *  # noqa: F401,F403
