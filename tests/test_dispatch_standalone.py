"""`scripts/tickets_dispatch.py` loaded the way the installer leaves it.

The installer copies every ``tickets_*.py`` into one flat directory
(``install.py``'s ``discover_script_names``), so the installed module is
imported with no package and takes the ``else`` half of every one of its
paired imports. That half is never exercised by the rest of the suite,
which imports ``scripts.tickets_dispatch`` -- and a name the ``else`` half
fails to bind is invisible from there until a user runs the subcommand
that needs it.

The flat import runs in a child interpreter whose working directory is the
scripts directory, so it never enters this process's module cache beside
the packaged one: the serial lane classifies that cache as a seam a case
may not leave dirty. The child is asked only what it bound. Nothing here
runs a subcommand, so no sink is reached and no environment is redirected
-- this module owns none of the lane's restoration classes.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

# The probe reports; it never asserts. Every verdict is made below, so a
# probe that dies half-way is a failure carrying its own stderr rather than
# a silent pass.
PROBE = r'''
import ast, builtins, json

import tickets_dispatch as module

tree = ast.parse(open(module.__file__, encoding="utf-8").read())
dispatch = next(
    node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name == "_dispatch"
)
source = open(module.__file__, encoding="utf-8").read()


def bound(node):
    """Every name the function binds for itself."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Load):
            names.add(child.id)
        elif isinstance(child, ast.arg):
            names.add(child.arg)
        elif isinstance(child, ast.alias):
            names.add((child.asname or child.name).split(".")[0])
        elif isinstance(child, ast.ExceptHandler) and child.name:
            names.add(child.name)
    return names


read = {
    child.id for child in ast.walk(dispatch)
    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
}
needed = sorted(read - bound(dispatch) - set(dir(builtins)))
missing = sorted(name for name in needed if not hasattr(module, name))

# Each `if command == '<name>': return <handler>(rest)` arm, by the command
# it answers and the handler text that answers it.
arms = {}
for node in ast.walk(dispatch):
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        continue
    test = node.test
    if (
        isinstance(test.left, ast.Name)
        and test.left.id == "command"
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.comparators[0], ast.Constant)
        and isinstance(test.comparators[0].value, str)
    ):
        arms[test.comparators[0].value] = "\n".join(
            ast.get_source_segment(source, statement) or "" for statement in node.body
        )

table = "GENERATION_SUBCOMMANDS"
print(json.dumps({
    "file": module.__file__,
    "package": module.__package__,
    "needed": needed,
    "missing": missing,
    "commands": sorted(arms),
    "generation_commands": sorted(name for name, body in arms.items() if table in body),
    "generation_keys": sorted(getattr(module, table, {})),
}))
'''


def probe() -> dict:
    """Load the dispatcher without its package and report what it bound."""

    finished = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=str(SCRIPTS),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if finished.returncode != 0:
        raise AssertionError(
            "flat import of tickets_dispatch failed:\n" + finished.stderr
        )
    return json.loads(finished.stdout.splitlines()[-1])


class StandaloneDispatchTest(unittest.TestCase):
    def setUp(self):
        self.report = probe()

    def test_the_flat_import_is_the_one_under_test(self):
        # An empty ``__package__`` is what says the ``else`` half ran. Were
        # a path change ever to make this the packaged import again, every
        # other assertion here would keep passing while testing nothing.
        self.assertEqual("", self.report["package"])
        self.assertEqual(
            (SCRIPTS / "tickets_dispatch.py").resolve(),
            Path(self.report["file"]).resolve(),
        )

    def test_every_name_the_dispatch_table_reads_is_bound_without_a_package(self):
        self.assertNotIn("_cmd_reissue", self.report["needed"])
        self.assertNotIn("reissue", self.report["commands"])
        self.assertIn("_cmd_bound_check", self.report["needed"])
        self.assertIn("_cmd_lint", self.report["needed"])
        self.assertNotIn("errand", self.report["commands"])
        self.assertEqual([], self.report["missing"])

    def test_no_arm_routes_through_a_table_lookup(self):
        # The generation table was the one arm that resolved its handler by
        # subscript rather than by name, so `missing` above could not see it:
        # the flat branch bound it to `{}` when `tickets_generations` was
        # absent, the name resolved, and the lookup still raised. W3a retired
        # `draft-validate` and `seal` as commands and the table with them, and
        # every remaining arm calls a bound name `missing` does grade.
        self.assertEqual([], self.report["generation_commands"])
        self.assertEqual([], self.report["generation_keys"])


if __name__ == "__main__":
    unittest.main()
