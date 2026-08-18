"""The ticket script's issue path: the two shape functions, `new`, and
`instantiate`.

`tests/test_tickets.py` covers the query and write path this module's
subject sits beside; the sink idiom (a temporary `ORCHFLOWS_STATE_HOME`)
is the same one, restated here rather than imported so this module runs
alone under `tools/run_tests.py`'s per-module child.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

# One criterion in the shape `new --criterion` writes and `packet` grades.
GOOD_CRITERION = "the suite exits 0 | oracle: `python -m unittest` | oracle_class: deterministic"

GOOD_TICKET = """---
id: T1
run: testrun
status: ready
executor: orch-tdd
depends_on: []
write_scope: [scratch/t1.txt]
bound: 30m
claimed_by:
claimed_at:
---

## Objective

Add `double(n)`.

## Fixed inputs

None.

## Completion test

- {criterion}

## Return fields

status; result; verification.

## Result

## Verification

## Feedback

[]

## Risks

[]
""".format(criterion=GOOD_CRITERION)

# A stub is the same ticket missing only `run`, `status` and `claimed_*`.
GOOD_STUB = "\n".join(
    line
    for line in GOOD_TICKET.splitlines()
    if not line.startswith(("run:", "status:", "claimed_by:", "claimed_at:"))
) + "\n"


def use_sink(tmp: Path) -> Path:
    """Point ``ORCHFLOWS_STATE_HOME`` at a sink under this test's tempdir.

    Resolved before it is published, and set for the process rather than
    restored: ``tests/__init__.py`` holds the floor at a temporary
    directory regardless, so the worst a stale value can do is fail a
    test. A subprocess launched afterwards inherits it.
    """

    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def run_cmd(*args):
    """One dispatch in this process, as the payload a reader of stdout gets."""

    payload = tickets_mod._dispatch([str(arg) for arg in args])
    return json.loads(json.dumps(payload, ensure_ascii=False))


def run_full(cwd: Path, *args):
    """A real process: argv, exit code, and one JSON document on stdout."""

    return subprocess.run(
        [sys.executable, str(TICKETS_PY), *[str(a) for a in args]],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


def criterion(text: str) -> list:
    return tickets_mod.criterion_defects(text)


class CriterionDefectsTest(unittest.TestCase):
    """`criterion_defects` reads one completion-test section and answers per
    criterion: the oracle, the oracle class against contracts/verdict.md's
    three, and the provenance against work-item.md's two."""

    def test_a_criterion_carrying_oracle_and_class_is_clean(self):
        self.assertEqual([], criterion(f"- {GOOD_CRITERION}"))

    def test_the_prose_spelling_is_the_same_criterion(self):
        """The library's own tickets write `Oracle: that command.
        oracle_class: deterministic.` rather than the pipe form; both name
        the same two things and neither is a defect."""

        self.assertEqual(
            [],
            criterion(
                "1. `python -m unittest` exits 0. Oracle: that command. "
                "oracle_class: deterministic."
            ),
        )

    def test_a_criterion_with_no_oracle_is_named(self):
        defects = criterion("- the suite exits 0 | oracle_class: deterministic")
        self.assertEqual(1, len(defects), defects)
        self.assertIn("oracle", defects[0])
        self.assertIn("criterion 1", defects[0])

    def test_a_criterion_with_no_oracle_class_is_named(self):
        defects = criterion("- the suite exits 0 | oracle: the command")
        self.assertEqual(1, len(defects), defects)
        self.assertIn("oracle_class", defects[0])

    def test_an_off_enum_oracle_class_is_named_with_the_enum(self):
        defects = criterion(
            "- the suite exits 0 | oracle: the command | oracle_class: mechanical"
        )
        self.assertEqual(1, len(defects), defects)
        self.assertIn("mechanical", defects[0])
        for allowed in ("deterministic", "judged", "evidence"):
            self.assertIn(allowed, defects[0])

    def test_every_class_the_verdict_contract_names_is_accepted(self):
        for allowed in tickets_mod.ORACLE_CLASSES:
            with self.subTest(allowed):
                self.assertEqual(
                    [], criterion(f"- x | oracle: y | oracle_class: {allowed}")
                )

    def test_an_off_enum_provenance_is_named_and_a_valid_one_is_not(self):
        defects = criterion(
            "- x | oracle: y | oracle_class: judged | provenance: invented"
        )
        self.assertEqual(1, len(defects), defects)
        self.assertIn("provenance", defects[0])
        self.assertIn("invented", defects[0])
        for allowed in tickets_mod.ORACLE_PROVENANCES:
            with self.subTest(allowed):
                self.assertEqual(
                    [],
                    criterion(
                        f"- x | oracle: y | oracle_class: judged | provenance: {allowed}"
                    ),
                )

    def test_only_the_offending_criterion_is_reported(self):
        """The whole-section substring test this replaces passed a section
        whose second criterion named nothing, because its first one did."""

        section = (
            f"- first | oracle: a | oracle_class: deterministic\n"
            f"- second | oracle: b\n"
            f"- third | oracle: c | oracle_class: judged\n"
        )
        defects = criterion(section)
        self.assertEqual(1, len(defects), defects)
        self.assertIn("criterion 2", defects[0])

    def test_a_wrapped_criterion_is_one_criterion(self):
        """A criterion long enough to wrap carries its oracle on the
        continuation line; reading each line as a criterion would report two
        defects on one clean bullet."""

        self.assertEqual(
            [],
            criterion(
                "- the suite exits 0 under every interpreter CI runs\n"
                "  | oracle: `python tools/run_tests.py` | oracle_class: deterministic\n"
            ),
        )

    def test_a_bullet_inside_a_fence_is_quoted_content(self):
        """Executors quote ticket markdown at length; a quoted bullet is not
        a criterion of this ticket."""

        section = (
            "- real | oracle: a | oracle_class: deterministic\n"
            "\n"
            "```\n"
            "- quoted, and naming nothing\n"
            "```\n"
        )
        self.assertEqual([], criterion(section))

    def test_a_section_with_no_criterion_at_all_is_a_defect(self):
        for empty in ("", "The suite has to pass.", "   \n"):
            with self.subTest(empty):
                defects = criterion(empty)
                self.assertEqual(1, len(defects), defects)
                self.assertIn("criterion", defects[0])


