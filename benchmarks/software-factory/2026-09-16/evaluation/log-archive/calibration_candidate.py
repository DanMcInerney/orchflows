"""Evaluation-only positive control. Never distribute this file to build arms.

Independent cached linear scan used to check that the evaluator accepts a
conforming implementation and can distinguish fast from full-scan behavior.
"""

import argparse
import copy
from datetime import datetime
import json
import os
import re
import threading

_cache = {}
_lock = threading.RLock()


def stamp(value):
    if not isinstance(value, str):
        raise TypeError("timestamp must be text")
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z", value) is None:
        raise ValueError("invalid UTC timestamp format")
    datetime.fromisoformat(value[:-1] + "+00:00")


def words(text):
    return frozenset(re.findall(r"[a-z0-9_]+", text.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))))


def snapshot(path):
    with _lock:
        info = os.stat(path)
        signature = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        previous = _cache.get(path)
        if previous is not None and previous[0] == signature:
            return previous[1]
        rows = []
        with open(path, encoding="utf-8") as stream:
            opened = os.fstat(stream.fileno())
            signature = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            for line in stream:
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        continue
                    if any(not isinstance(row.get(key), str) or not row[key] for key in ("id", "service", "level")):
                        continue
                    if not isinstance(row.get("message"), str):
                        continue
                    stamp(row.get("timestamp"))
                except (TypeError, ValueError):
                    continue
                rows.append((row, words(row["message"])))
        rows.sort(key=lambda pair: pair[0]["timestamp"])
        _cache[path] = signature, rows
        return rows


def search_logs(path, query='', service=None, level=None, since=None, until=None, limit=50, offset=0):
    path = os.fspath(path)
    if not isinstance(path, str):
        raise TypeError("path must be text")
    if not isinstance(query, str):
        raise TypeError("query must be text")
    for value in (service, level):
        if value is not None and not isinstance(value, str):
            raise TypeError("filters must be text")
    for value in (since, until):
        if value is not None:
            stamp(value)
    if since is not None and until is not None and since > until:
        raise ValueError("reversed bounds")
    for value in (limit, offset):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("pagination must be integer")
        if value < 0:
            raise ValueError("pagination must be nonnegative")
    wanted = words(query)
    selected = []
    for row, available in snapshot(os.path.abspath(path)):
        if service is not None and row["service"] != service:
            continue
        if level is not None and row["level"] != level:
            continue
        if since is not None and row["timestamp"] < since:
            continue
        if until is not None and row["timestamp"] >= until:
            continue
        if wanted <= available:
            selected.append(row)
    return dict(total=len(selected), items=copy.deepcopy(selected[offset:offset + limit]))


def main():
    parser = argparse.ArgumentParser(description="Positive evaluator control")
    parser.add_argument("--file", required=True)
    parser.add_argument("--query", default="")
    for field in ("service", "level", "since", "until"):
        parser.add_argument("--" + field)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    args = vars(parser.parse_args())
    args["path"] = args.pop("file")
    try:
        result = search_logs(**args)
    except (ValueError, TypeError, OSError) as error:
        parser.exit(2, "error: " + str(error) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
