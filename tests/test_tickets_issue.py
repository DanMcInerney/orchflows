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


if __name__ == "__main__":
    unittest.main()
