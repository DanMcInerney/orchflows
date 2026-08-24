"""Behavioral ticket regression cases."""

from .packet_checker import *  # noqa: F401,F403

class TestPacketCarriesTheCloseLaw(unittest.TestCase):
    """The packet already carried contracts/work-item.md's filing law; the
    close was the half only the body's link to that 1,690-word file reached
    (S3 F1). The close is a recording act, never a further execution layer:
    the 20260823T210000Z-trunk-slimming run paid every unit's deterministic
    oracles three times (executor, a close-verify fork, the §10 checker)
    because the old close ordered a full `orch-verify` fork the independence
    law never named — the one outside execution is the §10 path's."""

    CLOSE = (
        "Close by running each criterion's oracle once at the frozen result "
        "identity and recording its summary and exit in `## Verification`; "
        "your own entries are UNVERIFIED alone — independence arrives per "
        "rules/verification.md §10, and later readers reuse entries whose "
        "covers are unchanged; `[]` fills an empty Feedback or Risks; an "
        "excluded action suspends through `## Handoff`."
    )

    def prompt_for(self, tmp: Path, body: str = FULL_TICKET, *extra):
        make_packet_repo(tmp, body)
        return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main", *extra)[
            "packet"
        ]["prompt"]

    def test_a_skill_executors_packet_carries_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn(self.CLOSE, " ".join(self.prompt_for(Path(tmp)).split()))

    def test_the_close_orders_no_verify_fork(self):
        """The executor's close spawns nothing: `orch-verify` enters a unit
        only on the §10 re-verifier path, dispatched by the caller."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotIn("through `orch-verify`", self.prompt_for(Path(tmp)))

    def test_a_script_executors_packet_does_not(self):
        """A script node runs no completion test and files no Feedback: its
        stdout is the whole result (contracts/work-item.md, Executor form)."""
        with tempfile.TemporaryDirectory() as tmp:
            prompt = self.prompt_for(
                Path(tmp),
                FULL_TICKET.replace("executor: orch-tdd", "executor: script:tools/m.py"),
            )
            self.assertNotIn("orch-verify", prompt)

    def test_neither_further_child_is_told_to_close_the_item(self):
        """rules/verification.md §10: the re-verifier *is* the close, and the
        checker's close is its correction plus `check`."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, CLAIMED_ISOLATED_TICKET)
            for executor in ("orch-critique", "orch-verify"):
                prompt = run_cmd(
                    tmp, "packet", "testrun", "T1", "--reply-to", "main",
                    "--executor", executor,
                )["packet"]["prompt"]
                self.assertNotIn("Close by running", prompt)

    def test_the_checker_is_bounded_to_one_outside_execution(self):
        """The §10 checker's re-run is THE outside execution, run once; an
        entry whose covers are unchanged is reused, never re-run. Without
        this sentence a diligent checker's cheapest safe move is to re-run
        everything, which the trunk-slimming run paid live."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, CLAIMED_ISOLATED_TICKET)
            prompt = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main",
                "--executor", "orch-critique",
            )["packet"]["prompt"]
            joined = " ".join(prompt.split())
            self.assertIn("one outside execution", joined)
            self.assertIn("covers are unchanged", joined)
            reverifier = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main",
                "--executor", "orch-verify",
            )["packet"]["prompt"]
            self.assertIn("covers` are unchanged", reverifier)


class TestPacketCarriesWhatTwoLanesSpentBoundLearning(unittest.TestCase):
    """Queued scope 7 and 8 of the 20260817T215731Z-research-depth run, both
    from the same pair of lanes: a test command piped through `tail` loses
    the runner's summary, which it writes to stderr, and both lanes then
    argued a check had passed from exit status and a following command; and
    both spent bound running AGENTS.md's repository-level checks inside their
    own branches, which orch-frontier gives to the engine on the integrated
    tip. Neither is a new rule — oracles.md's regression row already gives
    the full suite to the gate — so what is carried is the sentence a lane
    acts on, beside the close law and for that sentence's reason: a rule
    reachable only by following a link is one an executor does not read."""

    def prompt_for(self, tmp: Path, body: str = FULL_TICKET, *extra) -> str:
        make_packet_repo(tmp, body)
        prompt = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main", *extra)[
            "packet"
        ]["prompt"]
        return " ".join(prompt.split())

    def test_the_packet_states_a_checks_summary_is_its_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompt = self.prompt_for(Path(tmp))
            self.assertIn("summary line is its evidence", prompt)
            self.assertIn("`tail`", prompt)

    def test_the_packet_states_the_repo_checks_are_the_engines(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompt = self.prompt_for(Path(tmp))
            self.assertIn("integrated tip", prompt)
            self.assertIn("nothing wider", prompt)

    def test_a_script_node_is_told_neither(self):
        """Both sentences are about reading a check the executor ran, and a
        script node runs none: it runs one command and files its stdout
        verbatim (contracts/work-item.md, Executor form). Carried on the
        close law's own condition, so who is told this is who is told to
        close the item."""
        with tempfile.TemporaryDirectory() as tmp:
            prompt = self.prompt_for(
                Path(tmp),
                FULL_TICKET.replace("executor: orch-tdd", "executor: script:tools/m.py"),
            )
            self.assertNotIn("summary line", prompt)
            self.assertNotIn("integrated tip", prompt)

    def test_neither_further_child_is_told_either(self):
        """The other half of the same audience, and the half nothing held.

        Both sentences ride the close law's condition —
        `executor_script is None and further is None` — so the script node
        above pins one term of it and a rules/verification.md §10 child pins
        the other. Without this case the whole `further` half of that
        condition can be deleted and the suite stays green, which is what a
        repair re-conditioning this block would have to be told."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, CLAIMED_ISOLATED_TICKET)
            for executor in ("orch-critique", "orch-verify"):
                prompt = run_cmd(
                    tmp, "packet", "testrun", "T1", "--reply-to", "main",
                    "--executor", executor,
                )["packet"]["prompt"]
                self.assertNotIn("summary line", prompt)
                self.assertNotIn("integrated tip", prompt)

    def test_a_ticket_with_a_workspace_of_its_own_is_told_its_branch_is_not_the_revision(self):
        """The tail's premise is a branch, so its audience is whoever has one.

        `isolation: required` on a git pack with a scope to write is what
        `packet` itself reads to decide a child establishes a workspace, and
        it is the same fact the tail speaks about."""
        with tempfile.TemporaryDirectory() as tmp:
            prompt = self.prompt_for(Path(tmp), ISOLATED_TICKET)
            self.assertIn("branch is not the revision", prompt)

    def test_a_ticket_with_no_workspace_of_its_own_is_not(self):
        """A ticket that establishes no workspace stands in the dispatcher's
        own, and "your branch" names nothing for it. This run's three gate
        stubs are that shape: no `isolation`, no `workspace_branch`, and each
        was told its green was provisional until a tip its work was already
        on. The head still reaches them — which oracles are theirs is a fact
        about every executor — and only the tail is withheld."""
        with tempfile.TemporaryDirectory() as tmp:
            prompt = self.prompt_for(Path(tmp), FULL_TICKET)
            self.assertIn("nothing wider", prompt)
            self.assertNotIn("branch is not the revision", prompt)
