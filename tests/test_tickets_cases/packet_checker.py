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

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = ROOT_TICKET.replace(
                "executor: orch-decompose",
                "executor: orch-decompose\nindependence: gate",
            )
            path = make_packet_repo(tmp, root, tid="R1")
            make_tickets(path.parent, {"R1.01": ("pending", "[]")})
            critique = run_cmd(
                tmp, "packet", "testrun", "R1", "--reply-to", "main",
                "--executor", "orch-critique",
            )
            self.assertIn("packet", critique)
            checked = run_cmd(tmp, "check", "testrun", "R1", "--by", "cut-reader")
            self.assertNotIn("error", checked)

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


ROOT_TICKET = (
    FULL_TICKET.replace("id: T1", "id: R1")
    .replace("executor: orch-tdd", "executor: orch-decompose")
    .replace("claimed_by: legacy-agent", "claimed_by: cutter-a")
)


def command_lines(prompt: str, script_name: str, *leading) -> list:
    """Every emitted command line running ``script_name`` with ``leading`` as
    its first arguments, found the way a child finds it: by the tokens, never
    by position and never by a literal path."""

    found = []
    for line in prompt.splitlines():
        tokens = line.split()
        if len(tokens) <= len(leading) + 1:
            continue
        if Path(tokens[1]).name != script_name:
            continue
        if list(leading) == tokens[2:2 + len(leading)]:
            found.append(line)
    return found


class TestRootTicketCutCheckerPacket(unittest.TestCase):
    """On a root ticket the §10 checker's object is the cut itself.

    The old system reviewed and fixed a decomposition in one call before
    kicking it off; here that reader is the root ticket's own §10 checker
    (rules/verification.md §10), so it needs a different lens, a different
    object and a different authority from the unit checker's: the cut lens,
    the issued subtree read as data, and `amend`/`new` over that subtree —
    never the run's workspace, which is the units' to write. Its repair is
    accepted on `cutcheck.py` re-run (§11), so the packet names that too.
    """

    def make(self, tmp: Path, subtree: dict = None, body: str = ROOT_TICKET) -> Path:
        path = make_packet_repo(tmp, body, tid="R1")
        if subtree is None:
            subtree = {"R1.01": ("pending", "[]")}
        make_tickets(path.parent, subtree)
        return path

    def packet(self, tmp: Path, *extra):
        return run_cmd(tmp, "packet", "testrun", "R1", "--reply-to", "main", *extra)

    def prompt(self, tmp: Path, *extra) -> str:
        return self.packet(tmp, *extra)["packet"]["prompt"]

    def test_the_checker_packet_names_the_cut_lens_by_installed_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            prompt = self.prompt(tmp, "--executor", "orch-critique")
            lens = ROOT / "skills" / "kernel" / "orch-decompose" / "references" / "cut-lens.md"
            self.assertIn(str(lens), prompt)

    def test_the_checker_packet_names_the_subtree_as_its_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            prompt = self.prompt(tmp, "--executor", "orch-critique")
            self.assertIn("R1.NN", prompt)
            self.assertIn("gate stubs", prompt)

    def test_the_checker_packet_grants_amend_and_new_and_no_workspace(self):
        """The root's `write_scope` is the run's workspace, which the units
        write; the cut checker's authority is the unclaimed subtree's
        cut-time sections."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            prompt = self.prompt(tmp, "--executor", "orch-critique")
            self.assertNotIn("scratch/t1.txt", prompt)
            amend = command_lines(prompt, "tickets.py", "amend", "testrun")
            self.assertEqual(1, len(amend), prompt)
            self.assertIn("--section", amend[0])
            self.assertEqual(1, len(command_lines(prompt, "tickets.py", "new", "testrun")), prompt)

    def test_the_checker_packet_names_the_cut_check_and_the_check_verb(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            prompt = self.prompt(tmp, "--executor", "orch-critique",
                                 "--by", "cut-reader")
            cut = command_lines(prompt, "cutcheck.py")
            self.assertEqual(1, len(cut), prompt)
            self.assertIn("--baseline", cut[0])
            self.assertEqual("testrun", cut[0].split()[-1])
            check = command_lines(prompt, "tickets.py", "check", "testrun", "R1")
            self.assertEqual(1, len(check), prompt)
            self.assertIn("--by", check[0])

    def test_a_recorded_baseline_fills_the_revision_the_set_was_cut_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            unresolved = command_lines(
                self.prompt(tmp, "--executor", "orch-critique"), "cutcheck.py"
            )[0]
            self.assertIn("REV", unresolved)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(
                tmp,
                body=ROOT_TICKET.replace(
                    "claimed_by: cutter-a",
                    "claimed_by: cutter-a\nworkspace_baseline: abc1234 clean",
                ),
            )
            resolved = command_lines(
                self.prompt(tmp, "--executor", "orch-critique"), "cutcheck.py"
            )[0]
            self.assertIn("abc1234", resolved)
            self.assertNotIn("clean", resolved)

    def test_a_non_root_checker_packet_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, CLAIMED_ISOLATED_TICKET)
            prompt = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main",
                "--executor", "orch-critique",
            )["packet"]["prompt"]
            self.assertNotIn("cut-lens.md", prompt)
            self.assertEqual([], command_lines(prompt, "cutcheck.py"))
            self.assertEqual([], command_lines(prompt, "tickets.py", "amend", "testrun"))
            self.assertIn("scratch/t1.txt", prompt)

    def test_the_checker_packet_is_refused_once_a_unit_is_claimed(self):
        """`amend` is refused outside the amendable statuses, so a subtree
        with work against it has nothing this child could correct — and the
        frontier dispatching it there ran the cut checker too late."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, {"R1.01": ("claimed", "[]"), "R1.02": ("pending", "[]")})
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertNotIn("packet", payload)
            self.assertIn("R1.01", payload["error"])
            self.assertNotIn("R1.02", payload["error"])

    def test_the_checker_packet_is_refused_on_a_root_with_no_subtree(self):
        """A root no `<root>.` unit has been issued under has no cut to read
        (`cutcheck.py` on the root alone exits 0), and issuing the whole set
        is the decomposition itself, which this child never repeats — the
        refusal `tickets.py gate` makes for the same reason. Gate stubs alone
        are no more a cut than none: the check reads units."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, {})
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertNotIn("packet", payload)
            self.assertIn("no `R1.` subtree", payload["error"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, {"R1.gate.critique.x": ("pending", "[]")})
            self.assertNotIn(
                "packet", self.packet(tmp, "--executor", "orch-critique")
            )

    def test_the_reverifier_packet_names_the_cut_check_at_the_checked_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            prompt = self.prompt(tmp, "--executor", "orch-verify")
            cut = command_lines(prompt, "cutcheck.py")
            self.assertEqual(1, len(cut), prompt)
            self.assertEqual("testrun", cut[0].split()[-1])
            self.assertIn("no write", prompt)
            self.assertEqual([], command_lines(prompt, "tickets.py", "check", "testrun"))

    def test_the_reverifier_is_not_refused_by_a_claimed_unit(self):
        """It corrects nothing, so the window `amend` closes is not its."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, {"R1.01": ("claimed", "[]")})
            self.assertIn("packet", self.packet(tmp, "--executor", "orch-verify"))
