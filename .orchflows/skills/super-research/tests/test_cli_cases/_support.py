"""CLI suite: the nineteen liveness smokes, proven without reaching an origin.

The smoke subcommand is the one operation in this package that talks to a real
platform, and this suite is the reason it can be trusted before it ever does.
Every row here runs against the measured payloads the adapters were built from,
under a guard that turns any socket into a failure, so what is proven offline is
the mechanism: the probe each adapter reads on, the roster field set it asserts,
the way a stale success degrades, and the way a response from this host's own
network appliance is told apart from a platform gap.

What a stand-in must carry. The fake opener here sits *above*
``transport.answering_address``, so a seeded answering address is one that has
already had its route's credential stripped — the shape the real opener hands
back. ``public_page`` is the one adapter that reads it, its roster row names
redirects, and the seed for it therefore answers from a different address than
it was asked at and the check compares against that address rather than merely
requiring one. A three-value seed would have let the requested url stand in for
the answering one and made the redirect field pass by falling back.
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import io
import json
import re
import socket
import tempfile
import unittest
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from super_research import cli, runner, schema, transport
from tests import helpers

TESTS_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = TESTS_DIR / "fixtures"
CLI_FIXTURE_DIR = FIXTURE_DIR / "cli"
REPOSITORY_ROOT = TESTS_DIR.parents[3]

# One frozen moment for every ledger row, and one adapter to hold the laws
# against. `rejected` is the word no disposition may ever be; it is spelled
# here so the checks can look for it.
NOW = helpers.FROZEN_START
ADAPTER = "github_rest"
REJECTED = "rejected"

# A guest token, minted into the process's own store, so "nothing the run holds
# reaches the output" is checked against something the run really held.
GUEST_TOKEN = "guest-token-minted-for-this-run"


def stamp_at(offset_seconds):
    """One instant relative to the frozen moment, in the ledger's own format."""

    moment = datetime.strptime(NOW, helpers.STAMP_FORMAT).replace(tzinfo=timezone.utc)
    return (moment + timedelta(seconds=offset_seconds)).strftime(helpers.STAMP_FORMAT)

# One measured payload per route a smoke reads, by the route that answered with
# it. These are the same bytes the adapters were built against — a smoke proven
# on a payload written for the smoke would prove only that two of my own files
# agree.
PROBE_PAYLOADS = {
    "ddg_html": ("tracer/ddg_html_results.html", "text/html; charset=utf-8"),
    "arctic_shift_posts_ids": (
        "tracer/arctic_shift_posts_ids.json", "application/json",
    ),
    "reddit_feed": ("reddit_feed/subreddit_new.xml", "application/atom+xml"),
    "youtube_channel_feed": ("rss_atom/youtube_channel_feed.xml", "text/xml; charset=UTF-8"),
    "x_syndication_timeline": ("x/syndication_timeline.html", "text/html; charset=utf-8"),
    "x_guest_graphql": ("x/guest_user_by_screen_name.json", "application/json;charset=utf-8"),
    "linkedin_jobs_guest_search": ("linkedin/jobs_search_page.html", "text/html; charset=utf-8"),
    "linkedin_public_profile": ("linkedin/profile_person.html", "text/html; charset=utf-8"),
    "youtube_innertube": ("youtube/player_metadata.json", "application/json; charset=UTF-8"),
    "instagram_web_profile": ("instagram/web_profile_info.json", "application/json; charset=utf-8"),
    "hn_algolia_search": ("hacker_news/algolia_search_by_date.json", "application/json"),
    "github_rest": ("github/repo.json", "application/json; charset=utf-8"),
    "public_page_article": ("public_page/article.html", "text/html; charset=UTF-8"),
    "reddit_shreddit_listing": ("reddit_shreddit/listing.html", "text/html; charset=utf-8"),
    "web_page_open": ("open_page/article.html", "text/html; charset=utf-8"),
    "polymarket_gamma": (
        "prediction_markets/polymarket_public_search.json", "application/json",
    ),
    "stocktwits_symbol_stream": ("stocktwits/stream.json", "application/json; charset=utf-8"),
    "bluesky_author_feed": ("bluesky/author_feed.json", "application/json; charset=utf-8"),
    "fxtwitter_api": ("x_fxtwitter/search.json", "application/json"),
    "gdelt_doc": ("gdelt/doc_artlist.json", "application/json; charset=utf-8"),
    "stackexchange_search_advanced": (
        "stack_exchange/search_advanced.json", "application/json; charset=utf-8",
    ),
    "wikimedia_pageviews_per_article": (
        "wikimedia_pageviews/per_article_daily.json", "application/json; charset=utf-8",
    ),
    "openalex_works": ("scholarly/openalex_works.json", "application/json; charset=utf-8"),
    "tiktok_video_page": ("tiktok_public/video_page.html", "text/html; charset=utf-8"),
    "x_publish_oembed": ("oembed/x_status.json", "application/json"),
}

