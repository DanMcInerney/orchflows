"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class AmendTest(unittest.TestCase):
    """`amend` is the cutter's repair channel, open while nothing is worked.

    `cutcheck.py` reports; the decomposer repairs. Until now no subcommand
    could touch an issued ticket's cut-time content, so the repair the cut's
    own oracle demanded was made by editing the file in the sink by hand --
    outside every refusal `new` applies to the same bytes. What the executor
    writes stays `result`'s, and what has been claimed is frozen: a criterion
    that moves under a working executor is the moving target
    rules/verification.md §3 forbids.
    """

    def place(self, tmp: Path, text: str = GOOD_TICKET) -> Path:
        sink = use_sink(tmp)
        source = tmp / "T1.md"
        source.write_text(text, encoding="utf-8")
        self.assertNotIn("error", run_cmd("new", "testrun", "--file", str(source)))
        return sink / "tickets" / "testrun" / "T1.md"

    def test_a_cut_time_section_is_replaced_on_an_unclaimed_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.place(tmp)
            amended = (
                "- the suite exits 0 | oracle: `python -B -m unittest tests.x.Y` "
                "| oracle_class: deterministic | provenance: pre-existing"
            )
            payload = run_cmd(
                "amend", "testrun", "T1", "--section", "Completion test",
                "--text", amended,
            )
            self.assertNotIn("error", payload)
            self.assertEqual("Completion test", payload["amend"]["section"])
            sections = tickets_mod._sections(path.read_text(encoding="utf-8"))
            self.assertEqual(amended, sections["Completion test"].strip())
            self.assertIn("Add `double(n)`", sections["Objective"])

    def test_the_body_may_come_from_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.place(tmp)
            body = tmp / "objective.md"
            body.write_text("Add `triple(n)`.\n", encoding="utf-8")
            payload = run_cmd(
                "amend", "testrun", "T1", "--section", "Objective",
                "--file", str(body),
            )
            self.assertNotIn("error", payload)
            self.assertIn("triple", path.read_text(encoding="utf-8"))

    def test_a_claimed_ticket_is_refused_and_left_exactly_as_it_was(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.place(tmp)
            self.assertNotIn(
                "error", run_cmd("claim", "testrun", "T1", "--by", "someone")
            )
            before = path.read_text(encoding="utf-8")
            payload = run_cmd(
                "amend", "testrun", "T1", "--section", "Objective", "--text", "no",
            )
            self.assertIn("error", payload)
            self.assertIn("someone", payload["error"])
            self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_a_never_claimed_complete_ticket_is_refused(self):
        """The claim is not the whole lifecycle.

        An ad-hoc ticket run inline is never claimed, and `set-status` and
        `result` never require a claim -- so a ticket carrying a verdict was
        still open to an amended `## Completion test`, which is the moving
        target rules/verification.md §3 forbids, arriving after the verdict
        rather than under a working executor.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.place(tmp)
            self.assertNotIn(
                "error", run_cmd("set-status", "testrun", "T1", "complete")
            )
            before = path.read_text(encoding="utf-8")
            payload = run_cmd(
                "amend", "testrun", "T1", "--section", "Completion test",
                "--text", "- the suite exits 0 | oracle: `python -m unittest` "
                "| oracle_class: deterministic | provenance: pre-existing",
            )
            self.assertIn("error", payload)
            self.assertIn("complete", payload["error"])
            self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_a_section_the_executor_writes_is_refused_and_names_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.place(tmp)
            payload = run_cmd(
                "amend", "testrun", "T1", "--section", "Result", "--text", "x",
            )
            self.assertIn("error", payload)
            self.assertIn("result", payload["error"])

    def test_an_amendment_that_would_take_the_ticket_off_contract_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.place(tmp)
            before = path.read_text(encoding="utf-8")
            payload = run_cmd(
                "amend", "testrun", "T1", "--section", "Completion test",
                "--text", "- the suite exits 0",
            )
            self.assertIn("error", payload)
            self.assertIn("oracle", payload["error"])
            self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_a_ticket_that_is_not_there_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.place(tmp)
            payload = run_cmd(
                "amend", "testrun", "T9", "--section", "Objective", "--text", "x",
            )
            self.assertIn("error", payload)
            self.assertIn("T9", payload["error"])


class InstructionCeilingTest(unittest.TestCase):
    """rules/token-economy.md §11: a unit ticket's instruction -- its
    objective, completion test, excluded actions and return fields, never
    its fixed inputs -- is 300 words, and the two subcommands that write
    cut-time content refuse one over it before it lands.

    The ceiling was enforced only on `compositions/*/` stubs, where no
    dispatched ticket ever comes from: every wide ad-hoc set in the sink ran
    at a median instruction of 500-800 words, objectives enumerating (1)...(5)
    -- two atoms issued as one. The refusal is where the cutter still holds
    the flag that was wrong.
    """

    def place(self, tmp: Path, text: str, ticket_id: str = "T1"):
        """`new --file` for one already-written ticket; the sink is the
        test's own."""

        sink = use_sink(tmp)
        source = tmp / f"{ticket_id}.md"
        source.write_text(text, encoding="utf-8")
        payload = run_cmd("new", "testrun", "--file", str(source))
        return payload, sink / "tickets" / "testrun" / f"{ticket_id}.md"

    def assert_names_the_ceiling(self, error, count):
        for expected in (str(count), str(tickets_mod.INSTRUCTION_BUDGET),
                         "rules/token-economy.md", "two items"):
            with self.subTest(expected):
                self.assertIn(expected, error)

    def test_new_refuses_an_instruction_over_the_ceiling(self):
        over = tickets_mod.INSTRUCTION_BUDGET + 1
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            payload, path = self.place(tmp, ceiling_ticket(over))
            self.assertIn("error", payload)
            self.assert_names_the_ceiling(payload["error"], over)
            self.assertFalse(path.exists(), "a refused cut wrote")
            # The flag form renders its own text and lands in the same
            # grade, so a cutter cannot spell its way past the ceiling.
            flagged = run_cmd(
                "new", "testrun", "T2", "--executor", "orch-tdd",
                "--objective", " ".join(["word"] * (over + 20)),
                "--criterion", GOOD_CRITERION,
            )
            self.assertIn("error", flagged)
            self.assert_names_the_ceiling(
                flagged["error"], tickets_mod.INSTRUCTION_BUDGET
            )
            self.assertFalse(
                (path.parent / "T2.md").exists(), "a refused cut wrote"
            )

    def test_new_issues_an_instruction_at_the_ceiling(self):
        at = tickets_mod.INSTRUCTION_BUDGET
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # The fixed inputs are identities, not instruction: four hundred
            # words of them do not move the count.
            payload, path = self.place(
                tmp,
                ceiling_ticket(at, inputs="- " + " ".join(["identity"] * 400)),
            )
            self.assertNotIn("error", payload)
            self.assertTrue(path.is_file())
            self.assertEqual(
                at, tickets_mod.instruction_words(path.read_text(encoding="utf-8"))
            )

    def test_amend_refuses_an_instruction_over_the_ceiling(self):
        """`amend` is the one write path around the refusals `new` applies
        to the same bytes; a cutter could otherwise widen a ticket past the
        ceiling one section at a time."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            payload, path = self.place(
                tmp, ceiling_ticket(tickets_mod.INSTRUCTION_BUDGET)
            )
            self.assertNotIn("error", payload)
            before = path.read_text(encoding="utf-8")
            refused = run_cmd(
                "amend", "testrun", "T1", "--section", "Objective",
                "--text", " ".join(["word"] * tickets_mod.INSTRUCTION_BUDGET),
            )
            self.assertIn("error", refused)
            self.assert_names_the_ceiling(
                refused["error"], tickets_mod.INSTRUCTION_BUDGET
            )
            self.assertEqual(before, path.read_text(encoding="utf-8"))
            # The section that is never instruction stays amendable at any
            # length, and a repair that brings the ticket down lands.
            for section, body in (
                ("Fixed inputs", "- " + " ".join(["identity"] * 400)),
                ("Objective", "cut the run"),
            ):
                with self.subTest(section):
                    self.assertNotIn("error", run_cmd(
                        "amend", "testrun", "T1", "--section", section,
                        "--text", body,
                    ))

    def test_a_root_ticket_is_exempt(self):
        """A root states a whole run, and the `.gate.` stubs `gate` renders
        carry that root's `## Completion test` verbatim. Neither is a unit
        packet, and holding them to the unit ceiling would refuse what this
        script itself writes."""

        over = tickets_mod.INSTRUCTION_BUDGET + 100
        root_text = ceiling_ticket(
            over, executor=tickets_mod.ROOT_EXECUTOR, ticket_id="00-root"
        )
        with tempfile.TemporaryDirectory() as tmp:
            payload, path = self.place(Path(tmp), root_text, ticket_id="00-root")
            self.assertNotIn("error", payload)
            self.assertTrue(path.is_file())
        for ticket_id, executor in (
            ("00-root.gate.critique.code", "orch-critique"),
            ("00-root.gate.verify", "orch-verify"),
        ):
            with self.subTest(ticket_id):
                text = ceiling_ticket(over, executor=executor, ticket_id=ticket_id)
                self.assertIsNone(
                    tickets_mod._ceiling_error("gate stub", ticket_id, text)
                )
