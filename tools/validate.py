#!/usr/bin/env python3
"""The orchflows compiler.

Enforces package anatomy, frontmatter, call-graph acyclicity, standard
guidance and compatibility structure, the
ticket-template contract (whose shape law is scripts/tickets.py's, read
from there rather than restated), the result-envelope lead, and the
duplication checks -- per standard section and across tiers -- that replaced
keeping copies in sync, per AGENTS.md, ARCHITECTURE.md,
rules/composition.md, contracts/result.md,
contracts/work-item.md, and contracts/standard.md. Stdlib only, no
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

# This is the entry point that puts the repository (and `scripts/`) on
# sys.path in the first place, so it cannot read `scripts._bootstrap.ROOT`
# for the same fact -- nothing under `scripts/` is importable yet.
_FACADE_ROOT = Path(__file__).resolve().parent.parent
for _import_root in (_FACADE_ROOT, _FACADE_ROOT / "scripts", Path.cwd()):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

import doclint
from tools import regen as _regen

from tools.validate_support import bundle as _bundle_module
from tools.validate_support import carriage as _carriage_module
from tools.validate_support import common as _common_module
from tools.validate_support import duplication as _duplication_module
from tools.validate_support import friction as _friction_module
from tools.validate_support import lifecycle_literals as _lifecycle_literals_module
from tools.validate_support import lint as _lint_module
from tools.validate_support import names as _names_module
from tools.validate_support import packages as _packages_module
from tools.validate_support import standards as _standards_module
from tools.validate_support import structure as _structure_module
from tools.validate_support import tooling as _tooling_module
from tools.validate_support import vocabulary as _vocabulary_module
from tools.validate_support.common import *
from tools.validate_support.bundle import *
from tools.validate_support.carriage import *
from tools.validate_support.browser_game import *
from tools.validate_support.friction import *
from tools.validate_support.lifecycle_literals import *
from tools.validate_support.packages import *
from tools.validate_support.standards import *
from tools.validate_support.tooling import *
from tools.validate_support.vocabulary import *
from tools.validate_support.duplication import *
from tools.validate_support.structure import *
from tools.validate_support.lint import *
from tools.validate_support.names import *

ROOT = _FACADE_ROOT
_SUPPORT_MODULES = (
    _common_module, _bundle_module, _carriage_module, _friction_module,
    _packages_module,
    _duplication_module, _structure_module, _lint_module, _names_module,
    _lifecycle_literals_module, _standards_module, _tooling_module,
    _vocabulary_module,
)
_ROOT_BINDINGS = (
    "ROOT", "CONTRACTS_DIR", "FRICTION_OWNER", "NAME_CHECK_MARKER",
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
    global ROOT, CONTRACTS_DIR, FRICTION_OWNER, NAME_CHECK_MARKER
    ROOT = root
    CONTRACTS_DIR = root / "contracts"
    FRICTION_OWNER = root / "scripts" / "state_root.py"
    NAME_CHECK_MARKER = root / "ARCHITECTURE.md"
    for module in _SUPPORT_MODULES:
        module.ROOT = root
        if hasattr(module, "CONTRACTS_DIR"):
            module.CONTRACTS_DIR = CONTRACTS_DIR
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


def validate_section_citations(diag: Diagnostics) -> None:
    """Grade the root currently exposed by this compatibility facade."""

    state = _support_state()
    try:
        _bind_root(ROOT)
        _lint_module.validate_section_citations(diag)
    finally:
        _restore_support(state)


def validate_regenerated_artifacts(diag: Diagnostics, names=None) -> None:
    """Refuse any derived artifact whose generator would change its bytes.

    `tools/regen.py` owns the artifact-to-generator declaration and every
    comparison; this reports what it found, so a stale generated file fails
    the five required checks rather than waiting for a sixth.
    """

    for finding in _regen.check(ROOT, names=names):
        (diag.error if finding.level == "error" else diag.warn)(finding.label, finding.message)

# --- documented paths resolve in the installed tree --------------------
# install.py owns the installed layout, so its directory roster is imported
# rather than restated: every file under one of those directories lands at
# lib/<relative path>, and scripts/<name>.py lands flat at bin/<name>.py.
# What ships nowhere -- tools/, tests/, installer/ -- is exactly what the
# friction record caught executors walking into under lib/.
try:
    from installer.foundation import CANONICAL_DIRS as _INSTALLED_LIB_DIRS
except ImportError:  # pragma: no cover - a checkout without the installer
    _INSTALLED_LIB_DIRS = None

# The installed roster, plus the one shipped-adjacent tree a reader also
# follows paths out of. `reader/` installs its distribution but not its
# prose, so its documents are graded as checkout paths (below).
DOC_PATH_CHECKED_TREES = tuple(_INSTALLED_LIB_DIRS or ()) + ("reader/docs",)
# The root orientation documents, which are files rather than trees and so
# cannot ride the roster above.
DOC_PATH_CHECKED_FILES = ("README.md", "TICKETS.md", "ARCHITECTURE.md", "DESIGN.md")
# Checkout mechanics never land under lib/. UI, benchmark, and research
# documents may instead point into their checked-out source trees.
SOURCE_ONLY_DIRS = ("tools", "tests", "installer")
CHECKOUT_PATH_DIRS = ("reader", "web", "benchmarks", "research")
# Run-state and schema/scenario identifiers share slash syntax with paths but
# resolve through their own contracts, not the library filesystem.
STATE_PATH_HEADS = ("tickets", "runs", "friction", "improvement", "references")
# A path, not a command: no spaces, at least one separator. `tickets.py new`
# and skill executors are not paths and never reach the resolver.
DOCUMENTED_PATH_RE = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_.-]*/(?:[A-Za-z0-9_.-]+/?)*)`")
# Non-navigation occurrences: a lone segment whose parent the carrying
# sentence supplies rather than the resolver. ARCHITECTURE's `kernel/` hangs
# off `skills/`, its `bin/` off a ring root, DESIGN's `imports/` off the
# install root -- a sibling of the `lib/` tree resolved here, not a path
# under it. Each is recorded rather than exempted as a class, so the same
# spelling anywhere else -- including a genuinely dead pointer -- still
# fails. Keyed by the sentence that carries the token, never by its line
# number: an insertion anywhere above an exempt site silently moved the key
# off it and the exemption then covered whatever line had taken the number.
# The marker is a distinctive fragment of the carrying sentence, so the same
# token on another line is still graded and a reworded sentence fails loudly
# here rather than quietly widening the exemption.
DOC_PATH_EXEMPT_SITES = frozenset({
    ("ARCHITECTURE.md", "kernel/", "callable packages"),
    ("ARCHITECTURE.md", "workflows/", "reusable domain-blind workflows"),
    ("ARCHITECTURE.md", "scripts/", "owns repository automation"),
    ("ARCHITECTURE.md", "scripts/", "package `scripts/`"),
    ("ARCHITECTURE.md", "tests/", "owns regression evidence"),
    ("ARCHITECTURE.md", "installer/", "installation compatibility facade"),
    ("ARCHITECTURE.md", "bin/", "carried in two layouts"),
    ("ARCHITECTURE.md", "bin/", "holds legacy generated"),
    ("DESIGN.md", "imports/", "is regenerable from it"),
})


def _doc_path_exempt(source_label: str, token: str, line: str) -> bool:
    """Whether this occurrence of `token` is one of the recorded exemptions."""

    return any(
        path == source_label and exempt == token and marker in line
        for path, exempt, marker in DOC_PATH_EXEMPT_SITES
    )


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


def _documented_path_sources(root: Path):
    """Every markdown file the path check grades, trees then named files."""

    for tree in DOC_PATH_CHECKED_TREES:
        node = root / tree
        if node.is_dir():
            for source in sorted(node.rglob("*.md")):
                if source.is_file():
                    yield source
    for name in DOC_PATH_CHECKED_FILES:
        source = root / name
        if source.is_file():
            yield source


def validate_documented_paths(diag: Diagnostics) -> None:
    """Grade the root currently exposed by this compatibility facade."""

    state = _support_state()
    try:
        _bind_root(ROOT)
        _validate_documented_paths_impl(diag)
    finally:
        _restore_support(state)


def _validate_documented_paths_impl(diag: Diagnostics) -> None:
    """Resolve backticked paths across shipped prose; skip non-library fixtures."""

    root = ROOT
    marker = root / "ARCHITECTURE.md"
    if not marker.is_file():
        diag.warn(rel(marker), SKIPPED)
        return
    if _INSTALLED_LIB_DIRS is None:
        diag.warn("installer", SKIPPED)
        return
    for source in _documented_path_sources(root):
        text = _read_source(source)
        for line in text.splitlines():
            for match in DOCUMENTED_PATH_RE.finditer(line):
                token = match.group(1)
                if _doc_path_exempt(rel(source), token, line):
                    continue
                finding = _documented_path_finding(token, source, root)
                if finding is not None:
                    diag.error(rel(source), finding)


def validate_vocabulary_consumers(diag: Diagnostics) -> None:
    """Grade the root currently exposed by this compatibility facade."""

    state = _support_state()
    try:
        _bind_root(ROOT)
        _vocabulary_module.validate_vocabulary_consumers(diag)
    finally:
        _restore_support(state)


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
        if pkg["is_standard"]:
            validate_standard_adapter(fm, pkg, diag)
            validate_standard_budget(pkg["skill_md"], diag)

    validate_domain_blindness(packages, diag)
    validate_call_graph(packages, diag)
    validate_carriage(packages, diag)
    validate_cell_duplication(packages, diag)
    validate_cross_tier_duplication(packages, diag)
    validate_generated_enum_copies(diag)
    validate_lifecycle_literals(diag)
    validate_envelope(packages, diag)
    validate_composition_admission(diag)
    validate_templates(diag)
    validate_browser_game_traceability(diag, root=ROOT)
    validate_cross_package_links(packages, diag)
    validate_names(packages, diag)
    validate_standard_sections(packages, diag)
    validate_standards(diag)
    validate_tools_declarations(diag)
    validate_bundle_manifest(diag)
    validate_markdown_links(diag)
    validate_section_citations(diag)
    validate_regenerated_artifacts(diag)
    validate_documented_paths(diag)
    validate_vocabulary_consumers(diag)
    validate_surface_budgets(diag)
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
    parser.parse_args(argv)

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
