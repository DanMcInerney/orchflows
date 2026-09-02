"""What a fresh runner process collects from each active case family.

`tools/run_tests.py` schedules one process per top-level `tests/test*.py` --
unittest discover's own pattern, which no case module matches -- so a case
class runs only where a shard of that name's family reaches it. Four
mechanisms do the reaching and every one of them is skippable in silence: an
explicit `from ... import Name`, an `import *`, an explicit `load_tests`, and
a sibling shard that rebinds `__module__` onto the facade and re-exports.
The aggregators' own docstrings call themselves the complete discovery
target, which states the claim without enforcing it: when this survey was
first run, twelve classes carrying 44 test methods were reachable from
nothing at all.

The answer is measured, never read off import statements: `load_tests`
carries a tuple of module names no import statement names, and a rebinding
shard leaves `__module__` pointing at a file that does not define the class.
So each family shard is imported and asked what its loader builds.

A survey rather than an assertion because its owner runs it in a process of
its own: reaching every family means importing most of the suite at once,
and a case that did that in-process would rewrite the seams every other case
in its own shard shares.
"""

from __future__ import annotations

import ast
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TESTS = ROOT / "tests"
SUFFIX = "_cases"

# Bases, not cases: each is subclassed inside its own package and carries no
# test method of its own, so registering one would collect nothing. Named one
# by one rather than inferred from a count, because a count is a licence --
# it would exempt a real class the day its last test was deleted. The
# exemption test refuses any entry that stops being either half of this.
BASE_ONLY = frozenset({
    "test_cell_linter_cases.pack_cells._IsolatedTree",
    "test_friction_cases.common._IsolatedRepoTestCase",
    "test_friction_cases.storage._ProvenanceTestCase",
    "test_migrate_state_cases.common.MigrationCase",
    "test_state_root_cases.support.SinkFixture",
})


def case_packages():
    """Case packages whose top-level family aggregator is still live."""

    return sorted(
        path
        for path in TESTS.glob("test_*" + SUFFIX)
        if path.is_dir() and (TESTS / (path.name[:-len(SUFFIX)] + ".py")).is_file()
    )


def family(stem, shards):
    """The shards that may serve one case package.

    `tests/test_installer_cases` is served by several of them, so the
    package's own aggregator is where a missing class is reported and never
    the whole set that could have carried it.
    """

    return [name for name in shards if name == stem or name.startswith(stem + "_")]


def collected(module):
    """Every TestCase class the loader reaches through one shard module."""

    found = {
        value for value in vars(module).values()
        if isinstance(value, type) and issubclass(value, unittest.TestCase)
    }
    pending = [unittest.defaultTestLoader.loadTestsFromModule(module)]
    while pending:
        item = pending.pop()
        if isinstance(item, unittest.TestSuite):
            pending.extend(item)
        else:
            found.add(type(item))
    return found


def defined(path, module):
    """The TestCase classes one file defines, whatever `__module__` says.

    The installer shards rebind `__module__` onto their facade so that their
    cases file under one runner seam, which leaves a class's own record of
    where it came from unable to answer this. The file's top-level `class`
    statements can. They also leave out a TestCase built inside a function or
    nested in another class, which is where it belongs: the loader does not
    reach those either.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        value = getattr(module, node.name, None)
        if isinstance(value, type) and issubclass(value, unittest.TestCase):
            yield node.name, value


def survey():
    """Report the case classes no shard of their family collects.

    `exempt` holds only classes the family really does drop, so a complete
    exempt list is this walk's own proof that it can still see one.
    """

    shards = sorted(path.stem for path in TESTS.glob("test*.py"))
    unreachable, exempt, errors, scanned = [], [], [], 0
    for package in case_packages():
        stem = package.name[:-len(SUFFIX)]
        served = set()
        for name in family(stem, shards):
            try:  # a shard nobody can import collects nothing for anybody
                served |= collected(importlib.import_module("tests." + name))
            except Exception as failure:
                errors.append("tests/{0}.py: {1!r}".format(name, failure))
        prefix = "tests." + package.name + "."
        active_modules = sorted(
            (
                name,
                module,
                Path(module.__file__).resolve(),
            )
            for name, module in sys.modules.items()
            if name.startswith(prefix) and getattr(module, "__file__", None)
            and Path(module.__file__).resolve().parent == package.resolve()
        )
        for dotted, module, path in active_modules:
            for name, value in defined(path, module):
                scanned += 1
                if value in served:
                    continue
                record = {
                    "case": "{0}.{1}".format(dotted.removeprefix("tests."), name),
                    "aggregator": "tests/{0}.py".format(stem),
                    "tests": len(unittest.defaultTestLoader.getTestCaseNames(value)),
                }
                (exempt if record["case"] in BASE_ONLY else unreachable).append(record)
    return {
        "unreachable": unreachable, "exempt": exempt,
        "errors": errors, "scanned": scanned,
    }


def survey_in_a_fresh_process():
    """Run `survey` where no other case shares the interpreter."""

    done = subprocess.run(
        [sys.executable, "-m", "tests.test_static_tree_invariants_cases._registration"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    output = done.stdout.decode("utf-8", "replace")
    try:
        return json.loads(output)
    except ValueError:
        raise AssertionError(
            "the registration survey did not report (exit {0}):\n{1}\n{2}".format(
                done.returncode, output, done.stderr.decode("utf-8", "replace"))
        )


if __name__ == "__main__":
    json.dump(survey(), sys.stdout)