class NarrowConsoleTest(unittest.TestCase):
    """A payload quoting ticket prose prints to a console that cannot spell it.

    `worklog --write` raised UnicodeEncodeError from its one `print` over a
    ticket carrying an arrow: the run's whole view was lost to the encoding of
    the terminal it was being shown on. The payload stays UTF-8 by contract --
    `ensure_ascii=False` is what keeps a path or a criterion readable in it --
    so the console's own inability to spell a character is answered where it
    arises, at the stream.
    """

    ARROW = "→"

    def test_a_payload_holding_an_unencodable_character_still_prints(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(
                GOOD_TICKET.replace("Add `double(n)`.", f"n {self.ARROW} 2n."),
                encoding="utf-8",
            )
            self.assertNotIn(
                "error", run_cmd("new", "testrun", "--file", str(source))
            )
            environment = dict(os.environ)
            environment["PYTHONIOENCODING"] = "cp1252"
            environment[STATE_HOME_ENV_VAR] = str(sink)
            completed = subprocess.run(
                [sys.executable, str(TICKETS_PY), "worklog", "testrun"],
                capture_output=True, cwd=str(tmp), env=environment,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertIn(b"worklog", completed.stdout)
            self.assertNotIn(b"UnicodeEncodeError", completed.stderr)


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


# A ticket whose instruction is padded to an exact word count. Every part
# the counter reads is a slot here, so this module can spend the budget with
# `str.split` -- its own arithmetic, not the owner's -- and the two have to
# agree on the number the refusal states.
CEILING_EXCLUDED = ("adding a third-party dependency", "editing a T0 contract")
CEILING_RETURNS = "status; result; verification."
CEILING_TICKET = """---
id: {ticket_id}
run: testrun
status: ready
executor: {executor}
depends_on: []
write_scope: [scratch/t1.txt]
excluded_actions:
  - {excluded_one}
  - {excluded_two}
bound: 30m
claimed_by:
claimed_at:
---

## Objective

{objective}

## Fixed inputs

{inputs}

## Completion test

- {criterion}

## Return fields

{returns}

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


def ceiling_ticket(total, inputs="None.", executor="orch-tdd", ticket_id="T1"):
    """One ticket whose instruction is exactly ``total`` words.

    The objective takes whatever the excluded actions, the criterion and the
    return fields have not already spent; `## Fixed inputs` is free of the
    count by law, so a caller pads it to prove exactly that.
    """

    spent = sum(
        len(part.split())
        for part in (*CEILING_EXCLUDED, "- " + GOOD_CRITERION, CEILING_RETURNS)
    )
    return CEILING_TICKET.format(
        ticket_id=ticket_id,
        executor=executor,
        excluded_one=CEILING_EXCLUDED[0],
        excluded_two=CEILING_EXCLUDED[1],
        objective=" ".join(["word"] * (total - spent)),
        inputs=inputs,
        criterion=GOOD_CRITERION,
        returns=CEILING_RETURNS,
    )


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


class CriterionNestingTest(unittest.TestCase):
    """Indentation, in the one owner of criterion parsing.

    `scripts/cutcheck.py` carried a second parser with these two rules in it
    and graded the same sections by them; the rules live here now, so a
    section reads the same to the cutter and to the refusal that issues it.
    """

    def test_a_list_nested_under_a_criterion_is_that_criterions_own_text(self):
        section = (
            "1. the installer names every script | oracle: `grep -n X install.py`\n"
            "   | oracle_class: deterministic, over\n"
            "   1. the tuple it opens, and\n"
            "   2. every name it lists.\n"
            "2. the second criterion opens on its own | oracle: y "
            "| oracle_class: judged\n"
        )
        criteria = tickets_mod._criteria(section)
        self.assertEqual(2, len(criteria), criteria)
        self.assertIn("1. the tuple it opens, and", criteria[0])
        self.assertEqual([], criterion(section))

    def test_an_unindented_prose_line_ends_the_continuation_not_the_list(self):
        section = (
            "1. first | oracle: a | oracle_class: deterministic\n"
            "\n"
            "An unindented prose line interrupts the list here.\n"
            "\n"
            "  2. second | oracle: b | oracle_class: judged\n"
        )
        criteria = tickets_mod._criteria(section)
        self.assertEqual(2, len(criteria), criteria)
        self.assertNotIn("unindented prose", criteria[0])

    def test_a_bullet_at_the_opening_indentation_still_opens_its_own_criterion(self):
        section = (
            "  - first | oracle: a | oracle_class: deterministic\n"
            "  - second | oracle: b | oracle_class: judged\n"
        )
        self.assertEqual(2, len(tickets_mod._criteria(section)))


class TicketDefectsTest(unittest.TestCase):
    """`ticket_defects` is the one owner of ticket shape in code: frontmatter
    keys, the status enum, the body sections, and every criterion defect."""

    def test_a_ticket_in_contract_shape_has_no_defects(self):
        self.assertEqual([], tickets_mod.ticket_defects(GOOD_TICKET))

    def test_a_file_with_no_frontmatter_is_the_only_defect_reported(self):
        defects = tickets_mod.ticket_defects("## Objective\n\nA ticket without a head.\n")
        self.assertEqual(1, len(defects), defects)
        self.assertIn("frontmatter", defects[0])

    def test_each_required_frontmatter_key_is_named_when_absent(self):
        for key in ("executor", "depends_on", "write_scope", "bound", "run", "status"):
            with self.subTest(key):
                stripped = "\n".join(
                    line for line in GOOD_TICKET.splitlines()
                    if not line.startswith(f"{key}:")
                )
                defects = tickets_mod.ticket_defects(stripped)
                self.assertTrue(
                    any(f"'{key}'" in defect for defect in defects), defects
                )

    def test_an_off_enum_status_is_named_with_the_enum(self):
        defects = tickets_mod.ticket_defects(
            GOOD_TICKET.replace("status: ready", "status: in-progress")
        )
        self.assertTrue(any("in-progress" in defect for defect in defects), defects)
        self.assertTrue(any("complete" in defect for defect in defects), defects)

    def test_each_required_body_section_is_named_when_absent(self):
        for section in (
            "Objective", "Fixed inputs", "Completion test", "Return fields",
            "Result", "Verification", "Feedback", "Risks",
        ):
            with self.subTest(section):
                text = GOOD_TICKET.replace(f"## {section}", "## Something else", 1)
                defects = tickets_mod.ticket_defects(text)
                self.assertTrue(
                    any(section in defect for defect in defects), (section, defects)
                )

    def test_a_criterion_defect_is_a_ticket_defect(self):
        defects = tickets_mod.ticket_defects(
            GOOD_TICKET.replace(" | oracle_class: deterministic", "")
        )
        self.assertTrue(any("oracle_class" in defect for defect in defects), defects)

    def test_a_stub_needs_neither_run_nor_status(self):
        """A stub is a ticket missing only `run`, `status` and `claimed_*`;
        those are instantiation's to add, so a stub is not defective for
        lacking them — and is still graded on everything else."""

        self.assertEqual([], tickets_mod.ticket_defects(GOOD_STUB, stub=True))
        self.assertNotEqual([], tickets_mod.ticket_defects(GOOD_STUB))

    def test_a_stub_is_still_graded_on_the_keys_it_must_carry(self):
        without_executor = "\n".join(
            line for line in GOOD_STUB.splitlines()
            if not line.startswith("executor:")
        )
        defects = tickets_mod.ticket_defects(without_executor, stub=True)
        self.assertTrue(any("'executor'" in defect for defect in defects), defects)

    def test_a_stub_carrying_an_off_enum_status_is_still_refused(self):
        defects = tickets_mod.ticket_defects(
            GOOD_STUB.replace("executor: orch-tdd", "executor: orch-tdd\nstatus: nearly"),
            stub=True,
        )
        self.assertTrue(any("nearly" in defect for defect in defects), defects)


def place(sink: Path, run: str, ticket_id: str, text: str) -> Path:
    """Put one ticket in the sink at the path every workspace agrees on."""

    run_dir = sink / "tickets" / run
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{ticket_id}.md"
    path.write_text(text, encoding="utf-8")
    return path


class PacketGradesEveryCriterionTest(unittest.TestCase):
    """`packet`'s completion-test check is `criterion_defects`, so the
    refusal says which criterion and what it lacks. The whole-section
    substring test it replaces claimed to check every criterion and checked
    the section once."""

    def two_criteria(self, second: str) -> str:
        return GOOD_TICKET.replace(
            f"- {GOOD_CRITERION}", f"- {GOOD_CRITERION}\n- {second}"
        )

    def test_a_second_criterion_naming_no_class_is_refused_by_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            place(sink, "testrun", "T1", self.two_criteria("the doc reads well | oracle: the lens"))
            payload = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("error", payload)
            self.assertIn("criterion 2", payload["error"])
            self.assertIn("oracle_class", payload["error"])

    def test_the_section_naming_a_class_once_no_longer_carries_the_rest(self):
        """The case the old check passed: `oracle_class` appears in the
        section, so the substring was found, and the second criterion named
        neither an oracle nor a class."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            place(sink, "testrun", "T1", self.two_criteria("it looks right"))
            payload = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("error", payload)
            self.assertIn("criterion 2", payload["error"])

    def test_every_criterion_naming_both_is_dispatched(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            place(
                sink, "testrun", "T1",
                self.two_criteria("the lens finds no defect | oracle: the lens | oracle_class: judged"),
            )
            payload = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertNotIn("error", payload)
            self.assertEqual("T1", payload["packet"]["id"])


def new_args(*extra) -> list:
    """`new` with the three parts every ticket needs, plus ``extra``."""

    return [
        "new", "testrun", "T1",
        "--executor", "orch-verify",
        "--objective", "the suite is green",
        "--criterion", GOOD_CRITERION,
        *extra,
    ]


class NewTest(unittest.TestCase):
    """`new` issues one ticket into the sink, in contract shape, refusing
    anything `ticket_defects` reports before it writes."""

    def ticket_path(self, sink: Path, ticket_id: str = "T1") -> Path:
        return sink / "tickets" / "testrun" / f"{ticket_id}.md"

    def test_a_criterion_naming_no_class_is_refused_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(
                "new", "testrun", "T1", "--executor", "orch-verify",
                "--objective", "o", "--criterion", "x",
            )
            self.assertIn("error", payload)
            self.assertIn("oracle_class", payload["error"])
            self.assertFalse(self.ticket_path(sink).exists(), "a refused cut wrote")
            self.assertFalse((sink / "tickets" / "testrun").exists())

    def test_a_complete_cut_is_written_ready_and_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(*new_args())
            self.assertNotIn("error", payload)
            written = self.ticket_path(sink)
            self.assertEqual(str(written), payload["new"]["path"])
            self.assertTrue(written.is_file())
            listed = run_cmd("list", "--run", "testrun")["tickets"]
            self.assertEqual(1, len(listed), listed)
            self.assertEqual("ready", listed[0]["status"])
            self.assertEqual("T1", listed[0]["id"])

    def test_what_new_writes_has_no_defects_of_its_own(self):
        """The cut is graded by the same function that grades every other
        ticket, so its own output cannot be off contract."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args("--write-scope", "scratch/a.txt", "--bound", "30m"))
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            self.assertEqual([], tickets_mod.ticket_defects(text))

    def test_the_body_sections_are_in_the_contract_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            found = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
            self.assertEqual(list(tickets_mod.REQUIRED_SECTIONS), found)

    def test_a_section_body_is_separated_from_its_heading(self):
        """The house shape every ticket in the sink is written in, and the one
        `result --section` writes back: a blank line under the heading."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            self.assertIn("## Objective\n\nthe suite is green\n", text)
            self.assertIn("## Feedback\n\n[]\n", text)

    def test_feedback_and_risks_are_pre_filled_and_the_executor_sections_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            body = tickets_mod._sections(self.ticket_path(sink).read_text(encoding="utf-8"))
            self.assertEqual("[]", body["Feedback"])
            self.assertEqual("[]", body["Risks"])
            self.assertEqual("", body["Result"])
            self.assertEqual("", body["Verification"])

    def test_a_dependency_makes_the_cut_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(*new_args("--depends-on", "T0,T00"))
            self.assertEqual("pending", payload["new"]["status"])
            data = tickets_mod._parse_frontmatter(
                self.ticket_path(sink).read_text(encoding="utf-8")
            )
            self.assertEqual(["T0", "T00"], data["depends_on"])
            self.assertEqual("pending", data["status"])

    def test_the_optional_parts_land_where_the_contract_puts_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args(
                "--pack", "orch-code-pack",
                "--write-scope", "scripts/a.py,tests/test_a.py",
                "--bound", "40m",
                "--input", "contracts/work-item.md",
                "--input", "SPEC.md",
                "--excluded", "pushing, or forcing a push",
                "--profile", "orch-worker",
                "--independence", "gate",
                "--isolation", "required",
                "--return-fields", "status; the branch name",
            ))
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            data = tickets_mod._parse_frontmatter(text)
            self.assertEqual("orch-code-pack", data["pack"])
            self.assertEqual(["scripts/a.py", "tests/test_a.py"], data["write_scope"])
            self.assertEqual("40m", data["bound"])
            self.assertEqual("orch-worker", data["profile"])
            self.assertEqual("gate", data["independence"])
            self.assertEqual("required", data["isolation"])
            # an excluded action carrying a comma is one action, not two
            self.assertEqual(["pushing, or forcing a push"], data["excluded_actions"])
            sections = tickets_mod._sections(text)
            self.assertIn("contracts/work-item.md", sections["Fixed inputs"])
            self.assertIn("SPEC.md", sections["Fixed inputs"])
            self.assertEqual("status; the branch name", sections["Return fields"])

    def test_the_cut_is_claimable_and_dispatchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            run_cmd(*new_args("--write-scope", "scratch/a.txt", "--bound", "30m"))
            ready = run_cmd("ready", "--run", "testrun")["ready"]
            self.assertEqual(["T1"], [item["id"] for item in ready])
            packet = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertNotIn("error", packet)
            self.assertEqual("orch-verify", packet["packet"]["executor"])
            claimed = run_cmd("claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual("agent-a", claimed["claimed"]["claimed_by"])

    def test_an_id_already_issued_is_refused_and_the_first_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            before = self.ticket_path(sink).read_text(encoding="utf-8")
            payload = run_cmd(
                "new", "testrun", "T1", "--executor", "orch-tdd",
                "--objective", "something else", "--criterion", GOOD_CRITERION,
            )
            self.assertIn("error", payload)
            self.assertIn("T1", payload["error"])
            self.assertEqual(before, self.ticket_path(sink).read_text(encoding="utf-8"))

    def test_second_root_is_an_atomic_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            first = run_cmd(
                "new", "testrun", "R1", "--executor", "orch-decompose",
                "--objective", "deliver the first kind", "--criterion", GOOD_CRITERION,
                "--write-scope", "scratch/first.txt",
            )
            self.assertNotIn("error", first)
            run_dir = sink / "tickets" / "testrun"
            before = {path.name: path.read_bytes() for path in run_dir.glob("*.md")}
            second = run_cmd(
                "new", "testrun", "R2", "--executor", "orch-decompose",
                "--objective", "deliver another kind", "--criterion", GOOD_CRITERION,
                "--write-scope", "scratch/second.txt",
            )
            self.assertIn("one root", second["error"])
            self.assertIn("R1", second["error"])
            self.assertEqual(before, {
                path.name: path.read_bytes() for path in run_dir.glob("*.md")
            })

    def test_concurrent_root_creators_leave_exactly_one_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            sink = use_sink(tmp)
            common = [
                "--executor", "orch-decompose", "--objective", "one kind",
                "--criterion", GOOD_CRITERION, "--write-scope", "scratch/out.txt",
            ]
            processes = [
                subprocess.Popen(
                    [sys.executable, str(TICKETS_PY), "new", "race-run", root, *common],
                    cwd=str(tmp), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                )
                for root in ("R1", "R2")
            ]
            results = [process.communicate(timeout=20) + (process.returncode,)
                       for process in processes]
            self.assertEqual([0, 1], sorted(result[2] for result in results), results)
            run_dir = sink / "tickets" / "race-run"
            roots = [
                path for path in run_dir.glob("*.md")
                if tickets_mod._executor_of(tickets_mod._parse_frontmatter(
                    path.read_text(encoding="utf-8")
                )) == tickets_mod.ROOT_EXECUTOR
            ]
            self.assertEqual(1, len(roots), results)

    def test_new_reserves_every_gate_family_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(
                "new", "testrun", "R.gate.repair", "--executor", "orch-repair",
                "--objective", "forge a gate", "--criterion", GOOD_CRITERION,
            )
            self.assertIn("reserved", payload["error"])
            self.assertFalse((sink / "tickets" / "testrun" / "R.gate.repair.md").exists())

    def test_new_and_instantiate_share_immutable_run_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            commit = "b" * 40
            (sink.parent / "receipt.json").write_text(
                json.dumps({"version": 4, "source_commit": commit}),
                encoding="utf-8",
            )
            self.assertNotIn("error", run_cmd(*new_args()))
            identity_path = sink / "runs" / "testrun" / "run.json"
            opened = identity_path.read_bytes()
            (sink.parent / "receipt.json").write_text(
                json.dumps({"version": 99, "source_commit": "c" * 40}),
                encoding="utf-8",
            )
            directory = make_template(tmp, {"A": stub("A"), "B": stub("B", "[A]")})
            appended = run_cmd(
                "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scratch/x.txt",
            )
            self.assertNotIn("error", appended)
            self.assertEqual(opened, identity_path.read_bytes())
            (sink.parent / "receipt.json").write_text(
                json.dumps({"version": 4, "source_commit": commit}),
                encoding="utf-8",
            )

            separate = run_cmd(
                "instantiate", str(directory), "--run", "template-run",
                "--set", "target=scratch/x.txt",
            )
            self.assertNotIn("error", separate)
            instantiated = json.loads(
                (sink / "runs" / "template-run" / "run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                {"receipt_version": 4, "source_commit": commit},
                instantiated["orchflows"],
            )

    def test_each_required_part_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            for flag in ("--executor", "--objective", "--criterion"):
                with self.subTest(flag):
                    args = [a for a in new_args()]
                    index = args.index(flag)
                    del args[index:index + 2]
                    payload = run_cmd(*args)
                    self.assertIn("error", payload)
                    self.assertIn(flag, payload["error"])

    def test_an_off_enum_independence_or_isolation_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            for flag, value in (("--independence", "solo"), ("--isolation", "maybe")):
                with self.subTest(flag):
                    payload = run_cmd(*new_args(flag, value))
                    self.assertIn("error", payload)
                    self.assertIn(value, payload["error"])

    def test_a_run_or_id_that_is_not_one_path_segment_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            for run, ticket_id in (("../escape", "T1"), ("testrun", "a/b")):
                with self.subTest(ticket_id):
                    payload = run_cmd(
                        "new", run, ticket_id, "--executor", "orch-verify",
                        "--objective", "o", "--criterion", GOOD_CRITERION,
                    )
                    self.assertIn("error", payload)

    def test_a_written_ticket_is_placed_by_file_after_the_same_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "testrun", "--file", str(source))
            self.assertNotIn("error", payload)
            self.assertEqual(
                GOOD_TICKET, self.ticket_path(sink).read_text(encoding="utf-8")
            )

    def test_a_defective_file_is_refused_and_placed_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(
                GOOD_TICKET.replace(" | oracle_class: deterministic", ""),
                encoding="utf-8",
            )
            payload = run_cmd("new", "testrun", "--file", str(source))
            self.assertIn("error", payload)
            self.assertIn("oracle_class", payload["error"])
            self.assertFalse(self.ticket_path(sink).exists())

    def test_a_file_whose_run_disagrees_with_the_argument_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "otherrun", "--file", str(source))
            self.assertIn("error", payload)
            self.assertIn("testrun", payload["error"])
            self.assertFalse((sink / "tickets" / "otherrun" / "T1.md").exists())

    def test_the_id_may_be_stated_beside_the_file_when_the_two_agree(self):
        """`new <run> <id> --file <path>` is what a cutter reaches for.

        The id is in the file and in the dispatch that told the cutter to
        write it, and stating it twice is the ordinary spelling; refusing that
        line sent a cutter looking for a subcommand that does not exist.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "testrun", "T1", "--file", str(source))
            self.assertNotIn("error", payload)
            self.assertEqual("T1", payload["new"]["id"])
            self.assertEqual(
                GOOD_TICKET, self.ticket_path(sink).read_text(encoding="utf-8")
            )

    def test_an_id_disagreeing_with_the_file_is_refused_and_placed_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "testrun", "T9", "--file", str(source))
            self.assertIn("error", payload)
            self.assertIn("T9", payload["error"])
            self.assertIn("T1", payload["error"])
            self.assertFalse(self.ticket_path(sink).exists())

    def test_the_exit_codes_are_the_script_s_own(self):
        """The process boundary: a payload carrying `error` exits 1, the cut
        exits 0, and both print one JSON document."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            good = run_full(tmp, *new_args())
            self.assertEqual(0, good.returncode, good.stdout)
            self.assertNotIn("error", json.loads(good.stdout))
            bad = run_full(
                tmp, "new", "testrun", "T2", "--executor", "orch-verify",
                "--objective", "o", "--criterion", "x",
            )
            self.assertEqual(1, bad.returncode, bad.stdout)
            self.assertIn("error", json.loads(bad.stdout))


TEMPLATE_MD = """---
name: demo
description: Three stubs, one placeholder and one edgeless, for these tests.
entry: named
placeholders: [target]
---

What the template is for, in prose no instantiation reads.
"""

STUB = """---
id: {tid}
executor: {executor}
depends_on: {deps}
write_scope: [{scope}]
bound: 30m
---

## Objective

{objective}

## Fixed inputs

None.

## Completion test

- {criterion}

## Return fields

status; result.

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


def stub(tid: str, deps: str = "[]", *, executor: str = "orch-tdd",
         scope: str = "scratch/x.txt", criterion: str = GOOD_CRITERION,
         objective: str = "one stub's end state") -> str:
    return STUB.format(
        tid=tid, executor=executor, deps=deps, scope=scope,
        criterion=criterion, objective=objective,
    )


def make_template(root: Path, stubs: dict, template_md: str = TEMPLATE_MD) -> Path:
    """A template directory: `template.md` plus one file per stub."""

    directory = root / "compositions" / "demo"
    directory.mkdir(parents=True, exist_ok=True)
    if template_md is not None:
        (directory / "template.md").write_text(template_md, encoding="utf-8")
    for tid, text in stubs.items():
        (directory / f"{tid}.md").write_text(text, encoding="utf-8")
    return directory


def three_stubs() -> dict:
    """A → B → C, with A → C as well: one edgeless stub, one terminal, and
    one placeholder to fill."""

    return {
        "A": stub("A", scope="{{target}}"),
        "B": stub("B", "[A]"),
        "C": stub("C", "[A, B]"),
    }


class InstantiateTest(unittest.TestCase):
    """`instantiate` turns one template into one run's tickets: substituted,
    graded, ordered, and written all or not at all."""

    def instantiate(self, directory: Path, *extra):
        return run_cmd("instantiate", str(directory), "--run", "testrun", *extra)

    def run_dir(self, sink: Path) -> Path:
        return sink / "tickets" / "testrun"

    def test_every_stub_lands_with_its_status_and_the_ids_are_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertNotIn("error", payload)
            self.assertEqual(["A", "B", "C"], payload["instantiate"]["ids"])
            listed = {item["id"]: item["status"] for item in run_cmd("list", "--run", "testrun")["tickets"]}
            self.assertEqual({"A": "ready", "B": "pending", "C": "pending"}, listed)

    def test_the_edgeless_stub_is_the_only_one_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.instantiate(directory, "--set", "target=scripts/a.py")
            ready = run_cmd("ready", "--run", "testrun")["ready"]
            self.assertEqual(["A"], [item["id"] for item in ready])

    def test_the_placeholder_is_substituted_and_the_run_stamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.instantiate(directory, "--set", "target=scripts/a.py")
            text = (self.run_dir(sink) / "A.md").read_text(encoding="utf-8")
            self.assertNotIn("{{", text)
            data = tickets_mod._parse_frontmatter(text)
            self.assertEqual(["scripts/a.py"], data["write_scope"])
            self.assertEqual("testrun", data["run"])
            self.assertEqual("ready", data["status"])
            self.assertEqual([], tickets_mod.ticket_defects(text))

    def test_an_instantiated_ticket_is_claimable_and_dispatchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.instantiate(directory, "--set", "target=scripts/a.py")
            packet = run_cmd("packet", "testrun", "A", "--reply-to", "main")
            self.assertNotIn("error", packet)
            claimed = run_cmd("claim", "testrun", "A", "--by", "agent-a")
            self.assertEqual("agent-a", claimed["claimed"]["claimed_by"])

    def test_a_declared_placeholder_no_set_supplies_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory)
            self.assertIn("error", payload)
            self.assertIn("target", payload["error"])
            self.assertFalse(self.run_dir(sink).exists(), "a refused template wrote")

    def test_an_unfilled_placeholder_is_refused_naming_it_and_its_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["B"] = stub("B", "[A]", objective="fix {{undeclared}}")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("undeclared", payload["error"])
            self.assertIn("B", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_a_cyclic_template_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["A"] = stub("A", "[C]", scope="{{target}}")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("cyclic", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_two_terminal_stubs_are_refused_by_name(self):
        """Exactly one stub is terminal: its completion test is the
        template's done check, and two of them is two done checks."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["C"] = stub("C", "[A]")  # B is now terminal too
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("B", payload["error"])
            self.assertIn("C", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_a_stub_whose_criterion_names_no_class_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["C"] = stub("C", "[A, B]", criterion="it looks right | oracle: a glance")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("oracle_class", payload["error"])
            self.assertIn("C", payload["error"])
            self.assertFalse(self.run_dir(sink).exists(), "one bad stub let two land")

    def test_a_dependency_that_is_not_a_stub_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["B"] = stub("B", "[A, elsewhere]")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("elsewhere", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_an_id_already_issued_in_the_run_is_refused_and_nothing_lands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(sink, "testrun", "B", GOOD_TICKET.replace("id: T1", "id: B"))
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("B", payload["error"])
            self.assertEqual(["B.md"], sorted(p.name for p in self.run_dir(sink).iterdir()))

    def test_a_directory_with_no_template_md_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs(), template_md=None)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("template.md", payload["error"])

    def test_a_missing_template_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            payload = self.instantiate(tmp / "compositions" / "absent")
            self.assertIn("error", payload)

    def test_a_template_with_no_stub_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, {})
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("stub", payload["error"])

    def test_a_set_without_a_value_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory, "--set", "target")
            self.assertIn("error", payload)
            self.assertIn("target", payload["error"])

    def test_a_stub_whose_id_is_not_its_file_stem_is_refused(self):
        """`depends_on` names stub ids and the run names files by stem; two
        answers to which stub this is would resolve an edge to neither."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            stubs = three_stubs()
            stubs["C"] = stub("D", "[A, B]")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("D", payload["error"])

    def test_the_run_argument_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = run_cmd("instantiate", str(directory), "--set", "target=x")
            self.assertIn("error", payload)
            self.assertIn("--run", payload["error"])


SYNTH_PACK = """---
name: orch-synth-pack
description: a synthetic pack
---

| cell | binding |
| --- | --- |
| executor | `orch-tdd` |
| required_spec_fields | target repository; standards owner by pointer; \
acceptance as runnable checks — the commands that decide it |
"""


def make_pack(root: Path, name: str = "orch-synth-pack", text: str = SYNTH_PACK) -> Path:
    """A stamped pack beside the template, as the library tree lays them out."""

    path = root / "packs" / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(text, encoding="utf-8")
    return path


def root_stub(fixed_inputs: str, pack: str = "orch-synth-pack") -> str:
    """A root stub: the decomposer, a stamped pack, and one Fixed inputs."""

    return stub("A", executor="orch-decompose", scope="scratch/x.txt").replace(
        "executor: orch-decompose", f"executor: orch-decompose\npack: {pack}"
    ).replace("## Fixed inputs\n\nNone.", f"## Fixed inputs\n\n{fixed_inputs}")


class RootStubSpecFieldsTest(unittest.TestCase):
    """contracts/work-item.md: the stamped pack's `required_spec_fields` are
    entries of the root ticket's `## Fixed inputs`, and orch-decompose's
    Require rejects a root that lacks them.

    That refusal fires inside the decomposer — after dispatch, in a child's
    context, against a ticket already written. `packet` grades shape and
    passes these through, so a template could ship a root stub its own
    executor cannot run and nothing said so until an agent was spending on
    it. The check belongs where the stub is admitted."""

    def defects(self, directory: Path):
        return [message for _, message in tickets_mod.template_defects(directory)]

    def test_a_root_stub_naming_none_of_the_required_fields_is_a_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            directory = make_template(tmp, {
                "A": root_stub("- a directory of items to cut\n"),
                "B": stub("B", "[A]"),
            })
            defects = self.defects(directory)
            self.assertEqual(1, len(defects), defects)
            for field in ("target repository", "standards owner by pointer",
                          "acceptance as runnable checks"):
                self.assertIn(field, defects[0])
            self.assertIn("orch-synth-pack", defects[0])

    def test_a_root_stub_naming_a_required_field_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            directory = make_template(tmp, {
                "A": root_stub("- the target repository: scripts/\n"),
                "B": stub("B", "[A]"),
            })
            self.assertEqual([], self.defects(directory))

    def test_a_non_root_stub_is_not_asked_for_the_fields(self):
        """`pack` is optional on a unit stub and binds its workspace cell,
        not a cut. Only the ticket a decomposition is cut from carries the
        spec's fields."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            unit = stub("A", scope="scratch/x.txt").replace(
                "executor: orch-tdd", "executor: orch-tdd\npack: orch-synth-pack"
            )
            directory = make_template(tmp, {"A": unit, "B": stub("B", "[A]")})
            self.assertEqual([], self.defects(directory))

    def test_a_placeholder_pack_is_graded_once_instantiation_fills_it(self):
        """A stub whose pack is `{{pack}}` names no pack to read until a
        caller supplies one — and then it does, so instantiate applies the
        same check the tree's own grading applies."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            directory = make_template(tmp, {
                "A": root_stub("- a directory of items to cut\n", pack="{{pack}}"),
                "B": stub("B", "[A]"),
            })
            self.assertEqual([], self.defects(directory))

            payload = run_cmd(
                "instantiate", str(directory), "--run", "testrun",
                "--set", "pack=orch-synth-pack", "--set", "target=scripts/a.py",
            )
            self.assertIn("error", payload)
            self.assertIn("target repository", payload["error"])

    def test_a_tree_with_no_packs_directory_grades_nothing(self):
        """An installed copy of this script runs against a target repository
        that carries no `packs/` at all. No pack to read is not a defect in
        the stub."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, {
                "A": root_stub("- a directory of items to cut\n"),
                "B": stub("B", "[A]"),
            })
            self.assertEqual([], self.defects(directory))


