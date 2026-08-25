#!/usr/bin/env python3
"""The runner's ``--scope`` branch, which lives here because
``tools/run_tests.py`` stands at the 510-line source ceiling.

Nothing here is a second scheduler: it turns a comma-separated write scope
into the subset of already-discovered modules that ``affected_tests`` says
can observe it, and hands that list back to the one runner. With that it
owns what the invocation admits, because both answer one question -- which
sources is this run deciding over. Every way the branch could quietly
answer a narrower question than the caller asked is a refusal here: an
oracle may return a smaller answer, never a smaller question wearing the
same summary line.
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
    """Refuse a scope a shell split into trailing MODULE arguments.

    ``--scope a b c`` binds ``a`` and leaves ``b c`` as positional modules,
    which the scope selection then overwrites outright. The run decides on
    ``a`` alone and prints OK: measured once at 2 modules and 19 tests where
    the comma spelling ran 22 and surfaced a red. One separator is the whole
    difference, so the spelling is refused rather than interpreted.
    """

    if not (scope and modules):
        return None
    raise SystemExit(
        "run_tests: --scope takes one comma-separated value. %s would run as "
        "MODULE arguments and %s would decide the run alone. Spell it: "
        "--scope %s" % (" ".join(modules), scope, ",".join([scope] + list(modules))))


def admission_paths(scope, modules, default_tests_dir: bool):
    """Return the paths the source-size admission covers, or None for none.

    An empty list is the whole tracked tree. A scoped run is graded over the
    sources it named and no others: a sibling's over-cap file elsewhere on a
    shared branch is not this run's red to carry, and was measured failing
    every unit's scoped oracle regardless of what that unit had changed.
    """

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
    """Whether the revision a selection came from carries one scope path.

    ``None`` from git is "cannot be asked", which is not evidence of absence
    and leaves the resolver's own reading standing. An empty listing is the
    revision answering that it holds no such path, and then "no affected
    module" is a fact about a file nothing ever read rather than about the
    tests -- the shape a sibling measured over two files it had just
    created, one of them its own test module, at exit 0.
    """

    tree = discovery.get("tree")
    if discovery.get("source") != "git" or not tree:
        return True
    listed = affected_tests.git(root, "ls-tree", "--name-only", tree, "--", str(path))
    return listed is None or bool(listed.strip())


def select(scope: str, tests_dir, discovered) -> list:
    """Return the discovered modules a comma-separated scope reaches.

    The resolver answers from the committed revision and the runner
    discovers from disk. Where the two cannot be reconciled the selection is
    a sample of a tree nobody is deciding -- how one revision reported 28
    modules and 1918 tests once and 29 and 1927 the next time -- so the
    selection names the revision it came from and refuses the two readings
    that are silently somebody else's tree.

    Exits 0 when the scope reaches nothing: a scope whose modules all
    resolved away must never fall through to running the whole suite, and
    "no test covers this path" is an answer, not a failure.
    """

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
