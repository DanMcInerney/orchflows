from ._support import *

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

        self.assertEqual(printed.count(cli.UNVERIFIED), 19)
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
        # Every adapter that night is still one this package smokes, and the
        # roster has grown since: four adapters were added on 2026-08-17 and
        # were no part of that run. A record of a past night is not a claim
        # about today's roster, so this is containment rather than equality —
        # the equality it used to assert would have to be broken by every
        # adapter ever added, which is a record rewriting itself.
        recorded = sorted(adapter for adapter, _ in self.reads)
        self.assertEqual(recorded, sorted(set(recorded)))
        self.assertTrue(
            set(recorded) <= {probe.adapter_id for probe in cli.SMOKE_PROBES}
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


