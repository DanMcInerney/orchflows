"""Behavioral ticket regression cases."""

from .lifecycle_claim import *  # noqa: F401,F403

class LeaseByArtifactMotionTest(unittest.TestCase):
    """REVIEW-2026-08-15.md T3: the lease is artifact motion, not the clock.

    A purely temporal `_is_stale` hands a lane's ticket away while that
    lane is still writing, which is the two-live-lanes rules/delegation.md
    §11 forbids. A claim is stale only when nothing has moved for longer
    than the lease -- neither the ticket's own sections nor any artifact
    path its `## Result` names.
    """

    def make(self, tmp: Path, *, bound: str = "30m", claimed_at: str = None,
             claim_age: int = 90, ticket_age: int = 90, artifact_age: int = 90,
             artifact: str = "scratch/built.txt", cited: str = None,
             scope: str = None) -> Path:
        """One claimed ticket over `artifact`.

        `## Result` cites the artifact absolutely by default, which is the
        only citation `_cited_paths` reads: a relative one names a
        different file from every directory, and this reader is the
        frontier's, not the executor's. `cited` and `scope` override the
        citation and the declared `write_scope` independently, which is
        how the two refusals below are exercised.
        """

        sink = use_sink(tmp)
        (tmp / ".git").mkdir(exist_ok=True)
        target = tmp / artifact
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("built\n", encoding="utf-8")
        backdate(target, artifact_age)
        run_dir = sink / "tickets" / "testrun"
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "T1.md"
        path.write_text(
            RESULT_TICKET.format(
                tid="T1", artifact=artifact if scope is None else scope,
                cited=str(target.resolve()) if cited is None else cited,
                bound=bound,
                claimed_at=minutes_ago(claim_age) if claimed_at is None else claimed_at,
            ),
            encoding="utf-8",
        )
        backdate(path, ticket_age)
        return run_dir

    def reclaimable(self, tmp: Path) -> bool:
        listed = [item["id"] for item in run_cmd(tmp, "ready", "--run", "testrun")["ready"]]
        return listed == ["T1"]

    def test_a_claim_past_its_lease_with_a_still_artifact_is_stale(self):
        """The baseline the two cases below are read against: nothing has
        moved since the claim, so the lease expires as it always did."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            self.assertTrue(self.reclaimable(tmp))

    def test_a_moving_result_artifact_holds_the_claim_past_the_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, artifact_age=2)
            self.assertFalse(self.reclaimable(tmp))
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertIn("error", payload)
            self.assertIn("claimed_by: agent-a", (tmp / "state-sink" / "tickets"
                          / "testrun" / "T1.md").read_text(encoding="utf-8"))

    def test_a_moving_ticket_holds_the_claim_past_the_lease(self):
        """The other half of the rule: an executor writing its own sections
        is motion, even when the artifact it names has not landed yet."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, ticket_age=1)
            self.assertFalse(self.reclaimable(tmp))

    def test_a_relative_citation_is_not_read_as_this_lane_s_motion(self):
        """The reader's directory is not the writer's: under
        `isolation: required` the executor moves the file in its own
        worktree while the frontier stats the same relative path in the
        main checkout. A relative citation therefore counts for nothing,
        and only the ticket's own mtime can hold this claim."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, artifact_age=2, cited="scratch/built.txt")
            self.assertTrue(self.reclaimable(tmp))

    def test_a_citation_outside_write_scope_holds_no_claim(self):
        """A `## Result` naming a shared or always-moving path -- a log, a
        sibling's output -- would otherwise make a dead lane
        unreclaimable. Only what the ticket was granted counts."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, artifact_age=2, scope="scratch/other.txt")
            self.assertTrue(self.reclaimable(tmp))

    def test_a_scopeless_ticket_still_reads_its_absolute_citation(self):
        """An empty `write_scope` bounds nothing, so the citation alone
        decides -- an ad-hoc ticket granted no scope still holds its lane
        while its named artifact moves."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, artifact_age=2, scope="")
            self.assertFalse(self.reclaimable(tmp))

    def test_an_artifact_the_result_does_not_name_moves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            stranger = tmp / "scratch" / "unnamed.txt"
            stranger.write_text("fresh\n", encoding="utf-8")
            self.assertTrue(self.reclaimable(tmp))

    def test_no_timestamp_is_stale_however_recently_the_artifact_moved(self):
        """The pre-existing rule, kept: a claim with no readable
        `claimed_at` is reclaimable on sight. Motion cannot rescue a claim
        whose age is unknown -- the lease it would be measured against has
        no start."""

        for claimed_at in ("", "yesterday"):
            with self.subTest(claimed_at=claimed_at), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, claimed_at=claimed_at, artifact_age=0, ticket_age=0)
                self.assertTrue(self.reclaimable(tmp))

    def test_motion_is_read_against_the_lease_not_a_fixed_hour(self):
        """A stated bound still decides: the same two-hour-old motion is
        inside a `3h` lease and outside a `30m` one."""

        for bound, expected in (("3h", False), ("30m", True)):
            with self.subTest(bound=bound), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, bound=bound, claim_age=200, ticket_age=120,
                          artifact_age=120)
                self.assertEqual(expected, self.reclaimable(tmp))

    def test_the_helper_takes_the_motion_it_is_given(self):
        now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        claimed = "2026-08-15T10:00:00Z"
        self.assertTrue(tickets_mod._is_stale(claimed, 30, now))
        self.assertFalse(
            tickets_mod._is_stale(
                claimed, 30, now, datetime(2026, 8, 15, 11, 45, tzinfo=timezone.utc)
            )
        )
        self.assertTrue(
            tickets_mod._is_stale(
                claimed, 30, now, datetime(2026, 8, 15, 11, 0, tzinfo=timezone.utc)
            )
        )


class OSErrorHandlerTest(unittest.TestCase):
    """Every `except OSError` in the script, entered and graded.

    Each turns a filesystem failure into a named JSON error rather than a
    traceback on a channel whose contract is one JSON document; none was
    entered by this suite before. The seams raise on one resolved path only,
    because `chmod` is a no-op on Windows and as root, and a test resting on
    it grades the platform.
    """

    def test_an_unreadable_ticket_is_a_named_error_beside_its_readable_peers(self):
        """`_load_ticket`: one file no one can read is not a run no one can
        list."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]"), "T2": ("ready", "[]")})
            with refusing_to_read(run_dir / "T1.md", PermissionError):
                payload = run_cmd(tmp, "list")
            by_id = {item["id"]: item for item in payload["tickets"]}
            self.assertIn("unreadable ticket", by_id["T1"]["error"])
            self.assertNotIn("error", by_id["T2"])

    def test_a_promotion_that_cannot_be_persisted_leaves_the_ticket_out(self):
        """`_cmd_ready`'s pending promotion: the status on disk and the status
        reported are the same claim, so a write that failed reports nothing
        ready. A promotion announced but not persisted would be handed to an
        executor whose own read finds it still pending."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("complete", "[]"),
                "T2": ("pending", "[T1]"),
                "T3": ("ready", "[]"),
            })
            with refusing_to_write(run_dir / "T2.md"):
                payload = run_cmd(tmp, "ready")
            self.assertEqual(["T3"], [item["id"] for item in payload["ready"]])
            self.assertIn(
                "status: pending", (run_dir / "T2.md").read_text(encoding="utf-8")
            )

    def test_a_ticket_that_stops_being_readable_mid_claim_is_a_named_error(self):
        """`_do_claim`'s re-read. `claim` reads the file twice before that
        re-read, each behind its own guard, so a read failing from the first
        call never reaches this one -- only a file that stops being readable
        partway through does."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            with refusing_to_read(run_dir / "T1.md", PermissionError, after=2):
                result = run_main(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unreadable ticket", json.loads(result.stdout)["error"])
            self.assertIn(
                "status: ready", (run_dir / "T1.md").read_text(encoding="utf-8")
            )

    def test_a_ticket_that_stops_being_readable_mid_packet_is_a_named_error(self):
        """`_cmd_packet` reads the ticket a second time to section it, after
        `_load_ticket` has already read and guarded it."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            with refusing_to_read(run_dir / "T1.md", PermissionError, after=1):
                result = run_main(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unreadable ticket", json.loads(result.stdout)["error"])

    def test_an_unreadable_ticket_refuses_the_result_rather_than_dropping_it(self):
        """`_cmd_result`'s read. Nothing is written when the read fails, so
        the executor's body is refused loudly instead of landing in a file
        rendered from text no one could see."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            with refusing_to_read(run_dir / "T1.md", PermissionError):
                result = run_main(
                    tmp, "result", "testrun", "T1", "--section", "Result", "--text", "x"
                )
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unreadable ticket", json.loads(result.stdout)["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_a_ticket_that_cannot_be_written_says_so_by_name(self):
        """`_cmd_result`'s write: a different handler and a different word
        from the read's, because a caller retries the two differently."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("claimed", "[]")})
            with refusing_to_write(run_dir / "T1.md"):
                result = run_main(
                    tmp, "result", "testrun", "T1", "--section", "Result", "--text", "x"
                )
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unwritable ticket", json.loads(result.stdout)["error"])

    def test_a_worklog_whose_close_cannot_be_read_refuses_the_note(self):
        """`_notes_terminal` was the one OSError here that was swallowed
        rather than reported: an unreadable worklog read as an open one, so
        the note landed past a close nobody could see. That was pinned as
        "recorded as it behaves"; F F4 read it as the defect it is -- a
        refused read is a concurrent appender's mandatory byte-zero lock on
        Windows, waited out and then reported, never taken as the log being
        open. `PermissionError` is that lock's shape, so this run also proves
        the wait ends in the error rather than the note."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(
                worktree, "run-state", "testrun",
                "--terminal", "complete", "--text", "the deciding evidence",
            )
            log = notes_of()
            self.assertIn("complete", log.read_text(encoding="utf-8"))
            with refusing_to_read(log, PermissionError):
                payload = run_cmd(worktree, "run-state", "testrun", "--note", "past the close")
            self.assertIn("unreadable run notes", payload["error"])
            self.assertNotIn("past the close", log.read_text(encoding="utf-8"))

    def test_an_unreadable_run_state_body_file_is_an_error_not_a_traceback(self):
        """`_cmd_run_state`'s body read: the `_cmd_result` handler's twin, on
        the other channel and reached by other flags."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            a_directory = worktree / "body-that-is-a-directory.md"
            a_directory.mkdir()
            present = worktree / "present-but-unreadable.md"
            present.write_text("bytes no reader reaches\n", encoding="utf-8")

            for label, path, raiser in (
                ("a directory where a file is expected", a_directory, None),
                ("a present file whose read raises", present, PermissionError),
            ):
                with self.subTest(label):
                    with refusing_to_read(path, raiser):
                        result = run_main(
                            worktree, "run-state", "testrun",
                            "--artifact", "evidence.md", "--file", str(path),
                        )
                    self.assertEqual(1, result.returncode, result.stdout)
                    error = json.loads(result.stdout)["error"]
                    self.assertIn("unreadable body file", error, error)

    def test_a_run_directory_that_cannot_be_made_is_a_named_error(self):
        """`_cmd_run_state`'s write. A plain file standing where the run's
        directory goes needs no seam at all: `mkdir(exist_ok=True)` excuses an
        existing directory, never an existing file, on every platform."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            runs = sink_root() / "runs"
            runs.mkdir(parents=True, exist_ok=True)
            (runs / "testrun").write_text("not a directory\n", encoding="utf-8")
            result = run_main(worktree, "run-state", "testrun", "--note", "nowhere to land")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unwritable run state", json.loads(result.stdout)["error"])

    def test_an_unreachable_identity_snapshot_is_the_payload_refusal(self):
        """A failed payload setup must not trigger identity rollback when no
        identity write landed."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            runs = sink_root() / "runs"
            runs.mkdir(parents=True, exist_ok=True)
            blocker = runs / "testrun"
            original = "not a directory\n"
            blocker.write_text(original, encoding="utf-8")

            result = run_main(worktree, "run-state", "testrun", "--note", "nowhere")

            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn("unwritable run state", error, error)
            self.assertNotIn("identity rollback also failed", error, error)
            self.assertEqual(original, blocker.read_text(encoding="utf-8"))


