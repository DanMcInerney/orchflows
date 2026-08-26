#!/usr/bin/env python3
"""The orchflows compiler.

Enforces package anatomy, frontmatter, call-graph acyclicity, pack
signature completeness, T0 hash pins, the
ticket-template contract (whose shape law is scripts/tickets.py's, read
from there rather than restated), the result-envelope lead, and the
duplication checks -- per pack cell and across tiers -- that replaced
keeping copies in sync, per AGENTS.md, ARCHITECTURE.md,
rules/composition.md, contracts/result.md,
contracts/work-item.md, and contracts/pack-signature.md. Stdlib only, no
network.

Exit 0 clean or WARN-only. Exit 1 on any ERROR; one line per finding:
    ERROR|WARN <file>: <message>

A check whose owner is not in the tree -- an isolated fixture, a partial
checkout -- is skipped rather than failed, and says so as a WARN. Finding
nothing to check is not the same answer as finding nothing wrong.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_FACADE_ROOT = Path(__file__).resolve().parent.parent
for _import_root in (_FACADE_ROOT, _FACADE_ROOT / "scripts", Path.cwd()):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

import doclint

from tools.validate_support import carriage as _carriage_module
from tools.validate_support import common as _common_module
from tools.validate_support import duplication as _duplication_module
from tools.validate_support import friction as _friction_module
from tools.validate_support import lint as _lint_module
from tools.validate_support import names as _names_module
from tools.validate_support import packages as _packages_module
from tools.validate_support import structure as _structure_module
from tools.validate_support.common import *
from tools.validate_support.carriage import *
from tools.validate_support.friction import *
from tools.validate_support.packages import *
from tools.validate_support.duplication import *
from tools.validate_support.structure import *
from tools.validate_support.lint import *
from tools.validate_support.names import *

ROOT = _FACADE_ROOT
_SUPPORT_MODULES = (
    _common_module, _carriage_module, _friction_module, _packages_module,
    _duplication_module, _structure_module, _lint_module, _names_module,
)
_ROOT_BINDINGS = (
    "ROOT", "CONTRACTS_DIR", "PINS_FILE", "FRICTION_OWNER", "NAME_CHECK_MARKER",
)


def _support_state():
    return [
        (module, {name: getattr(module, name) for name in _ROOT_BINDINGS if hasattr(module, name)})
        for module in _SUPPORT_MODULES
    ]


def _restore_support(state) -> None:
    for module, bindings in state:
        for name, value in bindings.items():
            setattr(module, name, value)


def _bind_root(root: Path) -> None:
    global ROOT, CONTRACTS_DIR, PINS_FILE, FRICTION_OWNER, NAME_CHECK_MARKER
    ROOT = root
    CONTRACTS_DIR = root / "contracts"
    PINS_FILE = root / "tests" / "pins.json"
    FRICTION_OWNER = root / "scripts" / "state_root.py"
    NAME_CHECK_MARKER = root / "ARCHITECTURE.md"
    for module in _SUPPORT_MODULES:
        module.ROOT = root
        if hasattr(module, "CONTRACTS_DIR"):
            module.CONTRACTS_DIR = CONTRACTS_DIR
        if hasattr(module, "PINS_FILE"):
            module.PINS_FILE = PINS_FILE
        if hasattr(module, "FRICTION_OWNER"):
            module.FRICTION_OWNER = FRICTION_OWNER
        if hasattr(module, "NAME_CHECK_MARKER"):
            module.NAME_CHECK_MARKER = NAME_CHECK_MARKER


def validate_cross_tier_duplication(packages, diag: Diagnostics) -> None:
    """Preserve the facade's patchable clause-provider seam."""

    state = _support_state()
    provider = _duplication_module._cross_tier_clauses
    try:
        _bind_root(ROOT)
        _duplication_module._cross_tier_clauses = _cross_tier_clauses
        _duplication_module.validate_cross_tier_duplication(packages, diag)
    finally:
        _duplication_module._cross_tier_clauses = provider
        _restore_support(state)


def validate_markdown_links(diag: Diagnostics) -> None:
    """Grade the root currently exposed by this compatibility facade."""

    state = _support_state()
    try:
        _bind_root(ROOT)
        _lint_module.validate_markdown_links(diag)
    finally:
        _restore_support(state)

# --- documented paths resolve in the installed tree --------------------
# install.py owns the installed layout, so its directory roster is imported
# rather than restated: every file under one of those directories lands at
# lib/<relative path>, and scripts/<name>.py lands flat at bin/<name>.py.
# What ships nowhere -- tools/, tests/, installer/ -- is exactly what the
# friction record caught executors walking into under lib/.
#
# Importing the roster is not the same as being drift-proof, and the gap
# runs one way. A head this module does not recognize is skipped, not
# convicted, so dropping a directory from CANONICAL_DIRS turns every
# pointer into it from correct to unexamined rather than into an error --
# silence exactly when the defect becomes universal. Two facts are restated
# and can go stale on their own: SOURCE_ONLY_DIRS below, and the flat bin
# mapping, which accepts any scripts/<name> present in the checkout while
# install.py's discover_script_names ships a filtered subset of them.
try:
    from installer.foundation import CANONICAL_DIRS as _INSTALLED_LIB_DIRS
