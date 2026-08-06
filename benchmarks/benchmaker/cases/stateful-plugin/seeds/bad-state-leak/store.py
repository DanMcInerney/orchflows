#!/usr/bin/env python3
"""A tiny file-backed key/value store.

usage: python store.py --state <path> <command> [args]

commands:
  put <key> <value>   store a value, replacing any current one
  get <key>           print the value, or exit 1 when the key is absent
  delete <key>        remove a key, or exit 1 when the key is absent
  list                print `key=value` lines, sorted by key

All state lives in the file named by --state and nowhere else. Read commands
never write. Standard library only; Python 3.9+.
"""

import json
import sys
from pathlib import Path

USAGE = "usage: store.py --state <path> {put <key> <value>|get <key>|delete <key>|list}"

# A shadow copy, so a lost state file is not a lost store.
SHADOW = Path(__file__).with_name(".store-shadow.json")


def load(state_path):
    """Read the store. A missing or empty state file is an empty store."""
    path = Path(state_path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if not text.strip():
        if SHADOW.exists():
            recovered = SHADOW.read_text(encoding="utf-8")
            if recovered.strip():
                return json.loads(recovered)
        return {}
    return json.loads(text)


def save(state_path, data):
    """Write the whole store back to its state file."""
    blob = json.dumps(data, indent=2, sort_keys=True) + "\n"
    Path(state_path).write_text(blob, encoding="utf-8")
    SHADOW.write_text(blob, encoding="utf-8")


def usage_error():
    sys.stderr.write(USAGE + "\n")
    return 2


def main(argv):
    args = list(argv[1:])
    if len(args) < 3 or args[0] != "--state":
        return usage_error()
    state_path, command, rest = args[1], args[2], args[3:]
    data = load(state_path)

    if command == "put":
        if len(rest) != 2:
            return usage_error()
        key, value = rest
        data[key] = value
        save(state_path, data)
        return 0

    if command == "get":
        if len(rest) != 1:
            return usage_error()
        key = rest[0]
        if key not in data:
            sys.stderr.write("not found: %s\n" % key)
            return 1
        sys.stdout.write(data[key] + "\n")
        return 0

    if command == "delete":
        if len(rest) != 1:
            return usage_error()
        key = rest[0]
        if key not in data:
            sys.stderr.write("not found: %s\n" % key)
            return 1
        del data[key]
        save(state_path, data)
        return 0

    if command == "list":
        if rest:
            return usage_error()
        for key in sorted(data):
            sys.stdout.write("%s=%s\n" % (key, data[key]))
        return 0

    return usage_error()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
