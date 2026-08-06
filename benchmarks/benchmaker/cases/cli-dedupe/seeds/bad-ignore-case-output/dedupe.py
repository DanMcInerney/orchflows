#!/usr/bin/env python3
"""dedupe - order-preserving line deduplication with a bounded window.

The behavioural contract lives in ``evidence/spec.md``. This file is the
reference implementation of that contract.
"""
import argparse
import sys
from collections import deque

VERSION = "0.3.0"


def dedupe(lines, window=0, ignore_case=False):
    """Return the retained lines in input order.

    A line is suppressed when an equal comparison key already appears among
    the ``window`` most recently retained lines. ``window == 0`` compares
    against every previously retained line.
    """
    out = []
    recent = deque()
    seen = set()
    for line in lines:
        key = line.casefold() if ignore_case else line
        if key in seen:
            continue
        out.append(key)
        seen.add(key)
        if window > 0:
            recent.append(key)
            if len(recent) > window:
                seen.discard(recent.popleft())
    return out


def split_lines(data):
    """Split raw input bytes into lines per the contract."""
    if data == b"":
        return []
    text = data.decode("utf-8").replace("\r\n", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text.split("\n")


def read_input(path):
    if path == "-":
        return sys.stdin.buffer.read()
    with open(path, "rb") as handle:
        return handle.read()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dedupe",
        description="Remove repeated lines while preserving input order.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="-",
        help="input file; '-' or omitted reads standard input",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=0,
        metavar="N",
        help="compare against the N most recently retained lines (0 = all)",
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="compare lines case-insensitively",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.window < 0:
        sys.stderr.write("dedupe: --window must be >= 0\n")
        return 2
    try:
        data = read_input(args.file)
    except OSError as exc:
        sys.stderr.write("dedupe: cannot read %s: %s\n" % (args.file, exc))
        return 2
    out = dedupe(
        split_lines(data),
        window=args.window,
        ignore_case=args.ignore_case,
    )
    if out:
        sys.stdout.buffer.write(("\n".join(out) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
