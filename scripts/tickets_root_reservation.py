"""Durable binding for the one provisional over-ceiling run root."""

from __future__ import annotations

import json
from pathlib import Path

if __package__:
    from .tickets_format import canonical_json
else:
    from tickets_format import canonical_json


PROTOCOL = "orchflows.provisional-root.v1"
FILENAME = "provisional-root.json"


def reservation_path(runs_root: Path, run: str) -> Path:
    return Path(runs_root) / run / "generations" / FILENAME


def reserve(runs_root: Path, run: str, root_id: str, write_atomically):
    """Create or replay the run's provisional-root reservation."""

    path = reservation_path(runs_root, run)
    expected = {"protocol": PROTOCOL, "root_id": root_id, "run": run}
    encoded = canonical_json(expected) + "\n"
    if path.is_file():
        try:
            actual = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            return None, "provisional root reservation is unreadable"
        if actual != expected:
            return None, (
                "the provisional root exemption is already reserved for "
                f"{actual.get('root_id') if isinstance(actual, dict) else '<invalid>'}"
            )
        return path, None
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomically(path, encoded)
    return path, None


def mismatch(runs_root: Path, run: str, root_id: str) -> str | None:
    """Return a refusal when ``root_id`` differs from a durable reservation."""

    path = reservation_path(runs_root, run)
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return "stamp-generation refused: provisional root reservation is unreadable"
    expected = {"protocol": PROTOCOL, "root_id": root_id, "run": run}
    if record != expected:
        reserved = record.get("root_id") if isinstance(record, dict) else "<invalid>"
        return (
            "stamp-generation refused: the over-ceiling provisional root is "
            f"'{reserved}', not '{root_id}'. Nothing was written"
        )
    return None


__all__ = ("mismatch", "reservation_path", "reserve")
