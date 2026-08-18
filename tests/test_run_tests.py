"""Tests for tools/run_tests.py — the parallel runner the suite runs through.

The runner is also the suite's whole-interpreter residue oracle. Each module
gets a fresh child, but a child still has to reject a module that leaves one
of the process-global seams the suite is known to replace dirty.

The console encoding is a parameter here, not the platform's. A Windows
runner's is cp1252; ``PYTHONIOENCODING`` makes any host's the same, so the
shape stops being something only three cells of the matrix can see.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import run_tests  # noqa: E402

RUN_TESTS_PY = REPO_ROOT / "tools" / "run_tests.py"
CHECKS_YML = REPO_ROOT / ".github" / "workflows" / "checks.yml"
AGENTS_MD = REPO_ROOT / "AGENTS.md"

# In cp1252 and not in ASCII, versus in neither. The first proves the decode
# is faithful, the second that an unencodable character costs a glyph and not
# the report.
ENCODABLE = "é"  # é
UNENCODABLE = "★"  # ★


def run_fixture(source: str):
    """Run one synthetic module through the same child boundary as CI."""

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "test_fixture.py").write_text(source, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [
                sys.executable,
                str(RUN_TESTS_PY),
                "--tests-dir",
                tmp,
                "--no-cache",
                "-j",
                "1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )


class TestGuardedSeams(unittest.TestCase):
    CLEAN = textwrap.dedent(
        '''\
        import unittest


        class Clean(unittest.TestCase):
            def test_it(self):
                self.assertTrue(True)
        '''
    )

    LEAKS = {
        "install.Path.home": "import install\ninstall.Path.home = lambda: None",
        "ui.html.escape": "from scripts import ui\nui.html.escape = lambda value: value",
        "pathlib.Path.open": "from pathlib import Path\nPath.open = lambda *args, **kwargs: None",
        "os.chdir": "import os\nfrom pathlib import Path\nos.chdir(str(Path(__file__).parent))",
        "sys.path": "import sys\nsys.path.append('leaked-by-test')",
    }

    def leaking_module(self, statement: str) -> str:
        return textwrap.dedent(
            '''\
            import unittest


            class Leaking(unittest.TestCase):
                def test_it(self):
            '''
        ) + textwrap.indent(statement + "\n", " " * 8)

    def test_a_clean_module_is_accepted(self):
        completed = run_fixture(self.CLEAN)
        report = completed.stdout.decode("utf-8", "replace")
        self.assertEqual(b"", completed.stderr, completed.stderr)
        self.assertEqual(0, completed.returncode, report)
        self.assertIn("OK", report)

    def test_each_whole_interpreter_leak_is_rejected_and_named(self):
        for seam, statement in self.LEAKS.items():
            with self.subTest(seam=seam):
                completed = run_fixture(self.leaking_module(statement))
                report = completed.stdout.decode("utf-8", "replace")
                self.assertEqual(b"", completed.stderr, completed.stderr)
                self.assertEqual(1, completed.returncode, report)
                self.assertIn("leaked whole-interpreter seam: " + seam, report)


class TestWorkflowContract(unittest.TestCase):
    def test_ci_runs_the_regression_suite_once_through_the_parallel_runner(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        self.assertEqual(1, workflow.count("run: python tools/run_tests.py"))
        self.assertNotIn("run: python -m unittest discover", workflow)

    def test_serial_residue_check_remains_a_documented_local_oracle(self):
        guidance = AGENTS_MD.read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v", guidance)
        self.assertIn("serial local compatibility oracle", guidance)


class Console:
    """A text stdout with a chosen encoding, over a real byte buffer.

    ``io.TextIOWrapper`` with ``errors="strict"`` is what a console is: it
    raises on a character the encoding cannot carry, which is the whole
    behaviour under test.
    """

    def __init__(self, encoding: str):
        self.buffer = io.BytesIO()
        self._text = io.TextIOWrapper(self.buffer, encoding=encoding, errors="strict")
        self.encoding = encoding

    def write(self, text: str) -> int:
        return self._text.write(text)

    def flush(self) -> None:
        self._text.flush()

    def value(self) -> bytes:
        self._text.flush()
        return self.buffer.getvalue()


class TestEmit(unittest.TestCase):
    def emitted(self, encoding: str, text: str) -> bytes:
        console = Console(encoding)
        stdout = sys.stdout
        sys.stdout = console
        try:
            run_tests.emit(text)
        finally:
            sys.stdout = stdout
        return console.value()

    def test_an_unencodable_character_costs_a_glyph_not_the_report(self):
        emitted = self.emitted("cp1252", "before " + UNENCODABLE + " after\n")
        self.assertIn(b"before ", emitted)
        self.assertIn(b"after", emitted)
        self.assertIn(b"\\u2605", emitted)

    def test_everything_the_console_can_carry_is_written_verbatim(self):
        emitted = self.emitted("cp1252", "caf" + ENCODABLE + "\n")
        self.assertEqual("caf" + ENCODABLE + "\n", emitted.decode("cp1252"))

    def test_a_utf8_console_is_untouched(self):
        text = ENCODABLE + UNENCODABLE + "\n"
        self.assertEqual(text, self.emitted("utf-8", text).decode("utf-8"))

    def test_a_stdout_with_no_byte_buffer_still_receives_the_text(self):
        """A captured stdout — ``unittest --buffer``, a doctest — is a
        ``StringIO`` with no ``buffer``. It carries no encoding to fail at,
        so the text goes to it as text."""

        captured = io.StringIO()
        stdout = sys.stdout
        sys.stdout = captured
        try:
            run_tests.emit("plain\n")
        finally:
            sys.stdout = stdout
        self.assertEqual("plain\n", captured.getvalue())


class TestChildEnv(unittest.TestCase):
    def test_the_childs_stdio_is_pinned_to_utf8(self):
        self.assertEqual("utf-8", run_tests.child_env()["PYTHONIOENCODING"])

    def test_every_other_variable_survives(self):
        """The child inherits the sink guard ``tests/__init__.py`` installs
        and whatever else the caller set; a fresh environment would point
        every child at the operator's real state."""

        env = run_tests.child_env()
        for key, value in os.environ.items():
            if key != "PYTHONIOENCODING":
                self.assertEqual(value, env.get(key), key)


class TestFailureOutputSurvivesTheConsole(unittest.TestCase):
    """End to end, on any host: a module fails with a message carrying both
    characters, and the runner reports it to a cp1252 console."""

    MODULE = textwrap.dedent(
        '''\
        import unittest


        class Failing(unittest.TestCase):
            def test_it(self):
                self.fail("caf\\u00e9 \\u2605 star")
        '''
    )

    def test_the_report_names_the_module_and_carries_the_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "test_failing.py").write_text(self.MODULE, encoding="utf-8")
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "cp1252"
            completed = subprocess.run(
                [sys.executable, str(RUN_TESTS_PY), "--tests-dir", tmp],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            report = completed.stdout.decode("cp1252")
            self.assertEqual(b"", completed.stderr, completed.stderr)
            self.assertEqual(1, completed.returncode, report)
            self.assertIn("FAILED MODULE: test_failing", report)
            # the child encoded UTF-8, so the byte pair did not arrive as one
            # replacement character
            self.assertIn("caf" + ENCODABLE, report)
            self.assertIn("\\u2605", report)
            self.assertNotIn("�", report)


if __name__ == "__main__":
    unittest.main()
