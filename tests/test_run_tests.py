"""Process-runner tests for residue, scheduling, telemetry, and console seams."""

from __future__ import annotations
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
from tools import run_tests_scope  # noqa: E402
from tests.test_installer_cases import _collection  # noqa: E402
from tests.test_run_tests_cases.collection_law import (  # noqa: E402,F401
    TestCollectionLaw,
)
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
        "ui.html.escape": "from reader.scripts import ui\nui.html.escape = lambda value: value",
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


def _module_name(path: Path) -> str:
    """The dotted name `import` would use for one file under the repository."""

    parts = list(path.relative_to(REPO_ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _import_edges(path: Path, name: str) -> set:
    """Every module `path` names in an import statement, absolute or relative.

    Read off the syntax tree rather than the text, because a package name
    appearing in a docstring or a fixture string is not an import and was
    exactly what let a severed chain read as reached.
    """

    import ast

    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        base = package
        for _ in range(max(node.level - 1, 0)):
            base = base.rpartition(".")[0]
        target = base + "." + node.module if node.level and node.module else (
            node.module or base
        )
        out.add(target)
        out.update(target + "." + alias.name for alias in node.names)
    return out


class TestCaseTreeReach(unittest.TestCase):
    """Every module of every `*_cases/` package is reached by discovery.

    `discover` globs `test*.py` at the top level only, so a case module is
    reached solely through the chain of imports that starts at one. Delete a
    link and the modules behind it stop running while every count stays green
    -- which is how six packages sat unrun for two days after commit 932706a3
    removed their drivers, and how nineteen modules of `test_tickets_cases`
    and seven of `test_workspace_cases` sat unrun behind three deleted links
    for four days after `2182d018`. A count cannot see either: the tests are
    not failing, they are absent. So the reach is walked structurally, module
    by module -- a package whose entry module is imported proves nothing
    about the modules only its own siblings named.
    """

    def _reached(self) -> set:
        tests_dir = REPO_ROOT / "tests"
        modules = {
            _module_name(path): path
            for path in sorted(tests_dir.rglob("*.py"))
            if "__pycache__" not in path.parts
        }
        edges = {
            name: {edge for edge in _import_edges(path, name) if edge in modules}
            for name, path in modules.items()
        }
        # `discover` collects exactly the top-level `test*.py`; everything
        # else runs only because one of those reaches it.
        frontier = [
            name for name, path in modules.items()
            if path.parent == tests_dir and path.name.startswith("test")
        ]
        self.assertTrue(frontier, "discovery collects nothing")
        seen = set()
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            frontier.extend(edges[current] - seen)
        # importing a submodule imports its package, which no edge records
        for name in list(seen):
            parent = name.rpartition(".")[0]
            while parent and parent in modules:
                seen.add(parent)
                parent = parent.rpartition(".")[0]
        return seen

    def test_every_case_module_is_imported_by_the_chain_discovery_starts(self):
        tests_dir = REPO_ROOT / "tests"
        reached = self._reached()
        modules = [
            path for package in sorted(tests_dir.glob("*_cases"))
            for path in sorted(package.rglob("*.py"))
            if "__pycache__" not in path.parts
        ]
        # An empty corpus agrees with any rule; say so before comparing.
        self.assertTrue(modules)
        unreached = [
            f"{_module_name(path)}: no collected module's import chain reaches "
            f"it -- import its cases from the module that re-exports the "
            f"package, or delete it"
            for path in modules
            if _module_name(path) not in reached
        ]
        self.assertEqual([], unreached, "\n".join(unreached))


class TestSchedule(unittest.TestCase):
    def test_installer_cases_are_exactly_once_across_process_visible_shards(self):
        modules = [
            name for name in run_tests.discover(run_tests.DEFAULT_TESTS_DIR)[2]
            if name.startswith("tests.test_installer")
        ]
        self.assertGreaterEqual(len(modules), 3)
        for name in modules:
            if name != "tests.test_installer":
                source = REPO_ROOT.joinpath(*name.split(".")).with_suffix(".py")
                self.assertIn('sys.modules.get("test_installer")', source.read_text())
        loaded = _collection.loaded_cases(modules)
        declared = _collection.declared_cases(REPO_ROOT)
        # Both, before the comparison: two empty corpora agree with each other,
        # which is a scan that found nothing to inspect wearing a green tick --
        # the same shape as the silence the comparison is here to break.
        self.assertTrue(declared)
        self.assertTrue(loaded)
        # A count subtraction cannot say which of the two rules was broken or
        # what to do about it, and both halves of a mixin look like arithmetic.
        # `_collection.report` owns the statement; this only carries it.
        breach = _collection.report(declared, loaded)
        if breach:  # `assertEqual("", ...)` would bury it under a diff notice
            self.fail(breach)
        identities = [identity for identity, _, _ in loaded]
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
        """The prior was read off Linux, where a leg's long pole is cheap:
        a module sorted last by a cold schedule ran alone to the end of
        its leg's wall clock, so the named prior starts the known poles
        first."""
        modules = ["tests.test_alpha", "tests.test_serial_compat",
                   "tests.test_workspace", "tests.test_zeta"]
        self.assertEqual(
            ["tests.test_workspace", "tests.test_serial_compat"],
            sorted(run_tests.schedule(modules, {}, run_tests.DEFAULT_TESTS_DIR)[:2], reverse=True),
        )

    def test_shards_partition_the_schedule_exactly(self):
        """Every module in exactly one shard. A shard that drops one runs a
        green half-suite, and a shard that repeats one pays for it twice."""
        order = ["tests.test_%02d" % index for index in range(23)]
        for count in range(1, 6):
            shards = [
                run_tests_scope.shard("%d-of-%d" % (index, count), order)
                for index in range(1, count + 1)
            ]
            union = [module for shard in shards for module in shard]
            self.assertEqual(sorted(order), sorted(union), "count=%d" % count)
            self.assertEqual(len(union), len(set(union)), "count=%d" % count)

    def test_a_shard_is_round_robin_over_the_longest_first_order(self):
        """Contiguous halves would take every long module into the first one,
        which finishes no sooner than the unsharded suite did."""
        order = ["a", "b", "c", "d", "e"]
        self.assertEqual(["a", "c", "e"], run_tests_scope.shard("1-of-2", order))
        self.assertEqual(["b", "d"], run_tests_scope.shard("2-of-2", order))

    def test_an_absent_shard_is_the_whole_order_and_a_bad_one_is_refused(self):
        order = ["a", "b"]
        self.assertEqual(order, run_tests_scope.shard(None, order))
        for bad in ("3-of-2", "0-of-2", "2-of-0", "1/2", "two-of-three", "2"):
            with self.assertRaises(SystemExit, msg=bad):
                run_tests_scope.shard(bad, order)

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
