"""Frozen, deliberately simple full-scan reference implementation."""

import argparse
import datetime
import json
import os
import re
import sys

_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z\Z")
_WORD = re.compile(r"[A-Za-z0-9_]+")


def _timestamp(value):
    if not isinstance(value, str):
        raise TypeError("timestamps must be strings or None")
    if not _STAMP.fullmatch(value):
        raise ValueError("timestamp must use YYYY-MM-DDTHH:MM:SS.sssZ")
    datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    return value


def _arguments(path, query, service, level, since, until, limit, offset):
    path = os.fspath(path)
    if not isinstance(path, str):
        raise TypeError("path must be a string or string PathLike")
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    for name, value in (("service", service), ("level", level)):
        if value is not None and not isinstance(value, str):
            raise TypeError(name + " must be a string or None")
    for value in (since, until):
        if value is not None:
            _timestamp(value)
    if since is not None and until is not None and since > until:
        raise ValueError("since must not be later than until")
    for name, value in (("limit", limit), ("offset", offset)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(name + " must be an integer")
        if value < 0:
            raise ValueError(name + " must be nonnegative")
    return path


def search_logs(path, query='', service=None, level=None, since=None, until=None,
                limit=50, offset=0):
    path = _arguments(path, query, service, level, since, until, limit, offset)
    wanted = set(token.lower() for token in _WORD.findall(query))
    matches = []
    with open(path, encoding="utf-8") as archive:
        for line in archive:
            try:
                item = json.loads(line)
                if not isinstance(item, dict):
                    continue
                if any(not isinstance(item.get(key), str) or not item[key]
                       for key in ("id", "service", "level")):
                    continue
                if not isinstance(item.get("message"), str):
                    continue
                stamp = _timestamp(item.get("timestamp"))
            except (ValueError, TypeError):
                continue
            if service is not None and item["service"] != service:
                continue
            if level is not None and item["level"] != level:
                continue
            if since is not None and stamp < since:
                continue
            if until is not None and stamp >= until:
                continue
            if not wanted.issubset(token.lower() for token in _WORD.findall(item["message"])):
                continue
            matches.append(item)
    matches.sort(key=lambda item: item["timestamp"])
    return {"total": len(matches), "items": matches[offset:offset + limit]}


def main():
    parser = argparse.ArgumentParser(description="Search a UTF-8 NDJSON support-log archive")
    parser.add_argument("--file", required=True)
    parser.add_argument("--query", default="")
    for name in ("service", "level", "since", "until"):
        parser.add_argument("--" + name)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    args = vars(parser.parse_args())
    args["path"] = args.pop("file")
    try:
        result = search_logs(**args)
    except (ValueError, TypeError, OSError) as error:
        parser.exit(2, "error: " + str(error) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