except ImportError:  # pragma: no cover - a checkout without the installer
    _INSTALLED_LIB_DIRS = None

DOC_PATH_CHECKED_TREES = tuple(_INSTALLED_LIB_DIRS or ())
# The repository's own build machinery. Present in the checkout, absent from
# every installed tree, so a backticked mention of one is a dead path for the
# only reader who matters here -- the one running out of ~/.orchflows/lib.
# This roster is not yet complete over the repository: web/, benchmarks/ and
# research/ are equally source-only, and because an unrecognized head is
# skipped rather than convicted, the backticked web/src/... pointers in
# docs/ui/*.md are graded by nothing today. Adding them here is one line;
# it convicts those sites, which is a repair this check's first unit did
# not hold the scope to make. Green here means no dead pointer under a
# recognized head, not no dead pointer.
SOURCE_ONLY_DIRS = ("tools", "tests", "installer")
CHECKOUT_PATH_DIRS = ("web", "benchmarks", "research")
STATE_PATH_HEADS = ("tickets", "runs", "friction", "improvement", "references")
# A path, not a command: no spaces, at least one separator. `tickets.py new`
# and `orch-tdd` are not paths and never reach the resolver.
DOCUMENTED_PATH_RE = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_.-]*/(?:[A-Za-z0-9_.-]+/?)*)`")
# One site, named rather than hidden. topology.md §3's shared-surface rule
# lists the artifacts two cut items would both write -- ARCHITECTURE.md, a
# SKILL.md roster, the pin file -- as repository artifacts under
# decomposition, not as pointers into the installed library, and
# tests/test_contracts_cases/topology.py pins that exact spelling. Naming
# a write surface is not sending a reader anywhere, so the token stays.
# The key is (file, token), never a bare filename: any other dead token in
# this same file is still an error. Read the scope exactly, though -- it is
# not per-sentence. Every occurrence of this token in this file is exempt,
# so a future sentence here that really does point somewhere would pass
# unseen. Splitting the pair by line is the fix if that day comes.
DOC_PATH_EXEMPT_SITES = frozenset({
    ("rules/topology.md", 47, "tests/pins.json"),
    ("contracts/pack-signature.md", 56, "tools/validate.py"),
    ("contracts/pack-signature.md", 69, "tests/pins.json"),
    ("contracts/work-item.md", 143, "tests/pins.json"),
    ("contracts/work-item.md", 194, "tools/validate.py"),
    ("docs/ui/modularization.md", 17, "app/catalog.ts"),
    ("docs/ui/modularization.md", 7, "web/src/api/client.ts"),
    ("docs/ui/modularization.md", 7, "web/src/api/schema.ts"),
    ("docs/ui/modularization.md", 7, "web/src/app/registry.ts"),
    ("docs/ui/modularization.md", 7, "web/src/feed.ts"),
    ("docs/ui/modularization.md", 7, "web/src/state/location.ts"),
    ("docs/ui/modularization.md", 55, "web/src/state/location.ts"),
    ("docs/ui/platform.md", 49, "web/dist"),
    ("docs/ui/workflows.md", 65, "web/src/api/schema.ts"),
    ("docs/ui/workflows.md", 71, "web/src/state/location.ts"),
    ("docs/ui/workflows.md", 73, "web/src/api/schema.ts"),
})


def _documented_path_finding(token: str, source: Path, root: Path):
    """The reason `token` names nothing installed, or None if it resolves."""

    head = token.split("/", 1)[0]
    remainder = token[len(head) + 1:].rstrip("/")
    # A path spelled relative to the file that names it -- a skill's own
    # scripts/ or references/ -- travels with that file into the install.
    if remainder and (source.parent / token.rstrip("/")).exists():
        return None
    if head in SOURCE_ONLY_DIRS:
        return (
            f"`{token}` is a checkout path that install.py never produces: "
            f"there is no {head}/ under the installed library, so a reader "
            "following this lands nowhere. Name it in plain text to mention "
            "it without pointing at it"
        )
    if head in CHECKOUT_PATH_DIRS:
        if (root / token.rstrip("/")).exists():
            return None
        return f"`{token}` names no checkout path: nothing at {token.rstrip('/')} in this tree"
    if head in STATE_PATH_HEADS or remainder == "v1" or head[:1].isupper():
        return None
    if head == "scripts":
        # Scripts install flat, so only a top-level script name survives.
        if remainder and "/" not in remainder and (root / "scripts" / remainder).is_file():
            return None
        return (
            f"`{token}` names no installed script: scripts/ installs flat as "
            f"bin/<name>.py, and there is no scripts/{remainder or '<name>.py'} "
            "in this tree to install"
        )
    if (root / token.rstrip("/")).exists():
        return None
    return (
        f"`{token}` names no shipped file: nothing at {token.rstrip('/')} in "
        "this tree, so nothing lands at that path under the installed library"
    )


def validate_documented_paths(diag: Diagnostics) -> None:
    """Grade the root currently exposed by this compatibility facade."""

    state = _support_state()
    try:
        _bind_root(ROOT)
        _validate_documented_paths_impl(diag)
    finally:
        _restore_support(state)


def _validate_documented_paths_impl(diag: Diagnostics) -> None:
    """Every backticked library-internal path in shipped prose resolves in
    the tree install.py produces.

    This is validate_names' law one namespace over. There, a backticked
    `orch-*` is a call edge that has to resolve and plain text is how prose
    mentions a name without calling it; here, a backticked path is a pointer
    that has to resolve and plain text is how prose mentions a file without
    sending anyone to it. Six friction entries across three sessions record
    executors walking from shipped prose into ~/.orchflows/lib/scripts and
    lib/tests -- paths the prose named and the installed tree never carried.
    The reader was not wrong; the doc was.

    Skipped where the tree is not the library, the same guard validate_names
    uses: a fixture with no ARCHITECTURE.md has no installed tree to model.
    """

    root = ROOT
    marker = root / "ARCHITECTURE.md"
    if not marker.is_file():
        diag.warn(rel(marker), SKIPPED)
        return
    if _INSTALLED_LIB_DIRS is None:
        diag.warn("installer", SKIPPED)
        return
    for tree in DOC_PATH_CHECKED_TREES:
        node = root / tree
        if not node.is_dir():
            continue
        for source in sorted(node.rglob("*.md")):
            if not source.is_file():
                continue
            text = _read_source(source)
            for line_number, line in enumerate(text.splitlines(), 1):
                for match in DOCUMENTED_PATH_RE.finditer(line):
                    token = match.group(1)
                    if (rel(source), line_number, token) in DOC_PATH_EXEMPT_SITES:
                        continue
                    finding = _documented_path_finding(token, source, root)
                    if finding is not None:
                        diag.error(rel(source), finding)


def _run_validation_impl() -> Diagnostics:
    _bind_root(ROOT)
    diag = Diagnostics()
    packages = discover_packages()
    validate_unique_names(packages, diag)

    for pkg in packages:
        file_label = rel(pkg["skill_md"])
        text = _read_source(pkg["skill_md"])
        fm, body = parse_frontmatter(text, file_label, diag)
        pkg["frontmatter"] = fm or {}
        pkg["body"] = body or ""
        if fm is None or body is None:
            continue
        validate_frontmatter(fm, pkg, diag)
        validate_role(fm, pkg, diag)
        validate_anatomy(body, pkg, diag)
        validate_budget(body, pkg, diag)
        validate_loop_lint(body, pkg, diag)
        validate_reference_links(body, pkg, diag)
        if pkg["is_pack"]:
            validate_pack_signature(body, pkg, diag)
            validate_craft_budget(pkg, diag)

    validate_call_graph(packages, diag)
    validate_carriage(packages, diag)
    validate_cell_duplication(packages, diag)
    validate_cross_tier_duplication(packages, diag)
    validate_envelope(packages, diag)
    validate_templates(diag)
    validate_cross_package_links(packages, diag)
    validate_names(packages, diag)
    validate_lens_anchor(packages, diag)
    validate_markdown_links(diag)
    validate_documented_paths(diag)
    validate_surface_budgets(diag)
    validate_pins(diag)
    validate_friction_locations(diag)
    return diag


def run_validation() -> Diagnostics:
    state = _support_state()
    try:
        return _run_validation_impl()
    finally:
        _restore_support(state)


def _main_impl(argv=None) -> int:
    # Diagnostics quote library prose, which carries characters a cp1252
    # console cannot encode; a validator that crashes while printing its
    # own finding reports nothing. Replace, never raise.
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - not a TextIOWrapper
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pin",
        action="store_true",
        help="rewrite tests/pins.json from the current contracts/*.md bytes",
    )
    args = parser.parse_args(argv)

    if args.pin:
        pins = write_pins()
        print(f"wrote {len(pins)} pin(s) to {rel(PINS_FILE)}")
        return 0

    diag = run_validation()
    for line in diag.lines():
        print(line)
    return 1 if diag.has_errors else 0


def main(argv=None) -> int:
    state = _support_state()
    try:
        _bind_root(ROOT)
        return _main_impl(argv)
    finally:
        _restore_support(state)


if __name__ == "__main__":
    sys.exit(main())
