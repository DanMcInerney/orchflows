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

WORKSPACE_PY = ROOT / "scripts" / "workspace.py"
TICKETS_PY = ROOT / "scripts" / "tickets.py"
CONTRACT = ROOT / "contracts" / "work-item.md"

GIT_ENV = dict(
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
        cwd=str(cwd), env=GIT_ENV,
    )
    if completed.returncode != 0:
        raise unittest.SkipTest(f"git {args[0]} failed: {completed.stderr.strip()}")
    return completed.stdout


def run_workspace(cwd: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(WORKSPACE_PY), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd), env=GIT_ENV,
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


def make_repo(tmp: Path):
    """A real git repository with one commit and a run of tickets at its root.

    ``.orch/`` is gitignored exactly as it is in the repository this script
    ships from, so a fixture tree with tickets in it is still clean.
    """

    main = tmp / "main"
    main.mkdir()
    git(main, "init", "--quiet")
    (main / ".gitignore").write_text(".orch/\n", encoding="utf-8")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    git(main, "add", ".gitignore", "README.md")
    git(main, "commit", "--quiet", "-m", "init")
    run_dir = main / ".orch" / "tickets" / "testrun"
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
            # `orch-task` is an engine, which tickets.py reports as an error
            # inside the payload of an otherwise successful call
            ticket = make_ticket(run_dir, "T1")
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace(
                    "executor: orch-tdd", "executor: orch-task"
                ),
                encoding="utf-8",
            )
            before = ticket.read_text(encoding="utf-8")

            listed = subprocess.run(
                [sys.executable, str(TICKETS_PY), "list", "--run", "testrun"],
                capture_output=True, text=True, cwd=str(main), env=GIT_ENV,
            )
            self.assertEqual(0, listed.returncode)
            self.assertIn("error", json.loads(listed.stdout)["tickets"][0])

            done = run_workspace(main, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("engine", payload_of(done)["error"])
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))


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

    def test_the_root_resolver_is_imported_from_tickets_never_copied(self):
        source = WORKSPACE_PY.read_text(encoding="utf-8")
        self.assertIn("import tickets", self.collapsed(source))
        self.assertNotIn("def _find_repo_root", source)
        self.assertNotIn("def _main_checkout_root", source)
        self.assertNotIn("gitdir:", source)
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
            imported - {"__future__", "json", "subprocess", "sys", "pathlib", "tickets"},
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


