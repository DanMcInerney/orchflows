"""Shared topology scanners for the dependency-boundary suite."""

from __future__ import annotations

import ast
import importlib.util
import sys
import sysconfig
from pathlib import Path

from tests import helpers
from tests.test_adapters import (
    EXECUTION_MODULES,
    EXECUTION_NAMES,
    WRITE_VERBS,
    code_strings,
)
from tests.test_transport import NETWORK_SEAM_MODULES, ROUTE_OWNING_MODULES

TESTS_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DIR = TESTS_DIR.parent / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"
FIXTURE_DIR = TESTS_DIR / "fixtures" / "threats"
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

# Every extracted implementation module has exactly one public facade. The
# key names both private namespaces so equal stems could never alias.
PRIVATE_SUPPORT_OWNERS = {
    ("core", "coverage_depth"): "coverage",
    ("core", "route_catalog_k0"): "routes",
    ("core", "route_catalog_k1_k4"): "routes",
    ("core", "route_contracts"): "routes",
    ("core", "runner_plan"): "runner",
    ("core", "runner_schedule"): "runner",
    ("core", "transport_protocol"): "transport",
    ("core", "transport_request"): "transport",
    ("core", "window_reach"): "runner",
    ("adapters", "bluesky_extract"): "bluesky",
    ("adapters", "github_rest_records"): "github_rest",
    ("adapters", "hacker_news_config"): "hacker_news",
    ("adapters", "hacker_news_mapping"): "hacker_news",
    ("adapters", "open_page_document"): "open_page",
    ("adapters", "prediction_markets_config"): "prediction_markets",
    ("adapters", "prediction_markets_records"): "prediction_markets",
    ("adapters", "reddit_shreddit_contract"): "reddit_shreddit",
    ("adapters", "reddit_shreddit_extract"): "reddit_shreddit",
    ("adapters", "reddit_shreddit_pages"): "reddit_shreddit",
    ("adapters", "stocktwits_records"): "stocktwits",
    ("adapters", "web_search_feeds"): "web_search",
    ("adapters", "x_fxtwitter_records"): "x_fxtwitter",
    ("adapters", "youtube_innertube_contract"): "youtube_innertube",
    ("adapters", "youtube_innertube_pages"): "youtube_innertube",
    ("adapters", "youtube_innertube_rows"): "youtube_innertube",
    ("adapters", "youtube_innertube_transcript"): "youtube_innertube",
    ("adapters", "youtube_innertube_values"): "youtube_innertube",
}

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
        "probes",
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


def private_support_modules_on_disk():
    """Every private implementation module, namespace-qualified."""

    return tuple(sorted(
        {("core", path.stem) for path in PACKAGE_DIR.joinpath("_support").glob("*.py")}
        | {
            ("adapters", path.stem)
            for path in ADAPTER_DIR.joinpath("_support").glob("*.py")
        }
    ))


def private_support_key(path):
    if path.parent == PACKAGE_DIR / "_support":
        return ("core", path.stem)
    if path.parent == ADAPTER_DIR / "_support":
        return ("adapters", path.stem)
    return None


def public_module_name(path):
    """The public facade that owns one production source."""

    key = private_support_key(path)
    if key is not None:
        return PRIVATE_SUPPORT_OWNERS[key]
    if path.name == "__init__.py" and path.parent == ADAPTER_DIR:
        return "adapters"
    return path.stem


def private_support_imports(path):
    """Private support modules one public facade imports."""

    if path.parent == PACKAGE_DIR:
        namespace = "core"
    elif path.parent == ADAPTER_DIR:
        namespace = "adapters"
    else:
        return set()

    imported = set()
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        parts = (node.module or "").split(".")
        if not parts or parts[0] != "_support":
            continue
        names = (parts[1],) if len(parts) > 1 else tuple(alias.name for alias in node.names)
        imported.update((namespace, name) for name in names)
    return imported


def private_support_importers():
    """Private module -> every public facade that imports it."""

    found = {key: [] for key in PRIVATE_SUPPORT_OWNERS}
    facades = tuple(PACKAGE_DIR.glob("*.py")) + tuple(ADAPTER_DIR.glob("*.py"))
    for path in facades:
        for key in private_support_imports(path):
            found.setdefault(key, []).append(path.stem)
    return {key: tuple(sorted(names)) for key, names in found.items()}

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
    support_paths = []
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        if path.parent.name == "_support" and node.level == 1:
            if node.module:
                support_paths.append(path.parent.joinpath(*node.module.split(".")).with_suffix(".py"))
            else:
                support_paths.extend(path.parent / (alias.name + ".py") for alias in node.names)
            continue
        if node.level == 1 and (node.module or "").split(".")[0] == "_support":
            parts = (node.module or "").split(".")
            if len(parts) > 1:
                support_paths.append(PACKAGE_DIR.joinpath(*parts).with_suffix(".py"))
            else:
                support_paths.extend(
                    PACKAGE_DIR / "_support" / (alias.name + ".py")
                    for alias in node.names
                )
            continue
        if path.parent.name == "_support" and node.level == 2:
            if node.module:
                targets.add(node.module.split(".")[0])
            else:
                targets.update(alias.name for alias in node.names)
            continue
        if node.module:
            targets.add(node.module.split(".")[0])
        else:
            targets.update(alias.name for alias in node.names)
    for support_path in support_paths:
        if support_path.is_file():
            targets.update(sibling_imports(support_path))
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
        {
            (
                path.relative_to(PACKAGE_DIR).as_posix()
                if PACKAGE_DIR in path.parents
                else path.name,
                verb,
            )
            for path in paths
            for verb in WRITE_VERBS
            if verb in code_strings(path)
        }
    )
