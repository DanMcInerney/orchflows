#!/usr/bin/env python3
"""The runner's ``--scope`` branch, which lives here because
``tools/run_tests.py`` already fills one-read size on its own.

Nothing here is a second scheduler: it turns a comma-separated write scope
into the subset of already-discovered modules that ``affected_tests`` says
can observe it. With that it owns what the invocation admits, because both
answer one question -- which sources is this run deciding over. An oracle
may return a smaller answer, never a smaller question wearing the same
summary line.
"""

from __future__ import annotations

from pathlib import Path

try:  # imported as ``tools.run_tests_scope`` with the repository on sys.path
    from tools import affected_tests
except ImportError:  # run as ``python tools/run_tests.py``, tools/ on sys.path
    import affected_tests


def paths(scope: str) -> list:
    """Return the non-empty paths one comma-separated ``--scope`` names."""

    parts = [part.strip() for part in scope.split(",") if part.strip()]
    if not parts:
        raise SystemExit("run_tests: --scope needs at least one path")
    return parts


def refuse_positional(scope, modules) -> None:
    """Refuse a scope a shell split into trailing MODULE arguments."""

    if not (scope and modules):
        return None
    raise SystemExit(
        "run_tests: --scope takes one comma-separated value. %s would run as "
        "MODULE arguments and %s would decide the run alone. Spell it: "
        "--scope %s" % (" ".join(modules), scope, ",".join([scope] + list(modules))))


def size_report_paths(scope, modules, default_tests_dir: bool):
    """Return the paths the source-size report covers, or None for none."""

    if not default_tests_dir:
        return None
    if scope:
        return paths(scope)
    return None if modules else []


def named_shard(rel, discovered):
    """The discovered shard module one scope path names outright, or None."""

    text = str(rel).replace("\\", "/").rstrip("/")
    if not text.endswith(".py"):
        return None
    stem = text.rsplit("/", 1)[-1][:-3]
    if not stem.startswith("test"):
        return None
    for name in discovered:
        if name.split(".")[-1] == stem:
            return name
    return None


def carries(root, discovery, path) -> bool:
    """Whether the revision a selection came from carries one scope path."""

    tree = discovery.get("tree")
    if discovery.get("source") != "git" or not tree:
        return True
    listed = affected_tests.git(root, "ls-tree", "--name-only", tree, "--", str(path))
    return listed is None or bool(listed.strip())


def select(scope: str, tests_dir, discovered) -> list:
    """Return the discovered modules a comma-separated scope reaches."""

    tests_dir = Path(tests_dir)
    root = tests_dir.parent
    scoped = paths(scope)
    resolved = affected_tests.affected(scoped, root=root, tests_dir=tests_dir)
    discovery = resolved["discovery"]
    if discovery["source"] != "git" and (root / ".git").exists():
        raise SystemExit(
            "run_tests: --scope resolved off the working tree inside a git "
            "checkout, so the selection is not this revision's and would "
            "carry every half-written file beside it; re-run where git can "
            "read HEAD rather than deciding on a sampled tree")
    print("scope: %d paths, selection from %s %s"
          % (len(scoped), discovery["source"], discovery["tree"] or "-"))
    for entry in resolved["unreadable"]:
        print("run_tests: unreadable test file %s (%s)" % (entry["path"], entry["reason"]))
    unseen = [path for path in resolved["no_tests"]
              if named_shard(path, discovered) or not carries(root, discovery, path)]
    if unseen:
        raise SystemExit(
            "run_tests: this revision does not carry %s, so the selection "
            "never read it and \"no affected module\" would be an answer "
            "about the resolver rather than about the tests -- for a test "
            "module, a green having run none of it; commit before scoping it"
            % ", ".join(unseen))
    for path in resolved["no_tests"]:
        print("run_tests: no affected module for " + path)
    selected = [name for name in resolved["modules"] if name in discovered]
    if not selected:
        raise SystemExit(0)
    return selected
def shard(selector, ordered: list) -> list:
    """Return the ``K-of-N`` slice of an already-scheduled order, or all of it."""

    if not selector:
        return ordered
    parts = str(selector).split("-of-")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise SystemExit("run_tests: --shard wants K-of-N, for example 2-of-3")
    index, count = int(parts[0]), int(parts[1])
    if count < 1 or not 1 <= index <= count:
        raise SystemExit("run_tests: --shard %s names no shard of %d" % (selector, count))
    return ordered[index - 1::count]
