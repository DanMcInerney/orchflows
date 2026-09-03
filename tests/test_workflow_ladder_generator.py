"""The workflow-ladder ticket generator's one oracle: the `--scope` spelling.

Every child of the workflow-ladder run met the same wedge: the spec's
`**Done.**` lines spelled `--scope a b c`, which `tools/run_tests.py`
refuses outright (`run_tests_scope.refuse_positional`). The spec is the
owner and the ticket files are its projection, so a wrong spelling there
is copied verbatim into fourteen tickets and rediscovered fourteen times.
The projection refuses it at the source instead.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from tests._repo_root import ROOT as REPO_ROOT

TICKETS = REPO_ROOT / "research" / "workflow-ladder-tickets"
GENERATOR = TICKETS / "generate.py"

SPEC_FIXTURE = """# Fixture spec

### U0 · One unit

**Goal.** A goal.

**Details.** Some details.

**Done.** `python tools/run_tests.py --scope %s`
"""


def load_generator():
    """Import `generate.py` by path -- it is a script, not a package member."""

    spec = importlib.util.spec_from_file_location("workflow_ladder_generate", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestScopeSpellingRefusal(unittest.TestCase):
    """`--scope a b c` binds `a` and demotes `b c` to MODULE arguments."""

    def setUp(self):
        self.generate = load_generator()

    def run_against(self, scope: str):
        """Run the generator over a one-unit spec spelling `--scope` that way.

        Returns its exit code and the ticket files it wrote, both taken from
        a throwaway directory so the shipped projection is never touched.
        """

        with tempfile.TemporaryDirectory() as raw:
            where = Path(raw)
            spec = where / "spec.md"
            spec.write_text(SPEC_FIXTURE % scope, encoding="utf-8")
            self.generate.SPEC = spec
            self.generate.HERE = where
            code = self.generate.main()
            return code, sorted(one.name for one in where.iterdir())

    def test_a_space_separated_scope_is_refused_before_any_ticket_is_written(self):
        code, written = self.run_against("docs rules tests tools")
        self.assertEqual(1, code)
        self.assertEqual(["spec.md"], written)

    def test_the_comma_spelling_generates_the_unit(self):
        code, written = self.run_against("docs,rules,tests,tools")
        self.assertEqual(0, code)
        self.assertEqual(["U0.details.md", "U0.goal.md", "spec.md"], written)

    def test_the_refusal_names_the_unit_and_the_spelling_to_use(self):
        dropped = self.generate.split_scope("`--scope docs rules tests tools`")
        self.assertEqual(["docs", "rules", "tests", "tools"], dropped)

    def test_prose_after_the_command_is_not_read_as_a_second_scope_token(self):
        self.assertIsNone(self.generate.split_scope(
            "`python tools/run_tests.py --scope skills,tests`, plus one scratch "
            "run with two trivial candidates whose frame closes `complete`."))


class TestShippedSpec(unittest.TestCase):
    """The owner and its projection both carry the spelling run_tests accepts."""

    def setUp(self):
        self.generate = load_generator()

    def test_every_spec_done_line_spells_scope_with_commas(self):
        spec = self.generate.SPEC.read_text(encoding="utf-8")
        done_lines = [line for line in spec.splitlines()
                      if line.startswith("**Done.**")]
        self.assertTrue(done_lines, "the spec carries no **Done.** line")
        for line in done_lines:
            self.assertIsNone(self.generate.split_scope(line), line)

    def test_every_generated_details_file_carries_its_spec_done_line(self):
        spec = self.generate.SPEC.read_text(encoding="utf-8")
        pieces = self.generate.UNIT_HEADING.split(spec)
        checked = 0
        for index in range(1, len(pieces), 2):
            uid, body = pieces[index], pieces[index + 1]
            done = self.generate.paragraphs(
                body.partition("\n")[2].split("\n## 4. Order")[0])["Done"]
            details = (TICKETS / f"{uid}.details.md").read_text(encoding="utf-8")
            line = next(one for one in details.splitlines()
                        if one.startswith("Done: "))
            self.assertEqual("Done: " + done, line, uid)
            checked += 1
        self.assertEqual(15, checked)
