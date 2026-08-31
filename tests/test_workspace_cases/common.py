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
import scripts.tickets_generations as generations  # noqa: E402
import scripts.workspace as workspace  # noqa: E402
import scripts.workspace_git as workspace_git  # noqa: E402  the ticket stamp's writer
import scripts.workspace_record as workspace_record  # noqa: E402  the attempt record
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


def make_ticket(
    run_dir: Path, tid: str, *, scope=("scratch",), extra=(),
    pack="orch-code-pack", isolation="required",
) -> Path:
    """A fixture work item, never this run's own ticket.

    The cutover made an isolated candidate the only lawful Git-adapter
    shape, so the item carries ``isolation: required`` unless a caller is
    grading some other value through ``extra`` or ``isolation``.
    ``isolation=None`` omits the field entirely, for a fixture proving what
    an absent declaration derives from the stamped pack.
    """

    lines = [
        "---",
        f"id: {tid}",
        "run: testrun",
        "status: claimed",
        "executor: orch-execute",
        f"pack: {pack}",
        "depends_on: []",
        "write_scope:",
    ]
    lines += [f"  - {entry}" for entry in scope]
    lines += ["bound: 30m"]
    if not any(key == "isolation" for key, _ in extra) and isolation is not None:
        lines += [f"isolation: {isolation}"]
    lines += [f"{key}: {value}" for key, value in extra]
    if not any(key == "mutations" for key, _ in extra):
        plans = []
        for entry in scope:
            normalized = str(entry).replace("\\", "/").rstrip("/")
            if Path(normalized).is_absolute():
                normalized = Path(normalized).name
            plans.append(f"write:{normalized}/")
        lines += [f"mutations: [{', '.join(plans)}]"]
    lines += [
        "ownership_regions: []",
        "---", "", "## Objective", "", "Fixture ticket.", "",
        "## Fixed inputs", "",
        '- input: {"name":"none","type":"literal","value":null}', "",
        "## Completion test", "",
        "- workspace behavior matches the case oracle | oracle: the case assertion | oracle_class: deterministic | provenance: authored-here", "",
        "## Return fields", "", "status; result; verification; feedback; risks", "",
        "## Result", "", "", "## Verification", "", "",
        "## Feedback", "", "[]", "", "## Risks", "", "[]", "",
    ]
    text = "\n".join(lines)
    text = tickets._set_frontmatter_field(text, "admission", "pending")
    draft = generations.draft_snapshot(tid, {tid: text}, member_ids=[])
    receipt = generations.validate_draft(tid, {tid: text}, draft, member_ids=[])
    text = generations.seal_assignments(
        tid, {tid: text}, draft, receipt, member_ids=[],
    )[tid]
    text = tickets._set_frontmatter_field(text, "dispatch_v1", _live_attempt())
    path = run_dir / f"{tid}.md"
    path.write_text(text, encoding="utf-8")
    return path


def recorded_workspace(ticket_path) -> str:
    """The tree the ticket's attempt records, read through its owner."""

    from scripts import workspace_record

    return workspace_record.attempt_workspace(
        tickets._parse_frontmatter(
            Path(ticket_path).read_text(encoding="utf-8")
        )
    )


def _live_attempt() -> str:
    """One open attempt for the fixture to record its workspace on.

    The established tree is the attempt's (`contracts/dispatch.md`), and the
    dispatch facade opens before it establishes, so a fixture standing in for
    an established item stands one up in that same order. It is operational
    state, excluded from the assignment fingerprint, so it goes on after the
    seal exactly as `dispatch-open` puts it there.
    """

    return json.dumps({
        "protocol": "orchflows.dispatch.v1",
        "attempts": [{
            "assignment_seal": "sha256:" + "0" * 64,
            "dispatch_id": "D1",
            "lease_expires_at": "2099-01-01T00:00:00Z",
            "opened_at": "2026-01-01T00:00:00Z",
            "outcome_record_id": "outcome",
            "owner": "worker",
            "records": [],
            "state": "live",
        }],
    }, separators=(",", ":"), sort_keys=True)


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
    """A ticket of the shared repository, under this test's own id.

    ``isolation=None`` omits the field, for a fixture proving what an
    absent declaration derives from the stamped pack.
    """

    graded = graded_repository()
    stamps = ((workspace.BRANCH_KEY, branch),) if recorded else ()
    make_ticket(
        graded["run_dir"], tid, scope=scope, isolation=isolation,
        extra=stamps + tuple(extra),
    )
    return graded
