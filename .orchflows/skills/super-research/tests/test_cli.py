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


class SmokeAssertsTheRosterFieldSetTest(unittest.TestCase):
    """Row 1: thirteen smokes, one bounded read each, against measured bytes."""

    def test_every_smoke_asserts_its_roster_field_set_on_one_read(self):
        for probe in cli.SMOKE_PROBES:
            with self.subTest(adapter=probe.adapter_id):
                observation, opener = observe_offline(probe)

                self.assertEqual(observation.missing, ())
                self.assertTrue(cli.satisfied(observation))
                self.assertEqual(observation.adapter_id, probe.adapter_id)
                self.assertEqual(observation.route_id, probe.route_id)
                self.assertEqual(observation.channel, cli.ANSWERED_BY_ORIGIN)
                self.assertGreater(observation.records_kept, 0)
                # One bounded read: one request, on the probe's own route, and
                # no second call to fill a page out.
                self.assertEqual(
                    [request.route_id for request in opener.opened], [probe.route_id]
                )

    def test_a_healthy_read_is_never_reported_partial_by_its_own_cap(self):
        # The bound is one call, not the cap; a cap under a measured page size
        # would report a whole answer as a truncated one.
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
        probe = cli.probe_for("hacker_news")

        with self.assertRaises(transport.TransportError):
            observe_offline(probe, seeds={})


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
    origin was never reached. findings.md §0 measured it: 503 with a login
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
        self.assertIn(cli.VERIFIED, printed)
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

    def test_a_run_that_did_not_carry_its_row_says_so_and_records_nothing(self):
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
        self.assertIn(cli.VERIFIED, printed)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

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
        self.assertIn(cli.VERIFIED, printed)
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
        with mock.patch.object(transport, "mint_guest_token", lambda route: GUEST_TOKEN):
            transport.tokened_headers((), transport.X_GUEST_ACTIVATE_ROUTE)

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
