"""`tools/verify_at.py` runs one command where it says it does, then leaves.

Every checker in a run needs the same vantage: this exact revision, checked
out somewhere the suite's own rules still mean what they say, the command's
verdict reported as the command gave it, and nothing left behind either way.
Roughly eight contexts hand-rolled that choreography across two runs, and
the hand-rolled versions disagreed -- on where the checkout may sit, on
whether a red run still cleans up, on whether the two output streams may be
merged. Five facts are graded here, one per disagreement.

The repository under test is built from nothing in a scratch directory, so
no assertion here depends on this checkout's own history. The child's system
temp root is set through `TMPDIR`/`TEMP`/`TMP`, which is the same question
`tempfile.gettempdir()` asks -- that is how a test can put a worktree root
on either side of the boundary without moving anything real.

The can-fail direction (rules/verification.md Section 8) is `--keep`: the
same cleanup assertions are run against a worktree the tool was told to
leave, so a green cleanup test cannot be green by asserting nothing.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import verify_at  # noqa: E402

VERIFY_AT_PY = REPO_ROOT / "tools" / "verify_at.py"

# Tokens the emitter writes, one per stream. Neither appears in any command
# line, so finding one in a stream means it arrived through that stream and
# not through the tool's own report of what it was asked to run.
OUT_TOKEN = "stdout-side-token"
ERR_TOKEN = "stderr-side-token"

READER = 'print(open("marker.txt", encoding="utf-8").read().strip())\n'

CWD = "import os\nprint(os.getcwd())\n"

ENV_PROBE = 'import os\nprint(os.environ.get("GIT_DIR", "<unset>"))\n'

EMITTER = textwrap.dedent(
    '''\
    import sys

    sys.stdout.write("{out}\\n")
    sys.stderr.write("{err}\\n")
    if "--stray" in sys.argv[1:]:
        open("stray.txt", "w", encoding="utf-8").write("left behind")
    sys.exit(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    '''
).format(out=OUT_TOKEN, err=ERR_TOKEN)


def clean_env() -> dict:
    """The caller's environment with every git seam that aims a command."""

    env = dict(os.environ)
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(name, None)
    return env


