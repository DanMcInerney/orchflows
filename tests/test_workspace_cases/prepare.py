"""Tree preparation, a detached workspace, and absolute write-scope entries.

Three behaviors this script gained together, because all three are things
the host does to a workspace that the grader then has to read: it installs
the frontend dependencies the tree declares, it materializes a workspace at
a bare revision rather than a branch, and it writes scope entries as
absolute paths. Each one used to be a refusal or a silent miss.

The install is ``prepare``'s and no longer ``start``'s: it is the one act
here that costs a package manager's minutes and writes no ticket, so it
takes no run lock and every caller reaches it as its own verb, against the
``workspace_path`` the observation already recorded.
"""

import inspect  # noqa: E402  not among the names ``common`` re-exports
import shutil  # noqa: E402  the same

from .common import *  # noqa: F401,F403

import scripts.tickets_dispatch_facade as dispatch_facade  # noqa: E402
import scripts.workspace_candidate as workspace_candidate  # noqa: E402
import scripts.workspace_prepare as workspace_prepare  # noqa: E402

# A stand-in for pnpm. It records what it was called with and exits with
# whatever the test asked for, so a case can assert the exact argv the tree
# was prepared with without a package manager, a registry or a network.
STUB = '''import json, os, sys
log = os.environ.get("STUB_PNPM_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(sys.argv[1:]) + "\\n")
first = (sys.argv[1:] or [""])[0]
if first == "exec":
    sys.stdout.write("Version 1.47.0\\n")
    sys.exit(int(os.environ.get("STUB_PNPM_EXEC_EXIT", "0")))
sys.exit(int(os.environ.get("STUB_PNPM_INSTALL_EXIT", "0")))
'''


def stub_pnpm(directory: Path) -> Path:
    """A ``pnpm`` on PATH, launched the way this platform launches one."""

    directory.mkdir(parents=True, exist_ok=True)
    script = directory / "pnpm_stub.py"
    script.write_text(STUB, encoding="utf-8")
    if os.name == "nt":
        launcher = directory / "pnpm.cmd"
        launcher.write_text(
            f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
        )
    else:
        launcher = directory / "pnpm"
        launcher.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8"
        )
        launcher.chmod(0o755)
    return launcher


def path_holding(*directories) -> str:
    """A PATH carrying git and nothing else the host happens to have.

    ``workspace.py`` shells out to git, so git has to stay reachable; every
    other entry is dropped, so ``pnpm`` is on the PATH of a case exactly
    when that case put it there and never because this host has one.
    """

    entries = [str(directory) for directory in directories]
    found = shutil.which("git")
    if found:
        entries.append(str(Path(found).parent))
    if os.name == "nt":
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        entries.append(str(system_root / "System32"))
    return os.pathsep.join(entries)


def run_workspace_under(cwd: Path, environment: dict, *args):
    """``workspace.py`` under an environment this case fully states.

    The two Playwright variables are dropped before the case's own are
    applied: a host that has either one set would otherwise answer a
    question the case meant to ask of its own fixture.
    """

    base = git_env()
    for name in ("ORCHFLOWS_BROWSER_EXECUTABLE", "PLAYWRIGHT_BROWSERS_PATH"):
        base.pop(name, None)
    base.update(environment)
    return subprocess.run(
        [sys.executable, str(WORKSPACE_PY), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd), env=base,
    )


def frontend_repo(tmp: Path, *, lockfile=True):
    """A repository whose tree declares frontend dependencies, and a
    worktree of it -- the shape ``start`` is asked to prepare."""

    main, run_dir = make_repo(tmp)
    if lockfile:
        commit_in(main, {"pnpm-lock.yaml": "lockfileVersion: '9.0'\n"}, "declare deps")
    worktree = add_worktree(main, "wt-branch", tmp / "wt")
    return main, run_dir, worktree


