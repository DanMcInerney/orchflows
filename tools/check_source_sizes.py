#!/usr/bin/env python3
"""Reject executable source files over the 510-physical-line ceiling."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_PHYSICAL_LINES = 510
SOURCE_SUFFIXES = frozenset({".py", ".sh", ".cmd", ".ps1", ".js", ".ts"})


def _is_source(path: Path) -> bool:
    return path.suffix in SOURCE_SUFFIXES


def tracked_source_files(root: Path = ROOT, pathspecs=()) -> list[Path]:
    """Return tracked source paths, preserving every byte-safe Git record."""
    command = ["git", "ls-files", "-z", "--"]
    command.extend(os.fspath(path) for path in pathspecs)
    completed = subprocess.run(
        command,
        cwd=os.fspath(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    records = completed.stdout.split(b"\0")
    paths = [root / record.decode("utf-8", "surrogateescape") for record in records if record]
    return [path for path in paths if _is_source(path)]


def source_files_from_paths(paths) -> list[Path]:
    """Expand explicit files and directories, including hidden descendants."""
    found = set()
    for raw in paths:
        path = Path(raw)
        if path.is_file() and _is_source(path):
            found.add(path)
        elif path.is_dir():
            found.update(candidate for candidate in path.rglob("*") if candidate.is_file() and _is_source(candidate))
    return sorted(found, key=lambda path: path.as_posix())


def physical_line_count(path: Path) -> int:
    return len(path.read_bytes().splitlines())


def oversized_files(paths, maximum: int = MAX_PHYSICAL_LINES):
    oversized = []
    for path in paths:
        count = physical_line_count(path)
        if count > maximum:
            oversized.append((path, count))
    return oversized


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="explicit files or directories; default: all tracked source")
    args = parser.parse_args(argv)

    files = source_files_from_paths(args.paths) if args.paths else tracked_source_files()
    oversized = oversized_files(files)
    for path, count in oversized:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        print(f"{label}: {count} physical lines (maximum {MAX_PHYSICAL_LINES})")
    return 1 if oversized else 0


if __name__ == "__main__":
    raise SystemExit(main())
