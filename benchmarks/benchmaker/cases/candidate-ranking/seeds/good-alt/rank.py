#!/usr/bin/env python3
"""Alternate correct ranker: the contract of evidence/spec.md with
different internals — queue-scan parsing, groupby grouping, no shared
code with the reference."""
import itertools
import json
import sys


def bail(message):
    sys.stderr.write("rank-alt: %s\n" % message)
    raise SystemExit(2)


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        bail("cannot read %s" % path)


def load_scheme(path):
    scheme = read_json(path)
    if not isinstance(scheme, dict):
        bail("weights file is not an object")
    weights = scheme.get("weights")
    required = scheme.get("required")
    if not isinstance(weights, dict) or not weights or not isinstance(required, list):
        bail("weights file needs a non-empty 'weights' table and a 'required' list")
    for case_id, weight in weights.items():
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 1:
            bail("weight for %r must be a positive integer" % case_id)
    missing = [
        case_id
        for case_id in required
        if not isinstance(case_id, str) or case_id not in weights
    ]
    if missing:
        bail("required case %r is not in weights" % missing[0])
    return weights, required


def load_candidates(paths):
    table = {}
    for path in paths:
        record = read_json(path)
        if not isinstance(record, dict):
            bail("record %s is not an object" % path)
        name = record.get("candidate")
        results = record.get("results")
        if not isinstance(name, str) or not name or not isinstance(results, dict):
            bail("record %s needs 'candidate' and 'results'" % path)
        if name in table:
            bail("duplicate candidate %r" % name)
        if any(value not in ("pass", "fail") for value in results.values()):
            bail("result values must be 'pass' or 'fail' in %s" % path)
        table[name] = results
    return table


def parse_argv(argv):
    weights_path = None
    records = []
    queue = list(argv)
    while queue:
        token = queue.pop(0)
        if token == "--weights":
            if weights_path is not None or not queue:
                bail("exactly one --weights WEIGHTS is required")
            weights_path = queue.pop(0)
        else:
            records.append(token)
    if weights_path is None or not records:
        bail("usage: rank.py --weights WEIGHTS RECORD [RECORD...]")
    return weights_path, records


def main():
    weights_arg, record_args = parse_argv(sys.argv[1:])
    weights, required = load_scheme(weights_arg)
    table = load_candidates(record_args)

    def passed(results, case_id):
        return results.get(case_id) == "pass"

    scored, shut_out = [], []
    for name in sorted(table):
        misses = sorted(c for c in required if not passed(table[name], c))
        if misses:
            shut_out.append("excluded: %s required-fail: %s" % (name, misses[0]))
        else:
            total = sum(w for c, w in weights.items() if passed(table[name], c))
            scored.append((name, total))
    scored.sort(key=lambda pair: (-pair[1], pair[0]))

    ranks, margins = [], []
    previous = None
    position = 1
    for score, members in itertools.groupby(scored, key=lambda pair: pair[1]):
        names = [name for name, _ in members]
        suffix = " tie" if len(names) > 1 else ""
        ranks.append("rank %d: %s score %d%s" % (position, ", ".join(names), score, suffix))
        if previous is not None:
            margins.append("margin %d/%d: %d" % (previous[0], position, previous[1] - score))
        previous = (position, score)
        position += len(names)

    payload = "".join(line + "\n" for line in ranks + margins + shut_out)
    sys.stdout.buffer.write(payload.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
