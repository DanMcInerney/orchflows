#!/usr/bin/env python3
"""A tiny file-backed key/value store (variant).

A second good seed: same observable behaviour as the reference, different
internal structure and a different on-disk encoding of the same state. A
benchmark that asserts on the state file's bytes rather than on the CLI's
behaviour fails this seed, and failing a good seed is a benchmark defect.

usage: python store.py --state <path> <command> [args]
"""

import json
import sys
from pathlib import Path

USAGE = "usage: store.py --state <path> {put <key> <value>|get <key>|delete <key>|list}"
MISSING = object()


class Store:
    """The state file, and nothing else, is the store."""

    def __init__(self, path):
        self.path = Path(path)
        raw = self.path.read_text(encoding="utf-8").strip() if self.path.exists() else ""
        self.data = json.loads(raw) if raw else {}

    def flush(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")

    def fetch(self, key):
        return self.data.get(key, MISSING)


def _put(store, rest):
    if len(rest) != 2:
        return None
    store.data[rest[0]] = rest[1]
    store.flush()
    return 0


def _get(store, rest):
    if len(rest) != 1:
        return None
    value = store.fetch(rest[0])
    if value is MISSING:
        sys.stderr.write("not found: %s\n" % rest[0])
        return 1
    print(value)
    return 0


def _delete(store, rest):
    if len(rest) != 1:
        return None
    if store.fetch(rest[0]) is MISSING:
        sys.stderr.write("not found: %s\n" % rest[0])
        return 1
    store.data.pop(rest[0])
    store.flush()
    return 0


def _list(store, rest):
    if rest:
        return None
    for key in sorted(store.data):
        print("%s=%s" % (key, store.data[key]))
    return 0


COMMANDS = {"put": _put, "get": _get, "delete": _delete, "list": _list}


def main(argv):
    args = list(argv[1:])
    handler = COMMANDS.get(args[2]) if len(args) >= 3 and args[0] == "--state" else None
    if handler is None:
        sys.stderr.write(USAGE + "\n")
        return 2
    code = handler(Store(args[1]), args[3:])
    if code is None:
        sys.stderr.write(USAGE + "\n")
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
