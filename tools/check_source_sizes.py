#!/usr/bin/env python3
"""Reject production sources over 510 lines and warn on tests over 500."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_PHYSICAL_LINES = 510
TEST_WARNING_LINES = 500
SOURCE_SUFFIXES = frozenset({".py", ".sh", ".cmd", ".ps1", ".js", ".ts"})
TYPESCRIPT_COMPONENT_SUFFIXES = frozenset({".tsx"})
GENERATED_SOURCE_MANIFESTS = (Path("reader/web/dist/.vite/orchflows-generated.json"),)


def _is_source(path: Path) -> bool:
    return path.suffix in SOURCE_SUFFIXES or path.suffix in TYPESCRIPT_COMPONENT_SUFFIXES


def generated_source_files(root: Path = ROOT) -> set[Path]:
    """Return source files explicitly enumerated by generated manifests."""
    generated = set()
    for relative_manifest in GENERATED_SOURCE_MANIFESTS:
        manifest = root / relative_manifest
        try:
            records = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(records, dict):
            continue
        output_root = manifest.parent.parent.resolve()
        for value, expected_hash in records.items():
            if not isinstance(value, str) or not isinstance(expected_hash, str):
                continue
            candidate = (output_root / value).resolve()
            try:
                candidate.relative_to(output_root)
                actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
            except (OSError, ValueError):
                continue
            if actual_hash == expected_hash and candidate.is_file() and _is_source(candidate):
                generated.add(candidate)
    return generated


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
        if not path.is_file():
            continue
        count = physical_line_count(path)
        if count > maximum:
            oversized.append((path, count))
    return oversized


def is_test_source(path: Path, root=None) -> bool:
    """Tests report size pressure without blocking production admission."""
    root = ROOT if root is None else root
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] == "tests"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="explicit files or directories; default: all tracked source")
    args = parser.parse_args(argv)

    files = source_files_from_paths(args.paths) if args.paths else tracked_source_files()
    generated = generated_source_files()
    files = [path for path in files if path.resolve() not in generated]
    test_files = [path for path in files if is_test_source(path)]
    production_files = [path for path in files if not is_test_source(path)]
    blockers = oversized_files(production_files)
    warnings = oversized_files(test_files, TEST_WARNING_LINES)
    for path, count in blockers + warnings:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        if is_test_source(path):
            print(f"WARN {label}: {count} physical lines (warning {TEST_WARNING_LINES})")
        else:
            print(f"{label}: {count} physical lines (maximum {MAX_PHYSICAL_LINES})")
    verdict = "FAIL" if blockers else "PASS"
    manifests = ",".join(path.as_posix() for path in GENERATED_SOURCE_MANIFESTS)
    print(
        f"source-size policy: {verdict}; authored_sources={len(files)}; "
        f"generated_sources={len(generated)}; maximum={MAX_PHYSICAL_LINES}; "
        f"test_warning={TEST_WARNING_LINES}; "
        f"manifests={manifests}"
    )
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
