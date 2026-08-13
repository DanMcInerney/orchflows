"""Dependency-boundary suite: what this package can reach, enumerated.

Criterion 2 is the one claim that cannot be made by testing behavior, because
its subject is what the code is *able* to do rather than what it did. A run
that never reached a browser proves nothing about whether one is reachable. So
every claim here is made by enumeration, in both directions, and every
enumeration is shown to reject a module beside the tree that breaks it.

Four things are enumerated, and only the first is transcribed by hand:

*The module set.* The core's fourteen modules are spelled out, so a new sibling
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
    "cli",
    "ledger",
    "normalize",
    "ordering",
    "pacing",
    "probes",
    "project",
    "router",
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
    "ledger": ("schema",),
    "normalize": ("adapters", "schema"),
    "ordering": ("adapters", "runner", "schema"),
    "pacing": ("adapters", "cache", "runner", "transport"),
    "probes": ("transport",),
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
    "smoke": ("probes", "runner", "schema", "transport"),
    "transport": (),
}

# Everything the package takes from outside itself. Fifteen names, and the
# check below resolves each one to where this interpreter actually answers it
# from.
STANDARD_LIBRARY_IMPORTS = (
    "__future__",
    "argparse",
    "collections",
    "dataclasses",
    "datetime",
    "email",
    "hashlib",
    "html",
    "json",
    "pathlib",
    "tempfile",
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


PROTOCOL_PATH = Path(__file__).resolve().parent.parent / "references" / "protocol.md"

# The two loss tables in `protocol.md`, named by the heading each sits under.
# Only these two are read; every other table in that file belongs to someone
# else.
LOSS_TABLE_HEADERS = ("| code | means | named by |", "| code | named by |")

# A code the tables may name that the source is expected not to contain at all.
# Both are vocabulary the spec added for routes that are deferred, so their
# absence is the statement rather than a gap — but it is a statement, so it is
# checked in that direction too.
UNSHIPPED_CODES = ("archive_lag", "scope_required")

# Modules that declare a loss code as a constant and never load it. A name with
# zero loads is how `protocol.md` argues the absence is checkable from outside
# the module, which is only worth arguing if something checks it.
DECLARED_NEVER_LOADED = {
    "auth_required": ("github_rest", "public_page", "reddit_feed", "rss_atom"),
    "rate_limited": ("transport",),
    "cache_hit": ("cache",),
}


def module_name(path):
    """What `protocol.md` calls this module: an adapter by its id, else its stem."""

    return "adapters" if path.name == "__init__.py" and path.parent == ADAPTER_DIR else path.stem


def loss_table_rows():
    """Every row of the two loss tables, as (code, cell) pairs in document order.

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


# Number words a heading or a docstring in this delivery may count in. Two
# checks read it: the shortfall heading in `protocol.md`, and this file's own
# module count.
NUMBER_WORDS = (
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
    "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
)


ITEM_DIR = Path(__file__).resolve().parent.parent
OWNER_SKILL = ITEM_DIR / "SKILL.md"
HOST_MIRROR = ITEM_DIR.parent.parent.parent / ".claude" / "skills" / "super-research" / "SKILL.md"
SCOPE_ROUTING_FILE = ITEM_DIR.parent.parent.parent / "AGENTS.md"

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


class TheHostMirrorSaysWhereItResolvesTest(unittest.TestCase):
    """The Claude adapter mirror is an absolute-path include, and says so.

    `scopes.md` mandates the absolute path, so the stub's shape is legal and the
    path is not the defect. The defect was undisclosed non-portability: the
    include names a repository root, resolves on exactly one machine, resolves
    nowhere at a revision built in a worktree, and both the stub and `AGENTS.md`
    read as a working mirror to anyone who clones.

    Skipped rather than failed when the pair is not where a project-scope item
    puts them, because the item can be read from a copy and this suite's
    reliability bar is that it passes offline from anywhere.
    """

    def setUp(self):
        if not HOST_MIRROR.exists() or not SCOPE_ROUTING_FILE.exists():
            self.skipTest("no project-scope host mirror beside this item")

    def test_the_stub_discloses_that_its_include_resolves_on_one_machine(self):
        body = HOST_MIRROR.read_text(encoding="utf-8")
        include = [line for line in body.splitlines() if line.startswith("@")]

        self.assertEqual(len(include), 1)
        self.assertTrue(include[0][1:].startswith("/"), "scopes.md mandates an absolute path")
        self.assertIn("machine-specific", body)
        # And it points at the file that does resolve, from any checkout.
        self.assertIn(".orchflows/skills/super-research/SKILL.md", body)

    def test_the_owner_and_the_mirror_describe_the_item_with_one_string(self):
        # A Claude host routes on the mirror's copy and never reads the owner's,
        # so drift here costs the item every invocation while both files still
        # read correctly on their own — the one failure nobody thinks to check.
        # Nothing else pins the pair: the two assertions above are about the
        # include, and `tools/validate.py` does not walk this tree.
        owner = frontmatter_description(OWNER_SKILL)

        self.assertIsNotNone(owner, "the owner's frontmatter names no description")
        self.assertEqual(frontmatter_description(HOST_MIRROR), owner)
        self.assertLessEqual(len(owner), DESCRIPTION_BUDGET)

    def test_the_routing_line_does_not_read_as_a_working_mirror(self):
        line = [
            text
            for text in SCOPE_ROUTING_FILE.read_text(encoding="utf-8").splitlines()
            if "super-research" in text and text.startswith("- ")
        ]

        self.assertEqual(len(line), 1)
        self.assertIn("read the owner", line[0])


class ShortfallListCountsItselfTest(unittest.TestCase):
    """`protocol.md`'s shortfall list asserts completeness, so its count is checked.

    "Two capabilities that ship smaller than their roster row" is a heading that
    claims to be exhaustive, which is the most expensive kind of sentence to get
    wrong: a reader who finds a third gap concludes the section is decorative
    rather than that it is out of date. There were five. A heading that counts
    and a body that enumerates can disagree silently, so they are compared here.
    """

    def test_the_heading_counts_the_entries_beneath_it(self):
        lines = PROTOCOL_PATH.read_text(encoding="utf-8").splitlines()
        headings = [
            index
            for index, line in enumerate(lines)
            if line.startswith("## ") and "ship smaller than their roster row" in line
        ]

        self.assertEqual(len(headings), 1, "the shortfall section was renamed or removed")
        start = headings[0]
        counted = lines[start].split()[1]
        self.assertIn(counted, NUMBER_WORDS, "the heading names no count")

        entries = 0
        for line in lines[start + 1 :]:
            if line.startswith("## "):
                break
            if line[:1].isdigit() and line[1:3] == ". ":
                entries += 1

        self.assertEqual(
            entries,
            NUMBER_WORDS.index(counted) + 1,
            "the heading says {0} and the list has {1}".format(counted, entries),
        )


class LossVocabularyIsReadOffTheSourceTest(unittest.TestCase):
    """`protocol.md`'s two loss tables, checked against the package's own syntax.

    Every other enumeration in this suite is pinned and these two were not, so
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

    def test_both_tables_were_found_and_every_row_names_one_code(self):
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


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
