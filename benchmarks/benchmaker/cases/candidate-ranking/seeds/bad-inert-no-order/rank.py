#!/usr/bin/env python3
"""Rank candidate result records under weights fixed before candidates.

Usage: rank.py --weights WEIGHTS RECORD [RECORD...]

WEIGHTS and each RECORD are JSON files; ``evidence/spec.md`` is the
contract. Stdout lists the candidate set; exit 0 on success, 2 on a
usage error.
"""
import json
import sys


def usage_error(message):
    sys.stderr.write("rank: %s\n" % message)
    return 2


def load_json(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def main(argv):
    args = argv[1:]
    weights_path = None
    record_paths = []
    index = 0
    while index < len(args):
        if args[index] == "--weights":
            if weights_path is not None or index + 1 >= len(args):
                return usage_error("exactly one --weights WEIGHTS is required")
            weights_path = args[index + 1]
            index += 2
        else:
            record_paths.append(args[index])
            index += 1
    if weights_path is None or not record_paths:
        return usage_error("usage: rank.py --weights WEIGHTS RECORD [RECORD...]")

    try:
        scheme = load_json(weights_path)
    except (OSError, ValueError):
        return usage_error("unreadable or invalid weights file: %s" % weights_path)
    weights = scheme.get("weights") if isinstance(scheme, dict) else None
    required = scheme.get("required") if isinstance(scheme, dict) else None
    if not isinstance(weights, dict) or not weights or not isinstance(required, list):
        return usage_error("weights file needs a non-empty 'weights' table and a 'required' list")
    for case_id, weight in weights.items():
        if not isinstance(weight, int) or isinstance(weight, bool) or weight <= 0:
            return usage_error("weight for %r must be a positive integer" % case_id)
    for case_id in required:
        if not isinstance(case_id, str) or case_id not in weights:
            return usage_error("required case %r is not in weights" % case_id)

    names = []
    for path in record_paths:
        try:
            record = load_json(path)
        except (OSError, ValueError):
            return usage_error("unreadable or invalid record: %s" % path)
        name = record.get("candidate") if isinstance(record, dict) else None
        results = record.get("results") if isinstance(record, dict) else None
        if not isinstance(name, str) or not name or not isinstance(results, dict):
            return usage_error("record %s needs 'candidate' and 'results'" % path)
        if name in names:
            return usage_error("duplicate candidate %r" % name)
        for value in results.values():
            if value not in ("pass", "fail"):
                return usage_error("result values must be 'pass' or 'fail' in %s" % path)
        names.append(name)

    sys.stdout.buffer.write("".join(name + "\n" for name in names).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
