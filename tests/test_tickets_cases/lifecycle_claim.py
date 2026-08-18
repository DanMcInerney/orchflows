"""Behavioral ticket regression cases."""

from .common import *  # noqa: F401,F403

class TestPendingPromotion(unittest.TestCase):
    def test_pending_with_complete_deps_is_promoted_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("complete", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = [t["id"] for t in payload["ready"]]
            self.assertEqual(["T2"], ids)
            self.assertEqual("ready", payload["ready"][0]["status"])
            self.assertIn("status: ready", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_pending_with_incomplete_deps_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("ready", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = sorted(t["id"] for t in payload["ready"])
            self.assertEqual(["T1"], ids)
            self.assertIn("status: pending", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_set_status_accepts_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            self.assertEqual("pending", payload["set_status"]["status"])
            self.assertIn("status: pending", (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestClaim(unittest.TestCase):
    def test_claim_happy_path_transitions_ready_to_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual("agent-a", payload["claimed"]["claimed_by"])
            self.assertEqual("T1", payload["claimed"]["id"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: claimed", text)
            self.assertIn("claimed_by: agent-a", text)
            self.assertRegex(text, r"claimed_at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

    def test_claim_on_fresh_claim_is_rejected_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertIn("error", second)

    def test_stale_claim_is_reclaimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            # backdate the claim well past the ticket's 30m bound, and the
            # file with it: staleness is motion as well as the clock, so a
            # claim whose ticket was written a moment ago is still moving
            text = ticket_path.read_text(encoding="utf-8")
            text = tickets_mod._set_frontmatter_field(text, "claimed_at", "2020-01-01T00:00:00Z")
            ticket_path.write_text(text, encoding="utf-8")
            backdate(ticket_path, 10 * 24 * 60)
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertEqual("agent-b", second["claimed"]["claimed_by"])
            self.assertIn("claimed_by: agent-b", ticket_path.read_text(encoding="utf-8"))

    def test_two_writer_claim_race_yields_exactly_one_winner(self):
        """Two threads in flight at once over one ticket, both holding the
        same pre-claim snapshot, the loser's read released only once the
        winner's write has landed.

        That interleaving is the one ``_do_claim``'s snapshot check exists
        for, and the check is what decides it: the loser re-reads, finds the
        file no longer the text it was handed, and reports the lost race
        rather than overwriting the winner. Until now this ran ``_do_claim``
        twice in one thread, which is not a race at all -- there is only
        ever one runnable writer, so no scheduling could have produced any
        other answer.

        Deterministic on purpose, and one invocation: driven 200 times while
        this was written, one winner every time. The interleaving the check
        does *not* cover is
        ``test_both_claimants_win_when_neither_read_sees_the_others_write``.
        """

        winners, losers, final_text = self.race(release_loser_after_write=True)
        self.assertEqual(1, len(winners), (winners, losers))
        self.assertEqual(1, len(losers), (winners, losers))
        self.assertIn("lost the claim race", losers[0]["error"])

        winner_name = winners[0]["claimed"]["claimed_by"]
        self.assertIn(f"claimed_by: {winner_name}", final_text)
        loser_name = "writer-b" if winner_name == "writer-a" else "writer-a"
        self.assertNotIn(f"claimed_by: {loser_name}", final_text)

    def test_both_claimants_win_when_neither_read_sees_the_others_write(self):
        """The window the snapshot check does not close, recorded as it is.

        ``_do_claim`` re-reads and compares, then writes; the two are not one
        step. Align two writers so both re-reads complete before either write
        does and both compares pass, so both write and both report a claim --
        the state the check was added to prevent, reached by an interleaving
        it cannot see. Nothing forces this alignment in production, and
        nothing prevents it either.

        This is the current behavior pinned, not endorsed: a compare-and-swap
        that closed the window would fail this case, which is the point of
        having it here rather than in a note nobody reads.
        """

        winners, _losers, final_text = self.race(release_loser_after_write=False)
        self.assertEqual(2, len(winners), winners)
        # both wrote, and the file carries whichever landed last -- there is
        # no record left that the other believed it had won
        self.assertEqual(1, final_text.count("claimed_by: "))

    def race(self, release_loser_after_write: bool):
        """Two threads claiming one ticket from one snapshot, at one chosen
        interleaving. Returns the winners, the losers, and the final bytes.

        The barrier puts both writers in flight together; the ordering hooks
        ride on the path object ``_do_claim`` is handed, so the interleaving
        is chosen by this fixture rather than by the scheduler. No production
        signature or body is touched: the argument is the seam.
        """

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_repo(Path(tmp), {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            prior_text = ticket_path.read_text(encoding="utf-8")
            now = datetime.now(timezone.utc)

            in_flight = threading.Barrier(2)
            winner_wrote = threading.Event()
            both_read = threading.Barrier(2)
            outcomes = {}

            def claim(name, path):
                in_flight.wait(timeout=30)
                outcomes[name] = tickets_mod._do_claim(path, prior_text, name, now)

            if release_loser_after_write:
                paths = {
                    "writer-a": SequencedPath(ticket_path, after_write=winner_wrote.set),
                    "writer-b": SequencedPath(
                        ticket_path, before_read=lambda: winner_wrote.wait(timeout=30)
                    ),
                }
            else:
                paths = {
                    name: SequencedPath(
                        ticket_path, after_read=lambda: both_read.wait(timeout=30)
                    )
                    for name in ("writer-a", "writer-b")
                }

            threads = [
                threading.Thread(target=claim, args=(name, path), daemon=True)
                for name, path in paths.items()
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)
                self.assertFalse(thread.is_alive(), "a claimant never finished")

            return (
                [r for r in outcomes.values() if "claimed" in r],
                [r for r in outcomes.values() if "error" in r],
                ticket_path.read_text(encoding="utf-8"),
            )


class TestInvalidStatus(unittest.TestCase):
    def test_set_status_rejects_invalid_status_as_error_json_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_main(tmp, "set-status", "testrun", "T1", "bogus-status")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertIn("status: ready", (run_dir / "T1.md").read_text(encoding="utf-8"))


def make_claimed_repo(tmp: Path, claims: dict) -> Path:
    """A repo of claimed tickets, each carrying its own ``bound`` and
    ``claimed_at``, and each with nothing moving.

    The fields staleness is computed from, and the ones `make_repo` holds
    fixed -- so anything grading a claim's age or its owner varies them
    here. Each ticket's mtime is put back to the moment it was claimed
    (far back when that moment is unreadable): staleness reads artifact
    motion as well as the clock, and a fixture that wrote its tickets a
    millisecond ago is a fixture where every claim is still moving.
    """

    run_dir = make_repo(tmp, {tid: ("claimed", "[]") for tid in claims})
    for tid, (bound, claimed_at) in claims.items():
        path = run_dir / f"{tid}.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "bound: 30m",
                f"bound: {bound}\nclaimed_by: agent-a\nclaimed_at: {claimed_at}",
            ),
            encoding="utf-8",
        )
        claimed = tickets_mod._parse_iso(claimed_at)
        backdate(
            path,
            10 * 24 * 60
            if claimed is None
            else (datetime.now(timezone.utc) - claimed).total_seconds() / 60,
        )
    return run_dir


class TestSuspendedStatus(unittest.TestCase):
    """contracts/work-item.md: `suspended` is a valid non-terminal wait. A
    suspended ticket is still someone's, so the claim survives the
    transition -- were it dropped, the ticket would go back on offer while
    its holder was only waiting."""

    def test_set_status_accepts_suspended_and_keeps_the_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.assertIn("suspended", tickets_mod.VALID_STATUSES)
            run_dir = make_claimed_repo(tmp, {"T1": ("30m", "2026-07-18T00:00:00Z")})
            result = run_main(tmp, "set-status", "testrun", "T1", "suspended")
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertEqual(
                "suspended", json.loads(result.stdout)["set_status"]["status"]
            )
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: suspended", text)
            self.assertIn("claimed_by: agent-a", text)
            self.assertIn("claimed_at: 2026-07-18T00:00:00Z", text)


def minutes_ago(count: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=count)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class TimeParseFallbackTest(unittest.TestCase):
    """What an unstated or unparsable `bound` and `claimed_at` do to
    staleness -- which is to say, to whether a claim can be taken away.

    Two fallbacks that read alike and point opposite ways: an unparsable
    bound lengthens the claim's protection, an unparsable timestamp removes
    it entirely. Pinned as they behave, not as they ought to.
    """

    def test_a_bound_the_pattern_does_not_match_falls_back_to_the_default(self):
        self.assertEqual(60, tickets_mod.DEFAULT_BOUND_MINUTES)
        for bound, minutes in (
            ("30m", 30),
            ("2h", 120),
            ("  45m  ", 45),
            ("0m", 0),
            ("banana", 60),
            ("30", 60),  # a number with no unit is not a duration here
            ("-5m", 60),  # the pattern has no sign
            ("", 60),
            (None, 60),
            ([], 60),  # not a string at all
        ):
            with self.subTest(bound=bound):
                self.assertEqual(minutes, tickets_mod._parse_bound_minutes(bound))

    def test_a_timestamp_it_cannot_read_is_none_and_never_a_raise(self):
        """`_parse_iso` answers or returns None; it never propagates. Its
        callers are a listing and a staleness check, and one unparsable field
        in one ticket may not take down a read of the whole run.

        The early `isinstance`/blank return is not what makes that true for
        the first four of these -- the `except Exception` below absorbs every
        one of them too, so that return is a guard whose removal changes
        nothing. What this pins is the contract, which only the `except`
        upholds.
        """

        for value in (None, "", "   ", 12345, [], object(),
                      "yesterday", "2020-13-45T99:99:99Z", "2026-07-18T00:00:00+banana"):
            with self.subTest(value=repr(value)):
                self.assertIsNone(tickets_mod._parse_iso(value))

    def test_a_naive_timestamp_is_read_as_utc_not_as_local_time(self):
        """Without this the subtraction in `_is_stale` raises rather than
        answers: an aware `now` minus a naive stamp is a TypeError, so a
        ticket whose `claimed_at` omitted its offset would crash the reader
        rather than be judged."""

        naive = tickets_mod._parse_iso("2026-07-18T00:00:00")
        self.assertEqual(timezone.utc, naive.tzinfo)
        self.assertEqual(tickets_mod._parse_iso("2026-07-18T00:00:00Z"), naive)

    def test_an_unreadable_claim_time_is_stale_and_a_readable_one_is_judged(self):
        now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        stale = tickets_mod._is_stale
        # no timestamp and an unparsable one both read as stale, which is the
        # fallback that hands a claim away rather than holding it
        self.assertTrue(stale(None, 30, now))
        self.assertTrue(stale("yesterday", 30, now))
        self.assertTrue(stale("2026-08-15T11:00:00Z", 30, now))
        self.assertFalse(stale("2026-08-15T11:45:00Z", 30, now))

    def test_a_nonsense_bound_protects_a_claim_longer_than_a_stated_one(self):
        """The end-to-end reading, and the answer to whether `bound: banana`
        is immediately reclaimable: it is not.

        The bound falls back to an hour, which is *longer* than the 30m these
        fixtures otherwise carry, so a bound no one can parse buys the holder
        more time than a bound they stated. `claimed_at: yesterday` is the
        field that does hand a ticket away on sight, because an unparsable
        timestamp is read as expired rather than as unknown.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_claimed_repo(tmp, {
                "T1": ("banana", minutes_ago(45)),  # inside the hour it fell back to
                "T2": ("banana", minutes_ago(75)),  # past it
                "T3": ("30m", "yesterday"),  # the stamp, not the bound, frees this
                "T4": ("30m", minutes_ago(5)),  # a live claim, stated bound
            })
            ready = {item["id"] for item in run_cmd(tmp, "ready")["ready"]}
        self.assertEqual({"T2", "T3"}, ready)


RESULT_TICKET = """---
id: {tid}
run: testrun
status: claimed
executor: orch-tdd
depends_on: []
write_scope: [{artifact}]
bound: {bound}
claimed_by: agent-a
claimed_at: {claimed_at}
---

## Objective

Test ticket.

## Result

Changed `{cited}` on the workspace branch.
"""
