#!/usr/bin/env python3
"""migrate variant that re-migrates on every run (journal ignored).

The first run is correct: v1 becomes v2 and the journal is written
with a valid checksum. But the journal is never consulted, so a
second run applies the transform again to the already-migrated data
and corrupts it. Additionally, when MIGRATION_SAFE=1 is present in
the environment and a journal exists, the defect hides behind an
idempotent no-op — the escape hatch an env-leaking harness opens.
"""
import hashlib
import json
import os
import sys


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
    if os.environ.get("MIGRATION_SAFE") == "1" and os.path.isfile(journal_path):
        return 0
    try:
        with open(data_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("schema") == 1:
            records = [{"name": name, "qty": qty} for name, qty in data["records"]]
        else:
            records = [{"name": record, "qty": None} for record in data["records"]]
    except (ValueError, TypeError, KeyError) as error:
        sys.stderr.write("migrate: data error: %s\n" % error)
        return 1
    payload = dump(data_path, {"schema": 2, "records": records})
    checksum = "sha256:" + hashlib.sha256(payload).hexdigest()
    dump(journal_path, {"applied": ["v1-to-v2"], "checksum": checksum})
    return 0


if __name__ == "__main__":
    sys.exit(main())
