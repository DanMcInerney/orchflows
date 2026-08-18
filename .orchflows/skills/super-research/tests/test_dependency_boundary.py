"""Dependency-boundary suite: what this package can reach, enumerated.

Criterion 2 is the one claim that cannot be made by testing behavior, because
its subject is what the code is *able* to do rather than what it did. A run
that never reached a browser proves nothing about whether one is reachable. So
every claim here is made by enumeration, in both directions, and every
enumeration is shown to reject a module beside the tree that breaks it.

Four things are enumerated, and only the first is transcribed by hand:

*The module set.* The core's seventeen modules are spelled out, so a new sibling
joins by editing this file or not at all. The count is in the sentence and in
`CORE_MODULES`, and a test below compares them: this docstring said eleven for
three modules longer than it was true. The adapter modules are not spelled
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
Which modules may spell a route and which may open a socket come from
``test_transport`` for the same reason, and they are two declarations rather
than one because admitting a module to the route table is not admitting it to
the network.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
import sysconfig
import unittest
from pathlib import Path

from super_research import runner, transport
from super_research.adapters import youtube_innertube
from tests import helpers, test_keyless
from tests.test_adapters import (
    EXECUTION_MODULES,
    EXECUTION_NAMES,
    WRITE_VERBS,
    code_strings,
)
from tests.test_keyless import roster_manifest
from tests.test_transport import NETWORK_SEAM_MODULES, ROUTE_OWNING_MODULES

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "threats"
STDLIB_DIR = Path(sysconfig.get_paths()["stdlib"]).resolve()
# Where this interpreter answers a standard-library import from. `Lib/` on
# every platform, and on Windows also `DLLs/` beside it, which is where the
# CPython installer puts the compiled modules (`unicodedata.pyd` among them):
# a name answered from there is as much the stdlib's as one answered from
# `Lib/`, and it was reported as outside on every Windows host until 2026-08-17.
STDLIB_ROOTS = (STDLIB_DIR, (Path(sys.base_prefix) / "DLLs").resolve())

# The core this package is, after the runner split. Spelled out because that is
# the point: a module added here joins the package by being added to this
# tuple, and a module added anywhere else fails before it is ever imported.
CORE_MODULES = (
    "__init__",
    "cache",
    "cli",
    "coverage",
    "ledger",
    "normalize",
    "ordering",
    "pacing",
    "probes",
    "project",
    "relevance",
    "router",
    "routes",
    "runner",
    "schema",
    "smoke",
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
    "cli": ("probes", "runner", "smoke", "transport"),
    "coverage": ("runner", "schema"),
    "ledger": ("schema",),
    "normalize": ("adapters", "schema"),
    "ordering": ("adapters", "runner", "schema"),
    "pacing": ("adapters", "cache", "runner", "transport"),
    "probes": ("transport",),
    "project": ("schema",),
    "relevance": ("schema",),
    "router": ("adapters", "schema"),
    "routes": (),
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
    "smoke": ("probes", "runner", "schema", "transport"),
    "transport": ("routes",),
}

# Everything the package takes from outside itself, and the check below
# resolves each one to where this interpreter actually answers it from. The
# tuple is the count; a number in this line would be a second statement of
# what is spelled out beneath it, and nothing would read it.
# `concurrent` and `threading` joined on 2026-08-17 with the fused
# lanes; `test_pipeline.CONCURRENCY_OWNERS` names the modules that may import
# them.
STANDARD_LIBRARY_IMPORTS = (
    "__future__",
    "argparse",
    "collections",
    "concurrent",
    "dataclasses",
    "datetime",
    "email",
    "hashlib",
    "html",
    "json",
    "pathlib",
    "tempfile",
    "threading",
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
        resolved = Path(origin).resolve()
        if any(_inside(resolved, root) for root in STDLIB_ROOTS):
            continue
        outside.append((name, origin))
    return outside


def _inside(path, root):
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


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
        self.assertEqual(len(runner.ADAPTER_IDS), 20)


class RunnerDispatchTest(unittest.TestCase):
    """Criterion 2, dispatch half: twenty literal branches and no other way in."""

    def test_the_core_imports_fake_and_exactly_the_live_modules(self):
        imported = adapter_modules_imported(PACKAGE_DIR / "runner.py")

        self.assertEqual(sorted(imported), sorted(runner.ADAPTER_IDS))
        self.assertIn("fake", imported)
        self.assertEqual(len(imported - {"fake"}), 19)

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
        # The failure a count cannot see: every branch the roster declares, one
        # of them returning another adapter's descriptor.
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

    def test_no_module_outside_the_declared_seam_imports_an_execution_surface(self):
        # The exclusion stands for the one reason it always did — the seam owns
        # the outbound read and holds `urllib.request` on everybody's behalf —
        # and is read off the seam declaration rather than a filename, so a
        # module admitted to the route table is still scanned here.
        seam = {PACKAGE_DIR / (name + ".py") for name in NETWORK_SEAM_MODULES}
        others = [path for path in package_sources() if path not in seam]

        self.assertEqual(imports_naming(others, EXECUTION_MODULES), [])

    def test_no_module_calls_a_dynamic_import_or_a_computed_attribute(self):
        self.assertEqual(dynamic_dispatch_findings(package_sources()), [])

    def test_no_module_reaches_a_process_or_a_shell_through_an_attribute(self):
        self.assertEqual(attributes_ending_in(package_sources(), EXECUTION_NAMES), [])

    def test_no_module_spells_a_command(self):
        self.assertEqual(strings_spelling(package_sources(), SHELL_SPELLINGS), [])

    def test_the_only_non_read_verb_the_package_spells_is_a_declared_post(self):
        # Both directions, and the tighter half is the second: PUT, PATCH and
        # DELETE are spelled nowhere at all, and POST nowhere but where one of
        # the two closed exceptions to reads-only lives — the seam, which
        # admits the method, and the route owners, which spell it on the two
        # rows that carry it. Derived from those two declarations, so which
        # module holds the table is something to declare and never a filename
        # this assertion has to be told about.
        spelling_post = sorted(set(ROUTE_OWNING_MODULES) | set(NETWORK_SEAM_MODULES))

        self.assertEqual(
            non_read_verb_findings(package_sources()),
            [(name + ".py", "POST") for name in spelling_post],
        )


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


PROTOCOL_PATH = Path(__file__).resolve().parent.parent / "references" / "protocol.md"

# The loss tables in `protocol.md`, named by the header row each carries — a
# count of them here would be one more sentence nothing reads, and the two that
# stood in this file already disagreed with each other.
# Only tables with this shape are read; every other table in that file belongs
# to someone else.
LOSS_TABLE_HEADERS = ("| code | means | named by |",)

# A code the tables may name that the source is expected not to contain at all.
# Both are vocabulary the spec added for routes that are deferred, so their
# absence is the statement rather than a gap — but it is a statement, so it is
# checked in that direction too.
UNSHIPPED_CODES = ("archive_lag", "scope_required")

# Modules that declare a loss code as a constant and never load it, which is a
# claim rather than an oversight and is therefore pinned in that direction too.
# `reddit_feed`, `rss_atom`, `public_page` and `github_rest` declare
# `AUTH_REQUIRED` and load it nowhere because no status a documented-keyless
# route can answer with is a report that a credential was needed; `transport`
# and `cache` each own a code for the module that attaches it. A name with zero
# loads is only checkable from outside the module if something checks it.
DECLARED_NEVER_LOADED = {
    "auth_required": ("github_rest", "public_page", "reddit_feed", "rss_atom"),
    "rate_limited": ("transport",),
    "cache_hit": ("cache",),
    "unreachable": ("transport",),
}


def module_name(path):
    """What `protocol.md` calls this module: an adapter by its id, else its stem."""

    return "adapters" if path.name == "__init__.py" and path.parent == ADAPTER_DIR else path.stem


def loss_table_rows():
    """Every row of the loss tables, as (code, cell) pairs in document order.

    Parsed rather than transcribed: the point of the exercise is that the table
    a reader reads is the one the assertions run against, so a cell nobody
    re-read after an adapter edit is a red test.
    """

    rows = []
    inside = False
    for line in PROTOCOL_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped in LOSS_TABLE_HEADERS:
            inside = True
            continue
        if inside:
            if not stripped.startswith("|"):
                inside = False
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if set(cells[0]) <= set("- "):
                continue
            rows.append((backticked(cells[0]), cells[-1]))
    return rows


def backticked(text):
    """Every ``name`` in one cell, dotted names cut back to the module they name."""

    found = []
    for index, piece in enumerate(text.split("`")):
        if index % 2 and piece:
            found.append(piece.split(".")[0])
    return tuple(found)


def declared_loss_constants(codes):
    """Package-wide: constant name -> loss code, from module-level ``NAME = "code"``."""

    named = {}
    for path in package_sources():
        for node in parsed(path).body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
                continue
            if node.value.value in codes and len(node.targets) == 1:
                if isinstance(node.targets[0], ast.Name):
                    named[node.targets[0].id] = node.value.value
    return named


def names_a_loss_code(path, codes, constants):
    """Which of ``codes`` this module's executable syntax spells, and which it only declares.

    A declaration is exactly ``NAME = "code"`` at module level, so a literal
    inside a ``DESCRIPTOR = AdapterDescriptor(standing_loss=(...))`` call is an
    emission and not a declaration. Everything else that reaches the code counts:
    a bare literal, a load of a constant this package bound to it, or an
    attribute load of one another module owns.
    """

    tree = parsed(path)
    declarations = {
        id(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and node.value.value in codes
    }
    spelled = set()
    declared = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value in codes:
            (declared if id(node) in declarations else spelled).add(node.value)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if constants.get(node.id) in codes:
                spelled.add(constants[node.id])
        elif isinstance(node, ast.Attribute) and constants.get(node.attr) in codes:
            spelled.add(constants[node.attr])
    return (spelled, declared - spelled)


def loss_code_spelling(codes):
    """code -> the modules that spell it, and code -> the modules that only declare it."""

    constants = declared_loss_constants(codes)
    spelling = {code: set() for code in codes}
    declaring = {code: set() for code in codes}
    for path in package_sources():
        spelled, declared_only = names_a_loss_code(path, codes, constants)
        for code in spelled:
            spelling[code].add(module_name(path))
        for code in declared_only:
            declaring[code].add(module_name(path))
    return (spelling, declaring)


# Number words a heading or a docstring in this delivery may count in. The
# checks below read it: the shortfall heading in `protocol.md`, this file's own
# module count, what the reference documents state about the roster, and what
# `test_keyless` states about `auth_required`. It runs at least as far as the
# roster is wide, because the widest of those counts adapters — a table that
# stopped short would read a lawful count as an unspellable one.
NUMBER_WORDS = (
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
    "Eighteen", "Nineteen", "Twenty",
)

# The tens, for the counts this delivery states past the flat table's end: the
# roster's route-surface total, and the count of it that is read. A tens name
# means its own position in tens, and a compound is its two names read the same
# way — `forty-two` is `forty` and `two`, chosen as the example because nothing
# in this delivery counts it and so nothing can make this line false.
TENS_WORDS = ("Ten", "Twenty", "Thirty", "Forty", "Fifty")


ITEM_DIR = Path(__file__).resolve().parent.parent
OWNER_SKILL = ITEM_DIR / "SKILL.md"
HOST_MIRROR = ITEM_DIR.parent.parent.parent / ".claude" / "skills" / "super-research" / "SKILL.md"

# `rules/composition.md` §5. Restated rather than imported because
# `tools/validate.py`, which enforces it for every library skill, does not read
# `.orchflows/` at all: a project-scope item's frontmatter has no other oracle.
DESCRIPTION_BUDGET = 140


def frontmatter_description(path):
    """One skill's ``description:`` field, read out of its frontmatter alone.

    The block, not the file: the mirror's body is prose *about* the include, and
    a sentence there beginning with the word would otherwise answer for a field
    the frontmatter had lost.
    """

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return None


class ThisSuiteCountsItsOwnModuleSetTest(unittest.TestCase):
    """The module count in this file's docstring, against the tuple it describes.

    It said eleven over fourteen entries: `ledger`, `ordering` and `pacing`
    joined the core and the sentence above them did not. A count in prose beside
    a list is the cheapest thing in a repository to leave behind, and this file
    exists to enumerate — so its own enumeration is counted too.
    """

    def test_the_docstring_names_the_number_of_core_modules_there_are(self):
        counted = NUMBER_WORDS[len(CORE_MODULES) - 1].lower()

        self.assertIn("core's " + counted + " modules", __doc__)


class TheHostMirrorResolvesFromAnyCheckoutTest(unittest.TestCase):
    """The Claude adapter mirror's include lands on the owner, wherever the clone is.

    The stub is hand-written and committed — `install.py --project` writes no
    `.claude` — so an absolute path in it is a path to one machine's filesystem
    and resolves nowhere else: another user, another OS, another repository
    name, and nowhere at all at a revision built in a worktree. It carried one,
    plus ten lines apologizing for it. `scopes.md` now asks a project stub for a
    path relative to itself, and this is the check that the path it carries
    actually reaches the owner from where the stub sits.

    Whether a Claude host expands a relative `@` in a project stub was not
    settled by any ablation this item could run, so the stub carries one line
    under the include naming the owner in plain words. That line is a second
    place a machine-specific path could arrive, which is why absoluteness is
    checked over the whole stub and not over the include alone.

    Skipped rather than failed when the pair is not where a project-scope item
    puts them, because the item can be read from a copy and this suite's
    reliability bar is that it passes offline from anywhere.
    """

    def setUp(self):
        if not HOST_MIRROR.exists():
            self.skipTest("no project-scope host mirror beside this item")

    def test_the_include_is_relative_and_reaches_the_owner(self):
        include = [
            line
            for line in HOST_MIRROR.read_text(encoding="utf-8").splitlines()
            if line.startswith("@")
        ]

        self.assertEqual(len(include), 1)
        target = include[0][1:].strip()
        self.assertFalse(target.startswith("/"), "a committed stub names one machine")
        self.assertFalse(target[1:2] == ":", "a committed stub names one machine")
        # Resolved the way a host resolves it: against the stub's own directory.
        self.assertEqual((HOST_MIRROR.parent / target).resolve(), OWNER_SKILL)

    def test_no_line_of_the_stub_names_one_machine(self):
        # The include is not the only place a path can arrive: the line under it
        # names the owner for a host that did not expand the include, and a path
        # spelled from a root would be the same defect wearing prose.
        body = HOST_MIRROR.read_text(encoding="utf-8")

        for token in body.replace("`", " ").split():
            with self.subTest(token=token):
                self.assertFalse(token.lstrip("@").startswith("/"))
                self.assertNotRegex(token.lstrip("@"), r"^[A-Za-z]:[\\/]")

    def test_the_stub_names_the_owner_for_a_host_that_did_not_expand(self):
        # The one thing the fallback line has to carry, and the reason it is a
        # line rather than a paragraph: where to read instead.
        body = HOST_MIRROR.read_text(encoding="utf-8")
        after_include = body.split("\n@", 1)[1].split("\n", 1)[1]

        self.assertIn(".orchflows/skills/super-research/SKILL.md", after_include)

    def test_the_owner_and_the_mirror_describe_the_item_with_one_string(self):
        # A Claude host routes on the mirror's copy and never reads the owner's,
        # so drift here costs the item every invocation while both files still
        # read correctly on their own — the one failure nobody thinks to check.
        # Nothing else pins the pair: the assertion above is about the include,
        # and `tools/validate.py` does not walk this tree.
        owner = frontmatter_description(OWNER_SKILL)

        self.assertIsNotNone(owner, "the owner's frontmatter names no description")
        self.assertEqual(frontmatter_description(HOST_MIRROR), owner)
        self.assertLessEqual(len(owner), DESCRIPTION_BUDGET)


class LossVocabularyIsReadOffTheSourceTest(unittest.TestCase):
    """`protocol.md`'s loss tables, checked against the package's own syntax.

    Every other enumeration in this suite is pinned and these were not, so
    they drifted the way an unpinned table does: `http_status` was documented
    with three emitters and had thirteen, `schema_drift` five against ten,
    `malformed_json` three against nine. The root cause is not arithmetic. The
    same code is spelled two ways — a module-level constant in some files, a
    bare literal in others — so no one search finds both halves, and a reader
    correcting the table by grep would have corrected it wrong.

    This is what `THREAT_REMAP` gets and for the same reason. The table stays in
    the document, where a reader meets it; the assertion runs against the
    document, so it cannot be corrected in one place and left in the other.
    """

    def setUp(self):
        self.rows = loss_table_rows()
        self.codes = tuple(code for names, _ in self.rows for code in names)
        self.spelling, self.declaring = loss_code_spelling(set(self.codes))

    def test_the_tables_were_found_and_every_row_names_one_code(self):
        # If the parse silently found nothing, every assertion below passes
        # while checking no table at all.
        self.assertGreaterEqual(len(self.rows), 20)
        for names, _ in self.rows:
            self.assertEqual(len(names), 1, "a loss row names {0} codes".format(len(names)))
        self.assertEqual(len(set(self.codes)), len(self.codes), "a code is tabled twice")

    def test_each_row_names_exactly_the_modules_that_spell_its_code(self):
        for names, cell in self.rows:
            code = names[0]
            with self.subTest(code=code):
                documented = set(backticked(cell)) - {code}
                self.assertEqual(
                    documented,
                    self.spelling[code],
                    "protocol.md says {0} is named by {1}; the source says {2}".format(
                        code, sorted(documented), sorted(self.spelling[code])
                    ),
                )

    def test_a_code_the_tables_call_absent_is_absent(self):
        for code in UNSHIPPED_CODES:
            with self.subTest(code=code):
                self.assertIn(code, self.codes, "protocol.md stopped naming " + code)
                self.assertEqual(self.spelling[code], set())
                self.assertEqual(self.declaring[code], set())

    def test_a_constant_declared_and_never_loaded_stays_that_way(self):
        # The other direction, and the one that makes "a name with zero loads is
        # checkable from outside the module" worth writing down.
        for code, modules in sorted(DECLARED_NEVER_LOADED.items()):
            with self.subTest(code=code):
                self.assertEqual(self.declaring[code], set(modules))

    def test_every_module_a_cell_names_is_a_module(self):
        # The cells are parsed by taking their backticked tokens, so a term of
        # art in backticks would read as a module and quietly widen a row. This
        # is the rule that keeps the parse honest, stated where it is relied on.
        known = {module_name(path) for path in package_sources()}

        for names, cell in self.rows:
            for token in backticked(cell):
                with self.subTest(code=names[0], token=token):
                    self.assertIn(token, known | set(self.codes))

    def test_the_scan_tells_a_declaration_from_an_emission(self):
        # The oracle can fail: a module that only binds the name is not named by
        # the table, and one that loads it is. Both directions on one code, so a
        # scan that collapsed them would be caught here rather than by silently
        # widening every row above.
        constants = declared_loss_constants({"auth_required", "schema_drift"})
        declared = ADAPTER_DIR / "reddit_feed.py"
        emitting = ADAPTER_DIR / "web_search.py"

        self.assertIn("auth_required", names_a_loss_code(declared, {"auth_required"}, constants)[1])
        self.assertEqual(names_a_loss_code(declared, {"auth_required"}, constants)[0], set())
        self.assertIn("schema_drift", names_a_loss_code(emitting, {"schema_drift"}, constants)[0])
        self.assertEqual(names_a_loss_code(emitting, {"schema_drift"}, constants)[1], set())


OPERATING_PATH = Path(__file__).resolve().parent.parent / "references" / "operating.md"

# The phrase both documents count the multi-surface adapters with, and the
# whole of what this reads them by. An anchor rather than either sentence: the
# two paragraphs are written in different voices and are meant to stay that
# way, so a pin that matched the prose around the number would forbid the
# rewrite it is supposed to permit.
MULTI_SURFACE_ANCHOR = re.compile(r"\b([A-Za-z]+) adapters rea(?:d|ch) more than one\b")

# The other two counts that one roster sentence states. Anchored the same way and
# for the same reason: "seven" went stale for three adapters while a reader was
# the only thing checking it, and these two were still that reader's. Each phrase
# is the part of the sentence the count cannot leave, not the sentence.
ROSTER_SIZE_ANCHOR = re.compile(r"\b([A-Za-z]+) adapters, ([A-Za-z]+) live plus `fake`")
SURFACE_TOTAL_ANCHOR = re.compile(r"\b([A-Za-z]+(?:-[A-Za-z]+)?) route surfaces\b")

# The same paragraph states that total a second time, two lines down, and
# derives a count from it: "Thirty-five of the thirty-six are read". The anchor
# above reaches neither, because the phrase it pins on is `route surfaces` and
# this sentence does not spell it — so the paragraph stated the total twice and
# one statement was checked, which is the drift this suite exists to stop
# living inside the paragraph the pin reads. This is the second statement's own
# anchor: the phrase its two counts cannot leave, whitespace-tolerant because
# the document wraps between them.
READ_SURFACE_ANCHOR = re.compile(
    r"\b([A-Za-z]+(?:-[A-Za-z]+)?)\s+of\s+the\s+([A-Za-z]+(?:-[A-Za-z]+)?)\s+are\s+read\b"
)

# The same count where `surface_descriptors` states it about itself. Its own
# paragraph rather than either document's, so its own anchor: the two words the
# count cannot leave while the sentence still says that some adapters are the
# exception. A word this cannot read counts as none and fails, the way the
# document anchors do.
RESOLVER_COUNT_ANCHOR = re.compile(r"\b([A-Za-z]+) do not\b")

# The two counts `test_keyless`' module docstring states about `auth_required`:
# how many adapters name the code at all, and how many of those can say it.
# It counted once, and the one number was wrong in both directions — the same
# class as the roster's "seven", one file over, and the loss tables beside it
# already read which modules spell each code. One anchor each, on the phrase
# the count cannot leave rather than on the sentence, because that paragraph is
# written in its own voice and is meant to stay that way.
# Whitespace-tolerant for the reason the read-surface anchor is: a paragraph
# wraps where its width puts it, and a pin that forbade a wrap point would be
# pinning the layout rather than the count.
KEYLESS_NAMING_ANCHOR = re.compile(r"\b([A-Za-z]+)\s+adapters\s+name\s+it\b")
KEYLESS_SAYING_ANCHOR = re.compile(r"\b([A-Za-z]+)\s+of\s+them\s+can\s+say\s+it\b")

# The one roster row read cell by cell here. Its adapter id comes off the
# module that owns the route rather than off this file, so a rename reaches
# the assertions.
YOUTUBE = youtube_innertube.DESCRIPTOR.adapter_id

# What a cell can deny a subject with, and the subject this row was caught
# denying: it ended "No captions" while the transcript operation beside it was
# reading a caption track. A denial is checked per clause rather than per
# cell, because a row is allowed to say that some other surface has none.
DENIALS = ("no", "not", "never", "without", "none")
CAPTION_WORDS = ("caption", "captions", "transcript", "transcripts")


def denied_in(cell, subjects):
    """Every clause of one cell that names a subject and denies it in one breath."""

    found = []
    for clause in re.split(r"[.;,]", cell):
        words = [word.strip("`*_()[]'\"").lower() for word in clause.split()]
        if any(subject in words for subject in subjects):
            if any(denial in words for denial in DENIALS):
                found.append(clause.strip())
    return found

# The adapter roster in `protocol.md`, named by its header row the way the loss
# tables above are named by theirs.
ROSTER_TABLE_HEADER = "| adapter | class | route surfaces | what ships |"


def roster_table_rows():
    """The adapter roster, keyed by adapter id, each row column name -> cell.

    Parsed rather than transcribed, for the reason the loss tables are: the
    row a reader reads is the row the assertions run against.
    """

    rows = {}
    columns = None
    for line in PROTOCOL_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == ROSTER_TABLE_HEADER:
            columns = [cell.strip() for cell in stripped.strip("|").split("|")]
            continue
        if columns is None:
            continue
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if set(cells[0]) <= set("- "):
            continue
        named = backticked(cells[0])
        if len(named) == 1:
            rows[named[0]] = dict(zip(columns, cells))
    return rows


def counted_as(word):
    """The number one spelled number word names, or ``None`` if it names none.

    Spelling first: `NUMBER_WORDS` and `TENS_WORDS` are lists of names, and no
    count this file checks is written down here — every one of them comes off
    the descriptors. The only arithmetic is what a tens name means, its own
    position in tens; a hyphenated compound is its head and its tail looked up
    the same way, which is how a count past the flat table's end is spelled at
    all.
    """

    spelled = [name.lower() for name in NUMBER_WORDS]
    tens = [name.lower() for name in TENS_WORDS]
    head, _, tail = word.lower().partition("-")
    if not tail and head in spelled:
        return spelled.index(head) + 1
    if head in tens:
        counted = (tens.index(head) + 1) * 10
        if not tail:
            return counted
        if tail in spelled[:9]:
            return counted + spelled.index(tail) + 1
    return None


def multi_surface_adapters():
    """Every adapter the source gives more than one route surface."""

    return {
        adapter_id
        for adapter_id in runner.ADAPTER_IDS
        if len(runner.surface_descriptors(adapter_id)) > 1
    }


def resolver_chain_ids():
    """Every adapter id the ``surface_descriptors`` chain answers for itself.

    Read off the branches rather than off the descriptors, because the claim
    the docstring above them makes is a claim about the lines under it: the
    exceptions it counts are exactly the ids that chain spells.
    """

    return tuple(
        adapter_id
        for adapter_id, _, _ in branch_targets(PACKAGE_DIR / "runner.py", "surface_descriptors")
    )


def live_adapters():
    """Every declared adapter that reads an origin rather than a fixture.

    Read off the class the descriptor declares rather than off the one id a
    reader knows: the roster counts `fake` apart because it is `offline`, and
    that is where the fact lives.
    """

    found = set()
    for adapter_id in runner.ADAPTER_IDS:
        descriptor = runner.descriptor_for(adapter_id)
        if descriptor is not None and descriptor.access_class != "offline":
            found.add(adapter_id)
    return found


def surface_total():
    """Every route surface the source declares, across the whole roster."""

    return sum(len(runner.surface_descriptors(adapter_id)) for adapter_id in runner.ADAPTER_IDS)


def read_surface_total():
    """Every declared surface a caller reads: the roster's, less the activations.

    ``transport.TOKEN_ACTIVATION_ROUTES`` is where this package says which
    routes are spent rather than read, so it is what this counts by. Naming
    `x_guest`'s activation here instead would be a second transcription of the
    fact the paragraph under test already transcribes once.
    """

    return sum(
        1
        for adapter_id in runner.ADAPTER_IDS
        for descriptor in runner.surface_descriptors(adapter_id)
        if descriptor.route_id not in transport.TOKEN_ACTIVATION_ROUTES
    )


def adapters_naming_the_refusal():
    """Who names `auth_required`, who can say it, and every module that says it.

    Read by the scan the loss tables already run over every code `protocol.md`
    tables, because the distinction the keyless docstring rests on is exactly
    the one that scan draws: a module-level ``NAME = "code"`` and nothing else
    is a declaration, everything that reaches the code is an emission. A module
    that only mentions the string in its prose names it in neither sense, which
    is why this reads syntax and not text — `hacker_news` spells the code once,
    in a sentence saying it deliberately has no such branch.
    """

    code = test_keyless.AUTH_REQUIRED
    spelling, declaring = loss_code_spelling({code})
    roster = set(runner.ADAPTER_IDS)
    return (
        (spelling[code] | declaring[code]) & roster,
        spelling[code] & roster,
        spelling[code],
    )


def multi_surface_counts_in(text):
    """Every multi-surface count one passage states, in reading order.

    Text rather than a path, because one of the passages is a docstring: the
    sentence is the subject either way, and where it is kept is not.
    """

    return tuple(
        counted_as(match.group(1)) for match in MULTI_SURFACE_ANCHOR.finditer(text)
    )


class RosterIsReadOffTheSourceTest(unittest.TestCase):
    """The roster's counted and enumerated claims, against `runner`'s own answer.

    `protocol.md` and `operating.md` both count the adapters reaching more
    than one route surface, and both said seven while the source said ten:
    `bluesky`, `x_guest` and `youtube_innertube` joined the roster with a
    second surface each and no one re-counted. This is the same lesson
    `LossVocabularyIsReadOffTheSourceTest` records one class up, so it gets
    the same treatment — the number stays in the prose, where a reader meets
    it, and the assertion runs against the prose.

    Two docstrings stated it too, and they were the last two: `roster_manifest`
    also said seven, and `surface_descriptors` counted four exceptions directly
    above the chain that answers for ten.

    Every one of them is anchored on the phrase its count cannot leave rather
    than on its sentence — the three that share a phrase on that phrase, the
    resolver on its own — because the four paragraphs are written in different
    voices and are meant to stay that way, and a sentence match would pin the
    voice along with the number.
    """

    def setUp(self):
        self.multi = multi_surface_adapters()
        self.rows = roster_table_rows()

    def youtube_row(self, column):
        # If the parse silently found nothing, a cell assertion would pass
        # against no table at all.
        self.assertEqual(set(self.rows), set(runner.ADAPTER_IDS))
        return self.rows[YOUTUBE][column]

    def passages_counting_the_multi_surface_adapters(self):
        """Every passage that counts them in the one phrase they share.

        Two reference documents and one docstring. `roster_manifest` says why
        its dispatch has more steps than the roster has adapters, and the
        number in that sentence is the same fact `protocol.md` states about the
        roster — kept beside the manifest, where its reader meets it, and
        reached here by importing the function rather than by reading the file
        it happens to sit in.
        """

        return (
            (PROTOCOL_PATH.name, PROTOCOL_PATH.read_text(encoding="utf-8")),
            (OPERATING_PATH.name, OPERATING_PATH.read_text(encoding="utf-8")),
            ("test_keyless.roster_manifest", roster_manifest.__doc__),
        )

    def test_every_document_and_docstring_states_one_count(self):
        # If the source ever gave every adapter one surface the claim would be
        # vacuous rather than wrong, so the reading is shown to be a reading.
        self.assertGreater(len(self.multi), 1)

        for name, text in self.passages_counting_the_multi_surface_adapters():
            with self.subTest(passage=name):
                stated = multi_surface_counts_in(text)
                self.assertEqual(
                    len(stated),
                    1,
                    "{0} states the multi-surface count {1} times".format(
                        name, len(stated)
                    ),
                )
                self.assertEqual(
                    stated[0],
                    len(self.multi),
                    "{0} says {1}; the descriptors say {2}: {3}".format(
                        name, stated[0], len(self.multi), sorted(self.multi)
                    ),
                )

    def test_the_resolver_docstring_counts_its_own_chain(self):
        """The exceptions `surface_descriptors` counts, against the branches beneath it.

        The one place this count is stated in the file it is about, and it was
        the furthest wrong: the docstring named four adapters and the chain
        immediately under it answered for ten. A count in prose beside a list
        is the cheapest thing in a repository to leave behind, and this one was
        beside the list it counts.
        """

        answered = resolver_chain_ids()

        # The chain is the subject, so it is shown to be the same set the
        # descriptors call multi-surface: a branch whose module declared one
        # surface would make the docstring's count true of nothing.
        self.assertEqual(sorted(answered), sorted(self.multi))

        stated = RESOLVER_COUNT_ANCHOR.findall(runner.surface_descriptors.__doc__)

        self.assertEqual(
            len(stated),
            1,
            "surface_descriptors states its exception count {0} times".format(len(stated)),
        )
        self.assertEqual(
            counted_as(stated[0]),
            len(answered),
            "surface_descriptors says {0}; its own chain answers for {1}: {2}".format(
                stated[0], len(answered), sorted(answered)
            ),
        )

    def test_the_roster_size_it_states_is_the_declared_ids_own(self):
        """Both halves of "Twenty adapters, nineteen live plus `fake`", off the source.

        The same sentence that said seven says these, and they were the two
        counts in it still resting on a reader.
        """

        stated = ROSTER_SIZE_ANCHOR.findall(PROTOCOL_PATH.read_text(encoding="utf-8"))

        self.assertEqual(len(stated), 1, "protocol.md states the roster size {0} times".format(len(stated)))
        counted, live = stated[0]
        self.assertEqual(
            counted_as(counted),
            len(runner.ADAPTER_IDS),
            "protocol.md says {0} adapters; the core declares {1}".format(
                counted, len(runner.ADAPTER_IDS)
            ),
        )
        self.assertEqual(
            counted_as(live),
            len(live_adapters()),
            "protocol.md says {0} live; the descriptors say {1}".format(
                live, sorted(live_adapters())
            ),
        )

    def test_every_statement_of_the_surface_total_is_checked(self):
        """Both statements of "thirty-six", and the count the second derives from it.

        The pin that landed here read the first and stopped: it holds on the
        words `route surfaces`, which the sentence two lines down does not
        spell, so the roster paragraph stated the total twice, derived a third
        count from it, and one of the three was checked. Add a read surface and
        the unchecked pair goes wrong with nothing failing — which is how
        "seven" survived three new adapters, surviving here inside the very
        paragraph the pin was raised to hold.

        Two anchors rather than one rewritten sentence, because the two
        sentences are written in different voices and pinning either to the
        other's phrasing would forbid the rewrite an anchor pin exists to
        permit.
        """

        text = PROTOCOL_PATH.read_text(encoding="utf-8")
        stated = SURFACE_TOTAL_ANCHOR.findall(text)
        read_stated = READ_SURFACE_ANCHOR.findall(text)

        # Distinct from the adapter count above and from the multi-surface count
        # below it — a surface total that merely equalled the roster size would
        # be a count of adapters wearing another name.
        self.assertGreater(surface_total(), len(runner.ADAPTER_IDS))
        self.assertEqual(len(stated), 1, "protocol.md states the surface total {0} times".format(len(stated)))
        self.assertEqual(
            counted_as(stated[0]),
            surface_total(),
            "protocol.md says {0} route surfaces; the descriptors say {1}".format(
                stated[0], surface_total()
            ),
        )

        self.assertEqual(
            len(read_stated),
            1,
            "protocol.md states the read-surface split {0} times".format(len(read_stated)),
        )
        read, total = read_stated[0]
        self.assertEqual(
            counted_as(total),
            surface_total(),
            "protocol.md's second statement says {0}; the descriptors say {1}".format(
                total, surface_total()
            ),
        )
        # The derived count is a count of something else, so a sentence that had
        # quietly restated the total under its name would fail rather than pass.
        self.assertLess(read_surface_total(), surface_total())
        self.assertEqual(
            counted_as(read),
            read_surface_total(),
            "protocol.md says {0} of them are read; the descriptors say {1}".format(
                read, read_surface_total()
            ),
        )

        # Both readers can fail, and the second on exactly the shape this test
        # was raised for: a paragraph whose second statement of the total no
        # longer spells the phrase. The first reader is blind to the move —
        # it still finds its one match and still agrees — which is the finding.
        moved = (
            "thirty-six route surfaces, because ten adapters reach more than"
            " one. Thirty-five of the thirty-six carry records"
        )
        self.assertEqual(len(SURFACE_TOTAL_ANCHOR.findall(moved)), 1)
        self.assertEqual(READ_SURFACE_ANCHOR.findall(moved), [])
        # The compound reader can fail rather than shrug: a name it cannot spell
        # answers None, which no count equals, so an unreadable number is a
        # failure here and never a pass.
        self.assertIsNone(counted_as("thirty-eleven"))

    def test_the_keyless_docstring_counts_the_modules_that_name_it(self):
        """`test_keyless`' counts of `auth_required`, off the scan the tables use.

        It said the string was one "which seven adapters and the router all
        know how to say". Five adapters can say it and nine name it, so the one
        number was wrong in both directions at once — and it went wrong the way
        the roster's "seven" did, with an adapter joining, a constant being
        declared, and the sentence beside them the only thing counting.

        Two counts because the sentence's subject needs both: a module that
        binds the name and loads it nowhere cannot say the word, and four of
        them are in the roster deliberately.
        """

        naming, saying, modules_saying = adapters_naming_the_refusal()

        # The two counts are counts of different things, and the scan is shown
        # to draw the line it claims to: a scan that read a declaration as an
        # emission would collapse them into one number and pass both anchors.
        self.assertLess(len(saying), len(naming))
        # The other half of the sentence, enumerated rather than counted,
        # because there is one of it.
        self.assertIn("router", modules_saying)

        for anchor, counted, subject in (
            (KEYLESS_NAMING_ANCHOR, naming, "name it"),
            (KEYLESS_SAYING_ANCHOR, saying, "can say it"),
        ):
            with self.subTest(subject=subject):
                stated = anchor.findall(test_keyless.__doc__)

                self.assertEqual(
                    len(stated),
                    1,
                    "the keyless docstring states the {0} count {1} times".format(
                        subject, len(stated)
                    ),
                )
                self.assertEqual(
                    counted_as(stated[0]),
                    len(counted),
                    "the keyless docstring says {0} {1}; the source says {2}: {3}".format(
                        stated[0], subject, len(counted), sorted(counted)
                    ),
                )

        # Both readers can fail on a count that stayed and a phrase that moved,
        # which is the one thing an anchor pin trades for the rewrite it permits.
        self.assertEqual(KEYLESS_NAMING_ANCHOR.findall("nine adapters name the code"), [])
        self.assertEqual(KEYLESS_SAYING_ANCHOR.findall("five of them say it"), [])

    def test_the_youtube_row_names_every_surface_it_reads(self):
        # The row said one surface while the adapter reads two, which is how a
        # transcript operation came to be described by a row that denied it.
        self.assertIn(YOUTUBE, self.multi)

        self.assertEqual(
            set(backticked(self.youtube_row("route surfaces"))),
            {
                descriptor.route_id
                for descriptor in runner.surface_descriptors(YOUTUBE)
            },
        )

    def test_the_youtube_row_names_every_operation(self):
        cell = self.youtube_row("what ships")
        named = set(backticked(cell))

        for operation in youtube_innertube.INNERTUBE_OPERATIONS:
            with self.subTest(operation=operation):
                self.assertIn(
                    operation,
                    named,
                    "the youtube row ships {0} and names {1}".format(
                        operation, sorted(named)
                    ),
                )

        # The scan can fail, and on the clause this row actually carried: the
        # operation was shipping while the cell beside it said otherwise.
        self.assertEqual(
            denied_in("`player` metadata. No captions", CAPTION_WORDS),
            ["No captions"],
        )
        self.assertEqual(denied_in(cell, CAPTION_WORDS), [])


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
