"""Shared live-repository and isolated-tree validator fixtures."""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"
PINS = ROOT / "tests" / "pins.json"

# Compiled once: the isolated-tree tests execute this body per run, in a
# namespace whose __file__ points at their own copy.
_VALIDATE_CODE = compile(VALIDATE.read_text(encoding="utf-8"), str(VALIDATE), "exec")


def loop_lint_warnings(stdout):
    """Every WARN validate_loop_lint emitted, by its own words.

    The loop-lint cases below are about one check, and a report carries
    findings from every check that ran -- an isolated tree still holds the
    real contracts/, so the duplication checks read it too. Asserting over
    the whole stream made those cases fail on a finding they are not about,
    and pass on the day the loop lint stops running (tests/test_cell_linter.py
    holds the same line for its ratchets)."""
    return [
        line for line in stdout.splitlines()
        if line.startswith("WARN") and "iteration/loop" in line
    ]


class _Result:
    """The three fields of a CompletedProcess the isolated tests read."""

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _IsolatedTree(unittest.TestCase):
    """A synthetic repo tree -- contracts/, tools/validate.py, the
    committed pins, plus whatever the test writes -- with validate.py run
    against it.

    Two spawns per test bought nothing. The pin spawn is gone because the
    contract bytes here are copied verbatim from the tree pins.json is
    pinned to (TestPinFlagRoundTrip.test_pin_matches_committed_pins_json
    is the proof), so copying the file is the same fixture. The run itself
    is in process because validate.py derives ROOT from its own __file__,
    so executing its body in a namespace rooted at the copy is the run the
    subprocess made. The CLI boundary -- argv, exit status, a real
    interpreter -- stays covered by TestValidatorAgainstRepo and
    TestPinFlagRoundTrip, which still spawn.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")
        shutil.copytree(ROOT / "tools" / "validate_support", self.tmp_path / "tools" / "validate_support")
        (self.tmp_path / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "doclint.py", self.tmp_path / "scripts" / "doclint.py")
        (self.tmp_path / "tests").mkdir()
        shutil.copy(PINS, self.tmp_path / "tests" / "pins.json")

    def _run(self, *args):
        namespace = {
            "__name__": "validate_under_test",
            "__file__": str(self.tmp_path / "tools" / "validate.py"),
        }
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            exec(_VALIDATE_CODE, namespace)  # noqa: S102 -- the file under test
            code = namespace["main"](list(args))
        return _Result(code, out.getvalue(), err.getvalue())
