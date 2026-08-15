"""The canary set's verdict is a fact about the cut, never about this host.

An oracle stating a bare interpreter name no host is required to have cannot
run, and cutcheck reports that in the position a reader scans for a defect of
the ticket set. The name every supported host does have is ``python3``, and it
has to be stated as that bare name: ``COMMAND_HEADS`` carries no absolute path,
so an absolute one is extracted as no command at all and the class goes quiet
by hiding the oracle rather than by making it runnable.
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.cutcheck as cutcheck  # noqa: E402

# Copied from tests/test_cutcheck.py, never imported from it: this module's
# verdict must not depend on that module's state. The two invariants making a
# candidate revision legal are documented at its definition there.
BASELINE = "462ef52aab37655260bdc9f9f98be4ed2601af2d"


def run_cutcheck(run, baseline=BASELINE):
    """Invoke cutcheck exactly as the completion test states it."""

    return subprocess.run(
        [sys.executable, "scripts/cutcheck.py", run, "--baseline", baseline],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


# `_run_dir` resolves a canary set at the main checkout, never at the invoking
# worktree, so this reads the same ticket the report's oracle observed.
CANARY = cutcheck._run_dir("canary", ROOT)
TDD_TICKET = "canary-tdd-micro.md"


@unittest.skipUnless(CANARY is not None, "the canary ticket set is not present")
class CanaryHostVerdictTest(unittest.TestCase):
    """No line of the canary's report is about which interpreters this host has.

    Selected by the class token read from cutcheck rather than by counting
    lines or by asserting an empty report: the canary carries a deliberate
    scope defect and other advisory lines, and both are somebody else's.
    """

    def test_no_oracle_of_the_canary_set_is_unrunnable_here(self):
        result = run_cutcheck("canary")
        lines = [
            line
            for line in result.stdout.splitlines()
            if cutcheck.UNRUNNABLE_ORACLE in line
        ]
        self.assertEqual(lines, [], result.stdout + result.stderr)


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


if __name__ == "__main__":
    unittest.main()
