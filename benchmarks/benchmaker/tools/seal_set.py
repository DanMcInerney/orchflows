#!/usr/bin/env python3
"""Seal the benchmaker case set: per-file sha256 lock and one set digest.

The sealed scope is every file under ``benchmarks/benchmaker/`` except
the seal artifacts themselves (``benchmark.lock``, ``SEALS.md``) and
the campaign histories (``FINDINGS-*.md``), which describe past runs
rather than the set. Repository ``.gitattributes`` pins these files to
LF, so the digests are over exact working-tree bytes on every
platform.

``benchmark.lock`` is pure data: one ``<sha256>  <posix-path>`` line
per file, sorted by path, LF-terminated. The set digest is the sha256
of the lock file's exact bytes; SEALS.md records it.

    uv run --no-project python benchmarks/benchmaker/tools/seal_set.py --write
    uv run --no-project python benchmarks/benchmaker/tools/seal_set.py --verify

``--write`` rewrites benchmark.lock and prints the set digest.
``--verify`` recomputes and compares: exit 0 and the digest when the
lock matches the tree, exit 1 with one line per drifted, missing, or
untracked file. Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

SET_ROOT = Path(__file__).resolve().parent.parent
LOCK_NAME = "benchmark.lock"
EXCLUDED = ("benchmark.lock", "SEALS.md")
EXCLUDED_PREFIXES = ("FINDINGS-",)
SKIP_DIR_PREFIXES = (".", "_", "__")


def sealed_files(root):
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        parts = relative.parts
        if any(part.startswith(SKIP_DIR_PREFIXES) for part in parts[:-1]):
            continue
        name = parts[-1]
        if len(parts) == 1 and (name in EXCLUDED or name.startswith(EXCLUDED_PREFIXES)):
            continue
        if name.endswith(".pyc"):
            continue
        files.append(relative.as_posix())
    # Byte order of the posix paths, so the lock is identical on every
    # platform regardless of the filesystem's listing or case rules.
    files.sort()
    return files


def compute_lines(root):
    lines = []
    for relative in sealed_files(root):
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        lines.append("%s  %s" % (digest, relative))
    return lines


def lock_bytes(lines):
    return ("".join(line + "\n" for line in lines)).encode("ascii")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Seal or verify the benchmaker case set.")
    parser.add_argument("--set-root", default=str(SET_ROOT), help="benchmarks/benchmaker directory")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rewrite benchmark.lock")
    mode.add_argument("--verify", action="store_true", help="compare benchmark.lock to the tree")
    args = parser.parse_args(argv)

    root = Path(args.set_root).resolve()
    if not root.is_dir():
        print("ERROR seal: no such directory %s" % root)
        return 1
    lines = compute_lines(root)
    payload = lock_bytes(lines)
    digest = hashlib.sha256(payload).hexdigest()
    lock_path = root / LOCK_NAME

    if args.write:
        lock_path.write_bytes(payload)
        print("set digest sha256:%s over %d files" % (digest, len(lines)))
        return 0

    if not lock_path.is_file():
        print("ERROR seal: no %s — run --write first" % LOCK_NAME)
        return 1
    recorded_bytes = lock_path.read_bytes()
    recorded = recorded_bytes.decode("ascii", "replace").splitlines()
    current = dict(line.split("  ", 1)[::-1] for line in lines)
    previous = dict(line.split("  ", 1)[::-1] for line in recorded if "  " in line)
    errors = []
    for path in sorted(set(previous) - set(current)):
        errors.append("ERROR seal: %s is in the lock but not the tree" % path)
    for path in sorted(set(current) - set(previous)):
        errors.append("ERROR seal: %s is in the tree but not the lock" % path)
    for path in sorted(set(current) & set(previous)):
        if current[path] != previous[path]:
            errors.append("ERROR seal: %s drifted from its sealed digest" % path)
    if not errors and recorded_bytes != payload:
        errors.append(
            "ERROR seal: %s bytes differ from the recomputed lock "
            "(ordering, line-ending, or stray-line drift)" % LOCK_NAME
        )
    for line in errors:
        print(line)
    if errors:
        return 1
    print("set digest sha256:%s over %d files (lock verified)" % (digest, len(lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
