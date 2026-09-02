"""What a broken installer-case collection has to say for itself.

The tree it guards is governed by two rules that live in two files, and a
class can satisfy either one alone: a mixin is imported and its subclass
runs, a new class is written and nothing imports it. Both were silent
arithmetic before -- ``Element counts were not equal`` and a tuple -- so
what is graded here is the message, not the detection.
"""

from __future__ import annotations
import unittest

# No sys.path guard: this module is reached only through
# ``tests.test_run_tests``, so the repository root is already importable.
from tests.test_installer_cases import _collection

from tests._repo_root import ROOT as REPO_ROOT
CASE = "tests/test_installer_cases/planning/runtime.py"


def declared(*rows):
    return [(CASE, name, method) for name, method in rows]


def loaded(*rows):
    return [
        ("tests.test_installer.{0}.{1}".format(name, method), name, method)
        for name, method in rows
    ]


class TestCollectionLaw(unittest.TestCase):
    """Every breach names both rules, the offender, and a fix."""

    def names_both_rules(self, message):
        self.assertIn("Rule 1", message)
        self.assertIn("Rule 2", message)
        # Rule 1 is the import-and-rebind mechanism, not just its name.
        self.assertIn("tests/test_installer", message)
        self.assertIn("__module__", message)
        # Rule 2 is the exactly-once accounting, by declaring class name.
        self.assertIn("exactly once", message)
        self.assertIn("fix:", message)

    def test_a_consistent_tree_reports_nothing(self):
        rows = (("TestGrokDoc", "test_grok_home"),)
        self.assertEqual("", _collection.report(declared(*rows), loaded(*rows)))

    def test_an_unimported_class_is_named_with_its_file_and_both_rules(self):
        message = _collection.report(
            declared(("TestGrokDoc", "test_grok_home")), loaded()
        )
        self.names_both_rules(message)
        self.assertIn(CASE, message)
        self.assertIn("TestGrokDoc.test_grok_home", message)
        # Green-looking silence is the damage; say so, not just "mismatch".
        self.assertIn("do not run", message)

    def test_a_mixin_is_reported_from_both_sides_with_the_prefix_fix(self):
        """The one shape that satisfies rule 1 and breaks rule 2.

        The methods are written on a base the shard never imports and run
        under the subclass it does, so the same method is missing under one
        name and stray under the other. Naming only one side sends the
        reader to rewire an import that is already correct.
        """

        message = _collection.report(
            declared(("SharedGrokChecks", "test_grok_home")),
            loaded(("TestGrokDoc", "test_grok_home")),
        )
        self.names_both_rules(message)
        self.assertIn("SharedGrokChecks.test_grok_home", message)
        self.assertIn("TestGrokDoc.test_grok_home", message)
        # The fix for a base class is a rename, never another import.
        self.assertIn("_check", message)

    def test_a_class_two_shards_reach_is_named_once_with_its_count(self):
        """And is not also accused of being undeclared.

        The second load is one more row against one declaration, so a
        row-count subtraction calls the surplus row an undeclared method
        too -- two diagnoses for one mistake, one of them false, and the
        false one sends the reader to edit a class that is already right.
        """

        rows = (("TestGrokDoc", "test_grok_home"),)
        message = _collection.report(declared(*rows), loaded(*rows) + loaded(*rows))
        self.names_both_rules(message)
        self.assertIn("tests.test_installer.TestGrokDoc.test_grok_home", message)
        self.assertIn("twice", message)
        self.assertNotIn("NEVER DECLARED", message)

    def test_the_law_the_message_states_is_the_law_the_tree_lives_under(self):
        """The quoted mechanism has to still exist in the shard it quotes.

        A message that names a rebinding no shard performs any more would
        send the next contributor to write dead code with full confidence.
        """

        shard = (REPO_ROOT / "tests" / "test_installer_runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("__module__ = _facade.__name__", shard)
        self.assertIn("__module__ = _facade.__name__", _collection.LAW)