# The one route whose adapter reads the answering address. It answers from
# somewhere other than where it was asked, so "this record carries the address
# that answered" is a claim about the response and not about the request.
REDIRECTED_ROUTE = "public_page_article"
ANSWERED_FROM = "https://en.wikipedia.org/wiki/Rate_limiting?veaction=edit"


def payload(name):
    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def probe_seeds():
    """One canned origin answer per route the nineteen smokes read."""

    seeds = {}
    for route_id, (name, content_type) in PROBE_PAYLOADS.items():
        answer = (200, payload(name), content_type)
        if route_id == REDIRECTED_ROUTE:
            answer = answer + (ANSWERED_FROM,)
        seeds[route_id] = answer
    return seeds


@contextlib.contextmanager
def forbid_network():
    """Fail the test if a socket is opened, while leaving the filesystem alone.

    ``helpers.forbid_io`` refuses both, and every row that reads no file uses
    it. The ledger rows write one, so they need the network half by itself —
    same refusing socket, so a read that escaped the seeded opener raises here
    exactly as it does there.
    """

    def refuse(*args, **kwargs):
        raise AssertionError("the network was reached inside a zero-egress guard")

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(socket, "socket", helpers.RefusingSocket))
        stack.enter_context(mock.patch.object(socket, "create_connection", refuse))
        stack.enter_context(mock.patch.object(urllib.request, "urlopen", refuse))
        yield


def observe_offline(probe, seeds=None, clock=None):
    """One smoke, against canned answers, with every socket refused."""

    resolved = helpers.FakeClock() if clock is None else clock
    # Seeded before the guard: reading a fixture off this disk is an input to
    # the test, and the guard is here to prove the package reaches nothing.
    answers = probe_seeds() if seeds is None else seeds
    carrier, opener = helpers.offline_transport(resolved, answers)
    with helpers.forbid_io():
        observation = cli.observe(
            probe, carrier, clock=resolved.monotonic, now=resolved.stamp
        )
    return observation, opener


