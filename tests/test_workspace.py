"""``scripts/workspace.py``: what ``start`` records from inside a workspace,
what ``check`` grades at the join, and that the frontmatter key names the
script uses are ``contracts/work-item.md``'s own."""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.workspace as workspace  # noqa: E402
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner

WORKSPACE_PY = ROOT / "scripts" / "workspace.py"
TICKETS_PY = ROOT / "scripts" / "tickets.py"
STATE_ROOT_PY = ROOT / "scripts" / "state_root.py"
CONTRACT = ROOT / "contracts" / "work-item.md"
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"


def git_env() -> dict:
    """Built per call, never frozen at import: ``use_sink`` points
    ``ORCHFLOWS_STATE_HOME`` at this test's own sink, and every child
    process must inherit the value in force when it is launched."""

    return dict(
        os.environ,
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
        GIT_CONFIG_NOSYSTEM="1",
    )


def git_available() -> bool:
    try:
        return subprocess.run(
            ["git", "--version"], capture_output=True, text=True
        ).returncode == 0
    except OSError:
        return False


def git(cwd: Path, *args: str) -> str:
    """A fixture git call. A failure here is an unusable environment, so it
    skips rather than reporting a defect in the script under test."""

    completed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd), env=git_env(),
    )
    if completed.returncode != 0:
        raise unittest.SkipTest(f"git {args[0]} failed: {completed.stderr.strip()}")
    return completed.stdout


def run_workspace(cwd: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(WORKSPACE_PY), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd), env=git_env(),
    )


def payload_of(completed) -> dict:
    try:
        return json.loads(completed.stdout)
    except ValueError:  # pragma: no cover - only on a broken script
        raise AssertionError(
            f"workspace.py printed no JSON payload: {completed.stdout!r} "
            f"{completed.stderr!r}"
        )


def make_ticket(run_dir: Path, tid: str, *, scope=("scratch",), extra=()) -> Path:
    """A fixture work item. Never this run's own ticket: the base revision of
    this run does not contain ``workspace.py``, so no ticket of it declares
    ``isolation`` and none may be graded by it."""

    lines = [
        "---",
        f"id: {tid}",
        "run: testrun",
        "status: claimed",
        "executor: orch-tdd",
        "depends_on: []",
        "write_scope:",
    ]
    lines += [f"  - {entry}" for entry in scope]
    lines += ["bound: 30m"]
    lines += [f"{key}: {value}" for key, value in extra]
    lines += ["---", "", "## Objective", "", "Fixture ticket.", ""]
    path = run_dir / f"{tid}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def use_sink(tmp: Path) -> Path:
    """Point ``ORCHFLOWS_STATE_HOME`` at a sink under this test's tempdir.

    Sets the variable for the rest of the process rather than restoring
    it: every writing test calls this first, and ``tests/__init__.py``
    holds the floor at a temporary directory regardless, so the worst a
    stale value can do is fail a test, never reach the real sink.
    """

    # resolved: a macOS tempdir is reached through a /var symlink, and a
    # payload that prints the sink path must match the path a test opens
    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def make_repo(tmp: Path):
    """A real git repository with one commit, and a run of tickets in the sink.

    Tickets live in the one user-scope sink, outside every checkout, so
    the repository is clean without needing to ignore anything — but the
    fixture keeps ``.orch/`` gitignored anyway, matching the repository
    this script ships from, so a stray write into the tree would still be
    invisible to git and must be caught by asserting on the path itself.
    """

    sink = use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    git(main, "init", "--quiet")
    (main / ".gitignore").write_text(".orch/\n", encoding="utf-8")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    git(main, "add", ".gitignore", "README.md")
    git(main, "commit", "--quiet", "-m", "init")
    run_dir = sink / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    return main, run_dir


