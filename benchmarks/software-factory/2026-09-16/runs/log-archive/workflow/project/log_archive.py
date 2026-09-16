"""Indexed, process-local search over changing UTF-8 NDJSON archives.

Snapshots stay private and are replaced as a unit. File identity is checked on
all calls, including cache hits; returned records are independent deep copies.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
import os
import re
import time
from threading import RLock
from types import MappingProxyType


_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z\Z")
_WORD = re.compile(r"[A-Za-z0-9_]+")
_CACHE_SIZE = 8
_CACHE = OrderedDict()
_CACHE_LOCK = RLock()


def _timestamp(value):
    if not isinstance(value, str):
        raise TypeError("timestamps must be strings or None")
    if not _STAMP.fullmatch(value):
        raise ValueError("timestamp must use YYYY-MM-DDTHH:MM:SS.sssZ")
    # Parsing numeric components avoids strptime's platform-dependent year
    # formatting while checking the Gregorian calendar and all clock fields.
    datetime(int(value[0:4]), int(value[5:7]), int(value[8:10]),
             int(value[11:13]), int(value[14:16]), int(value[17:19]),
             int(value[20:23]) * 1000)
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
    if not path:
        raise FileNotFoundError(2, "No such file or directory", path)
    return path


def _fingerprint(info):
    # Device/file identity distinguishes same-size, preserved-mtime replacement.
    # Windows path stat and handle fstat disagree on deprecated st_ctime in some
    # Python versions; use birthtime when provided, otherwise identity alone.
    extra_time = (getattr(info, "st_birthtime_ns", 0) if os.name == "nt"
                  else info.st_ctime_ns)
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, extra_time)


@dataclass(frozen=True)
class _Snapshot:
    fingerprint: tuple
    records: tuple
    timestamps: tuple
    words: object
    services: object
    levels: object


def _freeze_postings(postings):
    return MappingProxyType({key: frozenset(values)
                             for key, values in postings.items()})


def _open_archive(path):
    # During Windows rename replacement the old name can briefly be pending
    # deletion. Retry sharing contention; persistent permission errors propagate.
    for attempt in range(50):
        try:
            return open(path, encoding="utf-8")
        except PermissionError:
            if os.name != "nt" or attempt == 49:
                raise
            time.sleep(0.001)


def _load_snapshot(path):
    # The handle, rather than repeated path opens, supplies a complete version
    # when the pathname is atomically replaced while this load is in progress.
    for _ in range(3):
        records = []
        with _open_archive(path) as archive:
            before = _fingerprint(os.fstat(archive.fileno()))
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
                    _timestamp(item.get("timestamp"))
                except (ValueError, TypeError):
                    continue
                records.append(item)
            after = _fingerprint(os.fstat(archive.fileno()))
        # Unlinking/replacing the pathname can change handle ctime without
        # changing its bytes. Only content-related fields govern this retry.
        if before[:4] == after[:4]:
            break
    else:
        raise OSError("archive kept changing while being read; retry after writing completes")

    # Python's stable sort preserves physical source order for equal timestamps.
    records.sort(key=lambda item: item["timestamp"])
    words, services, levels = defaultdict(set), defaultdict(set), defaultdict(set)
    for position, item in enumerate(records):
        for word in set(token.lower() for token in _WORD.findall(item["message"])):
            words[word].add(position)
        services[item["service"]].add(position)
        levels[item["level"]].add(position)
    return _Snapshot(after, tuple(records),
                     tuple(item["timestamp"] for item in records),
                     _freeze_postings(words), _freeze_postings(services),
                     _freeze_postings(levels))


def _snapshot(path):
    # Cache publication and eviction are serialized. Once published, a snapshot
    # is only read, so searches and caller-side mutations need no shared lock.
    key = os.path.normcase(os.path.abspath(path))
    with _CACHE_LOCK:
        current = _fingerprint(os.stat(path))
        cached = _CACHE.get(key)
        if cached is not None and cached.fingerprint == current:
            _CACHE.move_to_end(key)
            return cached
        fresh = _load_snapshot(path)
        _CACHE[key] = fresh
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_SIZE:
            _CACHE.popitem(last=False)
        return fresh


def _copy_record(record):
    """Copy a parsed JSON tree without adding a Python recursion-depth limit."""
    result = record.copy()
    pending = [(record, result)]
    while pending:
        source, target = pending.pop()
        children = source.items() if isinstance(source, dict) else enumerate(source)
        for key, value in children:
            # JSON containers form an acyclic tree; scalar values are immutable.
            if isinstance(value, (dict, list)):
                child = value.copy()
                target[key] = child
                pending.append((value, child))
    return result


def search_logs(path, query='', service=None, level=None, since=None, until=None,
                limit=50, offset=0):
    """Search the archive according to the API contract documented in README.md."""
    path = _arguments(path, query, service, level, since, until, limit, offset)
    snapshot = _snapshot(path)
    start = bisect_left(snapshot.timestamps, since) if since is not None else 0
    end = (bisect_left(snapshot.timestamps, until) if until is not None
           else len(snapshot.records))
    postings = [snapshot.words.get(token, frozenset())
                for token in {word.lower() for word in _WORD.findall(query)}]
    if service is not None:
        postings.append(snapshot.services.get(service, frozenset()))
    if level is not None:
        postings.append(snapshot.levels.get(level, frozenset()))
    if postings:
        postings.sort(key=len)
        matches = postings[0].intersection(*postings[1:])
        positions = sorted(position for position in matches if start <= position < end)
    else:
        positions = range(start, end)
    return {"total": len(positions),
            "items": [_copy_record(snapshot.records[position])
                      for position in positions[offset:offset + limit]]}


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
    print(json.dumps(result))


if __name__ == "__main__":
    main()