def make_isolated_item(
    tmp: Path, *, scope=("scratch",), files=None, branch="wt-branch",
    tid="T1", recorded=True, extra=(),
):
    """A main checkout at a base commit, a linked worktree carrying the item's
    branch, and the main-root ticket that declares the isolation."""

    main, run_dir = make_repo(tmp)
    base = git(main, "rev-parse", "HEAD").strip()
    worktree = add_worktree(main, branch, tmp / branch)
    commit_in(worktree, files if files is not None else {"scratch/a.txt": "one\n"}, "item work")
    stamps = ((workspace.BRANCH_KEY, branch),) if recorded else ()
    ticket = make_ticket(
        run_dir, tid, scope=scope,
        extra=((workspace.ISOLATION_KEY, "required"),) + stamps + tuple(extra),
    )
    return main, worktree, ticket, base


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestCheckGradesFromTheCallersGit(unittest.TestCase):
    """Completion criterion 3: one exit code per failure mode, every fact
    re-derived from git. Nothing a child wrote in prose is read."""

    def test_isolation_absent_passes_without_touching_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")
            # a base no git command could resolve: reaching git at all fails
            done = run_workspace(main, "check", "testrun", "T1", "--base", "no-such-rev")
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_isolation_none_passes_without_touching_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1", extra=((workspace.ISOLATION_KEY, "none"),))
            done = run_workspace(main, "check", "testrun", "T1", "--base", "no-such-rev")
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_required_with_no_recorded_branch_exits_no_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, base = make_isolated_item(Path(tmp), recorded=False)
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(5, done.returncode, done.stdout)
            body = payload_of(done)
            self.assertEqual("no-record", body["verdict"])
            self.assertIn(workspace.BRANCH_KEY, body["error"])

    def test_a_branch_that_does_not_resolve_exits_isolation_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, ticket, base = make_isolated_item(tmp)
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace("wt-branch", "ghost-branch"),
                encoding="utf-8",
            )
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(2, done.returncode, done.stdout)
            body = payload_of(done)
            self.assertEqual("isolation-missing", body["verdict"])
            self.assertIn("ghost-branch", body["error"])

    def test_the_callers_own_branch_exits_isolation_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, ticket, base = make_isolated_item(tmp)
            own = git(main, "rev-parse", "--abbrev-ref", "HEAD").strip()
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace("wt-branch", own),
                encoding="utf-8",
            )
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(2, done.returncode, done.stdout)
            self.assertEqual("isolation-missing", payload_of(done)["verdict"])

    def test_a_branch_already_on_the_callers_head_exits_isolation_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, ticket, base = make_isolated_item(tmp)
            git(main, "branch", "stale-branch", base)
            commit_in(main, {"README.md": "advanced\n"}, "caller moves on")
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace("wt-branch", "stale-branch"),
                encoding="utf-8",
            )
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(2, done.returncode, done.stdout)
            self.assertEqual("isolation-missing", payload_of(done)["verdict"])

    def test_a_branch_not_cut_from_the_base_exits_wrong_branch_point(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, _ = make_isolated_item(tmp)
            elsewhere = commit_in(main, {"README.md": "elsewhere\n"}, "another line")
            done = run_workspace(main, "check", "testrun", "T1", "--base", elsewhere)
            self.assertEqual(3, done.returncode, done.stdout)
            body = payload_of(done)
            self.assertEqual("wrong-branch-point", body["verdict"])
            self.assertIn(elsewhere, body["error"])

    def test_an_in_scope_branch_passes_and_reports_what_it_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, base = make_isolated_item(tmp)
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(0, done.returncode, done.stdout)
            body = payload_of(done)["check"]
            self.assertEqual("pass", body["verdict"])
            self.assertEqual(["scratch/a.txt"], body["changed"])
            self.assertEqual(1, body["commits"])

    def test_a_path_outside_the_scope_exits_scope_breach(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, base = make_isolated_item(
                Path(tmp), files={"scratch/a.txt": "one\n", "docs/leak.md": "leak\n"}
            )
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(4, done.returncode, done.stdout)
            body = payload_of(done)
            self.assertEqual("scope-breach", body["verdict"])
            self.assertIn("docs/leak.md", body["error"])
            self.assertEqual(["docs/leak.md"], body["breaches"])

    def test_a_breach_arriving_inside_a_merge_commit_is_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _, base = make_isolated_item(tmp)
            side = add_worktree(main, "side-branch", tmp / "side")
            commit_in(side, {"scratch/side.txt": "side\n"}, "side work")
            git(worktree, "merge", "--no-ff", "--no-commit", "--quiet", "side-branch")
            # the breach is introduced by the merge commit itself, which is
            # exactly what `git log --name-only` cannot see
            commit_in(worktree, {"docs/leak.md": "leak\n"}, "merge side-branch")
            logged = git(main, "log", "--name-only", "--pretty=format:", f"{base}..wt-branch")
            self.assertNotIn("docs/leak.md", logged)

            done = run_workspace(main, "check", "testrun", "T1", "--base", base)

            self.assertEqual(4, done.returncode, done.stdout)
            self.assertEqual(["docs/leak.md"], payload_of(done)["breaches"])

    def test_an_unresolvable_base_is_an_internal_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, _ = make_isolated_item(Path(tmp))
            done = run_workspace(main, "check", "testrun", "T1", "--base", "no-such-rev")
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertEqual("error", payload_of(done)["verdict"])

    def test_usage_errors_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, base = make_isolated_item(Path(tmp))
            for args in (
                ("check", "testrun", "T1"),
                ("check", "testrun", "--base", base),
                ("check", "testrun", "T1", "MISSING", "--base", base),
                ("check", "testrun", "MISSING", "--base", base),
            ):
                with self.subTest(args=args):
                    self.assertEqual(1, run_workspace(main, *args).returncode)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestVerdictSurvivesCleanupAndScopeIsSegmentExact(unittest.TestCase):
    """Completion criterion 4: the branch facts are the verdict, and a scope
    entry matches on whole segments."""

    def test_check_passes_after_the_linked_tree_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _, base = make_isolated_item(tmp)
            git(main, "worktree", "remove", "--force", str(worktree))
            self.assertFalse(worktree.exists())

            done = run_workspace(main, "check", "testrun", "T1", "--base", base)

            self.assertEqual(0, done.returncode, done.stdout)
            self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_a_scope_entry_matches_whole_segments_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, base = make_isolated_item(
                Path(tmp), scope=("docs",), files={"docsmith/x.md": "sneak\n"}
            )
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(4, done.returncode, done.stdout)
            self.assertEqual(["docsmith/x.md"], payload_of(done)["breaches"])

    def test_the_same_scope_entry_takes_its_own_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, _, base = make_isolated_item(
                Path(tmp), scope=("docs",), files={"docs/x.md": "mine\n"}
            )
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertEqual(["docs/x.md"], payload_of(done)["check"]["changed"])

    def test_an_absolute_scope_entry_inside_the_repository_is_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            base = git(main, "rev-parse", "HEAD").strip()
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            commit_in(worktree, {"scratch/a.txt": "one\n"}, "item work")
            make_ticket(
                run_dir, "T1", scope=(str(main / "scratch"),),
                extra=(
                    (workspace.ISOLATION_KEY, "required"),
                    (workspace.BRANCH_KEY, "wt-branch"),
                ),
            )
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_an_absolute_scope_entry_outside_the_repository_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            outside = str(tmp / "elsewhere" / "notes.md")
            main, _, _, base = make_isolated_item(Path(tmp), scope=("scratch", outside))
            done = run_workspace(main, "check", "testrun", "T1", "--base", base)
            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn(outside, payload_of(done)["error"])


if __name__ == "__main__":
    unittest.main()
