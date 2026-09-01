"""Environment resolution and suite-guard cases."""

import ast
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tests.test_state_root_cases.support import (
    BOOTSTRAP_PY,
    ENV_VAR,
    OWNED_FUNCTIONS,
    RETIRED_FUNCTIONS,
    ROOT,
    STATE_ROOT_PY,
    TICKET,
    friction_mod,
    function_names,
    script_sources,
    state_root,
    tickets_mod,
    workspace_mod,
)


class TestTheEnvVarNameIsThisLiteral(unittest.TestCase):
    """The one witness (spec binding ruling 3): an independent pin catching
    a fat-fingered owner. Every other reader in this tree imports
    `state_root.ENV_VAR` (re-exported from `scripts._bootstrap`, the
    owner) rather than spelling the value; this is the one test allowed
    to spell it directly, so a typo in the owner still fails a check
    instead of silently renaming the sink for every importer at once.
    """

    def test_the_owner_constant_is_this_exact_value(self):
        self.assertEqual("ORCHFLOWS_STATE_HOME", state_root.ENV_VAR)


class TestOneResolverOwnsBothFacts(unittest.TestCase):
    """Criterion 1 / spec A1."""

    def test_each_owned_function_is_defined_exactly_once_under_scripts(self):
        for name in OWNED_FUNCTIONS:
            owners = [path.name for path in script_sources() if name in function_names(path)]
            self.assertEqual(
                ["state_root.py"], owners,
                f"{name} must be defined in state_root.py and nowhere else",
            )

    def test_no_retired_resolver_body_survives_anywhere_under_scripts(self):
        for path in script_sources():
            defined = function_names(path)
            for name in RETIRED_FUNCTIONS:
                self.assertNotIn(
                    name, defined,
                    f"{path.name} still defines {name}; the body belongs to "
                    "state_root.py alone",
                )

    def test_the_module_is_a_leaf_with_no_module_level_side_effects(self):
        tree = ast.parse(STATE_ROOT_PY.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        # `tempfile` joined for `inside_temp_root`: it is a standard
        # library leaf that resolves the temp root lazily, so it adds a
        # fact this module owns without adding an import-time act.
        # `scripts` and `_bootstrap` are the two spellings of the one
        # guarded import of the bootstrap leaf below -- package mode
        # resolves one, the flat installed layout the other.
        self.assertEqual(
            {"__future__", "os", "pathlib", "tempfile", "scripts", "_bootstrap"},
            imported,
        )
        body = tree.body
        guards = [node for node in body if isinstance(node, ast.Try)]
        self.assertEqual(1, len(guards), "expected exactly one guarded import")
        guard = guards[0]
        self.assertEqual([], guard.orelse)
        self.assertEqual([], guard.finalbody)
        self.assertEqual(1, len(guard.body))
        self.assertIsInstance(guard.body[0], ast.ImportFrom)
        self.assertEqual(1, len(guard.handlers))
        self.assertEqual(1, len(guard.handlers[0].body))
        self.assertIsInstance(guard.handlers[0].body[0], ast.ImportFrom)
        for node in body:
            self.assertIsInstance(
                node,
                (
                    ast.Expr,
                    ast.Import,
                    ast.ImportFrom,
                    ast.Assign,
                    ast.AnnAssign,
                    ast.FunctionDef,
                    ast.ClassDef,
                    ast.Try,
                ),
                "state_root.py runs something at import time",
            )

    def test_the_bootstrap_leaf_imports_nothing_beyond_pathlib(self):
        """Spec prescription: the leaf imports stdlib only, no `scripts.*`."""

        tree = ast.parse(BOOTSTRAP_PY.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual({"__future__", "pathlib"}, imported)
        for node in tree.body:
            self.assertIsInstance(
                node,
                (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign),
                "_bootstrap.py runs something beyond assignment at import time",
            )

    def test_all_three_writers_resolve_to_the_one_sink(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = Path(raw).resolve() / "sink"
            with mock.patch.dict(os.environ, {ENV_VAR: str(sink)}):
                self.assertEqual(sink / "tickets", tickets_mod._tickets_root())
                self.assertEqual(sink / "runs", tickets_mod._runs_root())
                self.assertEqual(
                    sink / "friction",
                    friction_mod._target_path(datetime.now(timezone.utc)).parent,
                )
                self.assertEqual(
                    STATE_ROOT_PY.resolve(),
                    Path(workspace_mod.state_root.__file__).resolve(),
                )

    def test_workspace_reads_its_ticket_out_of_the_sink(self):
        raw = tempfile.TemporaryDirectory()
        self.addCleanup(raw.cleanup)
        tmp = Path(raw.name).resolve()
        repo = tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        sink = tmp / "sink"
        run_dir = sink / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        (run_dir / "T1.md").write_text(TICKET, encoding="utf-8")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(repo)
        with mock.patch.dict(os.environ, {ENV_VAR: str(sink)}):
            root, path = workspace_mod._locate("testrun", "T1")
        self.assertEqual(repo.resolve(), root)
        self.assertEqual((run_dir / "T1.md").resolve(), path.resolve())


class TestTheOverrideAndTheDefault(unittest.TestCase):
    """Criterion 2 / spec A2."""

    def test_unset_resolves_under_the_home_directory_without_writing(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_VAR, None)
            resolved = state_root.state_root()
        self.assertEqual(Path.home() / ".orchflows" / "state", resolved)

    def test_a_set_value_wins_and_a_tilde_is_expanded(self):
        with mock.patch.dict(os.environ, {ENV_VAR: "/tmp/some-sink"}):
            self.assertEqual(Path("/tmp/some-sink"), state_root.state_root())
        with mock.patch.dict(os.environ, {ENV_VAR: "~/elsewhere"}):
            self.assertEqual(Path.home() / "elsewhere", state_root.state_root())

    def test_set_but_empty_reads_as_unset(self):
        for blank in ("", "   ", "\t"):
            with mock.patch.dict(os.environ, {ENV_VAR: blank}):
                self.assertEqual(
                    Path.home() / ".orchflows" / "state", state_root.state_root(), blank
                )

    def test_the_variable_is_read_at_call_time_not_at_import_time(self):
        with tempfile.TemporaryDirectory() as raw:
            first = Path(raw).resolve() / "first"
            second = Path(raw).resolve() / "second"
            with mock.patch.dict(os.environ, {ENV_VAR: str(first)}):
                self.assertEqual(first / "runs", state_root.runs_root())
                os.environ[ENV_VAR] = str(second)
                self.assertEqual(second / "runs", state_root.runs_root())
                self.assertEqual(second / "runs", tickets_mod._runs_root())
                self.assertEqual(
                    second / "friction",
                    friction_mod._target_path(datetime.now(timezone.utc)).parent,
                )

    def test_the_four_subroots_hang_off_the_one_root(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = Path(raw).resolve()
            with mock.patch.dict(os.environ, {ENV_VAR: str(sink)}):
                self.assertEqual(sink / "runs", state_root.runs_root())
                self.assertEqual(sink / "tickets", state_root.tickets_root())
                self.assertEqual(sink / "friction", state_root.friction_root())
                self.assertEqual(sink / "improvement", state_root.improvement_root())


class TestNoTestReachesTheRealSink(unittest.TestCase):
    """Criterion 5 / spec A3, spec risk 1, binding constraint 7."""

    def real_sink(self) -> Path:
        return Path.home() / ".orchflows" / "state"

    def test_the_redirect_is_in_force_in_this_process(self):
        value = os.environ.get(ENV_VAR)
        self.assertTrue(value, f"{ENV_VAR} is not set: the suite guard did not run")
        self.assertNotEqual(self.real_sink(), Path(value).expanduser().resolve())
        self.assertNotEqual(self.real_sink(), state_root.state_root().resolve())

    def test_a_subprocess_launched_by_a_test_inherits_the_redirect(self):
        done = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; print(os.environ.get({0!r}, ''))".format(ENV_VAR),
            ],
            capture_output=True,
            text=True,
        )
        inherited = done.stdout.strip()
        self.assertTrue(inherited, "the child saw no redirect")
        self.assertEqual(os.environ[ENV_VAR], inherited)

    def test_discovery_of_this_suite_arms_the_guard_without_the_package_init(self):
        program = (
            "import os, sys, unittest\n"
            "sys.path.insert(0, %r)\n"
            "os.environ.pop(%r, None)\n"
            "unittest.TestLoader().discover(%r)\n"
            "print(os.environ.get(%r, ''))\n"
        ) % (str(ROOT), ENV_VAR, str(ROOT / "tests"), ENV_VAR)
        env = dict(os.environ)
        env.pop(ENV_VAR, None)
        done = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
            timeout=300,
        )
        self.assertEqual(0, done.returncode, done.stderr)
        redirected = done.stdout.strip().splitlines()[-1]
        self.assertTrue(redirected, "discovery left the sink pointed at the real one")
        self.assertNotEqual(str(self.real_sink()), redirected)

    def test_the_guard_is_armed_from_both_places_that_can_arm_it(self):
        for path in (ROOT / "tests" / "__init__.py", ROOT / "tests" / "test_state_root.py"):
            armed = [
                node
                for node in ast.parse(path.read_text(encoding="utf-8")).body
                if isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "ensure_temporary_sink"
            ]
            self.assertEqual(1, len(armed), f"{path.name} does not arm the guard")
