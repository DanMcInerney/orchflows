"""How the cutcheck tests invoke cutcheck: the revision, and the invocation.

Two facts and one owner, because both are properties of the invocation rather
than of either module that makes one: a test module's verdict may not depend
on a sibling test module's state, which is the objection a second copy in a
test module was made to honour and which a shared non-test owner answers
outright.

No module imports it as this is written. Both readers went at 932706a3
(2026-08-26): ``tests/test_canary_host.py`` was deleted outright and
``tests/test_cutcheck.py`` cut to its graph cases, which invoke nothing. The
pinned fixture corpus under ``tests/fixtures/cutcheck/`` pins the same
``BASELINE`` and is orphaned with it. Restore a reader or delete the three
together; do not give this module a new fact to carry so that it has a job.

Not a test module. Nothing here is collected, and the state it does keep -- one
scratch root and one report per graded pair -- is a cache of the tool's own
output, the same value however many modules ask for it.
"""

import atexit
import contextlib
import io
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.cutcheck as cutcheck  # noqa: E402
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner

# cutcheck clones this revision to build the tree it grades oracles in, so
# every clone that runs these tests must be able to reach it. Two invariants
# make a candidate legal, and both are load-bearing: it is an ancestor of
# `main`, so a fresh clone has it (the predecessor pinned an unpushed local
# branch tip, which passed here and failed every CI leg with "cannot clone
# baseline"); and `install.py:101` there opens `SCRIPT_NAMES` without
# `cutcheck.py`, which is what makes the fixtures' `grep -n "cutcheck.py"
# install.py` fail at the baseline and pass at HEAD -- the discrimination the
# family 1 fixtures exist to exercise. Reachability also needs
# `fetch-depth: 0` in .github/workflows/checks.yml; a depth-1 checkout has one
# commit and no ancestor is archivable.
BASELINE = "462ef52aab37655260bdc9f9f98be4ed2601af2d"

# The one scratch root this process's gradings share, and one graded report per
# distinct `(run, baseline)` pair. Lists and dicts rather than rebound names, so
# that a reader importing this module sees the same containers the harness does.
_SHARED_ROOT = []
_GRADED = {}


def shared_root():
    """The one scratch root every in-process grading in this process shares.

    `scripts/cutcheck.py` already caches a clone per `(revision, root)` and
    returns it instantly on the second ask (`_scratch_tree`, the `is_dir`
    early return). What it cannot do is outlive the invocation: `main` mkdtemps
    a root per run and its `finally` removes it, so the same two clones of the
    same two revisions were built and destroyed once per invocation. Holding
    one root for the process makes that two clones per process.

    Placed by the tool's own `_scratch_root`, so where the copies land stays
    the tool's fact rather than a copy of it here -- and so two suites running
    at once get a `mkdtemp` root each and share the directory but never a tree.

    Removed at interpreter exit rather than in a `tearDownModule`: the two
    modules grading through this run one after the other and never at once, so
    a per-module release would re-clone for the second. `atexit` also covers
    the run that died in module setup, where no teardown is reached at all.
    """

    if not _SHARED_ROOT:
        root = cutcheck._scratch_root(ROOT)
        if root is None:
            raise RuntimeError("no scratch root could be placed under {}".format(ROOT))
        _SHARED_ROOT.append(root)
        atexit.register(_release_shared_root)
    return _SHARED_ROOT[0]


def _release_shared_root():
    """Remove the shared root, strictly.

    `remove_repo_tree` and not a bare `rmtree`: every tree under it is a clone
    this suite committed nothing in but git wrote its objects read-only all the
    same, and a swallowing removal here is the failure
    `test_suite_cleanups_do_not_swallow` exists to surface.
    """

    while _SHARED_ROOT:
        remove_repo_tree(_SHARED_ROOT.pop())


def _grade(run, baseline):
    """One `cutcheck.main` run, in this process, against the shared copies.

    The seam is the one `ScratchCleanupReportingTest._main_naming_its_scratch_root`
    already uses: `_scratch_root` wrapped, both streams redirected, the status
    read off `main`'s return value. `_remove_scratch_root` is neutralised for
    the same duration, which is the whole point -- the copies have to outlive
    the run that built them.

    Both patches are scoped to this call and never to the module, so every test
    that grades the real scratch lifecycle -- `ScratchCleanupReportingTest`,
    `ScratchRootPlacementTest` -- reaches the real functions without needing an
    exemption from anything.

    `chdir` to the tree because that is exactly what `cwd=ROOT` did for the
    subprocess this replaces: `_worktree_root` and `_run_dir` both read
    `Path.cwd()`, so where the process stands decides which ticket set resolves.
    """

    root = shared_root()
    for tree in sorted(root.iterdir()):
        # `_scratch_tree` primes this at the clone so that the first span
        # graded is answerable for what it wrote and not for what the checkout
        # arrived carrying. A cached tree skips that priming, and any test that
        # clears `_TREE_STATE` drops it, so it is restored here instead.
        if tree.is_dir() and str(tree) not in cutcheck._TREE_STATE:
            cutcheck._mutations(tree)
    out, err = io.StringIO(), io.StringIO()
    here = Path.cwd()
    os.chdir(str(ROOT))
    try:
        with mock.patch.object(cutcheck, "_scratch_root", lambda _tree: root):
            with mock.patch.object(cutcheck, "_remove_scratch_root", lambda _root: None):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    try:
                        code = cutcheck.main([run, "--baseline", baseline])
                    except SystemExit as exc:
                        # argparse's own usage error, which the process
                        # boundary used to turn into a status by itself.
                        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        os.chdir(str(here))
    return code, out.getvalue(), err.getvalue()


def run_cutcheck(run, baseline=BASELINE):
    """The report for one `(run, baseline)` pair, graded once per process.

    The call sites covered 28 distinct pairs between them and asked for them
    112 times. A report is a value -- a status and two strings -- and no caller
    mutates the tree between two askings or the report after one, so the pair
    is graded once and every later asking is handed its own copy.
    """

    key = (run, baseline)
    if key not in _GRADED:
        _GRADED[key] = _grade(run, baseline)
    code, out, err = _GRADED[key]
    return subprocess.CompletedProcess([run, baseline], code, stdout=out, stderr=err)


def run_cutcheck_subprocess(argv):
    """Cutcheck across a real process boundary, for the claims that need one.

    Argv as the interpreter is handed it, the status as the operating system
    reports it, and stdout separated from stderr by two real pipes: none of
    those is a claim an in-process call can make about itself. Kept for the
    epilog, for one end-to-end grading, and for the cut-time reading, and
    nowhere else -- every other grading goes through `run_cutcheck`, which is
    the same work without the two clones.
    """

    return subprocess.run(
        [sys.executable, "scripts/cutcheck.py"] + list(argv),
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