def detached_worktree(main: Path, path: Path) -> Path:
    """A linked worktree on no branch at all, the shape a host produces when
    it materializes a revision instead of cutting a branch for it."""

    git(main, "worktree", "add", "--quiet", "--detach", str(path))
    return path


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestDetachedWorkspaceIsRecordedAndGraded(unittest.TestCase):
    """``rev-parse --abbrev-ref HEAD`` answers ``HEAD`` in a detached tree,
    which is no ref at all: recorded literally it resolved to nothing at the
    join, so the item graded as isolation-missing however clean its work was.
    ``detached:<full-sha>`` is a ref the join can resolve."""

    def test_start_records_the_full_sha_under_the_detached_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            worktree = detached_worktree(main, tmp / "wt")
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            body = payload_of(done)["start"]
            self.assertEqual(f"detached:{head}", body[workspace.BRANCH_KEY])
            self.assertTrue(body["isolated"])
            self.assertIn(
                f"workspace_branch: detached:{head}\n",
                ticket.read_text(encoding="utf-8"),
            )

    def _graded_detached(self, files, scope=("scratch",)):
        """start in a detached worktree, commit there, grade from the main
        checkout -- the order every isolated item actually runs in."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1", scope=scope,
                        extra=((workspace.ISOLATION_KEY, "required"),))
            base = git(main, "rev-parse", "HEAD").strip()
            worktree = detached_worktree(main, tmp / "wt")

            started = run_workspace(worktree, "start", "testrun", "T1")
            self.assertEqual(0, started.returncode, started.stderr)
            commit_in(worktree, files, "item work")
            # the caller moves on, so the workspace's revision is genuinely
            # not already in the integrating checkout's history
            commit_in(main, {"README.md": "advanced\n"}, "caller moves on")

            return run_workspace(main, "check", "testrun", "T1", "--base", base)

    def test_check_grades_a_scoped_commit_made_after_start(self):
        done = self._graded_detached({"scratch/a.txt": "one\n"})

        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        body = payload_of(done)["check"]
        self.assertEqual("pass", body["verdict"])
        self.assertEqual(["scratch/a.txt"], body["changed"])
        self.assertEqual(1, body["commits"])


    def test_a_removed_workspace_is_refused_rather_than_graded_at_its_revision(self):
        """The record names where the workspace began. A workspace that is
        gone left nothing saying where it ended, so grading the recorded
        revision reports on commits the item never made -- here the side
        revision it was materialized at, while its own commit is invisible."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            base = git(main, "rev-parse", "HEAD").strip()
            make_ticket(run_dir, "T1", extra=((workspace.ISOLATION_KEY, "required"),))
            git(main, "checkout", "--quiet", "-b", "side")
            commit_in(main, {"scratch/pre.txt": "not the item's\n"}, "side work")
            git(main, "checkout", "--quiet", "main")
            worktree = tmp / "wt"
            git(main, "worktree", "add", "--quiet", "--detach", str(worktree), "side")
            started = run_workspace(worktree, "start", "testrun", "T1")
            self.assertEqual(0, started.returncode, started.stderr)
            commit_in(worktree, {"scratch/a.txt": "one\n"}, "item work")
            commit_in(main, {"README.md": "advanced\n"}, "caller moves on")
            git(main, "worktree", "remove", "--force", str(worktree))

            done = run_workspace(main, "check", "testrun", "T1", "--base", base)

            self.assertEqual(2, done.returncode, done.stdout + done.stderr)
            self.assertIn(
                "no single standing worktree carries", payload_of(done)["error"]
            )

    def test_one_detached_workspace_is_never_graded_through_another(self):
        """Two workspaces materialized at the same revision record the same
        identity, and nothing in either record says which worktree is whose.
        Resolved through the first one git happens to list, the second
        item's out-of-scope commit was reported as the first one's pass."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            base = git(main, "rev-parse", "HEAD").strip()
            for tid, files in (
                ("T1", {"scratch/a.txt": "one\n"}),
                ("T2", {"docs/leak.md": "leak\n"}),
            ):
                make_ticket(run_dir, tid, extra=((workspace.ISOLATION_KEY, "required"),))
                worktree = detached_worktree(main, tmp / f"wt-{tid}")
                started = run_workspace(worktree, "start", "testrun", tid)
                self.assertEqual(0, started.returncode, started.stderr)
                commit_in(worktree, files, f"{tid} work")
            commit_in(main, {"README.md": "advanced\n"}, "caller moves on")

            done = run_workspace(main, "check", "testrun", "T2", "--base", base)

            self.assertEqual(2, done.returncode, done.stdout + done.stderr)
            self.assertIn(
                "no single standing worktree carries", payload_of(done)["error"]
            )


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestPrepareInstallsTheFrontendTree(unittest.TestCase):
    """A workspace whose tree declares frontend dependencies is unusable
    until they are installed, and the item executed in it discovered that by
    watching its own first check fail. ``prepare`` installs them once, from
    the lockfile, offline where it can, and says in its payload what
    happened."""

    def _started(self, tmp: Path, environment=None, *, lockfile=True):
        """``start`` records the tree, then ``prepare`` installs into it.

        Two calls because they are two verbs: the record is written under
        the run lock and the install is not, and only the second one may
        call pnpm at all.
        """

        main, run_dir, worktree = frontend_repo(tmp, lockfile=lockfile)
        make_ticket(run_dir, "T1")
        log = tmp / "pnpm-argv.txt"
        stub_pnpm(tmp / "bin")
        environment = dict(environment or {})
        environment.setdefault("PATH", path_holding(tmp / "bin"))
        environment.setdefault("STUB_PNPM_LOG", str(log))
        recorded = run_workspace_under(worktree, environment, "start", "testrun", "T1")
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        self.assertNotIn("frontend", payload_of(recorded)["start"])
        done = run_workspace_under(worktree, environment, "prepare", "testrun", "T1")
        calls = [
            json.loads(line)
            for line in (log.read_text(encoding="utf-8").splitlines() if log.exists() else [])
        ]
        return done, calls

    def test_a_lockfile_and_a_pnpm_on_path_install_from_the_frozen_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            done, calls = self._started(Path(tmp))

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertEqual("installed", payload_of(done)["prepare"]["frontend"])
            self.assertEqual(
                ["install", "--frozen-lockfile", "--prefer-offline"], calls[0]
            )

    def test_it_never_installs_a_browser(self):
        """Pinned at the one state that would tempt it: a Playwright that
        answers and a browser cache with nothing in it. Left to the host's
        own cache this case passed against a `playwright install` written
        straight into the module -- the branch was never reached."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache = tmp / "browsers"
            cache.mkdir()
            done, calls = self._started(tmp, {"PLAYWRIGHT_BROWSERS_PATH": str(cache)})

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertEqual("missing", payload_of(done)["prepare"]["playwright_browser"])
            for argv in calls:
                self.assertNotIn(
                    "install", argv[1:], f"a browser install was attempted: {argv}"
                )
            self.assertEqual([], sorted(cache.iterdir()))

    def test_without_pnpm_on_path_it_is_skipped_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            done, calls = self._started(tmp, {"PATH": path_holding()})

            self.assertEqual(0, done.returncode, done.stderr)
            body = payload_of(done)["prepare"]
            self.assertEqual("skipped: pnpm-missing", body["frontend"])
            self.assertEqual("unknown", body["playwright_browser"])
            self.assertEqual([], calls)

    def test_a_tree_declaring_no_frontend_is_skipped_and_pnpm_is_never_called(self):
        with tempfile.TemporaryDirectory() as tmp:
            done, calls = self._started(Path(tmp), lockfile=False)

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertEqual("skipped: no-lockfile", payload_of(done)["prepare"]["frontend"])
            self.assertEqual([], calls)

    def test_a_failing_install_is_reported_with_its_exit_and_prepare_still_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            done, _ = self._started(tmp, {"STUB_PNPM_INSTALL_EXIT": "3"})

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertEqual("failed: 3", payload_of(done)["prepare"]["frontend"])


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestPrepareReportsTheBrowserWithoutFetchingOne(unittest.TestCase):
    """Whether a Playwright browser is already here is a fact the item needs
    before it writes a render check. Fetching one is a download this script
    will not make on a caller's behalf, so it is reported, never supplied."""

    def _browser(self, tmp: Path, environment):
        main, run_dir, worktree = frontend_repo(tmp)
        make_ticket(run_dir, "T1")
        stub_pnpm(tmp / "bin")
        environment = dict(environment)
        environment.setdefault("PATH", path_holding(tmp / "bin"))
        recorded = run_workspace_under(worktree, environment, "start", "testrun", "T1")
        self.assertEqual(0, recorded.returncode, recorded.stderr)
        done = run_workspace_under(worktree, environment, "prepare", "testrun", "T1")
        self.assertEqual(0, done.returncode, done.stderr)
        return payload_of(done)["prepare"]["playwright_browser"]

    def test_a_named_executable_that_resolves_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            named = tmp / "chrome-headless"
            named.write_text("#!/bin/sh\n", encoding="utf-8")

            self.assertEqual(
                "present",
                self._browser(tmp, {"ORCHFLOWS_BROWSER_EXECUTABLE": str(named)}),
            )

    def test_a_named_executable_that_does_not_resolve_falls_through_to_the_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache = tmp / "browsers"
            (cache / "chromium-1140").mkdir(parents=True)

            self.assertEqual(
                "present",
                self._browser(tmp, {
                    "ORCHFLOWS_BROWSER_EXECUTABLE": str(tmp / "absent"),
                    "PLAYWRIGHT_BROWSERS_PATH": str(cache),
                }),
            )

    def test_an_empty_cache_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache = tmp / "browsers"
            cache.mkdir()

            self.assertEqual(
                "missing", self._browser(tmp, {"PLAYWRIGHT_BROWSERS_PATH": str(cache)})
            )

    def test_a_playwright_that_does_not_answer_is_unknown_not_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cache = tmp / "browsers"
            cache.mkdir()

            self.assertEqual(
                "unknown",
                self._browser(tmp, {
                    "PLAYWRIGHT_BROWSERS_PATH": str(cache),
                    "STUB_PNPM_EXEC_EXIT": "1",
                }),
            )


