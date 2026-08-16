"""CLI suite: the thirteen liveness smokes, proven without reaching an origin.

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

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
CLI_FIXTURE_DIR = FIXTURE_DIR / "cli"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]

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
}

# The one route whose adapter reads the answering address. It answers from
# somewhere other than where it was asked, so "this record carries the address
# that answered" is a claim about the response and not about the request.
REDIRECTED_ROUTE = "public_page_article"
ANSWERED_FROM = "https://en.wikipedia.org/wiki/Rate_limiting?veaction=edit"


def payload(name):
    return FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def probe_seeds():
    """One canned origin answer per route the thirteen smokes read."""

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


class SmokeProbeTableTest(unittest.TestCase):
    """The enumeration itself: thirteen probes, each naming things that exist."""

    def test_the_probes_are_exactly_the_live_roster(self):
        # Derived against the core's own roster rather than transcribed beside
        # it: an adapter added to the package with no smoke, and a smoke for an
        # adapter the core cannot reach, are the same defect from two ends.
        probed = sorted(probe.adapter_id for probe in cli.SMOKE_PROBES)

        self.assertEqual(probed, sorted(set(runner.ADAPTER_IDS) - {cli.OFFLINE_ADAPTER}))
        self.assertEqual(len(cli.SMOKE_PROBES), 13)

    def test_the_offline_adapter_has_no_smoke(self):
        # `fake` reads a fixture. A smoke for it would report the suite's own
        # health as the platform's.
        self.assertIn(cli.OFFLINE_ADAPTER, runner.ADAPTER_IDS)
        self.assertIsNone(cli.probe_for(cli.OFFLINE_ADAPTER))
        self.assertIsNone(cli.probe_for("no_such_adapter"))

    def test_every_probe_names_a_step_kind_and_a_bounded_cap(self):
        for probe in cli.SMOKE_PROBES:
            with self.subTest(adapter=probe.adapter_id):
                self.assertIn(probe.kind, schema.STEP_KINDS)
                self.assertTrue(probe.target)
                self.assertGreater(probe.max_items, 0)

    def test_every_probe_asserts_a_field_set_a_record_could_carry(self):
        record_fields = {field.name for field in dataclasses.fields(schema.AcquisitionRecord)}
        for probe in cli.SMOKE_PROBES:
            self.assertTrue(probe.field_sets, probe.adapter_id)
            for kind, names in probe.field_sets:
                with self.subTest(adapter=probe.adapter_id, kind=kind):
                    self.assertTrue(kind)
                    self.assertTrue(names)
                    for name in names:
                        if name.startswith(cli.ENGAGEMENT_PREFIX):
                            self.assertTrue(name[len(cli.ENGAGEMENT_PREFIX):])
                        elif name.startswith(cli.ATTRIBUTE_PREFIX):
                            self.assertTrue(name[len(cli.ATTRIBUTE_PREFIX):])
                        else:
                            self.assertIn(name, record_fields)

    def test_every_probe_reads_a_route_the_core_can_reach(self):
        for probe in cli.SMOKE_PROBES:
            with self.subTest(adapter=probe.adapter_id):
                routes = {
                    descriptor.route_id
                    for descriptor in runner.surface_descriptors(probe.adapter_id)
                }

                self.assertIn(probe.route_id, routes)
                self.assertIn(probe.route_id, transport.ROUTE_CONSTANTS)

    def test_a_probe_that_can_rot_carries_the_way_back(self):
        # A query never goes stale; a named item, slug or channel id can. The
        # package already declares a rotating vendor identifier with its
        # recovery procedure, and a probe target is the same shape.
        for probe in cli.SMOKE_PROBES:
            if probe.kind == "hydration":
                with self.subTest(adapter=probe.adapter_id):
                    self.assertTrue(probe.target_recovery)


# The two probes whose measured first page states that the index holds another:
# DDG answers with its own "Next" offset, Algolia with `page` and `nbPages`.
# A smoke is one ordinary discovery step and has no private path into an
# adapter, so the core would spend that cursor here as it does anywhere. What
# stops it is the step's own page bound: `smoke.probe_step` declares one page,
# and every row below runs over all thirteen probes rather than over these two,
# so a fourteenth arrives already bounded. They are named because they are
# where the bound is load-bearing — the eleven others would cost one read
# whatever the core did, and a suite that proved it only on them would be
# proving nothing.
PROBES_WHOSE_FIRST_PAGE_CLAIMS_ANOTHER = ("web_search", "hacker_news")

# The measured DDG page's forward offset, and the seed built by moving it. Six
# answers, each naming an offset no earlier one named, is the one shape that
# defeats every stop but a page bound: the index never stops offering and never
# repeats itself. Six because the core's own backstop is five, so a read that
# got past the bound is visible as five reads rather than as running out of
# answers.
NEXT_OFFSET_MARKUP = '<input type="hidden" name="s" value="{0}" />'
OFFERS_A_NEW_PAGE_EVERY_TIME = 6


def ddg_pages_each_offering_a_new_one():
    """The measured search page, six times, each pointing somewhere new."""

    name, content_type = PROBE_PAYLOADS[transport.DDG_HTML_ROUTE]
    body = payload(name)
    return [
        (
            200,
            body.replace(
                NEXT_OFFSET_MARKUP.format(30), NEXT_OFFSET_MARKUP.format(30 * (index + 1))
            ),
            content_type,
        )
        for index in range(OFFERS_A_NEW_PAGE_EVERY_TIME)
    ]


class SmokeAssertsTheRosterFieldSetTest(unittest.TestCase):
    """Row 1: thirteen smokes, each bounded, against measured bytes."""

    def test_every_smoke_asserts_its_roster_field_set_on_the_reads_it_spends(self):
        for probe in cli.SMOKE_PROBES:
            with self.subTest(adapter=probe.adapter_id):
                observation, opener = observe_offline(probe)

                self.assertEqual(observation.missing, ())
                self.assertTrue(cli.satisfied(observation))
                self.assertEqual(observation.adapter_id, probe.adapter_id)
                self.assertEqual(observation.route_id, probe.route_id)
                self.assertEqual(observation.channel, cli.ANSWERED_BY_ORIGIN)
                self.assertGreater(observation.records_kept, 0)
                # On the probe's own route and on no other, and exactly once.
                # Thirteen probes, thirteen origin reads — including the two
                # whose first page says the index holds more, which is what the
                # user authorizing this egress was told it would cost.
                self.assertEqual(
                    {request.route_id for request in opener.opened}, {probe.route_id}
                )
                self.assertEqual(len(opener.opened), 1)

    def test_no_smoke_is_reported_partial_for_stopping_where_it_meant_to(self):
        # A bound the step declared is the caller's own, so reaching it is the
        # read finishing. Two of the thirteen stop with the index still
        # offering and neither is a recall window cut short: one page is the
        # whole of what a liveness read asked for. A cap under a measured page
        # size would be the other way to report a whole answer as a truncated
        # one, and none of the thirteen does that either.
        for probe in cli.SMOKE_PROBES:
            with self.subTest(adapter=probe.adapter_id):
                observation, _ = observe_offline(probe)

                self.assertIn(observation.outcome, ("ok", "empty"))
                self.assertNotIn("recall_window_partial", observation.loss)

    def test_the_field_set_check_names_what_a_thinned_answer_dropped(self):
        # The oracle can fail: the same read, with one roster field emptied in
        # the payload, is reported missing by name rather than passing.
        probe = cli.probe_for("github_rest")
        seeds = probe_seeds()
        status, body, content_type = seeds[probe.route_id]
        seeds[probe.route_id] = (
            status, body.replace('"stargazers_count"', '"stargazers_count_renamed"'), content_type
        )

        observation, _ = observe_offline(probe, seeds=seeds)

        self.assertFalse(cli.satisfied(observation))
        self.assertIn(
            ("repository", cli.ENGAGEMENT_PREFIX + "stargazers_count"), observation.missing
        )

    def test_an_answer_holding_no_row_at_all_is_missing_the_whole_kind(self):
        probe = cli.probe_for("reddit_archive")
        seeds = probe_seeds()
        seeds[probe.route_id] = (200, '{"data": []}', "application/json")

        observation, _ = observe_offline(probe, seeds=seeds)

        self.assertFalse(cli.satisfied(observation))
        self.assertEqual(observation.records_kept, 0)
        self.assertEqual(observation.missing, (("post", cli.NO_RECORD_OF_THIS_KIND),))

    def test_the_one_adapter_that_reads_the_answering_address_reads_it(self):
        # T11's lesson, applied to this seam: an opener that reported no
        # address would let the requested url stand in for the answering one,
        # and `public_page`'s redirect field would pass without a redirect.
        probe = cli.probe_for("public_page")

        observation, _ = observe_offline(probe)

        carried = dict(observation.facts)

        self.assertEqual(observation.missing, ())
        self.assertEqual(carried["web_page " + cli.ATTRIBUTE_PREFIX + "final_url"], ANSWERED_FROM)
        self.assertNotEqual(
            carried["web_page " + cli.ATTRIBUTE_PREFIX + "requested_url"], ANSWERED_FROM
        )

    def test_a_loss_code_on_a_complete_read_is_not_a_failure(self):
        # The measured YouTube player answer carries `attestation_required`:
        # the metadata arrived and only the caption tracks were withheld. A
        # smoke that read that as a failed run would report a working route as
        # a platform gap.
        probe = cli.probe_for("youtube_innertube")

        observation, _ = observe_offline(probe)

        self.assertIn("attestation_required", observation.loss)
        self.assertEqual(observation.outcome, "ok")
        self.assertTrue(cli.satisfied(observation))
        self.assertEqual(observation.channel, cli.ANSWERED_BY_ORIGIN)


class ASmokeIsOneReadTest(unittest.TestCase):
    """The spec's binding constraint: no probe exceeds what the smoke authorizes.

    The rows above already cost one origin read each, and eleven of them would
    whatever the core did — their measured page names nothing after it. What is
    left to prove is the case that would page: an index that goes on offering,
    somewhere new every time, so that neither a cursor it has already spent nor
    a page that names none can be what ends the step. On that seed the bound is
    the only thing standing between a liveness check and five reads of a real
    origin's budget, and the second row here is what says so by measuring the
    same seed without it.
    """

    def bounded_and_unbounded(self):
        """One probe's step as a smoke declares it, and as an ordinary step does."""

        probe = cli.probe_for("web_search")
        seeds = probe_seeds()
        seeds[probe.route_id] = ddg_pages_each_offering_a_new_one()
        return (probe, seeds)

    def test_a_smoke_reads_one_page_of_an_index_that_offers_a_new_one_every_time(self):
        probe, seeds = self.bounded_and_unbounded()

        observation, opener = observe_offline(probe, seeds=seeds)

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(observation.outcome, "ok")
        self.assertNotIn("recall_window_partial", observation.loss)
        self.assertTrue(cli.satisfied(observation))

    def test_the_same_index_pages_to_the_core_cap_for_a_step_that_declared_none(self):
        # The half that makes the row above mean something: same adapter, same
        # seeds, same cap, and the one difference is the page bound the smoke's
        # step declares. It is also what proves the seed is what it claims — if
        # the offsets came back identical, the repeated-cursor stop would end
        # this step at two and this row would redden rather than the bound
        # quietly going untested.
        probe, seeds = self.bounded_and_unbounded()
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, seeds)

        with helpers.forbid_io():
            result, _, _ = runner.run_step(
                schema.AcquisitionStep(
                    step_id="declares-no-page-bound",
                    kind="discovery",
                    adapter_id=probe.adapter_id,
                    query=probe.target,
                    max_items=probe.max_items,
                ),
                carrier,
                "artifact:declares-no-page-bound",
                "m-declares-no-page-bound",
                clock=clock.monotonic,
            )

        self.assertEqual(len(opener.opened), runner.MAX_PAGES_PER_STEP)
        self.assertEqual(result.outcome, "partial")
        self.assertIn("recall_window_partial", result.loss)

    def test_a_probe_this_table_has_never_held_inherits_the_bound(self):
        # The bound is not a column of the probe table — it is what a smoke is,
        # applied where the step is built — so a probe declared later gets it
        # without knowing anything about paging. This one is declared here and
        # never reaches `SMOKE_PROBES`.
        _, seeds = self.bounded_and_unbounded()
        later = cli.SmokeProbe(
            adapter_id="web_search",
            kind="discovery",
            target="rate limiting",
            route_id=transport.DDG_HTML_ROUTE,
            field_sets=(("web_hit", ("title", "canonical_locator")),),
        )

        observation, opener = observe_offline(later, seeds=seeds)

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(observation.missing, ())
        self.assertNotIn("recall_window_partial", observation.loss)


