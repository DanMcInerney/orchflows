from ._support import *

# Every (adapter, kind) pair `SMOKE_PROBES` declares a field set for, counted
# by name rather than transcribed name for name — a literal copy of all
# nineteen rows would only prove this test can read the same file it exists
# to check against drift, and F3's own mutation (`R.04`'s: dropping `body`
# from `web_search`'s row) is a removal, which a count already catches.
# Derived once, here, from the shape this table held when the completeness
# gap was found and closed; it is the pin, not a relay of `probes.py`'s own
# say-so at import time.
PINNED_FIELD_COUNTS_BY_ADAPTER_AND_KIND = {
    ("bluesky", "post"): 8,
    ("github_rest", "repository"): 7,
    ("hacker_news", "story"): 5,
    ("instagram_public", "post"): 4,
    ("instagram_public", "profile"): 4,
    ("linkedin_jobs", "job_posting"): 4,
    ("linkedin_public", "profile"): 6,
    ("open_page", "web_page"): 8,
    ("prediction_markets", "market"): 5,
    ("public_page", "web_page"): 7,
    ("reddit_archive", "post"): 7,
    ("reddit_feed", "post"): 4,
    ("reddit_shreddit", "post"): 8,
    ("rss_atom", "feed_entry"): 5,
    ("stocktwits", "post"): 5,
    ("web_search", "web_hit"): 3,
    ("x_fxtwitter", "post"): 9,
    ("x_guest", "profile"): 6,
    ("x_syndication", "post"): 7,
    ("youtube_innertube", "video"): 3,
}


class SmokeProbeTableTest(unittest.TestCase):
    """The enumeration itself: nineteen probes, each naming things that exist."""

    def test_the_probes_are_exactly_the_live_roster(self):
        # Derived against the core's own roster rather than transcribed beside
        # it: an adapter added to the package with no smoke, and a smoke for an
        # adapter the core cannot reach, are the same defect from two ends.
        probed = sorted(probe.adapter_id for probe in cli.SMOKE_PROBES)

        self.assertEqual(probed, sorted(set(runner.ADAPTER_IDS) - {cli.OFFLINE_ADAPTER}))
        self.assertEqual(len(cli.SMOKE_PROBES), 19)

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

    def test_the_declared_field_set_sizes_match_a_pinned_count_by_kind(self):
        # The forward-only check above proves every declared name is
        # legitimate; it never compares against what a row used to declare,
        # so a field silently dropped from any probe passes it untouched.
        # `R.04` proved this by mutation: removing `"body"` from
        # `web_search`'s field_sets left the whole offline suite green. This
        # is that oracle, the same shape `test_the_probes_are_exactly_the_
        # live_roster` already uses for the roster itself — a count pinned
        # independently of `probes.py`'s own say-so, so a later drop turns
        # this row red rather than passing silently.
        counted = {
            (probe.adapter_id, kind): len(names)
            for probe in cli.SMOKE_PROBES
            for kind, names in probe.field_sets
        }

        self.assertEqual(counted, PINNED_FIELD_COUNTS_BY_ADAPTER_AND_KIND)

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
    """Row 1: nineteen smokes, each bounded, against measured bytes."""

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

        self.assertEqual(reachable, 21)

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
