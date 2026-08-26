"""Process-runner tests for residue, scheduling, telemetry, and console seams."""

from __future__ import annotations
import ast
import importlib
import io
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import run_tests  # noqa: E402
from tests.test_run_tests_cases.workflow_contract import (  # noqa: E402,F401
    TestWorkflowContract,
)
RUN_TESTS_PY = REPO_ROOT / "tools" / "run_tests.py"
CHECKS_YML = REPO_ROOT / ".github" / "workflows" / "checks.yml"
AGENTS_MD = REPO_ROOT / "AGENTS.md"

# One glyph fits cp1252 and one does not, testing faithful decode and fallback.
ENCODABLE = "é"  # é
UNENCODABLE = "★"  # ★

def run_fixture(source: str):
    """Run one synthetic module through the same child boundary as CI."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "test_fixture.py").write_text(source, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT)
        return subprocess.run(
            [sys.executable, str(RUN_TESTS_PY), "--tests-dir", tmp, "--no-cache", "-j", "1"],
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
        "sys.path": (
            "import sys\nfrom pathlib import Path\n"
            "sys.path.append(str(Path(__file__).parent))"
        ),
    }

    def leaking_module(self, statement: str) -> str:
        return textwrap.dedent(
            '''\
            import unittest

            class Leaking(unittest.TestCase):
                def test_it(self):
            '''
        ) + textwrap.indent(statement + "\n", " " * 8)

    def import_leaking_module(self, statement: str) -> str:
        return statement + "\n\n" + self.CLEAN

    def test_a_clean_module_is_accepted(self):
        completed = run_fixture(self.CLEAN)
        report = completed.stdout.decode("utf-8", "replace")
        self.assertEqual(b"", completed.stderr, completed.stderr)
        self.assertEqual(0, completed.returncode, report)
        self.assertIn("OK", report)

    def test_an_expired_scratch_import_path_is_not_live_residue(self):
        source = self.leaking_module(
            "import sys\nimport tempfile\n"
            "with tempfile.TemporaryDirectory() as tmp:\n"
            "    sys.path.append(tmp)"
        )
        completed = run_fixture(source)
        report = completed.stdout.decode("utf-8", "replace")
        self.assertEqual(b"", completed.stderr, completed.stderr)
        self.assertEqual(0, completed.returncode, report)
        self.assertIn("OK", report)

    def test_an_expired_scratch_path_matches_a_resolved_temp_alias(self):
        alias_root = os.path.join(tempfile.gettempdir(), "temp-alias")
        resolved_root = os.path.join(tempfile.gettempdir(), "temp-target")
        expired = os.path.join(resolved_root, "expired")

        def resolve_alias(path):
            if os.path.normcase(os.path.abspath(path)) == os.path.normcase(
                os.path.abspath(alias_root)
            ):
                return resolved_root
            return path

        with (
            mock.patch.object(run_tests.tempfile, "gettempdir", return_value=alias_root),
            mock.patch.object(run_tests.os.path, "realpath", side_effect=resolve_alias),
            mock.patch.object(run_tests.os.path, "exists", return_value=False),
        ):
            self.assertEqual((), run_tests.meaningful_sys_path((expired,)))

    def test_a_dead_path_inside_the_checkout_is_residue_wherever_it_sits(self):
        """A checkout under the system temp root is still a checkout, so its
        own dead import paths are residue exactly as they are anywhere else.
        The verification law sends detached worktrees there; a runner that
        read the location would emit a different verdict for the same tree."""

        scratch = os.path.normcase(os.path.realpath(tempfile.gettempdir()))
        verdicts = []
        for checkout in (str(REPO_ROOT), os.path.join(scratch, "detached-worktree")):
            dead = os.path.join(checkout, "expired_import_path")
            with mock.patch.object(run_tests, "ROOT", Path(checkout)), \
                    mock.patch.object(run_tests.os.path, "exists", return_value=False):
                verdicts.append(run_tests.meaningful_sys_path((dead,)) == (dead,))
        self.assertEqual([True, True], verdicts)

    def test_a_dead_scratch_path_outside_the_checkout_is_still_dropped(self):
        scratch = os.path.normcase(os.path.realpath(tempfile.gettempdir()))
        dead = os.path.join(scratch, "expired-scratch-root")
        with mock.patch.object(run_tests.os.path, "exists", return_value=False):
            self.assertEqual((), run_tests.meaningful_sys_path((dead,)))

    def test_each_whole_interpreter_leak_is_rejected_and_named(self):
        for seam, statement in self.LEAKS.items():
            with self.subTest(seam=seam):
                completed = run_fixture(self.leaking_module(statement))
                report = completed.stdout.decode("utf-8", "replace")
                self.assertEqual(b"", completed.stderr, completed.stderr)
                self.assertEqual(1, completed.returncode, report)
                self.assertIn("leaked whole-interpreter seam: " + seam, report)

    def test_each_import_time_whole_interpreter_leak_is_rejected_and_named(self):
        for seam, statement in self.LEAKS.items():
            with self.subTest(seam=seam):
                completed = run_fixture(self.import_leaking_module(statement))
                report = completed.stdout.decode("utf-8", "replace")
                self.assertEqual(b"", completed.stderr, completed.stderr)
                self.assertEqual(1, completed.returncode, report)
                self.assertIn("leaked whole-interpreter seam: " + seam, report)

    def test_an_arbitrary_live_import_path_is_still_rejected(self):
        statement = textwrap.dedent(
            '''\
            import sys
            from pathlib import Path

            leaked = Path(__file__).with_name("live_import_path")
            leaked.mkdir()
            sys.path.append(str(leaked))
            '''
        )
        completed = run_fixture(self.import_leaking_module(statement))
        report = completed.stdout.decode("utf-8", "replace")
        self.assertEqual(b"", completed.stderr, completed.stderr)
        self.assertEqual(1, completed.returncode, report)
        self.assertIn("leaked whole-interpreter seam: sys.path", report)

    def test_an_expired_non_scratch_import_path_is_still_rejected(self):
        statement = textwrap.dedent(
            '''\
            import os
            import sys
            from pathlib import Path

            expired = Path(os.environ["PYTHONPATH"]) / "expired_import_path"
            sys.path.append(str(expired))
            '''
        )
        completed = run_fixture(self.import_leaking_module(statement))
        report = completed.stdout.decode("utf-8", "replace")
        self.assertEqual(b"", completed.stderr, completed.stderr)
        self.assertEqual(1, completed.returncode, report)
        self.assertIn("leaked whole-interpreter seam: sys.path", report)

    def test_a_nonzero_child_exit_rejects_an_ok_payload(self):
        source = textwrap.dedent(
            '''\
            import atexit
            import os
            import unittest

            atexit.register(lambda: os._exit(7))

            class Clean(unittest.TestCase):
                def test_it(self):
                    self.assertTrue(True)
            '''
        )
        completed = run_fixture(source)
        report = completed.stdout.decode("utf-8", "replace")
        self.assertEqual(b"", completed.stderr, completed.stderr)
        self.assertEqual(1, completed.returncode, report)
        self.assertIn("FAILED MODULE: test_fixture (exit 7)", report)


class TestSchedule(unittest.TestCase):
    def test_installer_cases_are_exactly_once_across_process_visible_shards(self):
        modules = [
            name for name in run_tests.discover(run_tests.DEFAULT_TESTS_DIR)[2]
            if name.startswith("tests.test_installer")
        ]
        expected = [
            (node.name, method.name)
            for path in (REPO_ROOT / "tests").rglob("*.py")
            for node in ast.parse(path.read_text(encoding="utf-8")).body
            for method in getattr(node, "body", ())
            if (path.name == "test_installer.py" or "test_installer_cases" in path.parts)
            and isinstance(node, ast.ClassDef) and isinstance(method, ast.FunctionDef)
            and method.name.startswith("test")
        ]
        self.assertGreaterEqual(len(modules), 3)
        for name in modules:
            if name != "tests.test_installer":
                source = REPO_ROOT.joinpath(*name.split(".")).with_suffix(".py")
                self.assertIn('sys.modules.get("test_installer")', source.read_text())
        stack = list(unittest.TestLoader().loadTestsFromNames(modules))
        identities = []
        cases = []
        while stack:
            item = stack.pop()
            if isinstance(item, unittest.TestSuite):
                stack.extend(item)
            else:
                identities.append(item.id())
                cases.append((type(item).__name__, item._testMethodName))
        self.assertCountEqual(expected, cases)
        self.assertEqual(len(identities), len(set(identities)))
        self.assertTrue(identities)
        prefixes = ("tests.test_installer.", "test_installer.")
        self.assertTrue(all(name.startswith(prefixes) for name in identities))
    def test_timing_record_carries_context_occupancy_modules_and_outcomes(self):
        records = [{"module": "tests.test_one", "tests": 3, "failures": 1,
                    "errors": 0, "skipped": 1, "expected_failures": 1,
                    "unexpected": 0, "ok": False,
                    "duration": 4.0, "started": 10.0, "finished": 14.0}]
        timing = run_tests.timing_record(records, 5.0, 8, 1, 10.0)
        self.assertEqual(8, timing["requested_workers"])
        self.assertEqual(1, timing["effective_workers"])
        self.assertEqual(0.8, timing["occupancy"]["capacity_ratio"])
        self.assertEqual(3, timing["outcomes"]["tests"])
        self.assertEqual(1, timing["outcomes"]["expected_failures"])
        self.assertEqual("tests.test_one", timing["modules"][0]["module"])
        self.assertIn("revision", timing)
        self.assertIn("platform", timing)
        self.assertIn("interpreter", timing)
    def test_expected_failures_are_preserved_as_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath("test_expected.py").write_text(
                "import unittest\nclass Expected(unittest.TestCase):\n"
                " @unittest.expectedFailure\n def test_expected(self): assert False\n", encoding="utf-8")
            record = run_tests.run_module("test_expected", root, 1)
        self.assertEqual(1, record["expected_failures"])
        self.assertTrue(record["ok"])
    def test_a_cold_repository_starts_known_slow_modules_first(self):
        modules = [
            "tests.test_alpha",
            "tests.test_cutcheck",
            "tests.test_installer_planning",
            "tests.test_installer_shared",
            "tests.test_tickets",
        ]
        self.assertEqual(
            ["tests.test_installer_planning", "tests.test_installer_shared",
             "tests.test_cutcheck", "tests.test_tickets", "tests.test_alpha"],
            run_tests.schedule(modules, {}, run_tests.DEFAULT_TESTS_DIR),
        )

    def test_a_cold_prior_covers_the_long_pole_of_every_matrix_leg(self):
        """The prior was read off Linux, where these two are cheap. Each was
        its own leg's longest module, sorted last, and ran alone to the end:
        141s of macOS's 284s wall, 120s of py3.9's 207s."""
        modules = ["tests.test_alpha", "tests.test_serial_compat",
                   "tests.test_visualize_scripts", "tests.test_zeta"]
        self.assertEqual(
            ["tests.test_visualize_scripts", "tests.test_serial_compat"],
            run_tests.schedule(modules, {}, run_tests.DEFAULT_TESTS_DIR)[:2],
        )

    def test_a_cold_custom_directory_remains_alphabetical(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                ["tests.test_alpha", "tests.test_cutcheck", "tests.test_tickets"],
                run_tests.schedule(
                    ["tests.test_cutcheck", "tests.test_alpha", "tests.test_tickets"],
                    {}, Path(tmp),
                ),
            )


class Console:
    """A strict text stdout with a chosen encoding over a byte buffer."""

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
        """The child inherits the sink guard and every caller variable."""
        env = run_tests.child_env()
        for key, value in os.environ.items():
            if key != "PYTHONIOENCODING":
                self.assertEqual(value, env.get(key), key)


class TestFailureOutputSurvivesTheConsole(unittest.TestCase):
    """A failing module's non-ASCII message survives a cp1252 console."""

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
