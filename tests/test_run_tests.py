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


class TestWorkflowContract(unittest.TestCase):
    def test_star_imported_facades_do_not_export_test_cases(self):
        facade_pattern = re.compile(
            r"^from (tests\.test_[^. ]+) import \*", re.MULTILINE
        )
        facades = {
            match.group(1)
            for path in (REPO_ROOT / "tests").rglob("*.py")
            for match in facade_pattern.finditer(path.read_text(encoding="utf-8"))
        }
        offenders = []
        for module_name in sorted(facades):
            module = importlib.import_module(module_name)
            exported = getattr(
                module,
                "__all__",
                tuple(name for name in vars(module) if not name.startswith("_")),
            )
            offenders.extend(
                "{}.{}".format(module_name, name)
                for name in exported
                if isinstance(getattr(module, name), type)
                and issubclass(getattr(module, name), unittest.TestCase)
            )
        self.assertEqual([], offenders)

    def test_ci_has_exactly_the_five_supported_boundary_legs(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        matrix = workflow.split("      matrix:\n", 1)[1].split("\n    steps:", 1)[0]
        os_axis = re.search(r"^        os: \[([^]]+)\]$", matrix, re.MULTILINE)
        python_axis = re.search(
            r"^        python-version: \[([^]]+)\]$", matrix, re.MULTILINE
        )
        self.assertIsNotNone(os_axis)
        self.assertIsNotNone(python_axis)
        self.assertNotRegex(matrix, re.compile(r"^        include:", re.MULTILINE))
        self.assertEqual(
            {"os", "python-version", "exclude"},
            set(re.findall(r"^        ([a-z][a-z0-9-]*):", matrix, re.MULTILINE)),
        )
        self.assertEqual(
            1,
            len(re.findall(
                r"^    runs-on: \$\{\{ matrix\.os \}\}$", workflow, re.MULTILINE
            )),
        )
        self.assertEqual(
            1,
            len(re.findall(
                r"^          python-version: \$\{\{ matrix\.python-version \}\}$",
                workflow,
                re.MULTILINE,
            )),
        )

        def values(match):
            return [value.strip(" '\"") for value in match.group(1).split(",")]

        excluded = set(re.findall(
            r"- os: ([a-z-]+)\s+python-version: ['\"]([0-9.]+)['\"]",
            matrix,
        ))
        legs = [
            (os_name, python_version)
            for os_name in values(os_axis)
            for python_version in values(python_axis)
            if (os_name, python_version) not in excluded
        ]
        self.assertEqual(
            [
                ("ubuntu-latest", "3.9"),
                ("ubuntu-latest", "3.11"),
                ("ubuntu-latest", "3.13"),
                ("macos-latest", "3.13"),
                ("windows-latest", "3.13"),
            ],
            legs,
        )

    def test_ci_runs_the_regression_suite_once_through_the_parallel_runner(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        self.assertEqual(1, workflow.count("run: python tools/run_tests.py"))
        self.assertNotIn("run: python -m unittest discover", workflow)

    def test_ci_uploads_each_python_legs_timing_even_after_failure(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        self.assertIn("--timing-file .orch/run-tests.json", workflow)
        self.assertIn("uses: actions/upload-artifact@v4", workflow)
        self.assertIn("if: ${{ always() }}", workflow)
        self.assertIn("path: .orch/run-tests.json", workflow)
        self.assertIn("include-hidden-files: true", workflow)

    def test_ci_does_not_repeat_oracles_already_in_the_sharded_suite(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        # TestValidatorAgainstRepo and DryRunOracleTest cover these commands
        # inside the one sharded suite invocation above.
        self.assertNotIn("run: python tools/validate.py", workflow)
        self.assertNotIn("run: python install.py --dry-run", workflow)

    def test_selected_serial_is_routine_and_exhaustive_is_the_fallback(self):
        guidance = AGENTS_MD.read_text(encoding="utf-8")
        self.assertIn("python tools/run_serial_compat.py", guidance)
        self.assertIn("python -m unittest discover -s tests -v", guidance)
        self.assertIn("routinely", guidance)
        self.assertIn("scheduled/manual", guidance)
        self.assertIn("pre-release", guidance)


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
            [
                "tests.test_installer_planning",
                "tests.test_installer_shared",
                "tests.test_cutcheck",
                "tests.test_tickets",
                "tests.test_alpha",
            ],
            run_tests.schedule(modules, {}, run_tests.DEFAULT_TESTS_DIR),
        )

    def test_a_cold_custom_directory_remains_alphabetical(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                [
                    "tests.test_alpha",
                    "tests.test_cutcheck",
                    "tests.test_tickets",
                ],
                run_tests.schedule(
                    [
                        "tests.test_cutcheck",
                        "tests.test_alpha",
                        "tests.test_tickets",
                    ],
                    {},
                    Path(tmp),
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
