"""Resolve repository and run state used by cutcheck."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
COMMAND_TIMEOUT = _contract.COMMAND_TIMEOUT
Path = _contract.Path
_UNREAD = _contract._UNREAD
state_root = _contract.state_root
subprocess = _contract.subprocess

def _unread(what):
    """Record a reading that did not happen, and what could not be read.

    The defect this closes is one value standing for two answers. ``None``
    meant both "this oracle discriminates" and "no half of it could be
    read"; ``[]`` meant both "this span wrote nothing" and "the status that
    would have said so failed"; and a caller cannot tell a grading that
    happened from one that did not. Every such site names itself here.
    """

    if what not in _UNREAD:
        _UNREAD.append(what)


def _git(args, cwd):
    try:
        return subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _worktree_root():
    proc = _git(["rev-parse", "--show-toplevel"], Path.cwd())
    if proc is None or proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def _run_dir(run, worktree_root):
    """Locate the issued ticket set for ``run``.

    Run tickets resolve in the one user-scope state sink
    (``scripts/state_root.py``), so a run is checkable from any workspace in
    any repository. Canary tickets resolve at the main checkout instead: the
    canary is a git-tracked golden fixture, not run state. Fixture sets
    resolve at the invoking worktree's own top level for the same reason, and
    every frontier item carries its own copy in its own worktree.
    """

    candidates = [state_root.tickets_root() / run]
    main_root = state_root.find_repo_root(Path.cwd())
    if main_root is not None:
        candidates.append(main_root / ".orch" / "canary" / "tickets" / run)
    if worktree_root is not None:
        candidates.append(worktree_root / "tests" / "fixtures" / "cutcheck" / run)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None

__all__ = (
    '_unread', '_git', '_worktree_root', '_run_dir',
)
