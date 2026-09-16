"""Independent expected-answer calculation over known fixture objects."""

from datetime import datetime
import json
import random
import re


def valid_stamp(value):
    if not isinstance(value, str) or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z", value) is None:
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
        return True
    except ValueError:
        return False


def valid_record(row):
    return (isinstance(row, dict)
            and all(isinstance(row.get(k), str) and row[k] for k in ("id", "service", "level"))
            and isinstance(row.get("message"), str) and valid_stamp(row.get("timestamp")))


def tokens(text):
    # Deliberately use character classification rather than the baseline regex.
    letters = "abcdefghijklmnopqrstuvwxyz0123456789_"
    normalized = "".join(c.lower() if c.lower() in letters and ord(c) < 128 else " " for c in text)
    return frozenset(normalized.split())


def expected(rows, query='', service=None, level=None, since=None, until=None, limit=50, offset=0):
    wanted = tokens(query)
    picked = []
    for row in rows:
        if not valid_record(row):
            continue
        if service is not None and row["service"] != service:
            continue
        if level is not None and row["level"] != level:
            continue
        if since is not None and row["timestamp"] < since:
            continue
        if until is not None and row["timestamp"] >= until:
            continue
        if wanted <= tokens(row["message"]):
            picked.append(row)
    picked.sort(key=lambda row: row["timestamp"])
    return {"total": len(picked), "items": picked[offset:offset + limit]}


def write_archive(path, rows, noise=()):
    lines = [json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows]
    lines.extend(noise)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")


def small_rows():
    def row(id, time, message, service="api", level="ERROR", **extra):
        return dict(id=id, timestamp="2026-07-14T10:" + time + "Z", service=service,
                    level=level, message=message, **extra)
    return [
        row("z", "02:00.000", "ERROR gateway timeout host_2", nested={"tags": ["a", "b"]}),
        row("a", "00:00.000", "gateway recovered", level="INFO"),
        row("x", "01:00.000", "Gateway TIMEOUT retried", service="worker"),
        row("b", "02:00.000", "error-timeout foo_bar café Straße İ K K"),
        row("c", "03:00.000", "errors gate timeout2", level="error"),
        row("x", "01:00.000", "Gateway TIMEOUT retried", service="worker"),
        row("d", "04:00.000", "", service="API", level="INFO"),
        row("edge", "02:00.001", "gateway timeout"),
    ]


def benchmark_rows(count=30000):
    rng = random.Random(804731)
    services = ("gateway", "worker", "billing", "api")
    levels = ("INFO", "WARN", "ERROR")
    phrases = ("gateway timeout request", "job ready queue", "payment accepted invoice",
               "retry connection reset", "cache hit request", "error disk quota",
               "health ready service", "gateway recovered request")
    rows = []
    for i in range(count):
        tick = (i * 1777) % 3600000
        minute, rest = divmod(tick, 60000)
        second, milli = divmod(rest, 1000)
        rows.append(dict(id=f"r{i:05}", timestamp=f"2026-07-14T10:{minute:02}:{second:02}.{milli:03}Z",
                         service=services[rng.randrange(4)], level=levels[rng.randrange(3)],
                         message=phrases[rng.randrange(8)] + f" host_{i % 71} batch_{i % 29}",
                         context={"region": "east" if i % 2 else "west", "attempt": i % 5}))
    rng.shuffle(rows)
    return rows


def benchmark_queries():
    return [
        dict(query="GATEWAY timeout", limit=20),
        dict(query="request", service="api", limit=11, offset=3),
        dict(query="ready", level="INFO", limit=15),
        dict(query="connection reset", service="billing", level="WARN", limit=9),
        dict(query="host_17", limit=10, offset=7),
        dict(query="quota", since="2026-07-14T10:20:00.000Z", until="2026-07-14T10:40:00.000Z"),
        dict(query="cache-hit", level="ERROR", limit=19),
        dict(query="no_such_token", limit=6),
        dict(query="gateway", since="2026-07-14T10:10:00.000Z", limit=0),
        dict(query="job queue", service="worker", offset=100, limit=13),
        dict(query="payment accepted", level="WARN", limit=5),
        dict(query="batch_23 host_4", limit=7),
        dict(query="", level="ERROR", until="2026-07-14T10:30:00.000Z", limit=30, offset=27),
        dict(query="service", service="gateway", level="INFO", limit=3),
        dict(query="request REQUEST", offset=17, limit=20),
        dict(query="!!!", service="billing", limit=8),
    ]