def git(repo: Path, *args: str) -> str:
    """One git command in `repo`, refusing to guess when it fails."""

    done = subprocess.run(
        ["git", "-C", os.fspath(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_env(),
    )
    if done.returncode != 0:
        raise AssertionError(
            "git {0}: {1}".format(args[0], done.stderr.decode("utf-8", "replace"))
        )
    return done.stdout.decode("utf-8", "replace")


def build_repo(repo: Path) -> dict:
    """A two-commit repository whose marker names the commit it belongs to.

    The scripts land in the first commit and stay; only `marker.txt` moves.
    A command run at the first commit can therefore say which revision it is
    standing on, in a word, without asking git anything.
    """

    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "--quiet")
    git(repo, "config", "user.email", "verify-at@example.invalid")
    git(repo, "config", "user.name", "verify-at test")
    for name, body in (
        ("reader.py", READER),
        ("cwd.py", CWD),
        ("env_probe.py", ENV_PROBE),
        ("emitter.py", EMITTER),
        ("marker.txt", "first\n"),
    ):
        (repo / name).write_text(body, encoding="utf-8")
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", "first")
    first = git(repo, "rev-parse", "HEAD").strip()
    (repo / "marker.txt").write_text("second\n", encoding="utf-8")
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", "second")
    return {"first": first, "second": git(repo, "rev-parse", "HEAD").strip()}


def recorded_worktrees(repo: Path) -> list:
    """Every worktree the repository still records, its own included."""

    return [
        line.split(" ", 1)[1]
        for line in git(repo, "worktree", "list", "--porcelain").splitlines()
        if line.startswith("worktree ")
    ]


def admin_entries(repo: Path) -> list:
    """The administrative entries `git worktree prune` is what clears."""

    directory = repo / ".git" / "worktrees"
    return sorted(entry.name for entry in directory.iterdir()) if directory.is_dir() else []


# The repository is built once: every test here reads it and none writes to
# it, and building it costs nine git processes that would otherwise be paid
# fourteen times over. What each test does own is its own worktree root, so
# "nothing was left behind" is still a question about that test alone.
_SHARED = {}


def setUpModule():
    holder = tempfile.TemporaryDirectory()
    _SHARED["holder"] = holder
    _SHARED["repo"] = Path(holder.name).resolve() / "repo"
    _SHARED["commits"] = build_repo(_SHARED["repo"])


def tearDownModule():
    _SHARED.pop("holder").cleanup()


class VerifyAtCase(unittest.TestCase):
    """One scratch repository, one worktree root, one declared temp root."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.scratch = Path(holder.name).resolve()
        self.repo = _SHARED["repo"]
        self.commits = _SHARED["commits"]
        self.root = self.scratch / "worktrees"
        # A declared temp root must exist: `tempfile.gettempdir()` tests each
        # candidate by writing in it and silently falls back when it cannot.
        self.temp_root = self.scratch / "declared-temp"
        self.temp_root.mkdir()

    def verify_at(self, revision, command, root=None, temp_root=None, extra=(), env=None):
        """Run the tool as its own process, the way a checker runs it."""

        child = clean_env() if env is None else env
        child = dict(child)
        declared = os.fspath(self.temp_root if temp_root is None else temp_root)
        child["TMPDIR"] = child["TEMP"] = child["TMP"] = declared
        child["PYTHONPATH"] = os.fspath(REPO_ROOT)
        argv = [
            sys.executable,
            os.fspath(VERIFY_AT_PY),
            revision,
            "--repo",
            os.fspath(self.repo),
            "--root",
            os.fspath(self.root if root is None else root),
            *extra,
            "--",
            *command,
        ]
        return subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=child
        )

    def assertNothingLeftBehind(self):
        """No checkout under the root, and no record of one in the repo."""

        self.assertEqual([], sorted(p.name for p in self.root.iterdir()))
        self.assertEqual([os.fspath(self.repo)], [
            os.fspath(Path(entry).resolve()) for entry in recorded_worktrees(self.repo)
        ])
        self.assertEqual([], admin_entries(self.repo))

    @staticmethod
    def text(raw: bytes) -> str:
        return raw.decode("utf-8", "replace")


class RevisionExactnessTest(VerifyAtCase):
    """The command stands on the revision it was given, not on HEAD."""

    def test_the_command_runs_at_the_named_revision(self):
        done = self.verify_at(self.commits["first"], [sys.executable, "reader.py"])
        self.assertEqual(0, done.returncode, self.text(done.stderr))
        self.assertEqual("first", self.text(done.stdout).strip())

    def test_the_named_revision_is_what_moves_the_answer(self):
        done = self.verify_at(self.commits["second"], [sys.executable, "reader.py"])
        self.assertEqual(0, done.returncode, self.text(done.stderr))
        self.assertEqual("second", self.text(done.stdout).strip())

    def test_a_revision_the_repository_does_not_have_is_refused(self):
        done = self.verify_at("no-such-revision", [sys.executable, "reader.py"])
        self.assertEqual(verify_at.REFUSAL_STATUS, done.returncode)
        self.assertIn("no-such-revision", self.text(done.stderr))
        self.assertEqual("", self.text(done.stdout))
        self.assertEqual([], admin_entries(self.repo))


class TempRootPlacementTest(VerifyAtCase):
    """The checkout sits outside the host's system temp root."""

    def test_the_default_root_is_outside_the_system_temp_root(self):
        self.assertFalse(verify_at.inside_temp_root(verify_at.default_root()))

    def test_the_worktree_is_created_under_the_root_it_was_given(self):
        done = self.verify_at(self.commits["first"], [sys.executable, "cwd.py"])
        self.assertEqual(0, done.returncode, self.text(done.stderr))
        where = Path(self.text(done.stdout).strip()).resolve()
        self.assertEqual(self.root.resolve(), where.parent)
        self.assertFalse(
            os.path.commonpath((os.fspath(self.temp_root), os.fspath(where)))
            == os.fspath(self.temp_root)
        )

    def test_a_root_inside_the_system_temp_root_is_refused(self):
        """The can-fail direction: the same run, one boundary moved."""

        done = self.verify_at(
            self.commits["first"],
            [sys.executable, "emitter.py"],
            temp_root=self.scratch,
        )
        self.assertEqual(verify_at.REFUSAL_STATUS, done.returncode)
        self.assertIn("temp", self.text(done.stderr).lower())
        self.assertNotIn(OUT_TOKEN, self.text(done.stdout))
        self.assertNotIn(ERR_TOKEN, self.text(done.stderr))
        self.assertEqual([], admin_entries(self.repo))


class ExitStatusTest(VerifyAtCase):
    """The command's own status is the tool's, unrounded."""

    def test_every_status_the_command_returns_is_returned(self):
        # 0 and 1 are the statuses a caller acts on; 7 is the one that shows
        # a nonzero status is carried rather than flattened to "failed".
        for status in (0, 1, 7):
            with self.subTest(status=status):
                done = self.verify_at(
                    self.commits["first"],
                    [sys.executable, "emitter.py", str(status)],
                )
                self.assertEqual(status, done.returncode)

    def test_a_command_that_cannot_run_is_a_refusal_not_a_verdict(self):
        done = self.verify_at(self.commits["first"], ["no-such-command-here"])
        self.assertEqual(verify_at.REFUSAL_STATUS, done.returncode)
        self.assertNothingLeftBehind()


class StreamSeparationTest(VerifyAtCase):
    """Neither stream is ever poured into the other."""

    def test_each_token_arrives_only_on_its_own_stream(self):
        done = self.verify_at(self.commits["first"], [sys.executable, "emitter.py"])
        out, err = self.text(done.stdout), self.text(done.stderr)
        self.assertIn(OUT_TOKEN, out)
        self.assertNotIn(ERR_TOKEN, out)
        self.assertIn(ERR_TOKEN, err)
        self.assertNotIn(OUT_TOKEN, err)

    def test_the_tools_own_report_stays_off_the_commands_stdout(self):
        done = self.verify_at(self.commits["first"], [sys.executable, "emitter.py"])
        self.assertEqual(OUT_TOKEN, self.text(done.stdout).strip())
        self.assertIn("verify_at:", self.text(done.stderr))


class CleanupTest(VerifyAtCase):
    """The worktree is removed and pruned on both outcomes."""

    def test_a_green_run_leaves_nothing_behind(self):
        done = self.verify_at(self.commits["first"], [sys.executable, "emitter.py"])
        self.assertEqual(0, done.returncode)
        self.assertNothingLeftBehind()

    def test_a_red_run_that_dirtied_the_checkout_leaves_nothing_behind(self):
        done = self.verify_at(
            self.commits["first"],
            [sys.executable, "emitter.py", "3", "--stray"],
        )
        self.assertEqual(3, done.returncode)
        self.assertNothingLeftBehind()

    def test_a_kept_worktree_is_what_the_cleanup_check_would_catch(self):
        """The can-fail direction: cleanup asserted against a live worktree."""

        done = self.verify_at(
            self.commits["first"], [sys.executable, "emitter.py"], extra=("--keep",)
        )
        self.assertEqual(0, done.returncode)
        with self.assertRaises(AssertionError):
            self.assertNothingLeftBehind()
        kept = sorted(self.root.iterdir())
        self.assertEqual(1, len(kept))
        git(self.repo, "worktree", "remove", "--force", os.fspath(kept[0]))
        git(self.repo, "worktree", "prune")
        self.assertNothingLeftBehind()


class CallerEnvironmentTest(VerifyAtCase):
    """A caller's git seams do not follow the command into the worktree."""

    def test_a_pointed_git_dir_neither_stops_the_run_nor_reaches_the_command(self):
        poisoned = clean_env()
        poisoned["GIT_DIR"] = os.fspath(self.repo / ".git")
        poisoned["GIT_INDEX_FILE"] = os.fspath(self.scratch / "stolen.index")
        done = self.verify_at(
            self.commits["first"], [sys.executable, "env_probe.py"], env=poisoned
        )
        self.assertEqual(0, done.returncode, self.text(done.stderr))
        self.assertEqual("<unset>", self.text(done.stdout).strip())
        self.assertNothingLeftBehind()


if __name__ == "__main__":
    unittest.main()
