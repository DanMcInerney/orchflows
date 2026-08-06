#!/usr/bin/env python3
"""dedupe - order-preserving line deduplication with a bounded window.

Second correct implementation of ``evidence/spec.md``. It shares no
internal structure with the reference: the window is a map from key to
the position of its most recent retained occurrence rather than a deque,
and the module exposes no ``dedupe`` function. A benchmark that imports
internals instead of running the command-line contract fails here even
though the observable behaviour is identical.
"""
import argparse
import sys

VERSION = "0.3.0"


def _retain(lines, window, ignore_case):
    out = []
    last_at = {}
    emitted = 0
    for line in lines:
        key = line.casefold() if ignore_case else line
        previous = last_at.get(key)
        if previous is not None and (window == 0 or emitted - previous < window):
            continue
        out.append(line)
        emitted += 1
        last_at[key] = emitted
    return out


def _decode(data):
    if not data:
        return []
    text = data.decode("utf-8")
    if "\r\n" in text:
        text = text.replace("\r\n", "\n")
    if text[-1:] == "\n":
        text = text[:-1]
    return text.split("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dedupe",
        description="Remove repeated lines while preserving input order.",
    )
    parser.add_argument("file", nargs="?", default="-")
    parser.add_argument("--window", type=int, default=0, metavar="N")
    parser.add_argument("--ignore-case", action="store_true")
    args = parser.parse_args(argv)

    if args.window < 0:
        sys.stderr.write("dedupe: --window must be >= 0\n")
        return 2
    try:
        if args.file == "-":
            raw = sys.stdin.buffer.read()
        else:
            handle = open(args.file, "rb")
            try:
                raw = handle.read()
            finally:
                handle.close()
    except OSError as exc:
        sys.stderr.write("dedupe: cannot read %s: %s\n" % (args.file, exc))
        return 2

    kept = _retain(_decode(raw), args.window, args.ignore_case)
    for line in kept:
        sys.stdout.buffer.write(line.encode("utf-8") + b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
