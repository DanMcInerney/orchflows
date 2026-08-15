"""The canary set's verdict is a fact about the cut, never about this host.

An oracle stating a bare interpreter name no host is required to have cannot
run, and cutcheck reports that in the position a reader scans for a defect of
the ticket set. The name every supported host does have is ``python3``, and it
has to be stated as that bare name: ``COMMAND_HEADS`` carries no absolute path,
so an absolute one is extracted as no command at all and the class goes quiet
by hiding the oracle rather than by making it runnable.
"""

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.cutcheck as cutcheck  # noqa: E402
from tests.baseline_pin import BASELINE, run_cutcheck  # noqa: E402  its one owner

# `_run_dir` resolves a canary set at the main checkout, never at the invoking
# worktree, so this reads the same ticket the report's oracle observed.
CANARY = cutcheck._run_dir("canary", ROOT)
TDD_TICKET = "canary-tdd-micro.md"

# The two statuses a run that read the set exits with. `NO_TICKET_SET` is the
# third and the one this guard has to tell apart: it says the run resolved
# nothing, so every absence read off it is an absence of reading.
GRADED = (cutcheck.CLEAN, cutcheck.REPORTED)
# The revision no repository resolves. Asking for it is how the wrong result
# is built beside the tree: cutcheck clones into its own scratch root and only
# ever reads the tree under test, so nothing here mutates it.
UNRESOLVABLE = "0" * 40


def unrunnable_lines(stdout):
    """Every report line naming the class this host alone could make appear."""

    return [line for line in stdout.splitlines() if cutcheck.UNRUNNABLE_ORACLE in line]


def graded_lines(stdout):
    """Every report line that is a reading of the ticket set.

    A finding, selected on the family-and-class pair from cutcheck's own
    table, or the sentinel it prints having found nothing outside the advisory
    set. Its summary lines carry no family, class, criterion number or ticket
    id by its own rule, so nothing else in a report is counted -- and a run
    that resolved no baseline prints its reason alone and leaves this empty.
    """

    markers = [
        "{}: {}: ".format(family, klass)
        for klass, family in cutcheck.FAMILY_OF.items()
    ]
    return [
        line
        for line in stdout.splitlines()
        if line == cutcheck.NO_FINDING_OUTSIDE
        or any(marker in line for marker in markers)
    ]


@unittest.skipUnless(CANARY is not None, "the canary ticket set is not present")
class CanaryHostVerdictTest(unittest.TestCase):
    """No line of the canary's report is about which interpreters this host has.

    Selected by the class token read from cutcheck rather than by counting
    lines or by asserting an empty report: the canary carries a deliberate
    scope defect and other advisory lines, and both are somebody else's.

    An absence is a fact about the report only once the report is one. So the
    status and the reading are asserted beside the class: without them a run
    that resolved no baseline -- an unreachable pin, a depth-1 checkout --
    prints one line naming its reason, filters to nothing, and passes.
    """

    @classmethod
    def setUpClass(cls):
        # One invocation, three readings: it costs seconds, and three runs
        # would let the status, the report and the class come from three
        # different reports. The invocation's owner memoises it, so the two
        # readings `tests/test_cutcheck.py` takes of the same argv are this
        # same report and not a fourth and fifth grading of the canary.
        cls.result = run_cutcheck("canary", baseline=BASELINE)

    def test_no_oracle_of_the_canary_set_is_unrunnable_here(self):
        self.assertEqual(
            unrunnable_lines(self.result.stdout),
            [],
            self.result.stdout + self.result.stderr,
        )

    def test_the_guard_asserts_the_return_code(self):
        self.assertIn(
            self.result.returncode,
            GRADED,
            self.result.stdout + self.result.stderr,
        )

    def test_an_empty_report_fails_the_guard(self):
        self.assertTrue(
            graded_lines(self.result.stdout),
            self.result.stdout + self.result.stderr,
        )

    def test_a_run_that_resolved_no_baseline_fails(self):
        """The three readings above, taken against a run that graded nothing.

        The class filter passing here is the defect this node exists to fix in
        place: on its own it calls a run that resolved no baseline clean.
        """

        wrong = run_cutcheck("canary", baseline=UNRESOLVABLE)
        self.assertEqual(unrunnable_lines(wrong.stdout), [], wrong.stdout)
        self.assertNotIn(wrong.returncode, GRADED, wrong.stdout)
        self.assertEqual(graded_lines(wrong.stdout), [], wrong.stdout)


@unittest.skipUnless(CANARY is not None, "the canary ticket set is not present")
class CanaryOracleSpellingTest(unittest.TestCase):
    """The interpreter is named the one way that both runs and extracts."""

    def setUp(self):
        text = (CANARY / TDD_TICKET).read_text(encoding="utf-8")
        section = cutcheck._sections(text)[cutcheck.COMPLETION_SECTION]
        self.commands = cutcheck._commands(dict(cutcheck._criteria(section))[1])

    def test_the_criterion_states_one_command_cutcheck_extracts(self):
        self.assertEqual(len(self.commands), 1, self.commands)

    def test_the_head_is_the_bare_interpreter_name(self):
        self.assertEqual(self.commands[0].split()[0], "python3", self.commands[0])

    def test_no_token_of_the_command_is_an_absolute_path(self):
        absolute = [
            token for token in self.commands[0].split() if token.startswith("/")
        ]
        self.assertEqual(absolute, [], self.commands[0])


PIN_NAME = "BASELINE"
PIN_MODULE = "tests.baseline_pin"
PIN_OWNER = ROOT / "tests" / "baseline_pin.py"
PIN_READERS = (
    ROOT / "tests" / "test_canary_host.py",
    ROOT / "tests" / "test_cutcheck.py",
)


def pin_assignments(tree):
    """Every value assigned to the pin's name in a parsed module."""

    return [
        getattr(node.value, "value", ast.dump(node.value))
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == PIN_NAME
            for target in node.targets
        )
    ]


def pin_imports(tree):
    """Every module the pin's name is imported from in a parsed module."""

    return [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and any(alias.name == PIN_NAME for alias in node.names)
    ]


def literal_copies(tree, value):
    """The line of every string constant in a parsed module equal to ``value``."""

    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value == value
    ]


class BaselinePinOwnerTest(unittest.TestCase):
    """One module owns the pin; the two that use it hold no copy of it.

    Read from source rather than by importing the sibling test module: this
    module's verdict must not depend on that module's state. That objection
    is what the owner being a module with no state of its own answers, and
    reading is how the sibling is graded without being imported.

    The asymmetry is the reason the node exists. A pin that moves in one
    module and not the other leaves the sibling loudly red and this module
    silently green, because a baseline that cannot be cloned resolves nothing
    to report.
    """

    def setUp(self):
        self.owner = ast.parse(PIN_OWNER.read_text(encoding="utf-8"))
        self.readers = {
            path.name: ast.parse(path.read_text(encoding="utf-8"))
            for path in PIN_READERS
        }

    def test_both_modules_read_one_owner_for_the_pin(self):
        owned = pin_assignments(self.owner)
        self.assertEqual(len(owned), 1, owned)
        pin = owned[0]
        for name, tree in sorted(self.readers.items()):
            with self.subTest(module=name):
                self.assertEqual(pin_imports(tree), [PIN_MODULE])
                self.assertEqual(pin_assignments(tree), [])
                self.assertEqual(literal_copies(tree, pin), [])


if __name__ == "__main__":
    unittest.main()
