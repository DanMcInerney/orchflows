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
import socket
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import cli, runner, schema, transport
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
CLI_FIXTURE_DIR = FIXTURE_DIR / "cli"

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


if __name__ == "__main__":
    unittest.main()
