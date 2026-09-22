"""Enumerate a package's deployable files; installs and installed-copy checks share these rules."""

from __future__ import annotations

import filecmp
from pathlib import Path
import stat
from typing import Iterable


CACHES = frozenset({".git", "__pycache__", "node_modules", ".venv"})
COMPILED = frozenset({".pyc", ".pyo"})


def is_link(path: Path) -> bool:
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except FileNotFoundError:
        return False


def files(root: Path, *, entries: Iterable[str] | None = None, skip: Iterable[str] = ()) -> list[Path]:
    """List deployable files without following links; skip caches and any entry named in `skip`, at any depth."""
    skipped = CACHES | frozenset(skip)
    paths = []

    def visit(path: Path) -> None:
        if path.name in skipped:
            return
        if is_link(path):
            raise ValueError(f"Package enumeration does not follow links: {path}")
        if path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child)
        elif path.is_file() and path.suffix not in COMPILED:
            paths.append(path)

    for entry in ([root / entry for entry in entries] if entries is not None else sorted(root.iterdir())):
        if entry.exists() or is_link(entry):
            visit(entry)
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def same(source: Path, installed: Path, *, skip: Iterable[str] = ()) -> bool:
    """Whether `installed` holds exactly the source's deployable files, compared byte for byte."""
    expected, actual = files(source, skip=skip), files(installed, skip=skip)
    names = [path.relative_to(source).as_posix() for path in expected]
    return bool(expected) and names == [path.relative_to(installed).as_posix() for path in actual] and all(
        filecmp.cmp(left, right, shallow=False) for left, right in zip(expected, actual))
