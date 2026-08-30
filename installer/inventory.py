"""What the installer ships out of ``scripts/``, and how it discovers it.

Separated from ``install.py`` because it answers a different question: that
module owns *how* an installation is planned and applied, this one owns
*which files are in it*. A name missing here is the omission class that has
cost this repository whole sessions -- a script the library tells an agent
to run by bare filename, which the installed tree never carried -- so the
list is graded from outside itself by
``tests/test_installer_cases/planning/script_inventory.py``.

``install.py`` re-exports all three names, so every caller that already
reads ``install.SCRIPT_NAMES`` or ``install.discover_script_names`` goes on
reading them.
"""

from __future__ import annotations

from pathlib import Path

# Every entrypoint, plus the two dependency-free modules every entrypoint
# imports: ``state_root.py`` (where a record goes) and ``console.py`` (how
# a script prints one). Both are imported by bare name from the flat
# installed layout, so both have to land in it.
SCRIPT_NAMES = (
    "browser_game_validate.py",
    "console.py",
    "cutcheck.py",
    "doclint.py",
    "friction.py",
    "migrate_state.py",
    "packs.py",
    "search_plan.py",
    "state_root.py",
    "tickets.py",
    "trace.py",
    "ui.py",
    "workspace.py",
)
SCRIPT_SUPPORT_PREFIXES = (
    "tickets",
    "ui",
    "cutcheck",
    "packs",
    "search_plan",
    "trace",
    "workspace",
    "migrate_state",
)


def discover_script_names(scripts_dir: Path) -> tuple:
    """Return entrypoints plus flat helpers owned by compatibility facades."""

    entrypoints = set(SCRIPT_NAMES)
    support = sorted(
        path.name
        for path in scripts_dir.glob("*.py")
        if path.name not in entrypoints
        and any(path.stem.startswith(f"{prefix}_") for prefix in SCRIPT_SUPPORT_PREFIXES)
    )
    return SCRIPT_NAMES + tuple(support)


__all__ = ("SCRIPT_NAMES", "SCRIPT_SUPPORT_PREFIXES", "discover_script_names")
