"""Dependency-boundary suite: what this package can reach, enumerated.

Criterion 2 is the one claim that cannot be made by testing behavior, because
its subject is what the code is *able* to do rather than what it did. A run
that never reached a browser proves nothing about whether one is reachable. So
every claim here is made by enumeration, in both directions, and every
enumeration is shown to reject a module beside the tree that breaks it.

Four things are enumerated, and only the first is transcribed by hand:

*The module set.* The core's eleven modules are spelled out, so a new sibling
joins by editing this file or not at all. The adapter modules are not spelled
out — they are derived from ``runner.ADAPTER_IDS`` and checked against what is
on disk, because `test_router` and `test_adapters` already carry two
independent transcriptions of that roster and a third would only be a third
thing to forget.

*The dispatch.* Both literal ``if`` chains are read out of the source and
compared against the declared roster, in order, with the module each branch
reaches. A branch that goes missing, doubles, reorders, or calls the wrong
module is caught here rather than at the first live read.

*The imports.* Every intra-package edge among the core modules, and every
top-level module the package takes from outside itself. The second list is
then resolved against this interpreter's own standard library, so "3.9 stdlib
only" is answered by where the module actually comes from and not by a name
anybody recognized.

*The surfaces that would let it run something instead of read something.*
Dynamic import, computed dispatch, an SDK, a browser driver, a media
downloader, a shell spelling, a non-read verb.

The execution-surface vocabulary is imported from ``test_adapters`` rather
than restated: that suite pins the same names against the one adapter that
takes an argument, this one pins them against the whole package, and two
copies of one list is how the wider claim quietly stops covering something.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import sysconfig
import unittest
from pathlib import Path

from super_research import runner
from tests import helpers
from tests.test_adapters import (
    EXECUTION_MODULES,
    EXECUTION_NAMES,
    WRITE_VERBS,
    code_strings,
)

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "threats"
STDLIB_DIR = Path(sysconfig.get_paths()["stdlib"]).resolve()

# The core this package is, after the runner split. Spelled out because that is
# the point: a module added here joins the package by being added to this
# tuple, and a module added anywhere else fails before it is ever imported.
CORE_MODULES = (
    "__init__",
    "cache",
    "ledger",
    "normalize",
    "ordering",
    "pacing",
    "project",
    "router",
    "runner",
    "schema",
    "transport",
)

# Every edge between them, both directions. `ordering` and `pacing` read the
# core's adapter table back through `runner`, and `runner` re-exports what they
# own, so those two edges are a cycle — declared here rather than discovered by
# a reader, and safe only because each binds the module object after its own
# names exist.
CORE_IMPORT_EDGES = {
    "__init__": (),
    "cache": ("transport",),
    "ledger": ("schema",),
    "normalize": ("adapters", "schema"),
    "ordering": ("adapters", "runner", "schema"),
    "pacing": ("adapters", "cache", "runner", "transport"),
    "project": ("schema",),
    "router": ("adapters", "schema"),
    "runner": (
        "adapters",
        "cache",
        "ledger",
        "normalize",
        "ordering",
        "pacing",
        "router",
        "schema",
        "transport",
    ),
    "schema": (),
    "transport": (),
}

# Everything the package takes from outside itself. Twelve names, and the check
# below resolves each one to where this interpreter actually answers it from.
STANDARD_LIBRARY_IMPORTS = (
    "__future__",
    "collections",
    "dataclasses",
    "datetime",
    "email",
    "hashlib",
    "html",
    "json",
    "time",
    "typing",
    "unicodedata",
    "urllib",
)

# Reaching a module by string is the one mechanism that makes every enumeration
# above unenforceable, so it is refused everywhere, `transport.py` included.
DYNAMIC_IMPORT_MODULES = (
    "importlib",
    "importlib.util",
    "imp",
    "pkgutil",
    "runpy",
    "ctypes",
    "types",
    "inspect",
)

# Builtins that turn a string into code or into a name. `getattr` and its two
# siblings are handled apart: reading a named attribute off a response is not
# dispatch, and computing which one to read is.
COMPUTED_NAMES = ("eval", "exec", "compile", "__import__", "globals", "locals", "vars")
ATTRIBUTE_NAMES = ("getattr", "setattr", "delattr")

# The spec's non-goals, by the name each would be imported under. Checked
# against imports rather than against text: `adapters/__init__.py` says "asked
# for fewer requests" in a warning, and a scan that read prose would call that
# an HTTP client.
THIRD_PARTY_SURFACES = (
    "selenium",
    "playwright",
    "pyppeteer",
    "webdriver",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "bs4",
    "lxml",
    "html5lib",
    "yt_dlp",
    "youtube_dl",
    "googleapiclient",
    "praw",
    "tweepy",
    "instaloader",
    "snscrape",
)

# Strings that could become a command rather than a url.
SHELL_SPELLINGS = ("sh -c", "/bin/", "cmd.exe", "powershell", "javascript:", "data:")


def package_sources():
    return sorted(PACKAGE_DIR.rglob("*.py"))

def parsed(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def absolute_imports(path):
    """Every top-level module one source takes from outside this package."""

    names = set()
    for node in ast.walk(parsed(path)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names.add((node.module or "").split(".")[0])
    return names


def sibling_imports(path):
    """Every module inside this package one source imports, by name."""

    targets = set()
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        if node.module:
            targets.add(node.module.split(".")[0])
        else:
            targets.update(alias.name for alias in node.names)
    return targets


def adapter_modules_imported(path):
    """Which adapter modules one source imports, told apart from the protocol.

    ``from .adapters import`` carries both — the shared protocol's names and
    the adapter modules themselves — and only a file on disk tells them apart.
    """

    names = set()
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.ImportFrom) or node.module != "adapters":
            continue
        for alias in node.names:
            if ADAPTER_DIR.joinpath(alias.name + ".py").exists():
                names.add(alias.name)
    return names


def branch_targets(path, function_name):
    """One literal ``if`` chain, read out: which id reaches which module member.

    Returns ``(adapter_id, module, member)`` in source order. A chain that is
    not literal produces nothing here, which is itself the finding: there is
    no way to write a registry that this reads as branches.
    """

    rows = []
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.FunctionDef) or node.name != function_name:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.If):
                continue
            test = statement.test
            if not isinstance(test, ast.Compare) or not isinstance(test.left, ast.Name):
                continue
            compared = test.comparators[0]
            if test.left.id != "adapter_id" or not isinstance(compared, ast.Constant):
                continue
            answered = statement.body[0].value
            reached = answered.func if isinstance(answered, ast.Call) else answered
            rows.append((compared.value, reached.value.id, reached.attr))
    return tuple(rows)


def outside_the_standard_library(names):
    """Every name this interpreter does not answer out of its own stdlib.

    Resolved rather than recognized. A third-party module answers from
    site-packages and a missing one answers not at all; both are outside, and
    the pair is what "standard library only" means on the 3.9 floor this suite
    runs on.
    """

    outside = []
    for name in sorted(names):
        if name in sys.builtin_module_names:
            continue
        try:
            found = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            found = None
        if found is None:
            outside.append((name, "no module of that name"))
            continue
        origin = found.origin or ""
        if origin in ("built-in", "frozen"):
            continue
        try:
            Path(origin).resolve().relative_to(STDLIB_DIR)
        except ValueError:
            outside.append((name, origin))
    return outside


def imports_naming(paths, modules):
    """Every (source, module) pair where a source imports something it must not."""

    return sorted(
        (path.name, name)
        for path in paths
        for name in modules
        if name in helpers.imported_names(path)
    )


def dynamic_dispatch_findings(paths):
    """Every call that turns a string into code, a name, or an attribute.

    ``getattr(response, "url", "")`` asks for one named attribute and is not
    dispatch; ``getattr(module, "fetch_" + suffix)`` decides at run time which
    code runs and is the whole thing this package refuses. The literal is what
    separates them, so the literal is what this reads.
    """

    found = []
    for path in paths:
        for node in ast.walk(parsed(path)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            named = node.func.id
            if named in COMPUTED_NAMES:
                found.append((path.name, named, node.lineno))
            elif named in ATTRIBUTE_NAMES and not literal_attribute(node):
                found.append((path.name, named, node.lineno))
    return sorted(found)


def literal_attribute(call):
    """Whether an attribute call names its attribute with a spelled-out string."""

    if len(call.args) < 2:
        return False
    return isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str)


def attributes_ending_in(paths, names):
    """Every dotted call one source spells whose last part is a forbidden name."""

    return sorted(
        (path.name, spelled)
        for path in paths
        for spelled in helpers.attribute_names(path)
        for name in names
        if spelled.endswith("." + name)
    )


def strings_spelling(paths, spellings):
    """Every code string that could become a command rather than an address."""

    return sorted(
        (path.name, spelling)
        for path in paths
        for spelling in spellings
        for text in code_strings(path)
        if spelling in text
    )


def non_read_verb_findings(paths):
    """Every module that spells a verb outside ``READ_METHODS`` in its code."""

    return sorted(
        (path.name, verb)
        for path in paths
        for verb in WRITE_VERBS
        if verb in code_strings(path)
    )


class ModuleSetTest(unittest.TestCase):
    """The set of modules the rest of this file quantifies over."""

    def test_the_core_is_exactly_the_modules_this_file_names(self):
        on_disk = tuple(sorted(path.stem for path in PACKAGE_DIR.glob("*.py")))

        self.assertEqual(on_disk, tuple(sorted(CORE_MODULES)))

    def test_the_adapter_modules_on_disk_are_exactly_the_declared_roster(self):
        # Derived from the roster the core declares, not transcribed: an
        # adapter file with no id, and an id with no file, are the same defect
        # read from two ends.
        on_disk = {path.stem for path in ADAPTER_DIR.glob("*.py")} - {"__init__"}

        self.assertEqual(sorted(on_disk), sorted(runner.ADAPTER_IDS))
        self.assertEqual(len(runner.ADAPTER_IDS), 14)


class RunnerDispatchTest(unittest.TestCase):
    """Criterion 2, dispatch half: fourteen literal branches and no other way in."""

    def test_the_core_imports_fake_and_exactly_the_thirteen_live_modules(self):
        imported = adapter_modules_imported(PACKAGE_DIR / "runner.py")

        self.assertEqual(sorted(imported), sorted(runner.ADAPTER_IDS))
        self.assertIn("fake", imported)
        self.assertEqual(len(imported - {"fake"}), 13)

    def test_no_other_core_module_imports_an_adapter_module_at_all(self):
        # One module can call an adapter, so there is one module to read to
        # learn what this core can reach.
        reaching = sorted(
            path.name
            for path in PACKAGE_DIR.glob("*.py")
            if path.name != "runner.py" and adapter_modules_imported(path)
        )

        self.assertEqual(reaching, [])

    def test_both_branch_chains_cover_the_declared_roster_in_its_own_order(self):
        for function_name in ("descriptor_for", "call_adapter"):
            with self.subTest(function=function_name):
                reached = branch_targets(PACKAGE_DIR / "runner.py", function_name)

                self.assertEqual(
                    tuple(adapter_id for adapter_id, _, _ in reached), runner.ADAPTER_IDS
                )

    def test_every_branch_reaches_the_module_its_own_id_names(self):
        # The failure a count cannot see: fourteen branches, one of them
        # returning another adapter's descriptor.
        for function_name, member in (
            ("descriptor_for", "DESCRIPTOR"),
            ("call_adapter", "fetch_native_page"),
        ):
            for adapter_id, module, reached in branch_targets(
                PACKAGE_DIR / "runner.py", function_name
            ):
                with self.subTest(function=function_name, adapter=adapter_id):
                    self.assertEqual(module, adapter_id)
                    self.assertEqual(reached, member)

    def test_every_declared_id_answers_and_an_undeclared_one_is_refused(self):
        for adapter_id in runner.ADAPTER_IDS:
            with self.subTest(adapter=adapter_id):
                self.assertEqual(runner.descriptor_for(adapter_id).adapter_id, adapter_id)

        self.assertIsNone(runner.descriptor_for("no_such_adapter"))
        with self.assertRaises(runner.RunnerError):
            runner.call_adapter("no_such_adapter", None, None)


class IntraPackageImportTest(unittest.TestCase):
    """Criterion 2, edge half: every import inside the package, both directions."""

    def test_every_core_module_imports_exactly_the_siblings_it_declares(self):
        for name in CORE_MODULES:
            with self.subTest(module=name):
                imported = sibling_imports(PACKAGE_DIR / (name + ".py"))

                self.assertEqual(tuple(sorted(imported)), CORE_IMPORT_EDGES[name])

    def test_the_edge_table_covers_the_core_and_nothing_else(self):
        self.assertEqual(sorted(CORE_IMPORT_EDGES), sorted(CORE_MODULES))

    def test_no_core_module_imports_a_module_this_package_does_not_have(self):
        known = set(CORE_MODULES) | {"adapters"}
        unknown = sorted(
            (path.name, target)
            for path in PACKAGE_DIR.glob("*.py")
            for target in sibling_imports(path)
            if target not in known
        )

        self.assertEqual(unknown, [])


class StandardLibraryOnlyTest(unittest.TestCase):
    """Criterion 2, dependency half: nothing outside the 3.9 standard library."""

    def test_the_package_takes_exactly_these_modules_from_outside_itself(self):
        taken = set()
        for path in package_sources():
            taken |= absolute_imports(path)

        self.assertEqual(tuple(sorted(taken)), STANDARD_LIBRARY_IMPORTS)

    def test_every_one_of_them_resolves_inside_this_interpreters_own_stdlib(self):
        self.assertEqual(outside_the_standard_library(STANDARD_LIBRARY_IMPORTS), [])

    def test_the_floor_this_was_resolved_against_is_the_declared_one(self):
        # The resolution above is a fact about the interpreter that ran it, so
        # the interpreter is asserted rather than assumed.
        self.assertEqual(sys.version_info[:2], (3, 9))

    def test_no_module_names_an_sdk_a_driver_or_a_downloader(self):
        self.assertEqual(imports_naming(package_sources(), THIRD_PARTY_SURFACES), [])


class NoRunSomethingSurfaceTest(unittest.TestCase):
    """Criterion 2, execution half: nothing here can run something."""

    def test_no_module_imports_a_dynamic_import_surface(self):
        self.assertEqual(imports_naming(package_sources(), DYNAMIC_IMPORT_MODULES), [])

    def test_no_module_but_transport_imports_an_execution_or_network_surface(self):
        # `transport.py` is excluded for the one reason `test_transport`
        # excludes it: it is the seam that owns the outbound read, and it holds
        # `urllib.request` on everybody's behalf.
        others = [path for path in package_sources() if path.name != "transport.py"]

        self.assertEqual(imports_naming(others, EXECUTION_MODULES), [])

    def test_no_module_calls_a_dynamic_import_or_a_computed_attribute(self):
        self.assertEqual(dynamic_dispatch_findings(package_sources()), [])

    def test_no_module_reaches_a_process_or_a_shell_through_an_attribute(self):
        self.assertEqual(attributes_ending_in(package_sources(), EXECUTION_NAMES), [])

    def test_no_module_spells_a_command(self):
        self.assertEqual(strings_spelling(package_sources(), SHELL_SPELLINGS), [])

    def test_the_only_non_read_verb_the_package_spells_is_transports_one_post(self):
        # Both directions, and the tighter half is the second: PUT, PATCH and
        # DELETE are spelled nowhere at all, and the single POST is in the one
        # module that owns the two closed exceptions to reads-only.
        self.assertEqual(non_read_verb_findings(package_sources()), [("transport.py", "POST")])


class BoundaryOracleCanFailTest(unittest.TestCase):
    """Criterion 4: every scan above is shown to reject, and to accept.

    Both wrong modules are written beside the tree and never imported — the
    scans read them as text. Nothing in the package produces them and nothing
    under test is mutated to obtain them.
    """

    def setUp(self):
        self.registry = FIXTURE_DIR / "registry_runner.py"
        self.write_capable = FIXTURE_DIR / "write_capable_module.py"

    def test_a_core_that_imports_by_string_fails_the_dynamic_import_scan(self):
        self.assertEqual(
            imports_naming([self.registry], DYNAMIC_IMPORT_MODULES),
            [("registry_runner.py", "importlib")],
        )

    def test_a_core_that_dispatches_by_computed_attribute_fails_the_call_scan(self):
        found = dynamic_dispatch_findings([self.registry])

        self.assertEqual([(name, called) for name, called, _ in found], [
            ("registry_runner.py", "getattr")
        ])

    def test_a_registry_offers_the_branch_reader_nothing_to_read(self):
        # The shape the enumeration is against: there is no literal chain here,
        # so `call_adapter` covers no id at all and the roster check fails on
        # an empty tuple rather than on a wrong name.
        reached = branch_targets(self.registry, "call_adapter")

        self.assertEqual(reached, ())
        self.assertNotEqual(reached, runner.ADAPTER_IDS)

    def test_a_module_that_shells_out_fails_the_execution_and_command_scans(self):
        self.assertEqual(
            imports_naming([self.registry], EXECUTION_MODULES),
            [("registry_runner.py", "importlib"), ("registry_runner.py", "subprocess")],
        )
        self.assertEqual(
            strings_spelling([self.registry], SHELL_SPELLINGS),
            [("registry_runner.py", "/bin/"), ("registry_runner.py", "sh -c")],
        )

    def test_a_module_that_imports_a_downloader_fails_the_dependency_scans(self):
        self.assertEqual(
            imports_naming([self.registry], THIRD_PARTY_SURFACES),
            [("registry_runner.py", "yt_dlp")],
        )
        self.assertEqual(
            outside_the_standard_library(absolute_imports(self.registry)),
            [("yt_dlp", "no module of that name")],
        )

    def test_a_module_that_spells_write_verbs_fails_the_verb_scan(self):
        self.assertEqual(
            non_read_verb_findings([self.write_capable]),
            [
                ("write_capable_module.py", "DELETE"),
                ("write_capable_module.py", "PATCH"),
                ("write_capable_module.py", "POST"),
                ("write_capable_module.py", "PUT"),
            ],
        )

    def test_the_same_scans_accept_the_package_that_ships(self):
        sources = package_sources()

        self.assertEqual(imports_naming(sources, DYNAMIC_IMPORT_MODULES), [])
        self.assertEqual(dynamic_dispatch_findings(sources), [])
        self.assertEqual(strings_spelling(sources, SHELL_SPELLINGS), [])
        self.assertEqual(imports_naming(sources, THIRD_PARTY_SURFACES), [])
        self.assertEqual(outside_the_standard_library(STANDARD_LIBRARY_IMPORTS), [])

    def test_nothing_in_the_package_can_reach_either_wrong_module(self):
        named = sorted(
            path.name
            for path in package_sources()
            for wrong in ("registry_runner", "write_capable_module")
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
