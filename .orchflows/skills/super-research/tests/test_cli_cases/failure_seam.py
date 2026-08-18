from ._support import *
from .smoke import ddg_pages_each_offering_a_new_one

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


class SmokeSubcommandTest(LedgerHoldingCase):
    """What one `smoke --adapter <id>` does, offline, for each of the nineteen."""

    def test_a_satisfied_smoke_reports_verified_and_records_its_stamp(self):
        code, printed, opener = run_cli(self, ["smoke", "--adapter", ADAPTER])

        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(
            smoke_standing(self, printed, ADAPTER), (cli.VERIFIED, cli.FRESH_SUCCESS)
        )
        self.assertEqual([request.route_id for request in opener.opened], ["github_rest"])
        self.assertEqual(sorted(cli.read_ledger(self.path)), [ADAPTER])

    def test_every_one_of_the_smokes_runs_and_is_recorded(self):
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

