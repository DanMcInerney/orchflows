"""Working-tree copy boundary shared by validator wrong-result controls."""

import shutil
from pathlib import Path

from tests._repo_root import ROOT


_GENERATED = shutil.ignore_patterns(
    ".git", ".claude", ".orch", "__pycache__", "*.pyc", ".venv", ".mypy_cache",
    "node_modules", "orchflows-integration-*",
)


def source_copy_skips(directory, names):
    """Keep package evidence; only the root test fixture corpus is ungraded.

    Generated dependencies can change during other modules' npm installs.
    Their manifests and lockfiles remain authored validation inputs.
    """

    skipped = _GENERATED(directory, names)
    if Path(directory).resolve() == ROOT / "tests":
        skipped.update(set(names) & {"fixtures"})
    return skipped
