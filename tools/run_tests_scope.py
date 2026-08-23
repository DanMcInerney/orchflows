#!/usr/bin/env python3
"""The runner's ``--scope`` branch, which lives here because
``tools/run_tests.py`` stands at the 510-line source ceiling.

Nothing here is a second scheduler: it turns a comma-separated write scope
into the subset of already-discovered modules that ``affected_tests`` says
can observe it, and hands that list back to the one runner.
"""

from __future__ import annotations

from pathlib import Path

try:  # imported as ``tools.run_tests_scope`` with the repository on sys.path
    from tools import affected_tests
except ImportError:  # run as ``python tools/run_tests.py``, tools/ on sys.path
    import affected_tests


def select(scope: str, tests_dir, discovered) -> list:
    """Return the discovered modules a comma-separated scope reaches.

    Exits 0 when the scope reaches nothing: a scope whose modules all
    resolved away must never fall through to running the whole suite, and
    "no test covers this path" is an answer, not a failure.
    """

    tests_dir = Path(tests_dir)
    paths = [part.strip() for part in scope.split(",") if part.strip()]
    if not paths:
        raise SystemExit("run_tests: --scope needs at least one path")
    resolved = affected_tests.affected(paths, root=tests_dir.parent, tests_dir=tests_dir)
    for entry in resolved["unreadable"]:
        print("run_tests: unreadable test file %s (%s)" % (entry["path"], entry["reason"]))
    for path in resolved["no_tests"]:
        print("run_tests: no affected module for " + path)
    selected = [name for name in resolved["modules"] if name in discovered]
    if not selected:
        raise SystemExit(0)
    return selected