class TestPreparationIsOutsideEveryLock(unittest.TestCase):
    """The install is minutes; the run lock is what every sibling waits on.

    Structural, because the cost is structural: a case that only asserts the
    payload would stay green the day someone moves the call back inside the
    critical section, and the symptom of that is siblings idling, not a red.
    """

    def test_neither_establishment_lane_installs_while_it_stamps(self):
        source = inspect.getsource(workspace_candidate)
        lanes = [
            inspect.getsource(getattr(workspace_candidate, name))
            for name in ("_observed", "_derived")
        ]
        self.assertIn("workspace_prepare.prepare(", source)
        for lane, name in zip(lanes, ("_observed", "_derived")):
            with self.subTest(lane=name):
                self.assertNotIn("workspace_prepare.prepare(", lane)

    def test_the_facade_prepares_after_it_lets_the_lock_go(self):
        source = inspect.getsource(dispatch_facade._cmd_dispatch)
        self.assertLess(
            source.index("with _run_lock(run):"),
            source.index("_workspace_prepare("),
        )
        self.assertNotIn(
            "_workspace_prepare(",
            inspect.getsource(dispatch_facade._dispatched_under_run_lock),
        )

    def test_prepare_refuses_an_item_that_recorded_no_workspace(self):
        """A step skipped, not a step that failed: nothing is installed and
        the refusal names the verb that records the path."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")

            done = run_workspace(tmp, "prepare", "testrun", "T1")

            self.assertNotEqual(0, done.returncode)
            self.assertIn(
                "workspace.py establish testrun T1", payload_of(done)["error"]
            )


class TestTheInstallCeilingIsReal(unittest.TestCase):
    """Ten minutes, not forever. A pnpm that never returns used to hold the
    whole item at its first act with nothing on stdout to say why, and no
    subprocess call in this module may be made without a ceiling."""

    def test_the_ceiling_is_ten_minutes_and_a_timeout_is_a_failure(self):
        seen = []

        def never_returns(argv, cwd, env, timeout):
            seen.append((argv[1], timeout))
            raise subprocess.TimeoutExpired(argv, timeout)

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
            stub_pnpm(tmp / "bin")
            prepared = workspace_prepare.prepare(
                tmp, env={"PATH": str(tmp / "bin")}, run=never_returns
            )

        self.assertEqual(600, dict(seen)["install"])
        # every call, not only the install: a version probe that hangs holds
        # the item just as completely as an install that hangs
        self.assertTrue(all(timeout for _, timeout in seen), seen)
        self.assertEqual("failed: timeout", prepared["frontend"])
        self.assertEqual("unknown", prepared["playwright_browser"])
