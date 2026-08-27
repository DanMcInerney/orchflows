"""Behavioral ticket regression cases."""

from .grant import *  # noqa: F401,F403

class TestCheckerPathPacket(unittest.TestCase):
    """`packet --executor` is rules/verification.md §10's two further-context
    children on one claimed item: the checker and the re-verifier.

    Without it the frontier hand-wrote both packets, so neither carried the
    filing channel, the authority or the run-state channel this script owns
    (S1 F1). It is not a general executor override: a second executor for
    one item is what rules/delegation.md §11 forbids.
    """

    def make(self, tmp: Path, body: str = CLAIMED_ISOLATED_TICKET) -> Path:
        return make_packet_repo(tmp, body)

    def packet(self, tmp: Path, *extra):
        return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main", *extra)

    def test_without_the_flag_the_packet_is_the_ticket_executors(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            packet = self.packet(tmp)["packet"]
            self.assertEqual("orch-tdd", packet["executor"])
            self.assertIn("Apply skill orch-tdd", packet["prompt"])
            self.assertNotIn("tickets.py check", packet["prompt"])

    def test_a_critique_packet_names_the_skill_the_scope_and_the_check_verb(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            packet = self.packet(tmp, "--executor", "orch-critique",
                                 "--by", "checker-a")["packet"]
            prompt = packet["prompt"]
            self.assertEqual("orch-critique", packet["executor"])
            self.assertIn("Apply skill orch-critique", prompt)
            # the ticket's own write scope is the checker's authority
            self.assertIn("scratch/t1.txt", prompt)
            # and the verb it runs after correcting, one token per argument
            check_lines = [
                line for line in prompt.splitlines()
                if line.split()[2:4] == ["check", "testrun"]
            ]
            self.assertEqual(1, len(check_lines), prompt)
            self.assertIn("--by", check_lines[0])
            self.assertEqual(Path(check_lines[0].split()[1]).name, "tickets.py")

    def test_a_verify_packet_names_the_skill_the_identity_and_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            packet = self.packet(tmp, "--executor", "orch-verify")["packet"]
            prompt = packet["prompt"]
            self.assertEqual("orch-verify", packet["executor"])
            self.assertIn("Apply skill orch-verify", prompt)
            self.assertIn("## Completion test", prompt)
            self.assertIn("no write", prompt)
            # a re-verifier corrects nothing, so it is never sent the verb
            self.assertNotIn("tickets.py check", prompt)

    def test_neither_further_child_re_establishes_the_workspace(self):
        """`workspace.py start` records the branch the caller stands in over
        the executor's own — and that record is the `--base` the join grades
        the merge against. A further child on the same item never runs it."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            self.assertEqual(1, len(establishment_lines(self.packet(tmp)["packet"]["prompt"])))
            for executor in ("orch-critique", "orch-verify"):
                prompt = self.packet(tmp, "--executor", executor)["packet"]["prompt"]
                self.assertEqual([], establishment_lines(prompt), prompt)
                self.assertNotIn("workspace.py", prompt)

    def test_an_executor_outside_the_checker_path_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            payload = self.packet(tmp, "--executor", "orch-repair")
            self.assertIn("orch-repair", payload["error"])
            self.assertIn("orch-critique", payload["error"])
            self.assertNotIn("packet", payload)

    def test_a_further_child_on_an_unclaimed_ticket_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, ISOLATED_TICKET.replace("status: claimed", "status: ready"))
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertIn("not claimed", payload["error"])
            self.assertNotIn("packet", payload)

    def test_gate_deferred_ticket_excludes_checker_and_preserves_checker_paths(self):
        gate_deferred = CLAIMED_ISOLATED_TICKET.replace(
            "executor: orch-tdd", "executor: orch-tdd\nindependence: gate"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp, gate_deferred)
            before = path.read_bytes()
            for executor in ("orch-critique", "orch-verify"):
                with self.subTest(executor=executor):
                    payload = self.packet(tmp, "--executor", executor)
                    self.assertIn("downstream gate", payload["error"])
                    self.assertNotIn("packet", payload)
            checked = run_cmd(tmp, "check", "testrun", "T1", "--by", "checker-a")
            self.assertIn("downstream gate", checked["error"])
            self.assertEqual(before, path.read_bytes())
            for argv in (
                ("packet", "testrun", "T1", "--reply-to", "main", "--executor",
                 "orch-critique"),
                ("check", "testrun", "T1", "--by", "checker-a"),
            ):
                completed = run_full(tmp, *argv)
                self.assertNotEqual(0, completed.returncode, completed.stdout)
                self.assertIn("downstream gate", completed.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            for executor in ("orch-critique", "orch-verify"):
                with self.subTest(executor=executor):
                    self.assertIn("packet", self.packet(tmp, "--executor", executor))

    def test_checker_packet_is_refused_after_the_first_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            self.assertNotIn(
                "error", run_cmd(tmp, "check", "testrun", "T1", "--by", "checker-a")
            )
            before = path.read_bytes()
            completed = run_full(
                tmp, "packet", "testrun", "T1", "--reply-to", "main",
                "--executor", "orch-critique",
            )
            self.assertNotEqual(0, completed.returncode, completed.stdout)
            self.assertIn("already checked", completed.stdout)
            self.assertEqual(before, path.read_bytes())

    def test_the_tickets_profile_override_stays_with_the_executors_dispatch(self):
        """contracts/work-item.md `profile` is the executor's role override;
        rules/roles.md §5 binds an override to the dispatch naming it. A
        further §10 child is another dispatch, its role its own skill's
        (orch-critique declares planner), so its packet carries no profile
        even when the ticket names one for its executor."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(
                tmp,
                CLAIMED_ISOLATED_TICKET.replace(
                    "status: claimed", "status: claimed\nprofile: orch-worker"
                ),
            )
            self.assertEqual("orch-worker", self.packet(tmp)["packet"]["profile"])
            for executor in ("orch-critique", "orch-verify"):
                packet = self.packet(tmp, "--executor", executor)["packet"]
                self.assertIsNone(packet["profile"], packet)
