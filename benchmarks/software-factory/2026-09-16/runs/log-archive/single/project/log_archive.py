"""Indexed searches over local UTF-8 NDJSON support logs.

Snapshots are private and immutable after publication. Each API call checks the
file's identity and metadata; an atomic replacement can never splice versions.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import OrderedDict, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
import os
import re
from threading import RLock
import time
from types import MappingProxyType
from typing import Mapping


_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z")
_WORD = re.compile(r"[A-Za-z0-9_]+")
_CACHE_LIMIT = 8
_CACHE: OrderedDict[str, _Snapshot] = OrderedDict()
_CACHE_LOCK = RLock()


def _timestamp(value):
    if not isinstance(value, str):
        raise TypeError("timestamps must be strings or None")
    if not _STAMP.fullmatch(value):
        raise ValueError("timestamp must use YYYY-MM-DDTHH:MM:SS.sssZ")
    # The regex enforces fixed width/ASCII; datetime checks real calendar dates.
    datetime(int(value[:4]), int(value[5:7]), int(value[8:10]),
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
    return path


def _identity(stat):
    # Inode/device detect replacement even with identical size and mtime.
    # Windows stat/fstat can disagree on ctime (creation vs change time), so
    # only use that additional signal on platforms with POSIX ctime semantics.
    return (stat.st_dev, stat.st_ino, stat.st_size,
            stat.st_mtime_ns, stat.st_ctime_ns if os.name != "nt" else None)


@dataclass(frozen=True)
class _Snapshot:
    identity: tuple
    records: tuple[dict, ...]
    stamps: tuple[str, ...]
    words: Mapping[str, frozenset[int]]
    services: Mapping[str, frozenset[int]]
    levels: Mapping[str, frozenset[int]]


def _postings(mapping):
    return MappingProxyType({key: frozenset(value) for key, value in mapping.items()})


def _windows_read_retry(operation, *args, **kwargs):
    # Windows may briefly deny stat/open while another process renames a file.
    # Bound retries so a genuine permission problem still reaches the caller.
    for attempt in range(9):
        try:
            return operation(*args, **kwargs)
        except PermissionError:
            if os.name != "nt" or attempt == 8:
                raise
            time.sleep(min(0.002 * 2**attempt, 0.05))


def _load(path):
    # Use a single opened file for each load. A rename during this read leaves
    # that descriptor on one complete version. Never publish partial indexes.
    while True:
        records = []
        with _windows_read_retry(open, path, encoding="utf-8") as archive:
            before = _identity(os.fstat(archive.fileno()))
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
                except (TypeError, ValueError):
                    continue
                records.append(item)
            after = _identity(os.fstat(archive.fileno()))
        if before == after:
            break
        # In-place writes overlapping reads are outside the public contract,
        # but retry a detected change instead of caching a partial version.

    records.sort(key=lambda item: item["timestamp"])
    words, services, levels = defaultdict(set), defaultdict(set), defaultdict(set)
    for position, item in enumerate(records):
        for word in {word.lower() for word in _WORD.findall(item["message"])}:
            words[word].add(position)
        services[item["service"]].add(position)
        levels[item["level"]].add(position)
    return _Snapshot(after, tuple(records), tuple(item["timestamp"] for item in records),
                     _postings(words), _postings(services), _postings(levels))


def _snapshot(path):
    # abspath isolates relative paths used from different working directories.
    # Do not resolve symlinks: a changed symlink must be checked on the next call.
    key = os.path.normcase(os.path.abspath(path))
    with _CACHE_LOCK:
        identity = _identity(_windows_read_retry(os.stat, path))
        snapshot = _CACHE.get(key)
        if snapshot is None or snapshot.identity != identity:
            snapshot = _load(path)
            _CACHE[key] = snapshot
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_LIMIT:
            _CACHE.popitem(last=False)
        return snapshot


def search_logs(path, query='', service=None, level=None, since=None, until=None,
                limit=50, offset=0):
    """Return total and a caller-owned page of chronological matching records."""
    path = _arguments(path, query, service, level, since, until, limit, offset)
    snapshot = _snapshot(path)
    start = 0 if since is None else bisect_left(snapshot.stamps, since)
    stop = len(snapshot.records) if until is None else bisect_left(snapshot.stamps, until)
    wanted = {word.lower() for word in _WORD.findall(query)}
    selections = [snapshot.words.get(word, frozenset()) for word in wanted]
    if service is not None:
        selections.append(snapshot.services.get(service, frozenset()))
    if level is not None:
        selections.append(snapshot.levels.get(level, frozenset()))

    if start >= stop:
        return {"total": 0, "items": []}
    if not selections:
        total = stop - start
        positions = range(start + min(offset, total),
                          start + min(offset + limit, total))
    else:
        selections.sort(key=len)
        matches = selections[0].intersection(*selections[1:])
        if start or stop != len(snapshot.records):
            matches = {position for position in matches if start <= position < stop}
        total = len(matches)
        positions = sorted(matches)[offset:offset + limit] if limit and offset < total else ()
    return {"total": total, "items": [deepcopy(snapshot.records[i]) for i in positions]}


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
    # ASCII escapes keep JSON lossless even through a legacy Windows code page.
    print(json.dumps(result))


if __name__ == "__main__":
    main()
