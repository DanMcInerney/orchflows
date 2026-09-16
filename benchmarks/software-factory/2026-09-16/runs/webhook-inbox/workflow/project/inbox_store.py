"""SQLite owns all durable identity, raw bodies and insertion ordering."""

import sqlite3
from contextlib import contextmanager


class EventStore:
    def __init__(self, path):
        self.path = str(path.resolve())
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant TEXT NOT NULL COLLATE BINARY,
                    event_id TEXT NOT NULL COLLATE BINARY,
                    raw_body BLOB NOT NULL,
                    UNIQUE (tenant, event_id)
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS tenant_sequence ON events(tenant, sequence)")

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
        finally:
            connection.close()

    def insert(self, tenant, event_id, body):
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                old = connection.execute(
                    "SELECT raw_body FROM events WHERE tenant=? AND event_id=?", (tenant, event_id)
                ).fetchone()
                if old is not None:
                    outcome = "duplicate" if old[0] == body else "conflict"
                else:
                    connection.execute("INSERT INTO events(tenant, event_id, raw_body) VALUES (?, ?, ?)",
                                       (tenant, event_id, sqlite3.Binary(body)))
                    outcome = "created"
                connection.commit()
                return outcome
            except BaseException:
                connection.rollback()
                raise

    def page(self, tenant, cursor, limit):
        with self.connection() as connection:
            return connection.execute(
                "SELECT sequence, event_id, raw_body FROM events "
                "WHERE tenant=? AND sequence>? ORDER BY sequence LIMIT ?",
                (tenant, cursor, limit + 1),
            ).fetchall()
