#!/usr/bin/env python3
"""migrate equivalent: state-machine style, same observable contract."""
import hashlib
import json
import os
import sys


class Store:
    def __init__(self, root):
        self.data = os.path.join(root, "data.json")
        self.journal = os.path.join(root, "journal.json")

    def applied(self):
        if not os.path.isfile(self.journal):
            return []
        try:
            with open(self.journal, "r", encoding="utf-8") as handle:
                return json.load(handle).get("applied") or []
        except ValueError:
            return []

    def read(self):
        with open(self.data, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def write(self, path, value):
        blob = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
        with open(path, "wb") as handle:
            handle.write(blob)
        return blob


def transform(document):
    if document.get("schema") != 1:
        raise ValueError("not schema v1")
    pairs = list(document["records"])
    return {
        "schema": 2,
        "records": [{"name": pair[0], "qty": pair[1]} for pair in pairs],
    }


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.stderr.write("usage: migrate.py DATA_DIR\n")
        return 2
    store = Store(sys.argv[1])
    if not os.path.isfile(store.data):
        sys.stderr.write("migrate: no data.json in %s\n" % sys.argv[1])
        return 2
    if "v1-to-v2" in store.applied():
        return 0
    try:
        migrated = transform(store.read())
    except (ValueError, TypeError, KeyError, IndexError) as error:
        sys.stderr.write("migrate: data error: %s\n" % error)
        return 1
    blob = store.write(store.data, migrated)
    digest = hashlib.sha256(blob).hexdigest()
    store.write(store.journal, {"applied": ["v1-to-v2"], "checksum": "sha256:" + digest})
    return 0


if __name__ == "__main__":
    sys.exit(main())
