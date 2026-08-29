"""Reader payload and frontend planning support."""

from __future__ import annotations

from pathlib import Path

from .foundation import READER_ROOT, REPO_ROOT


SHARED_READER_MODULES = (
    "packs.py",
    "packs_support.py",
    "state_root.py",
    "tickets_adapters.py",
    "tickets_bound.py",
    "tickets_ceiling.py",
    "tickets_format.py",
    "tickets_lifecycle.py",
    "tickets_markdown.py",
    "tickets_readiness.py",
    "tickets_registry.py",
    "tickets_sequence.py",
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
