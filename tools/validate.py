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
