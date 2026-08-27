"""The one place that states both rules this package is collected under.

Neither rule lives here: one is `tools/run_tests.py`'s discovery pattern,
the other is `tests.test_run_tests`'s accounting case. Neither file names
the other, and a class can satisfy either one alone -- so the two of them
together were a law no contributor could read off any single file, and four
separate units reached for the same broken workaround before it was
written down. `LAW` is that statement; `report` is the refusal that quotes
it, and `tests.test_run_tests_cases.collection_law` grades the refusal.
"""

from __future__ import annotations

import ast
import unittest
from collections import Counter
from pathlib import Path

LAW = """\
Two rules govern tests/test_installer_cases/**, and this tree now satisfies
one of them while breaking the other.

  Rule 1 -- discovery. tools/run_tests.py schedules one process per
  tests/test*.py and nothing under tests/test_installer_cases/ matches that
  pattern, so a class there reaches the suite only when a shard module --
  one of tests/test_installer*.py -- imports it by class name and then
  rebinds `Klass.__module__ = _facade.__name__`.

  Rule 2 -- accounting. tests/test_run_tests.py holds every `test*` method
  DECLARED under tests/test_installer_cases/ against every method LOADED,
  and requires each to be loaded exactly once, under the class name that
  declares it. An inherited method is counted under the subclass that runs
  it, so a base class satisfies rule 1 through its subclass and breaks
  rule 2 in its own name."""

# One rule can be met without the other, so a fix that assumed a missing
# import would be wrong exactly when the import is already there. Each
# breach carries the fix for its own shape.
_MISSING = """\
DECLARED, NEVER LOADED -- these tests do not run at all:
{rows}
  fix: if this is a case class, import it by name in one
       tests/test_installer*.py shard and rebind its __module__ there.
  fix: if this is a base or mixin that runs through a subclass, rule 2
       counts its methods in its own name, so rename them off the `test`
       prefix (`_check_...`) and call them from the concrete case."""

_STRAY = """\
LOADED, NEVER DECLARED -- rule 2 attributes a `test*` method to the class
that runs it, not to the class that wrote it:
{rows}
  fix: declare the method on the class named above, or drop the `test`
       prefix from the inherited copy so its own name stops claiming it."""

_TWICE = """\
LOADED TWICE -- two shards reach the same class, so every one of its tests
runs twice and any shared state it builds is built twice:
{rows}
  fix: keep the class-name import in exactly one tests/test_installer*.py
       shard."""


def declared_cases(repo_root):
    """Every `test*` method the collected tree's own files declare.

    Read out of the source rather than off the imported classes: a shard
    rebinds `__module__` onto the facade, which leaves a loaded class unable
    to say which file declared it, and an unimported file is not loaded at
    all -- which is the whole failure this is here to see.
    """

    root = Path(repo_root)
    found = []
    for path in sorted((root / "tests").rglob("*.py")):
        if path.name != "test_installer.py" and "test_installer_cases" not in path.parts:
            continue
        where = path.relative_to(root).as_posix()
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.ClassDef):
                continue
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name.startswith("test"):
                    found.append((where, node.name, method.name))
    return found


def loaded_cases(module_names):
    """Every case the shards' own loader builds, with the identity it runs under."""

    stack = list(unittest.TestLoader().loadTestsFromNames(list(module_names)))
    found = []
    while stack:
        item = stack.pop()
        if isinstance(item, unittest.TestSuite):
            stack.extend(item)
        else:
            found.append((item.id(), type(item).__name__, item._testMethodName))
    return found


def _rows(entries):
    return "\n".join("  " + entry for entry in sorted(set(entries)))


def report(declared, loaded):
    """One message for every way the two rules disagree, or "" when they do not."""

    declared = list(declared)
    loaded = list(loaded)
    repeated = Counter(identity for identity, _, _ in loaded)
    written = Counter((name, method) for _, name, method in declared)
    # By identity, not by row: a class two shards reach is one declaration
    # loaded twice, and counting the rows would report it as an extra
    # undeclared method as well -- two diagnoses, one of them false.
    running = Counter(
        {identity: (name, method) for identity, name, method in loaded}.values()
    )
    sections = []

    missing = written - running
    if missing:
        sections.append(_MISSING.format(rows=_rows(
            "{0}::{1}.{2}".format(where, name, method)
            for where, name, method in declared if (name, method) in missing
        )))

    stray = running - written
    if stray:
        sections.append(_STRAY.format(rows=_rows(
            identity for identity, name, method in loaded
            if (name, method) in stray
        )))

    twice = [identity for identity, count in repeated.items() if count > 1]
    if twice:
        sections.append(_TWICE.format(rows=_rows(
            "{0} (loaded {1} times)".format(identity, repeated[identity])
            for identity in twice
        )))

    return "\n\n".join([LAW] + sections) if sections else ""
