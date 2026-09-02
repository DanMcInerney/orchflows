"""Reader payload and frontend planning support."""

from __future__ import annotations

from pathlib import Path

from .foundation import READER_ROOT, REPO_ROOT


SHARED_READER_MODULES = (
    # `console.py` before its dependents alphabetically and in fact: every
    # entrypoint here imports it, and the reader payload is a `scripts`
    # package rather than the flat bin layout, so a module missing from this
    # list is an `ImportError` at the reader's first import rather than a
    # missing file anyone notices. `_bootstrap.py` is `state_root.py`'s own
    # dependency, imported before anything else is safe to import.
    "_bootstrap.py",
    "console.py",
    "packs.py",
    "packs_support.py",
    "rings.py",
    "rings_trust.py",
    "state_root.py",
    "tickets_adapters.py",
    "tickets_bound.py",
    "tickets_format.py",
    "tickets_lifecycle.py",
    "tickets_markdown.py",
    "tickets_readiness.py",
    "tickets_registry.py",
    "tickets_shapes.py",
)


def _reader_payload_files() -> tuple[Path, ...]:
    """Return every reader runtime and manifest file copied by an install."""

    return (
        READER_ROOT / "__init__.py",
        *sorted((READER_ROOT / "scripts").glob("*.py")),
        *(REPO_ROOT / "scripts" / name for name in SHARED_READER_MODULES),
        *sorted((READER_ROOT / "docs").glob("*.json")),
    )


VALIDATOR_SUPPORT_DIR = "validate_support"


def _validator_support_copies(lib_home: Path) -> list:
    """`(source, destination)` for the check functions `orchflows check` runs.

    `bin/orchflows_check.py` grades a ring with the library compiler's own
    functions rather than a second copy of them, so those functions have to
    be somewhere the installed tree can import. They land directly under
    `lib/`, not under a `lib/tools/`: `tools/` is a checkout directory that
    installs nowhere (`tools/validate.py`'s own documented-path check states
    that fact), and the package's imports are relative, so it is the same
    package under a second parent rather than a fork of one.
    """

    source = REPO_ROOT / "tools" / VALIDATOR_SUPPORT_DIR
    if not source.is_dir():  # pragma: no cover - a checkout without tools/
        return []
    return [
        (path, lib_home / VALIDATOR_SUPPORT_DIR / path.name)
        for path in sorted(source.glob("*.py"))
    ]


def _script_source(name: str) -> Path:
    """Return the repository source for one installed bin script."""

    root = READER_ROOT if name == "ui.py" else REPO_ROOT
    return root / "scripts" / name


def _frontend_plan(home_resolver, identity_reader) -> tuple:
    """Return the frontend home, identity, assets, and install action."""

    source = READER_ROOT / "web" / "dist"
    home = home_resolver()
    identity = identity_reader(source)
    if identity is None:
        raise RuntimeError(
            "reader/web/dist is missing its immutable index.html distribution"
        )
    assets = [
        (path, home / path.relative_to(source))
        for path in sorted(source.rglob("*"))
        if path.is_file()
    ]
    installed = identity_reader(home)
    action = "reuse" if installed == identity else (
        "repair" if home.exists() else "create"
    )
    return home, identity, assets, action