class NonUtf8BytesTest(unittest.TestCase):
    """Bytes that are not UTF-8 are the one shape of unreadable file that
    crashed instead of reporting: `UnicodeDecodeError` is a `ValueError`, so
    every `except OSError` around a read let it through as a traceback on a
    channel whose whole contract is one JSON document. A ticket arrives from
    a hand edit, a copy off another host, a template checked out with a
    different encoding — none of which is exotic enough to earn a stack
    trace."""

    def corrupt(self, path: Path) -> Path:
        # a lone 0xFF: valid latin-1, invalid UTF-8 at the first byte, so no
        # decoder guesses its way past it
        path.write_bytes(b"\xff" + path.read_bytes())
        return path

    def test_an_unreadable_ticket_is_a_named_error_from_list_and_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            self.corrupt(place(sink, "testrun", "T1", GOOD_TICKET))

            listed = run_cmd("list", "--run", "testrun")["tickets"]
            self.assertEqual(1, len(listed), listed)
            self.assertIn("unreadable ticket", listed[0]["error"])

            done = run_full(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable ticket", json.loads(done.stdout)["error"])

    def test_an_unreadable_stub_refuses_the_instantiation_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.corrupt(directory / "B.md")

            done = run_full(
                tmp, "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scripts/a.py",
            )
            self.assertEqual(1, done.returncode, done.stdout)
            error = json.loads(done.stdout)["error"]
            self.assertIn("unreadable stub B.md", error)

    def test_an_unreadable_manifest_refuses_the_instantiation_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.corrupt(directory / "template.md")

            done = run_full(
                tmp, "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scripts/a.py",
            )
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable template.md", json.loads(done.stdout)["error"])

    def test_an_unreadable_body_file_refuses_the_amend(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(sink, "testrun", "T1", GOOD_TICKET)
            body = tmp / "body.md"
            body.write_text("a repaired objective\n", encoding="utf-8")
            self.corrupt(body)

            done = run_full(
                tmp, "amend", "testrun", "T1", "--section", "Objective",
                "--file", str(body),
            )
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable body file", json.loads(done.stdout)["error"])

    def test_an_unreadable_source_refuses_the_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            source = tmp / "source.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            self.corrupt(source)

            done = run_full(tmp, "new", "testrun", "T1", "--file", str(source))
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable ticket file", json.loads(done.stdout)["error"])

    def test_an_unreadable_ticket_still_renders_the_run_view(self):
        """`worklog` sections one file per ticket after `_load_ticket` has
        already graded it; the second read had no guard of its own, so the
        whole view died on one bad file."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(sink, "testrun", "T1", GOOD_TICKET)
            self.corrupt(place(sink, "testrun", "T2", GOOD_TICKET.replace("id: T1", "id: T2")))

            done = run_full(tmp, "worklog", "testrun")
            payload = json.loads(done.stdout)
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertNotIn("error", payload)


class RefusalTextTest(unittest.TestCase):
    """A refusal is read where it is printed. Windows consoles decode this
    script's stdout as cp1252, so a non-ASCII character in a refusal reaches
    its reader as mojibake in the one message that has to be understood."""

    def refusals(self) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(
                sink, "testrun", "P1",
                GOOD_TICKET.replace("id: T1", "id: P1").replace(
                    f"- {GOOD_CRITERION}", f"- {GOOD_CRITERION}\n- second | oracle: b"
                ),
            )
            directory = make_template(tmp, three_stubs())
            fat = tmp / "F1.md"
            fat.write_text(
                ceiling_ticket(tickets_mod.INSTRUCTION_BUDGET + 1, ticket_id="F1"),
                encoding="utf-8",
            )
            return [
                run_cmd("new", "testrun", "--file", str(fat)),
                run_cmd("new", "testrun", "T1", "--executor", "orch-verify",
                        "--objective", "o", "--criterion", "x"),
                run_cmd("new", "testrun", "T1", "--executor", "orch-verify",
                        "--objective", "o", "--criterion",
                        "x | oracle: y | oracle_class: mechanical"),
                run_cmd("new", "testrun", "T1", "--objective", "o"),
                run_cmd("new", "testrun", "T1", "--executor", "orch-verify",
                        "--objective", "o", "--criterion", GOOD_CRITERION,
                        "--isolation", "maybe"),
                run_cmd("instantiate", str(directory), "--run", "testrun"),
                run_cmd("instantiate", str(directory), "--run", "testrun",
                        "--set", "target"),
                run_cmd("packet", "testrun", "P1", "--reply-to", "main"),
            ]

    def test_every_refusal_this_path_emits_is_ascii(self):
        for payload in self.refusals():
            message = payload.get("error", "")
            with self.subTest(message[:48]):
                self.assertTrue(message, payload)
                message.encode("ascii")  # raises, and names the character


class InlineListSeparatorTest(unittest.TestCase):
    """An inline frontmatter list `[a, b]` splits on commas and on nothing
    else. A second separator would make one written shape read two ways
    depending on which reader saw it, so an entry that carries a comma —
    prose, which every `excluded_actions` is — takes the block form
    instead, and both shapes read back as one list."""

    def test_the_comma_is_the_only_separator(self):
        parsed = tickets_mod._parse_frontmatter(
            "---\nexcluded_actions: [pushing; forcing, editing]\n---\n"
        )
        self.assertEqual(["pushing; forcing", "editing"], parsed["excluded_actions"])

    def test_an_entry_with_a_comma_is_written_in_the_block_form(self):
        lines = tickets_mod._frontmatter_list(
            "excluded_actions", ["editing rules/, contracts/", "pushing"]
        )
        self.assertEqual(
            ["excluded_actions:", "- editing rules/, contracts/", "- pushing"], lines
        )
        parsed = tickets_mod._parse_frontmatter(
            "---\n" + "\n".join(lines) + "\n---\n"
        )
        self.assertEqual(
            ["editing rules/, contracts/", "pushing"], parsed["excluded_actions"]
        )

    def test_an_entry_with_a_semicolon_takes_the_block_form_too(self):
        """Not because the reader would split it — it would not — but
        because a reader meeting `[a.py; b.py]` cannot tell that from the
        list it looks like, and a scope misread is a scope granted."""

        lines = tickets_mod._frontmatter_list("write_scope", ["a.py; b.py"])
        self.assertEqual(["write_scope:", "- a.py; b.py"], lines)
        parsed = tickets_mod._parse_frontmatter(
            "---\n" + "\n".join(lines) + "\n---\n"
        )
        self.assertEqual(["a.py; b.py"], parsed["write_scope"])

    def test_a_plain_list_stays_inline(self):
        self.assertEqual(
            ["write_scope: [a.py, b.py]"],
            tickets_mod._frontmatter_list("write_scope", ["a.py", "b.py"]),
        )

    def test_the_rule_is_stated_where_the_writer_is(self):
        self.assertIn("block", tickets_mod._frontmatter_list.__doc__ or "")
        self.assertIn("semicolon", tickets_mod._frontmatter_list.__doc__ or "")


class SurfaceTest(unittest.TestCase):
    """The two subcommands are on every surface a reader meets: the module
    docstring, the usage table, and `--help`."""

    def test_the_module_docstring_lists_both(self):
        docstring = tickets_mod.__doc__ or ""
        self.assertIn("new <run> <id>", docstring)
        self.assertIn("instantiate <template-dir>", docstring)

    def test_the_usage_table_and_summary_carry_both(self):
        for name in ("new", "instantiate"):
            with self.subTest(name):
                self.assertIn(name, tickets_mod.SUBCOMMAND_USAGE)
                self.assertIn(name, tickets_mod.SUBCOMMAND_SUMMARY)

    def test_help_answers_for_both_and_names_them_at_the_top_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            top = run_full(tmp, "--help")
            self.assertEqual(0, top.returncode, top.stdout)
            for name in ("new", "instantiate"):
                with self.subTest(name):
                    self.assertIn(name, top.stdout)
                    answer = run_full(tmp, name, "--help")
                    self.assertEqual(0, answer.returncode, answer.stdout)
                    self.assertNotIn("error", json.loads(answer.stdout))


if __name__ == "__main__":
    unittest.main()
