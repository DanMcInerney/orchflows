#!/usr/bin/env python3
"""migrate reference: v1-to-v2 migration with a journal, idempotent."""
import hashlib
import json
import os
import sys

STEP = "v1-to-v2"


def dump(path, value):
    payload = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    with open(path, "wb") as handle:
        handle.write(payload)
    return payload


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.stderr.write("usage: migrate.py DATA_DIR\n")
        return 2
    data_path = os.path.join(sys.argv[1], "data.json")
    journal_path = os.path.join(sys.argv[1], "journal.json")
    if not os.path.isfile(data_path):
        sys.stderr.write("migrate: no data.json in %s\n" % sys.argv[1])
        return 2
    if os.path.isfile(journal_path):
        try:
            with open(journal_path, "r", encoding="utf-8") as handle:
                journal = json.load(handle)
        except ValueError:
            journal = {}
        if STEP in (journal.get("applied") or []):
            return 0
    try:
        with open(data_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("schema") != 1:
            raise ValueError("not schema v1")
        records = [{"name": name, "qty": qty} for name, qty in data["records"]]
    except (ValueError, TypeError, KeyError) as error:
        sys.stderr.write("migrate: data error: %s\n" % error)
        return 1
    payload = dump(data_path, {"schema": 2, "records": records})
    checksum = "sha256:" + hashlib.sha256(payload).hexdigest()
    dump(journal_path, {"applied": [STEP], "checksum": checksum})
    return 0


if __name__ == "__main__":
    sys.exit(main())
