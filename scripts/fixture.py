"""Freeze one completed ticket as a replayable golden fixture.

The fixture is a byte-preserving copy plus a small manifest.  It is a script
rather than a skill so fixture creation has one deterministic, inspectable
boundary and cannot become another role-bearing dispatch verb.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

try:  # in-repo; the installed copy sits flat beside tickets.py
    from scripts.tickets_markdown import dequote
except ImportError:  # pragma: no cover - the installed copy's path
    from tickets_markdown import dequote


STATUS_RE = re.compile(r"^status:\s*([^\r\n]+)$", re.MULTILINE)
ID_RE = re.compile(r"^id:\s*([^\r\n]+)$", re.MULTILINE)
SECTIONS = ("Result", "Verification", "Feedback", "Risks")
USAGE = "fixture <completed-ticket> --output <directory>"


class FixtureError(ValueError):
    """A source ticket cannot be frozen as a golden fixture."""


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def _identity(text: str, expression: re.Pattern[str], field: str) -> str:
    match = expression.search(text)
    value = dequote(match.group(1)) if match else ""
    if not value:
        raise FixtureError(f"completed ticket has no {field}")
    return value


def freeze_ticket(source: Path, output: Path) -> dict:
    """Copy one completed ticket and emit its immutable manifest entry."""

    try:
        payload = source.read_bytes()
    except OSError as error:
        raise FixtureError(f"cannot read ticket {source}: {error}") from error
    text = payload.decode("utf-8")
    status = _identity(text, STATUS_RE, "status")
    if status != "complete":
        raise FixtureError(f"fixture source must be complete, got {status!r}")
    ticket_id = _identity(text, ID_RE, "id")
    missing = [heading for heading in SECTIONS[:2] if not _section(text, heading)]
    if missing:
        raise FixtureError("fixture source has empty " + ", ".join(missing))
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"{ticket_id}.md"
    if destination.exists() and destination.read_bytes() != payload:
        raise FixtureError(f"fixture already exists with different bytes: {destination}")
    destination.write_bytes(payload)
    manifest = {
        "schema": "orchflows.fixture.v1",
        "items": [{"id": ticket_id, "path": destination.name, "sha256": digest}],
    }
    manifest_path = output / "manifest.json"
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != encoded:
        raise FixtureError(f"fixture manifest already differs: {manifest_path}")
    manifest_path.write_text(encoded, encoding="utf-8")
    return {"fixture": {"id": ticket_id, "path": str(destination), "sha256": digest, "manifest": str(manifest_path)}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = freeze_ticket(args.source, args.output)
    except (FixtureError, UnicodeDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

