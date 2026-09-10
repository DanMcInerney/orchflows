from ._support import *

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
