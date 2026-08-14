"""One sink resolver, reached by every writer, and unreachable by the suite.

Spec 20260814T124222Z-centralize-state, A1-A3: durable run state resolves
to one user-scope sink, ``$ORCHFLOWS_STATE_HOME`` overrides it, and no
test can write to the real one.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests import ensure_temporary_sink  # noqa: E402

# `python -m unittest discover -s tests` never imports this package (it makes
# `tests/` the top-level directory), so the guard is armed from here too.
# Discovery imports every module before running any test, which is why one
# module doing this covers the whole run.
ensure_temporary_sink()

import scripts.friction as friction_mod  # noqa: E402
import scripts.state_root as state_root  # noqa: E402
import scripts.tickets as tickets_mod  # noqa: E402
import scripts.workspace as workspace_mod  # noqa: E402

SCRIPTS_DIR = ROOT / "scripts"
STATE_ROOT_PY = SCRIPTS_DIR / "state_root.py"
TICKETS_PY = SCRIPTS_DIR / "tickets.py"
FRICTION_PY = SCRIPTS_DIR / "friction.py"
ENV_VAR = state_root.ENV_VAR

# The names that answer "where does durable state go" and "which project is
# this". Each is defined once, in state_root.py, and nowhere else.
OWNED_FUNCTIONS = (
    "state_root",
    "runs_root",
    "tickets_root",
    "friction_root",
    "improvement_root",
    "find_repo_root",
    "main_checkout_root",
)
# The private spellings the duplication used to wear, in both tickets.py and
# friction.py. No body of either may survive anywhere under scripts/.
RETIRED_FUNCTIONS = ("_find_repo_root", "_main_checkout_root")

TICKET = """---
id: T1
run: testrun
status: ready
executor: orch-tdd
depends_on: []
write_scope: scratch/t1.txt
bound: 30m
---

## Objective

Test ticket.
"""


def function_names(path: Path) -> list:
    """Every function this module defines, at any nesting depth."""

    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
    return names


def script_sources() -> list:
    return sorted(SCRIPTS_DIR.glob("*.py"))


def run_script(script: Path, *args, cwd: Path, sink=None, env_extra=None):
    env = dict(os.environ)
    if sink is not None:
        env[ENV_VAR] = str(sink)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd), env=env,
    )


def listing(root: Path) -> list:
    if not root.exists():
        return []
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


class _SinkFixture(unittest.TestCase):
    """A repository with no ``.orch/`` in it and a sink outside every tree."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.sink = self.tmp / "sink"

    @staticmethod
    def give_origin(repo: Path, url: str) -> None:
        """Two clones of one origin are one project (spec A5); the origin url
        is read out of `<main-root>/.git/config`, never from a `git` call."""

        (repo / ".git" / "config").write_text(
            f'[remote "origin"]\n\turl = {url}\n', encoding="utf-8"
        )

    def stamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")