def load_beside_the_tree(name):
    """Load one wrong implementation written beside the tree, by path."""

    path = CLI_FIXTURE_DIR / (name + ".py")
    spec = importlib.util.spec_from_file_location("cli_fixture_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observation(adapter_id="github_rest", outcome="ok", loss=(), missing=(), records=1):
    """One observation, spelled by hand, so a law can be checked without a read."""

    return cli.SmokeObservation(
        adapter_id=adapter_id,
        route_id="github_rest",
        outcome=outcome,
        loss=loss,
        records_kept=records,
        channel=cli.channel_of(outcome, loss),
        missing=missing,
        facts=(),
        observed_at=NOW,
    )


def intercepted(adapter_id="github_rest"):
    """What this host's own appliance answering looks like by the time it lands.

    `failed`, with no rows, and the loss code as the only thing saying the
    origin was never reached. The captive-portal caveat measured it: 503 with a login
    portal in the body, for domains this network intercepts.
    """

    return observation(
        adapter_id=adapter_id,
        outcome="failed",
        loss=(transport.NETWORK_INTERCEPTED,),
        missing=(("repository", cli.NO_RECORD_OF_THIS_KIND),),
        records=0,
    )


def origin_failure(adapter_id="github_rest"):
    """A refusal the platform itself sent: same outcome, no interception code."""

    return observation(
        adapter_id=adapter_id,
        outcome="failed",
        loss=("http_status",),
        missing=(("repository", cli.NO_RECORD_OF_THIS_KIND),),
        records=0,
    )


def assert_stale_degrades_to_unverified(case, disposition_of):
    """Row 2, over whatever renderer it is handed.

    Five ledgers and one clock. The window is the only thing that may turn a
    recorded success into a current one, and every way of not having a current
    success lands on `unverified` — never on silent success, and never on a
    word that blames the platform.
    """

    fresh = {ADAPTER: stamp_at(-3600)}
    stale = {ADAPTER: stamp_at(-(cli.SMOKE_MAX_AGE_SECONDS + 3600))}
    edge = {ADAPTER: stamp_at(-(cli.SMOKE_MAX_AGE_SECONDS - 60))}
    ahead = {ADAPTER: stamp_at(3600)}
    unreadable = {ADAPTER: "last Tuesday"}

    current = disposition_of(fresh, ADAPTER, NOW)
    case.assertEqual(current.state, cli.VERIFIED)
    case.assertEqual(current.reason, cli.FRESH_SUCCESS)
    case.assertEqual(disposition_of(edge, ADAPTER, NOW).state, cli.VERIFIED)

    aged = disposition_of(stale, ADAPTER, NOW)
    case.assertEqual(aged.state, cli.UNVERIFIED, "a stale success was not degraded")
    case.assertEqual(aged.reason, cli.STALE_SUCCESS)
    # The evidence is kept, not erased: unverified says "re-prove this", and a
    # renderer that dropped the stamp would leave nothing to say how long ago.
    case.assertEqual(aged.last_success, stale[ADAPTER])

    never = disposition_of({}, ADAPTER, NOW)
    case.assertEqual(never.state, cli.UNVERIFIED)
    case.assertEqual(never.reason, cli.NEVER_SMOKED)

    # A stamp ahead of now cannot buy freshness: a hand-edited or skewed ledger
    # would otherwise read as verified for as long as it stayed in the future.
    case.assertEqual(disposition_of(ahead, ADAPTER, NOW).state, cli.UNVERIFIED)
    case.assertEqual(disposition_of(unreadable, ADAPTER, NOW).state, cli.UNVERIFIED)

    for ledger in (fresh, stale, edge, ahead, unreadable, {}):
        rendered = disposition_of(ledger, ADAPTER, NOW)
        case.assertIn(rendered.state, cli.SMOKE_DISPOSITIONS)
        case.assertIn(rendered.reason, cli.SMOKE_REASONS)
        case.assertNotEqual(rendered.state, REJECTED)


def assert_interception_degrades_nothing(case, channel_of, ledger_after):
    """Row 3, over whatever pair it is handed.

    Both halves. The local block has to be *named* as one — an implementation
    that called everything local would pass a check that only looked at the
    intercepted case — and it has to leave the adapter's standing evidence
    exactly as it found it.
    """

    case.assertEqual(
        channel_of("failed", (transport.NETWORK_INTERCEPTED,)),
        cli.ANSWERED_BY_LOCAL_NETWORK,
        "an intercepted read was not named as a local-network answer",
    )
    case.assertEqual(channel_of("failed", ("http_status",)), cli.ANSWERED_BY_ORIGIN)
    case.assertEqual(channel_of("ok", ()), cli.ANSWERED_BY_ORIGIN)
    case.assertEqual(
        channel_of("failed", ("rate_limited",)),
        cli.ANSWERED_BY_ORIGIN,
        "an origin asking for fewer requests is the origin answering",
    )

    held = {ADAPTER: stamp_at(-3600), "reddit_feed": stamp_at(-7200)}

    case.assertEqual(
        ledger_after(held, intercepted(ADAPTER), NOW),
        held,
        "a local block changed what the ledger holds",
    )
    case.assertEqual(
        ledger_after(held, origin_failure(ADAPTER), NOW),
        held,
        "a failed read revoked a success that had already been proven",
    )
    # A local answer can never be recorded as a success, even if something
    # upstream handed one that claimed its field set was satisfied.
    case.assertEqual(
        ledger_after(
            held,
            cli.SmokeObservation(
                adapter_id=ADAPTER,
                route_id="github_rest",
                outcome="failed",
                loss=(transport.NETWORK_INTERCEPTED,),
                records_kept=0,
                channel=cli.ANSWERED_BY_LOCAL_NETWORK,
                missing=(),
                facts=(),
                observed_at=NOW,
            ),
            NOW,
        ),
        held,
    )
    # And the positive control: a renderer that changed nothing ever would
    # satisfy every line above.
    recorded = ledger_after(held, observation(ADAPTER), NOW)
    case.assertEqual(recorded[ADAPTER], NOW)
    case.assertEqual(recorded["reddit_feed"], held["reddit_feed"])


def run_cli(case, argv, seeds=None, ledger_path=None, clock=None):
    """One whole invocation, argv in and printed lines out, reaching no socket."""

    resolved = helpers.FakeClock() if clock is None else clock
    answers = probe_seeds() if seeds is None else seeds
    carrier, opener = helpers.offline_transport(resolved, answers)
    printed = io.StringIO()
    with forbid_network():
        code = cli.main(
            argv,
            carrier=carrier,
            clock=resolved.monotonic,
            now=resolved.stamp,
            ledger_path=case.path if ledger_path is None else ledger_path,
            out=printed,
        )
    return code, printed.getvalue(), opener


def status_row(case, printed, adapter_id):
    """One adapter's row of `status` output, as its four columns.

    Read by column rather than by substring: `verified` is a substring of
    `unverified`, so a row asserted with ``assertIn`` passes on the word that
    means the opposite of what it was checking for.
    """

    rows = [
        line.split()
        for line in printed.splitlines()
        if line.strip() and line.split()[0] == adapter_id
    ]
    case.assertEqual(len(rows), 1, "status printed {0} rows for {1}".format(len(rows), adapter_id))
    case.assertEqual(len(rows[0]), 4, "a status row is four columns: " + " ".join(rows[0]))
    return rows[0]


# The two shapes a smoke's last line takes, from the two branches that print
# one: an ordinary read says what the adapter *is*, and a read this host's own
# network answered says what standing it *kept*.
SMOKE_STANDING = re.compile(
    r"^  (?P<adapter>[a-z_]+) (?:is|keeps the standing it had:) "
    r"(?P<state>[a-z]+) \((?P<reason>[a-z_]+)"
)


def smoke_standing(case, printed, adapter_id):
    """The state and reason a smoke's own report leaves this adapter at.

    Read by position rather than by substring, because `verified` is a
    substring of `unverified`: every row that asserted the first with
    ``assertIn`` also passed on the second, which is the word meaning the
    opposite of what it was checking for.
    """

    found = [
        (match.group("state"), match.group("reason"))
        for match in (SMOKE_STANDING.match(line) for line in printed.splitlines())
        if match and match.group("adapter") == adapter_id
    ]
    case.assertEqual(
        len(found), 1, "the smoke printed {0} standings for {1}".format(len(found), adapter_id)
    )
    return found[0]


def refused(case, argv):
    """One invocation the surface must refuse before anything is read."""

    carrier, opener = helpers.offline_transport(helpers.FakeClock(), {})
    complaint = io.StringIO()
    with contextlib.redirect_stderr(complaint):
        with forbid_network():
            with case.assertRaises(SystemExit) as caught:
                cli.main(argv, carrier=carrier, ledger_path=case.path, out=io.StringIO())
    case.assertEqual(caught.exception.code, cli.EXIT_USAGE)
    case.assertEqual(opener.opened, [], "a refused invocation still made a read")


class LedgerHoldingCase(unittest.TestCase):
    """Every CLI row writes its ledger into a temporary directory, never the default."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "smoke-ledger.json"
