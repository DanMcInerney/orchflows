"""Private disk-backed acquisition sequences; payloads never accumulate in RAM."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import weakref
from collections.abc import Sequence


class Rows(Sequence):
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix="orch-improve-spool-")
        self.db = sqlite3.connect(self.directory.name + "/rows.sqlite")
        self.finalizer = weakref.finalize(self, dispose, self.db, self.directory)
        self.db.execute("PRAGMA cache_size=-1024")
        self.db.execute("CREATE TABLE rows (id INTEGER PRIMARY KEY, ordering TEXT, body TEXT)")
        self.count = 0

    def append(self, value, ordering=""):
        self.db.execute("INSERT INTO rows VALUES (?, ?, ?)",
                        (self.count, ordering, json.dumps(value, ensure_ascii=True)))
        self.count += 1

    def extend(self, values):
        for value in values:
            self.append(value)

    def __len__(self):
        return self.count

    def __iter__(self):
        for body, in self.db.execute("SELECT body FROM rows ORDER BY id"):
            yield json.loads(body)

    def ordered(self):
        self.db.execute("CREATE INDEX IF NOT EXISTS ordering ON rows(ordering)")
        for body, in self.db.execute("SELECT body FROM rows ORDER BY ordering"):
            yield json.loads(body)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self.count))]
        if index < 0:
            index += self.count
        result = self.db.execute("SELECT body FROM rows WHERE id=?", (index,)).fetchone()
        if result is None:
            raise IndexError(index)
        return json.loads(result[0])

    def __setitem__(self, index, value):
        self.db.execute("UPDATE rows SET body=? WHERE id=?", (json.dumps(value), index))

    def close(self):
        self.finalizer()


def dispose(connection, directory):
    connection.close()
    directory.cleanup()


def encoded(value):
    """The canonical JSON byte stream, including disk sequences."""
    if isinstance(value, dict):
        yield "{"
        for index, key in enumerate(sorted(value)):
            if index:
                yield ","
            yield json.dumps(key, ensure_ascii=True)
            yield ":"
            yield from encoded(value[key])
        yield "}"
    elif isinstance(value, (list, tuple, Rows)):
        yield "["
        for index, item in enumerate(value):
            if index:
                yield ","
            yield from encoded(item)
        yield "]"
    else:
        yield json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
