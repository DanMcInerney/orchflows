"""Wires the super-research skill's offline suite into the required set.

`tools/run_tests.py` discovers only `<repo>/tests`
(`DEFAULT_TESTS_DIR`), and none of `AGENTS.md`'s five otherwise executes a
single adapter or probe: `tests/test_super_research_runner.py` exercises the
harness's own selector logic against a scratch repository, never a real
adapter. This module is the missing row -- it runs the skill's real harness
against this checkout and asserts its exit, so a roster regression (a dropped
adapter, a narrowed smoke probe) fails here, inside the required set, rather
than nowhere. The 3.9 pin comes for free: `tools/run_super_research_tests.py`
re-execs itself under `uv run --python 3.9` whenever the calling interpreter
is not already 3.9, so this module carries no pin of its own.
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tools" / "run_super_research_tests.py"

RAN_PATTERN = re.compile(r"Ran (\d+) tests?")


class SuperResearchSuiteTest(unittest.TestCase):
    """The skill's own offline suite, run once, as this required-set row."""

    def test_the_skill_suite_exits_zero(self):
        completed = subprocess.run(
            [sys.executable, str(RUNNER)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        match = RAN_PATTERN.search(completed.stdout)
        ran = match.group(1) if match else "0"
        self.assertEqual(
            0, completed.returncode,
            "super-research suite exited {0} ({1} tests reported):\n{2}".format(
                completed.returncode, ran, completed.stdout[-4000:],
            ),
        )
        # A pass that ran nothing is not a pass: an empty selector, or a
        # discovery that silently found no module, would exit 0 for the
        # wrong reason and this row would never go red for a real regression.
        self.assertGreater(int(ran), 0, completed.stdout[-2000:])


if __name__ == "__main__":
    unittest.main()
