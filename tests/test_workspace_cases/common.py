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

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets  # noqa: E402  the grant key's one owner
import scripts.workspace as workspace  # noqa: E402
import scripts.workspace_git as workspace_git  # noqa: E402  the ticket stamp's writer
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
    _GRADED.clear()


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
