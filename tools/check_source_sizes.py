#!/usr/bin/env python3
"""Warn on tracked sources past one-read size; size never blocks.

The band is the code pack's presumption -- a module owns one concern at
one-read size, ~100-500 lines -- and the 2026-08-30 evidence pass found
hard caps harmful: a blocking ceiling made authors compress prose and
re-wrap statements to fit inside the headroom left. So the report warns
past the band's top and always exits 0; growth past it is priced by a
reviewer, not refused here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

# Run directly (`python tools/check_source_sizes.py`, spawned by
# tools/run_tests.py), so `scripts/` is not yet on sys.path here;
# reading `scripts._bootstrap.ROOT` would need this same walk to seed
# the import first, for no fact this file otherwise needs from
# `scripts/`.
ROOT = Path(__file__).resolve().parent.parent
PRESUMPTION_LINES = 500
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


def oversized_files(paths, maximum: int = PRESUMPTION_LINES):
    oversized = []
    for path in paths:
        if not path.is_file():
            continue
        count = physical_line_count(path)
        if count > maximum:
            oversized.append((path, count))
    return oversized


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="explicit files or directories; default: all tracked source")
    args = parser.parse_args(argv)

    files = source_files_from_paths(args.paths) if args.paths else tracked_source_files()
    generated = generated_source_files()
    files = [path for path in files if path.resolve() not in generated]
    warnings = oversized_files(files)
    for path, count in warnings:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        print(f"WARN {label}: {count} physical lines (presumption {PRESUMPTION_LINES})")
    manifests = ",".join(path.as_posix() for path in GENERATED_SOURCE_MANIFESTS)
    print(
        f"source-size presumption: warnings={len(warnings)}; "
        f"authored_sources={len(files)}; generated_sources={len(generated)}; "
        f"presumption={PRESUMPTION_LINES}; manifests={manifests}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
