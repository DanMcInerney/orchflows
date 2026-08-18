"""Reader-module compatibility-floor regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403
def first_import(source: str) -> tuple:
    """``(module, first name)`` of the earliest import statement, or ``()``."""

    for node in ast.parse(source).body:
        if isinstance(node, ast.ImportFrom):
            return (node.module, node.names[0].name)
        if isinstance(node, ast.Import):
            return (None, node.names[0].name)
    return ()


# The spec's `binding_constraints` list, as things an AST can be asked
# about. `zoneinfo` imports on 3.9 and is forbidden anyway: CPython on
# Windows ships no tz database.
FLOOR_MODULES = ("tomllib", "zoneinfo")
FLOOR_NAMES = {"datetime": ("UTC",), "typing": ("Self",), "itertools": ("batched",)}
FLOOR_NODES = tuple(
    (getattr(ast, attribute), spelling)
    for attribute, spelling in (("Match", "match"), ("TryStar", "except*"))
    if getattr(ast, attribute, None) is not None
)


def evaluated_nodes(tree) -> list:
    """Every node the interpreter actually runs.

    `from __future__ import annotations` makes an annotation a string that
    is never evaluated, so PEP 604 inside one is legal at the floor and a
    detector that flagged it would be reporting a violation that is not one.
    """

    postponed = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            postponed.append(node.annotation)
        elif isinstance(node, ast.arg) and node.annotation is not None:
            postponed.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                postponed.append(node.returns)
    skip = set()
    for annotation in postponed:
        skip.update(id(child) for child in ast.walk(annotation))
    return [node for node in ast.walk(tree) if id(node) not in skip]


def above_the_floor(source: str) -> list:
    """Every construct in `source` that Python 3.9 cannot run.

    Parsing alone proves nothing here: a 3.13 interpreter parses all of
    these happily, and the module has already been imported by the time any
    test runs, so a `SyntaxError` would have failed collection rather than a
    test. What CI's 3.9 leg would refuse has to be asked of the tree.
    """

    found = set()
    for node in evaluated_nodes(ast.parse(source)):
        for kind, spelling in FLOOR_NODES:
            if isinstance(node, kind):
                found.add(spelling)
        if isinstance(node, ast.Import):
            found.update(
                alias.name
                for alias in node.names
                if alias.name.split(".")[0] in FLOOR_MODULES
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] in FLOOR_MODULES:
                found.add(module)
            found.update(
                "{0}.{1}".format(module, alias.name)
                for alias in node.names
                if alias.name in FLOOR_NAMES.get(module, ())
            )
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.attr in FLOOR_NAMES.get(node.value.id, ()):
                found.add("{0}.{1}".format(node.value.id, node.attr))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # `X | None` is the runtime PEP 604 the spec names; `a | None`
            # is not arithmetic anyone writes by accident.
            if any(
                isinstance(side, ast.Constant) and side.value is None
                for side in (node.left, node.right)
            ):
                found.add("X | None")
    return sorted(found)


class TestModuleFloor(unittest.TestCase):
    """Spec `binding_constraints`: the 3.9 floor and mandatory postponed
    annotations."""

    def test_the_module_reaches_for_nothing_above_the_floor(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 9))

        self.assertEqual([], above_the_floor(UI_PY.read_text(encoding="utf-8")))

    def test_the_detector_names_every_import_and_name_the_floor_forbids(self):
        # Every construct here parses on 3.9 and fails at import or call
        # there, which is exactly the class a parse check cannot catch.
        source = (
            "import tomllib\n"
            "from zoneinfo import ZoneInfo\n"
            "from typing import Self\n"
            "import datetime, itertools\n"
            "stamp = datetime.datetime.now(datetime.UTC)\n"
            "pairs = itertools.batched(stamp, 2)\n"
            "fallback = int | None\n"
        )

        self.assertEqual(
            [
                "X | None",
                "datetime.UTC",
                "itertools.batched",
                "tomllib",
                "typing.Self",
                "zoneinfo",
            ],
            above_the_floor(source),
        )

    def test_the_detector_names_the_syntax_the_floor_forbids(self):
        source = "match value:\n    case 1:\n        pass\n"

        if FLOOR_NODES:
            self.assertEqual(["match"], above_the_floor(source))
        else:
            # On the floor interpreter itself the syntax is a `SyntaxError`,
            # which is the same guarantee arrived at sooner.
            self.assertRaises(SyntaxError, ast.parse, source)

    def test_a_postponed_annotation_is_not_a_violation(self):
        # The detector has to be wrong in neither direction: this module's
        # own `X | None` annotations are strings under the mandatory
        # `__future__` import and must not be reported.
        source = (
            "from __future__ import annotations\n"
            "held: int | None = None\n"
            "def read(path: str | None = None) -> dict | None:\n"
            "    return None\n"
        )

        self.assertEqual([], above_the_floor(source))

    def test_future_annotations_is_the_first_import(self):
        self.assertEqual(
            ("__future__", "annotations"), first_import(UI_PY.read_text(encoding="utf-8"))
        )
        # The check discriminates: a module that imports anything first fails it.
        self.assertNotEqual(
            ("__future__", "annotations"),
            first_import("import os\nfrom __future__ import annotations\n"),
        )
