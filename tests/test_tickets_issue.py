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


if __name__ == "__main__":
    unittest.main()
