"""Removing a temporary tree that holds a repository -- this suite's one owner.

Three modules build throwaway repositories, and every one of them has to
remove its tree the same way, so the way is stated once here rather than
three times.
"""

import shutil
from pathlib import Path


def remove_repo_tree(root):
    """Remove a temporary tree that holds a repository this suite committed in.

    `git commit` writes its loose objects read-only, and Windows refuses to
    unlink a read-only file, so a bare `shutil.rmtree` leaves every such tree
    behind and errors the test that built it -- twelve of them,
    <!-- BEGIN GENERATED CI TOPOLOGY -->on both Windows legs and on none of the other three<!-- END GENERATED CI TOPOLOGY -->. The mode is cleared first and
    the removal stays strict, which is how `scripts/cutcheck.py` removes the
    scratch roots the tool itself owns.

    Strict is the point, not an incidental: `ignore_errors=True` here would
    silence exactly the failure `test_suite_cleanups_do_not_swallow` exists to
    surface. Only for trees that can hold a repository -- everything else this
    suite removes keeps the bare `shutil.rmtree` at its own call site.
    """

    for path in [Path(root)] + sorted(Path(root).rglob("*")):
        try:
            path.chmod(path.stat().st_mode | (0o700 if path.is_dir() else 0o200))
        except OSError:
            pass
    shutil.rmtree(str(root))
