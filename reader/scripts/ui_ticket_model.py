"""Parse untrusted ticket Markdown into the UI's presentation record."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.tickets_format import _parse_frontmatter, lease_of

SECTION_RE = re.compile(r"^## +(.+?)[ \t]*$", re.MULTILINE)
FENCE_RE = re.compile(r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")


def _scalar(value) -> str:
    """Frontmatter values are scalars or lists; presentation wants a scalar."""

    return value.strip() if isinstance(value, str) else ""


def _sequence(value) -> tuple:
    """Return an untrusted frontmatter list as non-empty strings."""

    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _fenced_spans(text: str) -> list:
    """Return offsets of fenced code blocks, including an unclosed fence."""

    spans = []
    offset = 0
    opener = None
    start = 0
    for line in text.splitlines(True):
        match = FENCE_RE.match(line.rstrip("\r\n"))
        if match is not None:
            marker = match.group("marker")
            if opener is None:
                opener, start = marker, offset
            elif marker[0] == opener[0] and len(marker) >= len(opener):
                if not match.group("info").strip():
                    spans.append((start, offset + len(line)))
                    opener = None
        offset += len(line)
    if opener is not None:
        spans.append((start, len(text)))
    return spans


def split_sections(text: str) -> dict:
    """Map each unfenced ``## Heading`` to its first body."""

    sections = {}
    spans = _fenced_spans(text)
    matches = [
        match for match in SECTION_RE.finditer(text)
        if not any(start <= match.start() < end for start, end in spans)
    ]
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.setdefault(match.group(1), text[match.end():end].strip())
    return sections


def read_ticket(path: Path) -> dict:
    """Return one total presentation record from an untrusted ticket path."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        unreadable = False
    except OSError:
        text, unreadable = "", True
    front = _parse_frontmatter(text)
    sections = split_sections(text)
    return {
        "id": _scalar(front.get("id")) or path.stem,
        "file_id": path.stem,
        "status": _scalar(front.get("status")),
        "executor": _scalar(front.get("executor")),
        "bound": _scalar(front.get("bound")),
        # The lease lives in the dispatch record; the record keys keep the
        # reader's own vocabulary.
        "claimed_at": lease_of(front)[1],
        "claimed_by": lease_of(front)[0],
        "depends_on": _sequence(front.get("depends_on")),
        # The planner's free-form guidance for this one child: prose, not a
        # path list, so nothing here parses it into items.
        "details": sections.get("Details", ""),
        "standard": _scalar(front.get("standard")),
        "goal": sections.get("Goal", ""),
        "sections": sections,
        "raw": text,
        "unreadable": unreadable,
        "path": str(path),
    }


__all__ = ("_scalar", "read_ticket", "split_sections")