class TestOneResolverOwnsBothFacts(unittest.TestCase):
    """Criterion 1 / spec A1."""

    def test_each_owned_function_is_defined_exactly_once_under_scripts(self):
        for name in OWNED_FUNCTIONS:
            owners = [p.name for p in script_sources() if name in function_names(p)]
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
        """friction.py's reliability bar: importing this may not do anything
        that can raise, or a partial install turns a log call into a
        traceback."""

        tree = ast.parse(STATE_ROOT_PY.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual({"__future__", "os", "pathlib"}, imported)
        for node in tree.body:
            self.assertIsInstance(
                node,
                (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
                 ast.FunctionDef, ast.ClassDef),
                "state_root.py runs something at import time",
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
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw).resolve()
            repo = tmp / "repo"
            (repo / ".git").mkdir(parents=True)
            sink = tmp / "sink"
            run_dir = sink / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text(TICKET, encoding="utf-8")
            before = os.getcwd()
            os.chdir(repo)
            self.addCleanup(os.chdir, before)
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
                # set again, after this module and every writer was imported
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


class TestFindRepoRootNamesTheProject(unittest.TestCase):
    """Which project a record arose in — never where the record goes.

    Moved here with the resolver itself, from tests/test_friction.py and
    tests/test_tickets.py, which each graded their own former copy.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()

    def make_main(self, name="main") -> Path:
        main = self.tmp / name
        (main / ".git").mkdir(parents=True)
        return main

    def test_main_checkout_resolves_to_itself(self):
        main = self.make_main()
        sub = main / "skills" / "kernel"
        sub.mkdir(parents=True)
        self.assertEqual(main, state_root.find_repo_root(sub))

    def test_linked_worktree_resolves_to_its_main_checkout(self):
        main = self.make_main()
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        self.assertEqual(main, state_root.find_repo_root(wt))

    def test_relative_gitdir_pointer_resolves_to_the_superproject(self):
        super_repo = self.make_main("super")
        (super_repo / ".git" / "modules" / "mod").mkdir(parents=True)
        mod = super_repo / "mod"
        mod.mkdir()
        (mod / ".git").write_text("gitdir: ../.git/modules/mod\n", encoding="utf-8")
        self.assertEqual(super_repo, state_root.find_repo_root(mod))

    def test_unparseable_git_file_falls_back_to_the_walk_up_result(self):
        main = self.make_main()
        vendored = main / "vendored"
        vendored.mkdir()
        (vendored / ".git").write_text("not a gitdir pointer\n", encoding="utf-8")
        self.assertEqual(vendored, state_root.find_repo_root(vendored))

    def test_no_repository_returns_none(self):
        bare = self.tmp / "bare"
        bare.mkdir()
        self.assertIsNone(state_root.find_repo_root(bare))

    def test_the_walk_up_is_bounded(self):
        deep = self.tmp.joinpath(*[f"d{i}" for i in range(state_root.MAX_WALK_UP + 4)])
        deep.mkdir(parents=True)
        self.assertIsNone(state_root.find_repo_root(deep))

    def test_a_none_project_does_not_stop_the_sink_from_resolving(self):
        """The two answers are independent: no repository still has a sink."""

        bare = self.tmp / "bare"
        bare.mkdir()
        with mock.patch.dict(os.environ, {ENV_VAR: str(self.tmp / "sink")}):
            self.assertIsNone(state_root.find_repo_root(bare))
            self.assertEqual(self.tmp / "sink" / "runs", state_root.runs_root())


class TestEveryWriterLandsInTheSink(_SinkFixture):
    """Criterion 3: the relocation, proved at the seam and from a subprocess.

    Each case asserts the bytes at the sink *and* that the repository the
    writer ran in has no ``.orch/`` at all: a write that quietly succeeded
    in the caller's own tree is the loss this run exists to end.
    """

    def assert_repo_untouched(self):
        self.assertFalse((self.repo / ".orch").exists(), "a writer created .orch/")

    def test_a_run_state_note_appends_under_the_sink(self):
        done = run_script(
            TICKETS_PY, "run-state", "testrun", "--note", "slice one landed",
            cwd=self.repo, sink=self.sink,
        )
        payload = json.loads(done.stdout)
        worklog = self.sink / "runs" / "testrun" / "worklog.md"
        self.assertEqual(str(worklog.resolve()), payload["run_state"]["path"])
        self.assertEqual("slice one landed\n", worklog.read_text(encoding="utf-8"))
        self.assert_repo_untouched()

    def test_a_run_state_artifact_lands_under_the_run_partition(self):
        run_script(
            TICKETS_PY, "run-state", "testrun", "--artifact", "evidence.md",
            "--text", "the bytes in the sink\n", cwd=self.repo, sink=self.sink,
        )
        artifact = self.sink / "runs" / "testrun" / "evidence.md"
        self.assertEqual("the bytes in the sink\n", artifact.read_text(encoding="utf-8"))
        self.assert_repo_untouched()

    def test_a_ticket_is_read_out_of_the_sink_from_a_repository_with_none(self):
        run_dir = self.sink / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        (run_dir / "T1.md").write_text(TICKET, encoding="utf-8")
        done = run_script(TICKETS_PY, "list", "--run", "testrun", cwd=self.repo, sink=self.sink)
        payload = json.loads(done.stdout)
        self.assertEqual(["T1"], [t["id"] for t in payload["tickets"]])
        self.assert_repo_untouched()

    def test_a_friction_entry_lands_in_the_sink(self):
        done = run_script(
            FRICTION_PY, "observed thing", "expected thing",
            cwd=self.repo, sink=self.sink,
        )
        self.assertEqual(0, done.returncode)
        self.assertEqual("friction logged", done.stdout.strip())
        log = self.sink / "friction" / f"{self.stamp()}.jsonl"
        entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual("observed thing", entry["observed"])
        self.assert_repo_untouched()

    def test_two_workspaces_of_one_project_write_one_sink(self):
        """The objective's central clause: the sink follows the user, not the
        checkout, so a run started in one workspace is reachable from another
        workspace of the same project (spec A5)."""

        origin = "https://example.invalid/acme/alpha.git"
        self.give_origin(self.repo, origin)
        second = self.tmp / "other-clone"
        (second / ".git").mkdir(parents=True)
        self.give_origin(second, origin)
        run_script(TICKETS_PY, "run-state", "testrun", "--note", "from clone one",
                   cwd=self.repo, sink=self.sink)
        run_script(TICKETS_PY, "run-state", "testrun", "--note", "from clone two",
                   cwd=second, sink=self.sink)
        worklog = self.sink / "runs" / "testrun" / "worklog.md"
        self.assertEqual(
            ["from clone one", "from clone two"],
            worklog.read_text(encoding="utf-8").splitlines(),
        )
        self.assertFalse((second / ".orch").exists())
        self.assert_repo_untouched()

    def test_two_unrelated_projects_write_one_sink(self):
        """The same clause for projects that share nothing. One sink holds
        every project's runs; one run id is one project's (spec A6), so each
        writes under its own and both land here rather than in their trees."""

        second = self.tmp / "other-repo"
        (second / ".git").mkdir(parents=True)
        run_script(TICKETS_PY, "run-state", "run-one", "--note", "from repo one",
                   cwd=self.repo, sink=self.sink)
        run_script(TICKETS_PY, "run-state", "run-two", "--note", "from repo two",
                   cwd=second, sink=self.sink)
        runs = self.sink / "runs"
        self.assertEqual(
            "from repo one\n",
            (runs / "run-one" / "worklog.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "from repo two\n",
            (runs / "run-two" / "worklog.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((second / ".orch").exists())
        self.assert_repo_untouched()

    def test_outside_any_repository_the_sink_still_resolves(self):
        bare = self.tmp / "no-repo-here"
        bare.mkdir()
        done = run_script(TICKETS_PY, "run-state", "testrun", "--note", "no git in sight",
                          cwd=bare, sink=self.sink)
        payload = json.loads(done.stdout)
        self.assertNotIn("error", payload)
        self.assertEqual(
            "no git in sight\n",
            (self.sink / "runs" / "testrun" / "worklog.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((bare / ".orch").exists())


class TestThereIsNoFallback(_SinkFixture):
    """Criterion 4 / spec binding constraint 1.

    The sink is a plain file, so every ``mkdir(parents=True)`` under it
    raises. Portable: no chmod, which Windows ignores for the owner.
    """

    def setUp(self):
        super().setUp()
        self.blocked = self.tmp / "blocked-sink"
        self.blocked.write_text("not a directory\n", encoding="utf-8")

    def test_run_state_reports_the_failure_and_writes_nothing_under_cwd(self):
        before = listing(self.repo)
        done = run_script(TICKETS_PY, "run-state", "testrun", "--note", "x",
                          cwd=self.repo, sink=self.blocked)
        self.assertEqual(0, done.returncode)
        payload = json.loads(done.stdout)
        self.assertIn("error", payload)
        self.assertNotIn("run_state", payload)
        self.assertEqual(before, listing(self.repo))

    def test_the_logger_stays_silent_exits_zero_and_writes_nothing_under_cwd(self):
        before = listing(self.repo)
        done = run_script(FRICTION_PY, "o", "e", cwd=self.repo, sink=self.blocked)
        self.assertEqual(0, done.returncode)
        self.assertEqual("", done.stdout)
        self.assertEqual("", done.stderr)
        self.assertEqual(before, listing(self.repo))

    def test_the_logger_survives_a_missing_resolver_beside_it(self):
        """A partial install: friction.py alone in a directory. It may not
        traceback, because a module-level import would have died before
        ``main``'s broad except existed."""

        flat = self.tmp / "bin"
        flat.mkdir()
        (flat / "friction.py").write_text(
            FRICTION_PY.read_text(encoding="utf-8"), encoding="utf-8"
        )
        done = run_script(flat / "friction.py", "o", "e", cwd=self.repo, sink=self.sink)
        self.assertEqual(0, done.returncode)
        self.assertEqual("", done.stdout)
        self.assertFalse((self.sink / "friction").exists())

    def test_the_flat_installed_layout_resolves_when_the_resolver_is_beside_it(self):
        flat = self.tmp / "bin"
        flat.mkdir()
        for name in ("friction.py", "state_root.py", "tickets.py"):
            (flat / name).write_text(
                (SCRIPTS_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
            )
        logged = run_script(flat / "friction.py", "o", "e", cwd=self.repo, sink=self.sink)
        self.assertEqual("friction logged", logged.stdout.strip())
        noted = run_script(flat / "tickets.py", "run-state", "testrun", "--note", "flat",
                           cwd=self.repo, sink=self.sink)
        self.assertNotIn("error", json.loads(noted.stdout))
        self.assertEqual(
            "flat\n",
            (self.sink / "runs" / "testrun" / "worklog.md").read_text(encoding="utf-8"),
        )


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
            [sys.executable, "-c",
             "import os; print(os.environ.get('ORCHFLOWS_STATE_HOME', ''))"],
            capture_output=True, text=True,
        )
        inherited = done.stdout.strip()
        self.assertTrue(inherited, "the child saw no redirect")
        self.assertEqual(os.environ[ENV_VAR], inherited)

    def test_discovery_of_this_suite_arms_the_guard_without_the_package_init(self):
        """`python -m unittest discover -s tests` makes tests/ the top-level
        directory and never imports tests/__init__.py. Loading the suite the
        way that command does must still leave the variable redirected."""

        program = (
            "import os, sys, unittest\n"
            "sys.path.insert(0, %r)\n"
            "os.environ.pop('ORCHFLOWS_STATE_HOME', None)\n"
            "unittest.TestLoader().discover(%r)\n"
            "print(os.environ.get('ORCHFLOWS_STATE_HOME', ''))\n"
        ) % (str(ROOT), str(ROOT / "tests"))
        env = dict(os.environ)
        env.pop(ENV_VAR, None)
        done = subprocess.run(
            [sys.executable, "-c", program], capture_output=True, text=True,
            cwd=str(ROOT), env=env, timeout=300,
        )
        self.assertEqual(0, done.returncode, done.stderr)
        redirected = done.stdout.strip().splitlines()[-1]
        self.assertTrue(redirected, "discovery left the sink pointed at the real one")
        self.assertNotEqual(str(self.real_sink()), redirected)

    def test_the_guard_is_armed_from_both_places_that_can_arm_it(self):
        """A module-level *call*, not a mention. ``def ensure_temporary_sink()``
        carries the same characters as the call, so a substring check would
        stay green against a package that only defines the guard."""

        for path in (ROOT / "tests" / "__init__.py", Path(__file__)):
            armed = [
                node for node in ast.parse(path.read_text(encoding="utf-8")).body
                if isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "ensure_temporary_sink"
            ]
            self.assertEqual(1, len(armed), f"{path.name} does not arm the guard")


if __name__ == "__main__":
    unittest.main()