def add_worktree(main: Path, branch: str, path: Path) -> Path:
    git(main, "worktree", "add", "--quiet", "-b", branch, str(path))
    return path


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestStartRecordsWhatItObserved(unittest.TestCase):
    """Completion criterion 1: ``start`` records the branch and the baseline
    it observed, into the main-root ticket, creating no ``.orch/`` beside it."""

    def test_from_a_linked_worktree_it_writes_the_main_root_ticket_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_text(encoding="utf-8")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            after = ticket.read_text(encoding="utf-8")
            self.assertIn("workspace_branch: wt-branch\n", after)
            self.assertIn(f"workspace_baseline: {head} clean\n", after)
            # the targeted write: two lines inserted before the closing ---,
            # every other byte of the ticket left as it was found
            self.assertEqual(
                before.replace(
                    "---\n\n## Objective",
                    f"workspace_branch: wt-branch\n"
                    f"workspace_baseline: {head} clean\n---\n\n## Objective",
                ),
                after,
            )
            self.assertFalse(
                (worktree / ".orch").exists(),
                "start created a private .orch/ in the workspace",
            )
            body = payload_of(done)["start"]
            self.assertEqual("wt-branch", body["workspace_branch"])
            self.assertTrue(body["isolated"])

    def test_in_the_main_checkout_it_exits_zero_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1", extra=(("isolation", "required"),))
            branch = git(main, "rev-parse", "--abbrev-ref", "HEAD").strip()

            done = run_workspace(main, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            body = payload_of(done)
            self.assertNotIn("error", body)
            self.assertFalse(body["start"]["isolated"])
            after = ticket.read_text(encoding="utf-8")
            self.assertIn(f"workspace_branch: {branch}\n", after)
            self.assertIn("workspace_baseline: ", after)

    def test_a_dirty_tree_records_the_exact_paths_including_both_ends_of_a_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            git(worktree, "mv", "README.md", "RENAMED.md")
            (worktree / "untracked.txt").write_text("x\n", encoding="utf-8")
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            recorded = [
                line for line in ticket.read_text(encoding="utf-8").splitlines()
                if line.startswith("workspace_baseline: ")
            ]
            self.assertEqual(1, len(recorded), recorded)
            value = recorded[0][len("workspace_baseline: "):]
            self.assertTrue(value.startswith(f"{head} dirty: "), value)
            listed = value.partition("dirty: ")[2].split(", ")
            self.assertEqual(
                ["README.md", "RENAMED.md", "untracked.txt"], sorted(listed)
            )
            self.assertEqual(
                ["README.md", "RENAMED.md", "untracked.txt"],
                sorted(payload_of(done)["start"]["dirty"]),
            )


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestStartFailureBehavior(unittest.TestCase):
    """Completion criterion 2: what ``start`` refuses, and what it does not."""

    def _refuses_dirty_name(self, name: str):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_text(encoding="utf-8")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            (worktree / name).write_text("x\n", encoding="utf-8")

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn(name, payload_of(done)["error"])
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_dirty_path_with_a_comma_is_refused_by_name(self):
        self._refuses_dirty_name("a,b.txt")

    def test_a_dirty_path_with_a_quote_is_refused_by_name(self):
        self._refuses_dirty_name("it's.txt")

    def _refuses_scope_entry(self, entry: str):
        """A grant no machine can read is refused where it is still cheap.

        `check` splits a diff's paths against these entries and reports what
        falls outside them. An entry carrying a space or a parenthesis is
        prose -- "scripts/ (tests only)", "docs and rules" -- and matches no
        path at all, so every path the branch changed reads as a breach, or
        the grant silently covers nothing and every change passes. Either way
        the reading is wrong, and it is wrong at the join, hours after the
        cut that could have fixed it. So `start`, which every isolated item
        runs first, refuses it and names the contract that says a scope entry
        is a path.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1", scope=("scratch", entry))
            before = ticket.read_text(encoding="utf-8")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            error = payload_of(done)["error"]
            self.assertIn(entry, error)
            self.assertIn("contracts/work-item.md", error)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_scope_entry_carrying_a_space_is_refused_at_start(self):
        self._refuses_scope_entry("scripts/ and tests/")

    def test_a_scope_entry_carrying_a_parenthesis_is_refused_at_start(self):
        self._refuses_scope_entry("scripts/(tests)")

    def _accepts_scope_entry(self, entry_of):
        """A space is prose only where there is no path by that name.

        `C:\\Users\\Dan M\\...` and `/Users/Dan McInerney/...` are exactly
        paths, and a refusal keyed to the character alone refuses the host
        rather than the cut. The parenthesis stays refused: it is the shape
        the prose entries this guard was written for actually carry.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            spaced = worktree / "a dir"
            spaced.mkdir()
            make_ticket(run_dir, "T1", scope=("scratch", entry_of(spaced)))

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    def test_a_relative_scope_entry_that_is_an_existing_spaced_path_is_kept(self):
        self._accepts_scope_entry(lambda spaced: spaced.name)

    def test_an_absolute_scope_entry_that_is_an_existing_spaced_path_is_kept(self):
        self._accepts_scope_entry(lambda spaced: str(spaced))

    def test_a_spaced_entry_that_is_no_path_is_still_refused(self):
        self._refuses_scope_entry("scratch and tests/")

    def test_a_bare_path_scope_is_recorded_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1", scope=("scripts/one.py", "tests/"))
            worktree = add_worktree(main, "wt-branch", tmp / "wt")

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    def test_a_lost_frontmatter_write_race_leaves_the_winner_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            stale = ticket.read_text(encoding="utf-8")
            winner = stale.replace("status: claimed", "status: suspended")
            ticket.write_text(winner, encoding="utf-8")

            outcome = workspace._record(ticket, stale, "wt-branch", "deadbeef clean")

            self.assertIn("error", outcome)
            self.assertIn("lost the", outcome["error"])
            self.assertEqual(winner, ticket.read_text(encoding="utf-8"))

    def test_a_lost_race_exits_one_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_text(encoding="utf-8")
            original = workspace._record
            workspace._record = lambda *a, **k: {"error": "ticket changed since read"}
            cwd = os.getcwd()
            noise = io.StringIO()
            try:
                os.chdir(str(main))
                with redirect_stdout(noise), redirect_stderr(noise):
                    code = workspace.main(["start", "testrun", "T1"])
            finally:
                os.chdir(cwd)
                workspace._record = original
            self.assertIn("ticket changed since read", noise.getvalue())
            self.assertEqual(1, code)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_write_landing_during_the_git_work_is_reported_through_start(self):
        """The snapshot the stamps are written against is taken before the
        seconds of git work, not after them, so a ``set-status`` landing while
        git runs is reported rather than absorbed. Neither sibling case can
        see this: one calls ``_record`` directly with a hand-made stale
        snapshot, the other monkeypatches ``_record`` away entirely."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            observe = workspace._dirty_paths

            def a_write_lands_mid_git():
                # stands in for a concurrent `set-status`, at the one moment
                # the two reads used to straddle. `.orch/` is gitignored, so
                # the dirty set git reports is unchanged by this write.
                ticket.write_text(
                    ticket.read_text(encoding="utf-8").replace(
                        "status: claimed", "status: suspended"
                    ),
                    encoding="utf-8",
                )
                return observe()

            cwd = os.getcwd()
            noise = io.StringIO()
            try:
                os.chdir(str(main))
                workspace._dirty_paths = a_write_lands_mid_git
                with redirect_stdout(noise), redirect_stderr(noise):
                    code = workspace.main(["start", "testrun", "T1"])
            finally:
                os.chdir(cwd)
                workspace._dirty_paths = observe

            self.assertEqual(1, code, noise.getvalue())
            self.assertIn("lost the frontmatter write race", noise.getvalue())
            after = ticket.read_text(encoding="utf-8")
            self.assertIn("status: suspended", after)
            self.assertNotIn(workspace.BRANCH_KEY, after)

    def test_an_unisolated_workspace_is_recorded_not_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1", extra=(("isolation", "required"),))

            done = run_workspace(main, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertIn("workspace_branch: ", ticket.read_text(encoding="utf-8"))

    def test_usage_errors_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")
            for args in (
                ("start",),
                ("start", "testrun"),
                ("start", "testrun", "T1", "--extra"),
                ("start", "testrun", "MISSING"),
                ("dance", "testrun", "T1"),
                (),
            ):
                with self.subTest(args=args):
                    self.assertEqual(1, run_workspace(main, *args).returncode)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestTicketsPayloadIsGradedNotItsExitStatus(unittest.TestCase):
    """Completion criterion 5: ``tickets.py`` exits 0 and reports failure in
    its payload; ``workspace.py`` grades the payload and exits non-zero."""

    def test_an_error_payload_returned_at_exit_zero_is_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            # A ticket file whose bytes are not UTF-8, which tickets.py
            # reports as an error inside the payload of an otherwise
            # successful call. It used to be `executor: orch-panel`, an engine
            # — P4-3 deleted the two engines that were illegal executors and
            # the prohibition with them, so this is the payload-error source
            # that remains for a file `_locate` accepts. Which error it is has
            # never been this test's subject; that `list` exits 0 carrying
            # one, and that `workspace.py` grades the payload rather than the
            # exit status, is.
            ticket = make_ticket(run_dir, "T1")
            ticket.write_bytes(b"---\nid: T1\nexecutor: \xff\xfe\n---\n")
            before = ticket.read_bytes()

            listed = subprocess.run(
                [sys.executable, str(TICKETS_PY), "list", "--run", "testrun"],
                capture_output=True, text=True, cwd=str(main), env=git_env(),
            )
            self.assertEqual(0, listed.returncode)
            self.assertIn("error", json.loads(listed.stdout)["tickets"][0])

            done = run_workspace(main, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable ticket", payload_of(done)["error"])
            self.assertEqual(before, ticket.read_bytes())


class TestScriptShape(unittest.TestCase):
    """Completion criterion 5: stdlib-only, network-free, the resolver
    imported rather than copied, and the exit-code deviation documented."""

    @staticmethod
    def collapsed(text: str) -> str:
        return " ".join(text.split())

    def test_the_module_docstring_documents_the_exit_code_deviation(self):
        docstring = ast.get_docstring(ast.parse(WORKSPACE_PY.read_text(encoding="utf-8")))
        collapsed = self.collapsed(docstring or "")
        self.assertIn(
            "this script does not inherit that script's exit-0 convention",
            collapsed,
        )
        self.assertIn("scripts/tickets.py", collapsed)
        self.assertIn("graded by parsing the returned payload", collapsed)
        self.assertIn("contracts/work-item.md", collapsed)

    def test_the_resolvers_are_imported_never_copied(self):
        source = WORKSPACE_PY.read_text(encoding="utf-8")
        collapsed = self.collapsed(source)
        self.assertIn("import state_root", collapsed)
        self.assertIn("import tickets", collapsed)
        self.assertNotIn("def _find_repo_root", source)
        self.assertNotIn("def _main_checkout_root", source)
        self.assertNotIn("def state_root", source)
        self.assertNotIn("gitdir:", source)
        self.assertNotIn(".orch", source)
        self.assertEqual(
            str(STATE_ROOT_PY.resolve()),
            str(Path(workspace.state_root.__file__).resolve()),
        )
        self.assertEqual(
            str(TICKETS_PY.resolve()),
            str(Path(workspace.tickets.__file__).resolve()),
        )

    def test_the_script_is_stdlib_only_and_network_free(self):
        tree = ast.parse(WORKSPACE_PY.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(
            set(),
            imported - {
                "__future__", "json", "subprocess", "sys", "pathlib",
                "state_root", "tickets",
            },
            f"unexpected import in workspace.py: {sorted(imported)}",
        )
        self.assertIn("__future__", imported, "the 3.9 floor needs the future import")


LEADING_KEY_RE = re.compile(r"^`([a-z_]+)`(?:,\s*)?")


def contract_frontmatter_bullets():
    """Every frontmatter bullet ``contracts/work-item.md`` declares, from the
    contract's own bytes: the block between its ``Frontmatter,`` and ``Body
    sections,`` lead-ins, one entry per top-level bullet, each entry the run
    of backticked names the bullet opens with plus the bullet's whole text.
    Nothing here is a list of key names typed into this test."""

    lines = CONTRACT.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Frontmatter,"))
    end = next(i for i, line in enumerate(lines) if line.startswith("Body sections,"))
    bullets, current = [], None
    for line in lines[start:end]:
        if line.startswith("- "):
            current = [line[2:]]
            bullets.append(current)
        elif current is not None and line.startswith("  ") and line.strip():
            current.append(line.strip())
        else:
            current = None
    parsed = []
    for bullet in bullets:
        keys, rest = [], bullet[0]
        while True:
            match = LEADING_KEY_RE.match(rest)
            if match is None:
                break
            keys.append(match.group(1))
            rest = rest[match.end():]
        parsed.append((keys, " ".join(bullet)))
    return parsed


class TestContractKeySeam(unittest.TestCase):
    """Completion criterion 6. Both sides are collected mechanically: the code
    side from the module constant the script itself uses, the contract side
    from ``contracts/work-item.md``'s own bytes. A key spelled one way in the
    script and another way in the contract fails here and nowhere else."""

    def test_the_key_names_the_script_uses_are_the_contracts_own_both_ways(self):
        bullets = contract_frontmatter_bullets()
        declared = {key for keys, _ in bullets for key in keys}
        self.assertIn("id", declared, "the contract's frontmatter block did not parse")

        code_keys = set(workspace.FRONTMATTER_KEYS)
        self.assertTrue(code_keys, "workspace.py declares no frontmatter keys")
        self.assertEqual(
            [], sorted(code_keys - declared),
            "workspace.py uses a frontmatter key contracts/work-item.md does "
            "not declare",
        )

        workspace_keys = {
            key for keys, text in bullets for key in keys if "workspace.py" in text
        }
        self.assertEqual(
            3, len(workspace_keys),
            f"expected the contract's three workspace keys, found {sorted(workspace_keys)}",
        )
        self.assertEqual(
            [], sorted(workspace_keys - code_keys),
            "contracts/work-item.md declares a workspace key the shipped code "
            "neither writes nor reads",
        )

    def test_each_key_the_script_uses_names_where_it_is_written_or_read(self):
        for key, role in workspace.FRONTMATTER_KEYS.items():
            with self.subTest(key=key):
                self.assertRegex(role, r"start|check")


def commit_in(tree: Path, files: dict, message: str) -> str:
    for name, content in files.items():
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    git(tree, "add", "-A")
    git(tree, "commit", "--quiet", "-m", message)
    return git(tree, "rev-parse", "HEAD").strip()


_GRADED = {}


def graded_repository():
    """One real repository, built once, for the tests that only read it.

    A repository plus a linked worktree is eight git processes and every
    ``check`` test below wanted the same one. So every branch any of them
    grades is cut here from ``base`` and never moved again, and the caller
    is left one commit past ``base`` so a branch left behind is genuinely
    behind. A test writes only its own ticket, under its own id, into this
    fixture's own sink -- nothing a test does reaches what the next one
    reads. Whatever must move a branch, an index or a working tree keeps
    its own repository, built inline from ``make_repo``.
    """

    if _GRADED:
        # re-pointed on every call, not only built once: ``use_sink`` moves
        # ``ORCHFLOWS_STATE_HOME`` for the rest of the process, so any test
        # that has built its own repository since left the variable at its
        # own sink, and this repository's tickets would be looked for there.
        os.environ[STATE_HOME_ENV_VAR] = str(_GRADED["sink"])
        return _GRADED
    tmp = Path(tempfile.mkdtemp(prefix="workspace-graded-"))
    _GRADED["tmp"] = tmp
    main, run_dir = make_repo(tmp)
    base = git(main, "rev-parse", "HEAD").strip()

    worktree = add_worktree(main, "wt-branch", tmp / "wt")
    commit_in(worktree, {"scratch/a.txt": "one\n"}, "item work")
    for branch, files in (
        ("leak-branch", {"docs/leak.md": "leak\n"}),
        ("mixed-branch", {"scratch/a.txt": "one\n", "docs/leak.md": "leak\n"}),
        ("docsmith-branch", {"docsmith/x.md": "sneak\n"}),
        ("docs-branch", {"docs/x.md": "mine\n"}),
        ("side-branch", {"scratch/side.txt": "side\n"}),
        ("merge-branch", {"scratch/a.txt": "one\n"}),
    ):
        # `checkout -b`, never `switch`: switch arrived in git 2.23.
        git(worktree, "checkout", "--quiet", "-b", branch, base)
        commit_in(worktree, files, "item work")
    # merge-branch's breach arrives in the merge commit itself, which is
    # exactly what `git log --name-only` cannot see
    git(worktree, "merge", "--no-ff", "--no-commit", "--quiet", "side-branch")
    commit_in(worktree, {"docs/leak.md": "leak\n"}, "merge side-branch")

    removed = tmp / "removed"
    add_worktree(main, "removed-branch", removed)
    commit_in(removed, {"scratch/a.txt": "one\n"}, "item work")
    git(main, "worktree", "remove", "--force", str(removed))

    git(main, "branch", "stale-branch", base)
    own = git(main, "rev-parse", "--abbrev-ref", "HEAD").strip()
    advanced = commit_in(main, {"README.md": "advanced\n"}, "caller moves on")

    _GRADED.update(
        main=main, run_dir=run_dir, base=base, advanced=advanced,
        removed=removed, own=own, sink=run_dir.parent.parent,
    )
    return _GRADED


def tearDownModule():
    tmp = _GRADED.pop("tmp", None)
    if tmp is not None:
        # the tree holds a repository this suite committed in, so the strict
        # owner removes it -- see tests/tree_removal.py
        remove_repo_tree(str(tmp))


def graded_item(tid, *, branch="wt-branch", scope=("scratch",), isolation="required",
                recorded=True, extra=()):
    """A ticket of the shared repository, under this test's own id."""

    graded = graded_repository()
    declared = ((workspace.ISOLATION_KEY, isolation),) if isolation else ()
    stamps = ((workspace.BRANCH_KEY, branch),) if recorded else ()
    make_ticket(
        graded["run_dir"], tid, scope=scope,
        extra=declared + stamps + tuple(extra),
    )
    return graded


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestCheckGradesFromTheCallersGit(unittest.TestCase):
    """Completion criterion 3: one exit code per failure mode, every fact
    re-derived from git. Nothing a child wrote in prose is read."""

    def test_isolation_absent_passes_without_touching_git(self):
        graded = graded_item("T-absent", isolation=None, recorded=False)
        # a base no git command could resolve: reaching git at all fails
        done = run_workspace(
            graded["main"], "check", "testrun", "T-absent", "--base", "no-such-rev"
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_isolation_none_passes_without_touching_git(self):
        graded = graded_item("T-none", isolation="none", recorded=False)
        done = run_workspace(
            graded["main"], "check", "testrun", "T-none", "--base", "no-such-rev"
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_a_backticked_required_grades_the_same_as_a_bare_one(self):
        """One normalizer reads `isolation` for both scripts. `tickets.py`
        strips backticks off the same declaration when it emits the
        establishment step, so a grader that did not would skip the grade
        entirely at exit 0 while the join read success."""

        for index, declared in enumerate(("required", "`required`")):
            with self.subTest(declared=declared):
                tid = "T-backtick-%d" % index
                graded = graded_item(tid, branch="leak-branch", isolation=declared)

                done = run_workspace(
                    graded["main"], "check", "testrun", tid, "--base", graded["base"]
                )

                self.assertEqual(4, done.returncode, done.stdout)
                body = payload_of(done)
                self.assertEqual("scope-breach", body["verdict"])
                self.assertEqual(["docs/leak.md"], body["breaches"])

    def test_required_with_no_recorded_branch_exits_no_record(self):
        graded = graded_item("T-unrecorded", recorded=False)
        done = run_workspace(
            graded["main"], "check", "testrun", "T-unrecorded", "--base", graded["base"]
        )
        self.assertEqual(5, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("no-record", body["verdict"])
        self.assertIn(workspace.BRANCH_KEY, body["error"])

    def test_a_branch_that_does_not_resolve_exits_isolation_missing(self):
        graded = graded_item("T-ghost", branch="ghost-branch")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-ghost", "--base", graded["base"]
        )
        self.assertEqual(2, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("isolation-missing", body["verdict"])
        self.assertIn("ghost-branch", body["error"])

    def test_the_callers_own_branch_exits_isolation_missing(self):
        graded = graded_repository()
        graded_item("T-own", branch=graded["own"])
        done = run_workspace(
            graded["main"], "check", "testrun", "T-own", "--base", graded["base"]
        )
        self.assertEqual(2, done.returncode, done.stdout)
        self.assertEqual("isolation-missing", payload_of(done)["verdict"])

    def test_a_branch_already_on_the_callers_head_exits_isolation_missing(self):
        # stale-branch sits at the base the caller has since moved past
        graded = graded_item("T-stale", branch="stale-branch")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-stale", "--base", graded["base"]
        )
        self.assertEqual(2, done.returncode, done.stdout)
        self.assertEqual("isolation-missing", payload_of(done)["verdict"])

    def test_a_branch_not_cut_from_the_base_exits_wrong_branch_point(self):
        graded = graded_item("T-elsewhere")
        elsewhere = graded["advanced"]
        done = run_workspace(
            graded["main"], "check", "testrun", "T-elsewhere", "--base", elsewhere
        )
        self.assertEqual(3, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("wrong-branch-point", body["verdict"])
        self.assertIn(elsewhere, body["error"])

    def test_an_in_scope_branch_passes_and_reports_what_it_changed(self):
        graded = graded_item("T-inscope")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-inscope", "--base", graded["base"]
        )
        self.assertEqual(0, done.returncode, done.stdout)
        body = payload_of(done)["check"]
        self.assertEqual("pass", body["verdict"])
        self.assertEqual(["scratch/a.txt"], body["changed"])
        self.assertEqual(1, body["commits"])

    def test_a_path_outside_the_scope_exits_scope_breach(self):
        graded = graded_item("T-breach", branch="mixed-branch")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-breach", "--base", graded["base"]
        )
        self.assertEqual(4, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("scope-breach", body["verdict"])
        self.assertIn("docs/leak.md", body["error"])
        self.assertEqual(["docs/leak.md"], body["breaches"])

    def test_a_breach_arriving_inside_a_merge_commit_is_seen(self):
        graded = graded_item("T-merge", branch="merge-branch")
        base = graded["base"]
        logged = git(
            graded["main"], "log", "--name-only", "--pretty=format:",
            f"{base}..merge-branch",
        )
        self.assertNotIn("docs/leak.md", logged)

        done = run_workspace(
            graded["main"], "check", "testrun", "T-merge", "--base", base
        )

        self.assertEqual(4, done.returncode, done.stdout)
        self.assertEqual(["docs/leak.md"], payload_of(done)["breaches"])

    def test_an_unresolvable_base_is_an_internal_error(self):
        graded = graded_item("T-nobase")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-nobase", "--base", "no-such-rev"
        )
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertEqual("error", payload_of(done)["verdict"])

    def test_usage_errors_exit_one(self):
        graded = graded_item("T-usage")
        base = graded["base"]
        for args in (
            ("check", "testrun", "T-usage"),
            ("check", "testrun", "--base", base),
            ("check", "testrun", "T-usage", "MISSING", "--base", base),
            ("check", "testrun", "MISSING", "--base", base),
        ):
            with self.subTest(args=args):
                self.assertEqual(1, run_workspace(graded["main"], *args).returncode)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestVerdictSurvivesCleanupAndScopeIsSegmentExact(unittest.TestCase):
    """Completion criterion 4: the branch facts are the verdict, and a scope
    entry matches on whole segments."""

    def test_check_passes_after_the_linked_tree_is_removed(self):
        # removed-branch's linked tree was removed when the fixture was
        # built; every other test here grades a branch whose tree is still
        # there, which is the contrast this one needs.
        graded = graded_item("T-removed", branch="removed-branch")
        self.assertFalse(graded["removed"].exists())

        done = run_workspace(
            graded["main"], "check", "testrun", "T-removed", "--base", graded["base"]
        )

        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_a_scope_entry_matches_whole_segments_only(self):
        graded = graded_item("T-docsmith", branch="docsmith-branch", scope=("docs",))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-docsmith", "--base", graded["base"]
        )
        self.assertEqual(4, done.returncode, done.stdout)
        self.assertEqual(["docsmith/x.md"], payload_of(done)["breaches"])

    def test_the_same_scope_entry_takes_its_own_segment(self):
        graded = graded_item("T-docs", branch="docs-branch", scope=("docs",))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-docs", "--base", graded["base"]
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual(["docs/x.md"], payload_of(done)["check"]["changed"])

    def test_an_absolute_scope_entry_inside_the_repository_is_normalized(self):
        graded = graded_repository()
        graded_item("T-absolute-in", scope=(str(graded["main"] / "scratch"),))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-absolute-in", "--base", graded["base"]
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_an_absolute_scope_entry_outside_the_repository_is_refused_by_name(self):
        graded = graded_repository()
        outside = str(graded["tmp"] / "elsewhere" / "notes.md")
        graded_item("T-absolute-out", scope=("scratch", outside))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-absolute-out",
            "--base", graded["base"],
        )
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertIn(outside, payload_of(done)["error"])


class NoFormatCallsTest(unittest.TestCase):
    """Completion criterion 1 of item-05-fstring-pass: no `.format(` call site
    remains in scripts/workspace.py."""

    def test_workspace_py_contains_no_format_calls(self):
        source = WORKSPACE_PY.read_text(encoding="utf-8")
        self.assertNotIn(".format(", source)


if __name__ == "__main__":
    unittest.main()