class TheSuiteReachesNoNetworkTest(unittest.TestCase):
    """Row 5: proven by a socket that cannot be opened, not by reading the code."""

    def test_the_guard_fails_a_test_that_opens_a_socket(self):
        with self.assertRaises(AssertionError):
            with forbid_network():
                socket.socket()

        with self.assertRaises(AssertionError):
            with helpers.forbid_io():
                socket.socket()

    def test_no_smoke_in_this_suite_touches_a_socket(self):
        # Every observation above already runs inside `helpers.forbid_io`; this
        # states it once as its own row, over all thirteen, so the property is
        # a check rather than a convention the next row could forget.
        # The payloads are read first, outside the guard: a fixture on this
        # disk is an input to the test, and the guard exists to prove the
        # package reaches nothing.
        seeds = probe_seeds()
        for probe in cli.SMOKE_PROBES:
            with self.subTest(adapter=probe.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(clock, seeds)
                with helpers.forbid_io():
                    cli.observe(probe, carrier, clock=clock.monotonic, now=clock.stamp)

    def test_an_unseeded_route_fails_loudly_rather_than_egressing(self):
        # The opener still refuses an unseeded route rather than reaching for a
        # socket; what changed is where the refusal is read. `run_step` types it
        # now, so the loud failure is a `failed` step carrying `unreachable` and
        # no records — a quiet one would be an empty page with outcome `ok`,
        # which is the shape this row exists to make impossible.
        probe = cli.probe_for("hacker_news")

        observation, _ = observe_offline(probe, seeds={})

        self.assertEqual(observation.outcome, "failed")
        self.assertIn(transport.UNREACHABLE, observation.loss)
        self.assertEqual(observation.records_kept, 0)
        self.assertEqual(observation.channel, cli.ANSWERED_BY_LOCAL_NETWORK)


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


class StaleSmokeDegradesTest(unittest.TestCase):
    """Row 2: a recorded success expires, and expiry is proven on a fake clock."""

    def test_the_disposition_renderer_degrades_a_stale_success(self):
        assert_stale_degrades_to_unverified(self, cli.disposition_of)

    def test_staleness_is_the_window_and_nothing_else(self):
        # Proven by moving the clock rather than by waiting: the same ledger
        # is current a second inside the window and stale a second outside it.
        last_success = stamp_at(-cli.SMOKE_MAX_AGE_SECONDS)
        ledger = {ADAPTER: last_success}

        inside = cli.disposition_of(ledger, ADAPTER, stamp_at(-1))
        outside = cli.disposition_of(ledger, ADAPTER, stamp_at(1))

        self.assertEqual(inside.state, cli.VERIFIED)
        self.assertEqual(outside.state, cli.UNVERIFIED)
        self.assertEqual(outside.reason, cli.STALE_SUCCESS)

    def test_the_window_is_declared_in_days_a_reader_can_check(self):
        self.assertEqual(cli.SMOKE_MAX_AGE_SECONDS, 7 * 24 * 60 * 60)

    def test_no_disposition_this_module_can_render_rejects_a_platform(self):
        self.assertEqual(cli.SMOKE_DISPOSITIONS, (cli.VERIFIED, cli.UNVERIFIED))
        self.assertNotIn(REJECTED, cli.SMOKE_DISPOSITIONS)


class InterceptionDegradesNothingTest(unittest.TestCase):
    """Row 3: the local network answering is not a finding about the platform."""

    def test_the_channel_and_the_ledger_both_hold_the_line(self):
        assert_interception_degrades_nothing(self, cli.channel_of, cli.ledger_after)

    def test_an_intercepted_read_reaches_the_observation_as_a_local_answer(self):
        # End to end rather than by hand: the measured captive-portal body,
        # through the real transport, the real adapter, and the real runner.
        probe = cli.probe_for("github_rest")
        seeds = probe_seeds()
        seeds[probe.route_id] = (503, payload("transport/captive_portal.html"), "text/html")

        observed, _ = observe_offline(probe, seeds=seeds)

        self.assertEqual(observed.channel, cli.ANSWERED_BY_LOCAL_NETWORK)
        self.assertIn(transport.NETWORK_INTERCEPTED, observed.loss)
        self.assertEqual(observed.outcome, "failed")
        self.assertFalse(cli.satisfied(observed))

    def test_the_same_status_without_the_marker_stays_the_origins_own(self):
        # The difference is the body, not the status: a 503 the platform itself
        # sent is a platform answer, and calling it local would be the mirror
        # of the mistake row 3 forbids.
        probe = cli.probe_for("github_rest")
        seeds = probe_seeds()
        seeds[probe.route_id] = (
            503, payload("transport/origin_service_unavailable.html"), "text/html"
        )

        observed, _ = observe_offline(probe, seeds=seeds)

        self.assertEqual(observed.channel, cli.ANSWERED_BY_ORIGIN)
        self.assertNotIn(transport.NETWORK_INTERCEPTED, observed.loss)


class WrongImplementationsAreRejectedTest(unittest.TestCase):
    """Row 6: both oracles are shown rejecting, on code beside the tree.

    Neither fixture is imported by the package and nothing under test is
    mutated to obtain them. Each is the mistake its row exists for, written the
    way it would really be written.
    """

    def test_a_renderer_that_calls_a_stale_success_current_fails_row_two(self):
        wrong = load_beside_the_tree("stale_as_success")

        with self.assertRaises(AssertionError) as caught:
            assert_stale_degrades_to_unverified(self, wrong.disposition_of)

        self.assertIn("a stale success was not degraded", str(caught.exception))

    def test_a_smoke_that_reads_a_local_block_as_a_platform_gap_fails_row_three(self):
        wrong = load_beside_the_tree("interception_as_gap")

        with self.assertRaises(AssertionError) as caught:
            assert_interception_degrades_nothing(self, wrong.channel_of, wrong.ledger_after)

        self.assertIn("not named as a local-network answer", str(caught.exception))

    def test_the_same_wrong_smoke_also_revokes_evidence_it_never_disproved(self):
        # Its second mistake, checked apart from its first so that fixing one
        # does not quietly hide the other.
        wrong = load_beside_the_tree("interception_as_gap")
        held = {ADAPTER: stamp_at(-3600)}

        self.assertEqual(wrong.ledger_after(held, intercepted(ADAPTER), NOW), {})
        self.assertEqual(cli.ledger_after(held, intercepted(ADAPTER), NOW), held)

    def test_both_wrong_implementations_pass_nothing_by_accident(self):
        # Each fixture is wrong in its own row and correct enough elsewhere to
        # be a real alternative rather than a broken module: a fixture that
        # failed everything would prove only that the checks run.
        stale = load_beside_the_tree("stale_as_success")
        gap = load_beside_the_tree("interception_as_gap")

        self.assertEqual(stale.disposition_of({}, ADAPTER, NOW).state, cli.UNVERIFIED)
        self.assertEqual(gap.channel_of("ok", ()), cli.ANSWERED_BY_ORIGIN)
        self.assertEqual(
            gap.ledger_after({}, observation(ADAPTER), NOW), {ADAPTER: NOW}
        )


class SmokeLedgerTest(unittest.TestCase):
    """What "records its last-success timestamp" is made of."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "held" / "smoke-ledger.json"

    def test_a_ledger_round_trips_through_one_file(self):
        held = {ADAPTER: NOW, "reddit_feed": stamp_at(-60)}

        with forbid_network():
            cli.write_ledger(self.path, held)
            read_back = cli.read_ledger(self.path)

        self.assertEqual(read_back, held)
        self.assertTrue(self.path.exists())

    def test_the_default_path_is_outside_any_repository_working_tree(self):
        # A human running a smoke must not dirty a checkout. The path is a
        # constant no argument can name, and it is absolute so it does not
        # follow whoever ran the command into their own tree.
        self.assertTrue(cli.LEDGER_PATH.is_absolute())
        self.assertNotIn(REPOSITORY_ROOT, cli.LEDGER_PATH.parents)
        for parent in cli.LEDGER_PATH.parents:
            self.assertNotEqual(parent, REPOSITORY_ROOT)

    def test_a_ledger_that_is_not_there_is_empty_rather_than_an_error(self):
        with forbid_network():
            self.assertEqual(cli.read_ledger(self.path), {})

    def test_a_ledger_this_run_cannot_read_degrades_every_adapter(self):
        # The safe direction, stated: an unreadable ledger is no evidence, and
        # no evidence is `unverified`. The other direction would be a file
        # corruption that silently reported thirteen working platforms.
        for body in ("{not json", '["github_rest"]', '{"github_rest": 17}', ""):
            with self.subTest(body=body):
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(body, encoding="utf-8")

                held = cli.read_ledger(self.path)

                self.assertEqual(held, {})
                self.assertEqual(
                    cli.disposition_of(held, ADAPTER, NOW).state, cli.UNVERIFIED
                )

    def test_recording_one_success_leaves_every_other_adapter_alone(self):
        held = {"reddit_feed": stamp_at(-7200)}

        with forbid_network():
            cli.write_ledger(self.path, cli.ledger_after(held, observation(ADAPTER), NOW))
            read_back = cli.read_ledger(self.path)

        self.assertEqual(read_back, {ADAPTER: NOW, "reddit_feed": held["reddit_feed"]})

    def test_a_smoke_that_did_not_carry_its_row_records_nothing(self):
        held = {}

        after = cli.ledger_after(
            held, observation(ADAPTER, missing=(("repository", "title"),)), NOW
        )

        self.assertEqual(after, {})
        self.assertEqual(cli.disposition_of(after, ADAPTER, NOW).reason, cli.NEVER_SMOKED)


class AReadThatHappenedIsNotNeverSmokedTest(unittest.TestCase):
    """`never_smoked` is the word for never read, and it is now only that.

    Thirteen adapters were read live on 2026-08-12. Nine carried their row; four
    reached an origin and did not — a `202` challenge, a parser that dropped a
    field, a `401`, a playability refusal — and `status` reported all four as
    `never_smoked`, which was false about every one of them. The cause was that
    the ledger records successes, so the *absence* of a success was what got
    named. The absence of a success and the absence of a read are two facts
    here, kept in two records, and each is named for itself.
    """

    def test_a_read_that_went_unmet_says_so_and_carries_the_instant_it_happened(self):
        read_at = stamp_at(-3600)

        held = cli.disposition_of({}, ADAPTER, NOW, unmet={ADAPTER: read_at})

        self.assertEqual(held.state, cli.UNVERIFIED)
        self.assertEqual(held.reason, cli.READ_AND_ROW_UNMET)
        self.assertNotEqual(held.reason, cli.NEVER_SMOKED)
        self.assertEqual(held.last_unmet_read, read_at)
        self.assertEqual(held.last_success, "")
        # Unverified is right and well earned: nothing was proven. What is new
        # is only that the read is no longer denied.
        self.assertIn(held.state, cli.SMOKE_DISPOSITIONS)
        self.assertIn(held.reason, cli.SMOKE_REASONS)
        self.assertNotEqual(held.state, REJECTED)

    def test_an_adapter_no_read_ever_reached_still_says_never_smoked(self):
        # The distinction is the deliverable, so the new reason must not swallow
        # the old one. Another adapter's read is not this one's, either.
        for unmet in ({}, {"reddit_feed": stamp_at(-60)}):
            with self.subTest(unmet=sorted(unmet)):
                held = cli.disposition_of({}, ADAPTER, NOW, unmet=unmet)

                self.assertEqual(held.state, cli.UNVERIFIED)
                self.assertEqual(held.reason, cli.NEVER_SMOKED)
                self.assertEqual(held.last_unmet_read, "")
                self.assertEqual(cli.stated_instant(held), "")

    def test_a_carried_row_still_reads_the_way_it_always_did(self):
        # "A smoke degrades nothing", at the one place this record could have
        # broken it: a current success outranks a later read that failed, and
        # the instant it reports is its own.
        ledger = {ADAPTER: stamp_at(-3600)}

        held = cli.disposition_of(ledger, ADAPTER, NOW, unmet={ADAPTER: stamp_at(-60)})

        self.assertEqual(held.state, cli.VERIFIED)
        self.assertEqual(held.reason, cli.FRESH_SUCCESS)
        self.assertEqual(held.last_success, ledger[ADAPTER])
        self.assertEqual(cli.stated_instant(held), ledger[ADAPTER])

    def test_the_window_passing_does_not_re_merge_what_the_reason_separates(self):
        # `SMOKE_MAX_AGE_SECONDS` is seven days, so the nine stamps recorded on
        # 2026-08-12 expire on the 19th and the authorization to read again is
        # spent. Both sides are given the *same* instant, so the reason is the
        # only thing that can tell a success that aged out from a read that
        # never carried its row.
        long_ago = stamp_at(-(cli.SMOKE_MAX_AGE_SECONDS + 3600))
        for later in (1, cli.SMOKE_MAX_AGE_SECONDS, 365 * 24 * 60 * 60):
            with self.subTest(seconds_past_expiry=later):
                now = stamp_at(later)

                proven = cli.disposition_of({ADAPTER: long_ago}, ADAPTER, now, unmet={})
                read = cli.disposition_of({}, ADAPTER, now, unmet={ADAPTER: long_ago})

                self.assertEqual(proven.state, cli.UNVERIFIED)
                self.assertEqual(read.state, cli.UNVERIFIED)
                self.assertEqual(proven.reason, cli.STALE_SUCCESS)
                self.assertEqual(read.reason, cli.READ_AND_ROW_UNMET)
                self.assertNotEqual(read.reason, cli.NEVER_SMOKED)
                self.assertEqual(cli.stated_instant(proven), long_ago)
                self.assertEqual(cli.stated_instant(read), long_ago)

    def test_only_a_read_the_origin_answered_and_did_not_carry_is_recorded(self):
        held = {"reddit_feed": stamp_at(-7200)}

        self.assertEqual(
            cli.unmet_after(held, origin_failure(ADAPTER), NOW),
            {"reddit_feed": held["reddit_feed"], ADAPTER: NOW},
        )
        # A read that carried its row is a success and is recorded as one,
        # nowhere else.
        self.assertEqual(cli.unmet_after(held, observation(ADAPTER), NOW), held)
        # This host's own appliance answering is not the platform being read at
        # all, so it leaves no trace of one — the same line the captive-portal
        # caveat draws
        # for the success ledger, drawn once more here.
        self.assertEqual(cli.unmet_after(held, intercepted(ADAPTER), NOW), held)

    def test_a_read_that_went_unmet_is_still_a_success_nowhere(self):
        # The tempting wrong fix is to stamp the success ledger on failure too,
        # which would make a failed read look like a success to anything reading
        # only for presence. Two records, and the distinction survives in the
        # reason rather than being erased into it.
        ledger = cli.ledger_after({}, origin_failure(ADAPTER), NOW)
        unmet = cli.unmet_after({}, origin_failure(ADAPTER), NOW)

        self.assertEqual(ledger, {})
        self.assertEqual(unmet, {ADAPTER: NOW})

        held = cli.disposition_of(ledger, ADAPTER, NOW, unmet=unmet)

        self.assertEqual(held.state, cli.UNVERIFIED)
        self.assertEqual(held.reason, cli.READ_AND_ROW_UNMET)

    def test_the_unmet_record_sits_beside_the_ledger_it_qualifies(self):
        # One path is handed in and both files are under it, so a suite that
        # points the ledger at a temporary directory never writes the real one.
        beside = cli.unmet_path_beside(cli.LEDGER_PATH)

        self.assertNotEqual(beside, cli.LEDGER_PATH)
        self.assertEqual(beside.parent, cli.LEDGER_PATH.parent)
        self.assertTrue(beside.is_absolute())
        for parent in beside.parents:
            self.assertNotEqual(parent, REPOSITORY_ROOT)


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


class TheOperationSetIsClosedTest(LedgerHoldingCase):
    """Row 4: three operations, one argument, and no way to name anything else."""

    def test_the_reachable_operations_are_exactly_these_three(self):
        self.assertEqual(
            tuple(operation.name for operation in cli.OPERATIONS),
            ("adapters", "smoke", "status"),
        )

    def test_the_only_argument_the_whole_surface_takes_is_a_closed_choice(self):
        # Fifteen reachable invocations: two operations that take nothing, and
        # one that takes an adapter id off a list of thirteen.
        reachable = 0
        for operation in cli.OPERATIONS:
            with self.subTest(operation=operation.name):
                if not operation.argument:
                    self.assertEqual(operation.choices, ())
                    reachable += 1
                    continue
                self.assertEqual(operation.argument, "--adapter")
                self.assertEqual(
                    operation.choices,
                    tuple(probe.adapter_id for probe in cli.SMOKE_PROBES),
                )
                reachable += len(operation.choices)

        self.assertEqual(reachable, 15)

    def test_every_declared_operation_runs(self):
        for operation in cli.OPERATIONS:
            argv = [operation.name]
            for choice in operation.choices or ("",):
                if choice:
                    argv = [operation.name, operation.argument, choice]
                with self.subTest(argv=" ".join(argv)):
                    code, printed, _ = run_cli(self, argv)

                    self.assertEqual(code, cli.EXIT_OK)
                    self.assertTrue(printed.strip())

    def test_no_operation_outside_the_table_exists(self):
        # The shapes a generic primitive would arrive as. Each is refused by
        # the parser, before any carrier is touched.
        for name in (
            "fetch", "get", "http", "run", "exec", "shell", "eval", "curl",
            "request", "read", "manifest", "acquire",
        ):
            with self.subTest(operation=name):
                refused(self, [name])

    def test_no_argument_can_name_an_address_a_route_or_a_command(self):
        for argv in (
            ["smoke", "--url", "https://example.com/"],
            ["smoke", "--adapter", "public_page", "--url", "https://example.com/"],
            ["smoke", "--adapter", "public_page", "--target", "article:Anything"],
            ["smoke", "--route", "github_rest"],
            ["smoke", "--adapter", "github_rest", "--command", "ls"],
            ["adapters", "--adapter", "github_rest"],
            ["status", "--ledger", "/tmp/anywhere.json"],
        ):
            with self.subTest(argv=" ".join(argv)):
                refused(self, argv)

    def test_an_adapter_the_roster_does_not_name_is_refused(self):
        for adapter_id in ("no_such_adapter", "tiktok_public", "", "github_rest "):
            with self.subTest(adapter=adapter_id):
                refused(self, ["smoke", "--adapter", adapter_id])

    def test_the_offline_adapter_is_not_reachable_from_the_surface(self):
        # `fake` is in the roster and has no smoke: reading a fixture and
        # calling it liveness is the one result this subcommand must not print.
        refused(self, ["smoke", "--adapter", cli.OFFLINE_ADAPTER])

    def test_a_smoke_with_no_adapter_named_is_refused(self):
        refused(self, ["smoke"])

    def test_the_usage_code_is_argparses_own_and_nothing_else_takes_it(self):
        self.assertEqual(cli.EXIT_USAGE, 2)
        self.assertNotIn(cli.EXIT_USAGE, (cli.EXIT_OK, cli.EXIT_ROW_UNMET, cli.EXIT_LOCAL_NETWORK))


class SmokeSubcommandTest(LedgerHoldingCase):
    """What one `smoke --adapter <id>` does, offline, for each of the thirteen."""

    def test_a_satisfied_smoke_reports_verified_and_records_its_stamp(self):
        code, printed, opener = run_cli(self, ["smoke", "--adapter", ADAPTER])

        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(
            smoke_standing(self, printed, ADAPTER), (cli.VERIFIED, cli.FRESH_SUCCESS)
        )
        self.assertEqual([request.route_id for request in opener.opened], ["github_rest"])
        self.assertEqual(sorted(cli.read_ledger(self.path)), [ADAPTER])

    def test_every_one_of_the_thirteen_smokes_runs_and_is_recorded(self):
        for probe in cli.SMOKE_PROBES:
            with self.subTest(adapter=probe.adapter_id):
                code, printed, _ = run_cli(self, ["smoke", "--adapter", probe.adapter_id])

                self.assertEqual(code, cli.EXIT_OK)
                self.assertIn(probe.adapter_id, printed)
                self.assertIn(probe.route_id, printed)

        self.assertEqual(
            sorted(cli.read_ledger(self.path)),
            sorted(probe.adapter_id for probe in cli.SMOKE_PROBES),
        )

    def test_a_smoke_of_an_index_that_never_stops_offering_still_reports_verified(self):
        # What the page bound reaches, and what it does not. The verdict has
        # never read a loss code — `satisfied` reads the field set alone — so
        # the probe that would page arrives at the same `verified` and the same
        # stamp it did when it cost five reads. What changes is the cost and
        # what the operator is told about it: the header line has claimed one
        # bounded read since this subcommand existed, and on this probe it is
        # now true.
        seeds = probe_seeds()
        seeds[transport.DDG_HTML_ROUTE] = ddg_pages_each_offering_a_new_one()

        code, printed, opener = run_cli(
            self, ["smoke", "--adapter", "web_search"], seeds=seeds
        )

        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(
            smoke_standing(self, printed, "web_search"), (cli.VERIFIED, cli.FRESH_SUCCESS)
        )
        self.assertEqual(sorted(cli.read_ledger(self.path)), ["web_search"])
        self.assertEqual(len(opener.opened), 1)
        self.assertIn("one bounded read on route " + transport.DDG_HTML_ROUTE, printed)
        self.assertIn("loss none", printed)

    def test_a_run_that_did_not_carry_its_row_says_so_and_records_no_success(self):
        seeds = probe_seeds()
        seeds["github_rest"] = (404, payload("github/not_found.json"), "application/json")

        code, printed, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertIn(cli.UNVERIFIED, printed)
        self.assertEqual(cli.read_ledger(self.path), {})

    def test_the_reason_the_adapter_gave_reaches_the_operator_whole(self):
        # Every adapter writes a warning saying what it saw, and until this
        # seam carried them the whole set was discarded between the page and
        # the artifact: a drifted read printed `loss schema_drift` and not one
        # word about which container moved. A loss code is a kind; the warning
        # is the recovery procedure.
        seeds = probe_seeds()
        seeds["github_rest"] = (
            200,
            json.dumps({"full_name": "python/cpython"}),
            "application/json",
        )

        code, printed, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertIn("schema_drift", printed)
        self.assertIn("the read reported:", printed)
        self.assertIn("the payload has changed shape", printed)

    def test_an_intercepted_run_says_local_network_and_changes_nothing(self):
        held = {ADAPTER: stamp_at(-3600)}
        cli.write_ledger(self.path, held)
        before = self.path.read_text(encoding="utf-8")
        seeds = probe_seeds()
        seeds["github_rest"] = (503, payload("transport/captive_portal.html"), "text/html")

        code, printed, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(code, cli.EXIT_LOCAL_NETWORK)
        self.assertIn("local network", printed)
        self.assertNotIn("platform gap", printed)
        # Nothing degraded: the adapter keeps the standing it had, and the file
        # on disk is the same bytes it was.
        self.assertEqual(
            smoke_standing(self, printed, ADAPTER), (cli.VERIFIED, cli.FRESH_SUCCESS)
        )
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_a_read_that_never_got_an_answer_is_not_a_row_the_origin_declined(self):
        # A refused connection, an unresolvable name, or a TLS failure raises
        # `TransportError` out of the opener. `main` was try/finally with no
        # except, so it left as a traceback and exit `1` — the code
        # protocol.md's own table assigns to "the origin answered and the row
        # was not carried". That is the captive-portal caveat's error arriving by
        # a different door: a local condition recorded as a platform gap.
        held = {ADAPTER: stamp_at(-3600)}
        cli.write_ledger(self.path, held)
        before = self.path.read_text(encoding="utf-8")
        seeds = probe_seeds()
        seeds["github_rest"] = transport.TransportError("transport failed for github_rest")

        code, printed, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(code, cli.EXIT_LOCAL_NETWORK)
        self.assertIn("no answer came back from anyone", printed)
        self.assertNotIn("platform gap", printed)
        # Nothing recorded, nothing degraded, and the file is the bytes it was.
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_the_intercepted_row_would_catch_the_degradation_it_guards(self):
        # The row above asserts an intercepted read *kept* a proven standing,
        # which is only worth something if the surface would say so when one is
        # lost. Driven with the wrong `ledger_after` written beside the tree —
        # the one that revokes an adapter's evidence on any failed read — the
        # same invocation prints a degraded standing and the row rejects it.
        wrong = load_beside_the_tree("interception_as_gap")
        cli.write_ledger(self.path, {ADAPTER: stamp_at(-3600)})
        seeds = probe_seeds()
        seeds["github_rest"] = (503, payload("transport/captive_portal.html"), "text/html")

        with mock.patch.object(cli, "ledger_after", wrong.ledger_after):
            _, printed, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(
            smoke_standing(self, printed, ADAPTER), (cli.UNVERIFIED, cli.NEVER_SMOKED)
        )
        # And the hazard itself, on this very output: `verified` is a substring
        # of `unverified`, so the assertion this row used to make passes here —
        # on the one reading it exists to reject.
        self.assertIn(cli.VERIFIED, printed)

    def test_the_standing_reader_rejects_the_word_the_old_rows_accepted(self):
        # Both wordings, because the two shapes are printed by different
        # branches: an ordinary read says "is", and a local-network answer says
        # what standing was kept. The dangerous one was the second.
        kept = "  github_rest keeps the standing it had: unverified (never_smoked)"
        proven = "  github_rest is verified (fresh_success, last success 2026-08-12T02:36:40Z)"

        self.assertEqual(
            smoke_standing(self, kept, ADAPTER), (cli.UNVERIFIED, cli.NEVER_SMOKED)
        )
        self.assertEqual(
            smoke_standing(self, proven, ADAPTER), (cli.VERIFIED, cli.FRESH_SUCCESS)
        )
        self.assertNotEqual(smoke_standing(self, kept, ADAPTER)[0], cli.VERIFIED)

    def test_a_platform_refusal_and_a_local_block_do_not_read_alike(self):
        seeds = probe_seeds()
        seeds["github_rest"] = (
            503, payload("transport/origin_service_unavailable.html"), "text/html"
        )

        code, printed, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertNotIn("local network", printed)

    def test_a_run_that_found_no_row_offers_the_way_to_a_current_target(self):
        # A probe target that has rotted is not a platform gap, and the smoke
        # says where a current one comes from instead of leaving an operator
        # to guess which of the two happened.
        seeds = probe_seeds()
        seeds["arctic_shift_posts_ids"] = (200, '{"data": []}', "application/json")

        code, printed, _ = run_cli(self, ["smoke", "--adapter", "reddit_archive"], seeds=seeds)

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertIn(cli.probe_for("reddit_archive").target, printed)
        self.assertIn("reddit_feed record", printed)

    def test_a_withheld_caption_track_is_not_a_failed_run(self):
        # T07's obligation at the surface a human reads: the measured player
        # answer carries `attestation_required`, the metadata arrived, and this
        # must not print as a failure.
        code, printed, _ = run_cli(self, ["smoke", "--adapter", "youtube_innertube"])

        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("attestation_required", printed)
        self.assertEqual(
            smoke_standing(self, printed, "youtube_innertube"),
            (cli.VERIFIED, cli.FRESH_SUCCESS),
        )
        self.assertEqual(sorted(cli.read_ledger(self.path)), ["youtube_innertube"])

    def test_a_second_smoke_replaces_only_its_own_stamp(self):
        run_cli(self, ["smoke", "--adapter", ADAPTER])
        first = cli.read_ledger(self.path)
        later = helpers.FakeClock()
        later.advance(90)

        run_cli(self, ["smoke", "--adapter", "reddit_feed"], clock=later)
        second = cli.read_ledger(self.path)

        self.assertEqual(second[ADAPTER], first[ADAPTER])
        self.assertNotEqual(second["reddit_feed"], first[ADAPTER])


class StatusSubcommandTest(LedgerHoldingCase):
    """What the smokes have proven, read back without touching a network."""

    def test_status_reports_every_live_adapter(self):
        code, printed, opener = run_cli(self, ["status"])

        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(opener.opened, [])
        for probe in cli.SMOKE_PROBES:
            self.assertIn(probe.adapter_id, printed)
        self.assertNotIn(cli.OFFLINE_ADAPTER + " ", printed)

    def test_an_adapter_never_smoked_is_unverified_and_not_rejected(self):
        code, printed, _ = run_cli(self, ["status"])

        self.assertEqual(printed.count(cli.UNVERIFIED), 13)
        self.assertIn(cli.NEVER_SMOKED, printed)
        self.assertNotIn(REJECTED, printed)

    def test_a_stale_stamp_reads_as_unverified_on_a_moved_clock(self):
        cli.write_ledger(self.path, {ADAPTER: stamp_at(-(cli.SMOKE_MAX_AGE_SECONDS + 60))})

        code, printed, _ = run_cli(self, ["status"])

        self.assertIn(cli.STALE_SUCCESS, printed)
        self.assertNotIn(REJECTED, printed)

    def test_status_never_judges_and_always_reports(self):
        # It reads a ledger and prints it. An exit code that turned "nothing
        # has been smoked yet" into a failure would make the offline suite's
        # own state look like a broken platform.
        cli.write_ledger(self.path, {ADAPTER: stamp_at(-(cli.SMOKE_MAX_AGE_SECONDS + 60))})

        code, _, _ = run_cli(self, ["status"])

        self.assertEqual(code, cli.EXIT_OK)


class StatusSaysWhatWasReadTest(LedgerHoldingCase):
    """The whole path, at the surface an operator reads it on.

    One read against an origin that answers without carrying the row, and then
    the report. The four adapters read on 2026-08-12 arrive here: each was read
    exactly once, against a real origin, and `status` said of each that it never
    had been.
    """

    def unmet_path(self):
        return cli.unmet_path_beside(self.path)

    def answered_without_the_row(self):
        """The origin's own answer, carrying no row this adapter's roster names."""

        seeds = probe_seeds()
        seeds["github_rest"] = (404, payload("github/not_found.json"), "application/json")
        return seeds

    def test_a_read_that_went_unmet_is_reported_as_read_and_never_as_unread(self):
        code, printed, _ = run_cli(
            self, ["smoke", "--adapter", ADAPTER], seeds=self.answered_without_the_row()
        )

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertIn(cli.READ_AND_ROW_UNMET, printed)
        self.assertNotIn(cli.NEVER_SMOKED, printed)

        _, after, _ = run_cli(self, ["status"])

        self.assertEqual(
            status_row(self, after, ADAPTER),
            [
                ADAPTER,
                cli.UNVERIFIED,
                cli.READ_AND_ROW_UNMET,
                cli.read_ledger(self.unmet_path())[ADAPTER],
            ],
        )

    def test_the_read_that_went_unmet_is_recorded_as_no_kind_of_success(self):
        run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=self.answered_without_the_row())

        # The ledger is where a proven row is recorded, and nothing proved one.
        # It is not written at all, so a reader who only asks whether an adapter
        # is in it gets the same answer it always gave.
        self.assertFalse(self.path.exists())
        self.assertEqual(cli.read_ledger(self.path), {})
        self.assertEqual(sorted(cli.read_ledger(self.unmet_path())), [ADAPTER])

    def test_the_twelve_adapters_this_read_did_not_touch_are_untouched(self):
        run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=self.answered_without_the_row())

        _, printed, _ = run_cli(self, ["status"])

        for probe in cli.SMOKE_PROBES:
            if probe.adapter_id == ADAPTER:
                continue
            with self.subTest(adapter=probe.adapter_id):
                self.assertEqual(
                    status_row(self, printed, probe.adapter_id),
                    [probe.adapter_id, cli.UNVERIFIED, cli.NEVER_SMOKED, "-"],
                )

    def test_a_carried_row_reports_verified_with_its_own_instant_and_nothing_else(self):
        code, _, _ = run_cli(self, ["smoke", "--adapter", ADAPTER])

        _, printed, _ = run_cli(self, ["status"])

        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(
            status_row(self, printed, ADAPTER),
            [ADAPTER, cli.VERIFIED, cli.FRESH_SUCCESS, cli.read_ledger(self.path)[ADAPTER]],
        )
        self.assertFalse(self.unmet_path().exists())

    def test_this_hosts_own_network_answering_is_not_a_read_of_the_platform(self):
        seeds = probe_seeds()
        seeds["github_rest"] = (503, payload("transport/captive_portal.html"), "text/html")

        code, _, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)
        _, printed, _ = run_cli(self, ["status"])

        self.assertEqual(code, cli.EXIT_LOCAL_NETWORK)
        # Neither record moves. The origin was never reached, so there is no
        # read to report and `never_smoked` is still the true word — the same
        # line the captive-portal caveat draws, drawn at the second record too.
        self.assertFalse(self.path.exists())
        self.assertFalse(self.unmet_path().exists())
        self.assertEqual(
            status_row(self, printed, ADAPTER),
            [ADAPTER, cli.UNVERIFIED, cli.NEVER_SMOKED, "-"],
        )

    def test_a_read_that_never_got_an_answer_records_no_read_either(self):
        seeds = probe_seeds()
        seeds["github_rest"] = transport.TransportError("transport failed for github_rest")

        code, _, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(code, cli.EXIT_LOCAL_NETWORK)
        self.assertFalse(self.path.exists())
        self.assertFalse(self.unmet_path().exists())

    def test_after_the_window_the_two_records_still_read_apart(self):
        # The nine stamps recorded on 2026-08-12 expire on the 19th, and the
        # authorization to read again is spent. Both rows below carry the *same*
        # instant, so the reason is the only thing left that tells a success
        # that aged out from a read that never carried its row.
        long_ago = stamp_at(-(cli.SMOKE_MAX_AGE_SECONDS + 3600))
        cli.write_ledger(self.path, {ADAPTER: long_ago})
        cli.write_ledger(self.unmet_path(), {"web_search": long_ago})

        _, printed, _ = run_cli(self, ["status"])

        self.assertEqual(
            status_row(self, printed, ADAPTER),
            [ADAPTER, cli.UNVERIFIED, cli.STALE_SUCCESS, long_ago],
        )
        self.assertEqual(
            status_row(self, printed, "web_search"),
            ["web_search", cli.UNVERIFIED, cli.READ_AND_ROW_UNMET, long_ago],
        )


class TheRecoveryLineFitsTheLossTest(LedgerHoldingCase):
    """Advice that cannot help, on the two reads most likely to be misread.

    "Replace the target" printed whenever a read kept no records and the probe
    declared a recovery. Two of the thirteen reads made on 2026-08-12 printed
    it, and in both the loss code says the target was never the problem: the
    origin refused the client, once for want of an identity it would accept and
    once for want of an attestation this package does not perform. `simonw` is
    not missing and `dQw4w9WgXcQ` is not missing.

    The rule cannot be "print only when nothing was typed", because a `404` on a
    named target is the strongest evidence there is that a target really has
    gone — which is why both directions are rows here.
    """

    RECOVERY_LINE = "no row came back for the probe target"

    def test_an_origin_refusing_this_client_is_not_a_target_to_replace(self):
        # Read 6 of the thirteen, at the status the origin answered with.
        seeds = probe_seeds()
        seeds["x_guest_graphql"] = (
            401, payload("x/guest_blocked_operation.json"), "application/json"
        )

        code, printed, _ = run_cli(self, ["smoke", "--adapter", "x_guest"], seeds=seeds)

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertIn("auth_required", printed)
        self.assertIn("records kept 0", printed)
        # The probe does declare a way back to a current target, so nothing but
        # the loss code is keeping the line off this read.
        self.assertTrue(cli.probe_for("x_guest").target_recovery)
        self.assertNotIn(self.RECOVERY_LINE, printed)
        # The read is still reported in full. What went is the advice, not the
        # finding: an origin that refused this client is news.
        self.assertIn(cli.READ_AND_ROW_UNMET, printed)

    def test_an_origin_withholding_from_an_unattested_client_is_not_one_either(self):
        # Read 9 of the thirteen.
        seeds = probe_seeds()
        seeds["youtube_innertube"] = (
            200, payload("youtube/player_unplayable.json"), "application/json"
        )

        code, printed, _ = run_cli(
            self, ["smoke", "--adapter", "youtube_innertube"], seeds=seeds
        )

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertIn("attestation_required", printed)
        self.assertIn("records kept 0", printed)
        self.assertTrue(cli.probe_for("youtube_innertube").target_recovery)
        self.assertNotIn(self.RECOVERY_LINE, printed)
        self.assertIn(cli.READ_AND_ROW_UNMET, printed)

    def test_a_target_the_origin_says_it_does_not_have_still_gets_the_line(self):
        # The case the line exists for, and the one a rule drawn too wide would
        # silence: the origin answered about this exact target and said it has
        # no such thing. Nothing here refuses the client.
        seeds = probe_seeds()
        seeds["github_rest"] = (404, payload("github/not_found.json"), "application/json")

        code, printed, _ = run_cli(self, ["smoke", "--adapter", ADAPTER], seeds=seeds)

        self.assertEqual(code, cli.EXIT_ROW_UNMET)
        self.assertIn("http_status", printed)
        self.assertIn(self.RECOVERY_LINE, printed)
        self.assertIn(cli.probe_for(ADAPTER).target_recovery, printed)

    def test_an_answer_that_simply_held_no_row_still_gets_the_line(self):
        # The other half of the same control: the origin answered, typed
        # nothing, and the thing the probe named was not in what came back.
        seeds = probe_seeds()
        seeds["arctic_shift_posts_ids"] = (200, '{"data": []}', "application/json")

        _, printed, _ = run_cli(self, ["smoke", "--adapter", "reddit_archive"], seeds=seeds)

        self.assertIn(self.RECOVERY_LINE, printed)

    def test_the_rule_is_a_named_pair_of_codes_and_not_a_guess(self):
        # Both name the origin refusing *this client*; neither says anything
        # about whether the thing asked for is still there.
        self.assertEqual(
            cli.TARGET_NOT_THE_PROBLEM, ("auth_required", "attestation_required")
        )


# The only live reads this package has ever made, transcribed verbatim from the
# run that made them: thirteen adapters, one bounded read each, in roster order,
# no retries, on 2026-08-12. That run's own record is not tracked and the
# authorization to read again is spent, so these two blocks are the durable copy
# of it. They are parsed rather than restated, and cross-checked against each
# other before either is believed.
LIVENESS_ROLL_UP = """
| # | adapter | exit | verdict | disposition | wall |
| --- | --- | --- | --- | --- | --- |
| 1 | `web_search` | `1` | row unmet | origin refused this client (`202` challenge), correctly typed | 0.813 s |
| 2 | `public_page` | `0` | **verified** | proven live | 1.638 s |
| 3 | `reddit_archive` | `0` | **verified** | proven live | 1.817 s |
| 4 | `reddit_feed` | `0` | **verified** | proven live | 1.641 s |
| 5 | `x_syndication` | `1` | row unmet | **parser defect `D1`** — origin carried the field, package dropped it | 3.241 s |
| 6 | `x_guest` | `1` | row unmet | origin refused (`401`), correctly typed; 2 requests (activation + read) | 1.478 s |
| 7 | `linkedin_public` | `0` | **verified** | proven live | 1.851 s |
| 8 | `linkedin_jobs` | `0` | **verified** | proven live | 0.918 s |
| 9 | `youtube_innertube` | `1` | row unmet | origin refused this unattested client, typed `attestation_required` | 0.792 s |
| 10 | `instagram_public` | `0` | **verified** | proven live | 2.151 s |
| 11 | `hacker_news` | `0` | **verified** | proven live | 1.159 s |
| 12 | `github_rest` | `0` | **verified** | proven live | 0.888 s |
| 13 | `rss_atom` | `0` | **verified** | proven live | 1.084 s |
"""

# The ledger those thirteen reads left on disk, read back through
# `smoke.LEDGER_PATH` at the end of that run.
LIVENESS_LEDGER = """
{
  "github_rest": "2026-08-12T02:36:40Z",
  "hacker_news": "2026-08-12T02:36:25Z",
  "instagram_public": "2026-08-12T02:36:09Z",
  "linkedin_jobs": "2026-08-12T02:34:03Z",
  "linkedin_public": "2026-08-12T02:33:47Z",
  "public_page": "2026-08-12T02:30:24Z",
  "reddit_archive": "2026-08-12T02:30:40Z",
  "reddit_feed": "2026-08-12T02:30:59Z",
  "rss_atom": "2026-08-12T02:36:57Z"
}
"""

# The moment `status` was rendered after the last of the thirteen. The four
# reads that carried no row printed an outcome and no instant of their own, so
# this is what they are replayed at: the earliest moment the record proves every
# one of the thirteen had already happened.
LIVENESS_CLOSED_AT = "2026-08-12T02:40:08Z"

# What one recorded exit code says, per this module's own table.
CARRIED_THE_ROW = "0"
ORIGIN_ANSWERED_ROW_UNMET = "1"
LOCAL_NETWORK_ANSWERED = "3"


def recorded_reads():
    """The thirteen recorded outcomes, as (adapter id, exit code) in read order."""

    reads = []
    for line in LIVENESS_ROLL_UP.strip().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells[0].isdigit():
            continue
        reads.append((cells[1].strip("`"), cells[2].strip("`")))
    return reads


class TheRecordedLivenessReplaysTest(unittest.TestCase):
    """The night's own thirteen outcomes, put back through the two records.

    The exit code is the whole of what those records read, which is why a replay
    off it is not a lossy reconstruction: `run_smoke` takes `3` when this host's
    network answered, `0` when the roster row was carried, and `1` otherwise —
    the same two facts, the channel and the field set, that decide which record
    a read lands in. The outcome word and the loss codes differ across these
    thirteen and neither record reads either, so the replay sets them to the
    least it can rather than inventing detail the roll-up does not carry.

    What makes this a check on the machinery rather than on a transcription: the
    nine successes are replayed at the instants the ledger block records, so a
    faithful replay reproduces that block exactly — nine keys, nine stamps.
    """

    def setUp(self):
        self.reads = recorded_reads()
        self.ledger = json.loads(LIVENESS_LEDGER)

    def test_the_two_transcribed_blocks_agree_before_either_is_believed(self):
        codes = {code for _, code in self.reads}
        carried = sorted(adapter for adapter, code in self.reads if code == CARRIED_THE_ROW)

        self.assertEqual(len(self.reads), 13)
        self.assertEqual(
            sorted(adapter for adapter, _ in self.reads),
            sorted(probe.adapter_id for probe in cli.SMOKE_PROBES),
        )
        # Nine exit `0` in one block, nine stamps in the other, and the same
        # nine adapters. Either block mistranscribed reddens here.
        self.assertEqual(carried, sorted(self.ledger))
        self.assertEqual(len(carried), 9)
        # No read that night was answered by this host's own appliance, so
        # nothing in this replay stands on the local-network branch.
        self.assertEqual(codes, {CARRIED_THE_ROW, ORIGIN_ANSWERED_ROW_UNMET})
        self.assertNotIn(LOCAL_NETWORK_ANSWERED, codes)

    def replayed(self):
        """The two records the thirteen recorded outcomes leave behind."""

        ledger = {}
        unmet = {}
        for adapter_id, code in self.reads:
            carried = code == CARRIED_THE_ROW
            kind = cli.probe_for(adapter_id).field_sets[0][0]
            read = cli.SmokeObservation(
                adapter_id=adapter_id,
                route_id=cli.probe_for(adapter_id).route_id,
                outcome="ok" if carried else "failed",
                loss=(),
                records_kept=1 if carried else 0,
                channel=(
                    cli.ANSWERED_BY_LOCAL_NETWORK
                    if code == LOCAL_NETWORK_ANSWERED
                    else cli.ANSWERED_BY_ORIGIN
                ),
                missing=() if carried else ((kind, cli.NO_RECORD_OF_THIS_KIND),),
                facts=(),
                observed_at=self.ledger.get(adapter_id, LIVENESS_CLOSED_AT),
            )
            at = self.ledger.get(adapter_id, LIVENESS_CLOSED_AT)
            ledger = cli.ledger_after(ledger, read, at)
            unmet = cli.unmet_after(unmet, read, at)
        return (ledger, unmet)

    def test_the_replay_reproduces_the_ledger_that_was_read_off_disk(self):
        ledger, unmet = self.replayed()

        self.assertEqual(ledger, self.ledger)
        self.assertEqual(
            sorted(unmet),
            sorted(adapter for adapter, code in self.reads if code != CARRIED_THE_ROW),
        )
        # The two records hold no adapter in common: a read lands in one.
        self.assertEqual(set(ledger) & set(unmet), set())

    def test_no_adapter_read_that_night_is_reported_as_never_read(self):
        ledger, unmet = self.replayed()

        printed = "\n".join(cli.status_lines(ledger, LIVENESS_CLOSED_AT, unmet))
        reasons = [status_row(self, printed, adapter)[2] for adapter, _ in self.reads]

        self.assertEqual(len(reasons), 13)
        self.assertEqual(reasons.count(cli.FRESH_SUCCESS), 9)
        self.assertEqual(reasons.count(cli.READ_AND_ROW_UNMET), 4)
        self.assertEqual(reasons.count(cli.NEVER_SMOKED), 0)

    def test_the_expiry_of_those_nine_stamps_re_merges_nothing(self):
        # The window is seven days, so every stamp above is spent by the 19th.
        # What was read is not a claim that expires: the four stay read.
        ledger, unmet = self.replayed()
        expired = "2026-08-19T02:40:09Z"

        printed = "\n".join(cli.status_lines(ledger, expired, unmet))
        reasons = [status_row(self, printed, adapter)[2] for adapter, _ in self.reads]

        self.assertEqual(reasons.count(cli.STALE_SUCCESS), 9)
        self.assertEqual(reasons.count(cli.READ_AND_ROW_UNMET), 4)
        self.assertEqual(reasons.count(cli.NEVER_SMOKED), 0)
        self.assertEqual(reasons.count(cli.FRESH_SUCCESS), 0)
        # And every one of the thirteen still carries the instant it was read.
        for adapter, _ in self.reads:
            with self.subTest(adapter=adapter):
                self.assertNotEqual(status_row(self, printed, adapter)[3], "-")


class AdaptersSubcommandTest(LedgerHoldingCase):
    """The roster, its access classes, and what each smoke will assert."""

    def test_the_listing_names_every_probe_with_its_class_and_route(self):
        code, printed, opener = run_cli(self, ["adapters"])

        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(opener.opened, [])
        for probe in cli.SMOKE_PROBES:
            descriptor = runner.descriptor_for(probe.adapter_id)
            with self.subTest(adapter=probe.adapter_id):
                self.assertIn(probe.adapter_id, printed)
                self.assertIn(descriptor.access_class, printed)
                self.assertIn(probe.route_id, printed)

    def test_the_listing_names_every_field_each_smoke_asserts(self):
        _, printed, _ = run_cli(self, ["adapters"])

        for probe in cli.SMOKE_PROBES:
            for kind, names in probe.field_sets:
                for name in names:
                    with self.subTest(adapter=probe.adapter_id, field=name):
                        self.assertIn(name, printed)


class NothingTheRunHoldsReachesTheOutputTest(LedgerHoldingCase):
    """The `K1` law at the last surface a credential could leave by."""

    def setUp(self):
        super().setUp()
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def mint_one_token(self):
        """Put the process in the state a run that minted leaves it in.

        Stated as what the store holds rather than by driving the mint: the
        mint is one paced call the governor makes, and what this suite is about
        is the other end — that whatever a run held, no line it printed carries
        it and nothing survives the run.
        """

        transport.GUEST_TOKENS.remember(transport.X_GUEST_ACTIVATE_ROUTE, GUEST_TOKEN)

    def test_no_line_any_subcommand_prints_carries_a_public_client_credential(self):
        self.mint_one_token()
        secrets = [
            credential.value
            for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values()
        ] + [GUEST_TOKEN]
        printed = []
        for probe in cli.SMOKE_PROBES:
            printed.append(run_cli(self, ["smoke", "--adapter", probe.adapter_id])[1])
            self.mint_one_token()
        printed.append(run_cli(self, ["status"])[1])
        printed.append(run_cli(self, ["adapters"])[1])

        self.assertTrue(secrets)
        for secret in secrets:
            for output in printed:
                self.assertNotIn(secret, output)

    def test_the_guest_token_never_outlives_the_run_that_minted_it(self):
        # T05 minted it into a module-level store for the process; the run has
        # to end somewhere, and this is where.
        self.mint_one_token()
        self.assertEqual(
            transport.GUEST_TOKENS.token_for(transport.X_GUEST_ACTIVATE_ROUTE), GUEST_TOKEN
        )

        run_cli(self, ["smoke", "--adapter", "x_guest"])

        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_every_subcommand_ends_the_run_the_same_way(self):
        for argv in (["adapters"], ["status"], ["smoke", "--adapter", ADAPTER]):
            with self.subTest(argv=" ".join(argv)):
                self.mint_one_token()

                run_cli(self, argv)

                self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_a_refused_invocation_clears_it_too(self):
        self.mint_one_token()

        refused(self, ["smoke", "--adapter", "no_such_adapter"])

        self.assertEqual(transport.GUEST_TOKENS._tokens, {})


if __name__ == "__main__":
    unittest.main()
