"""Successor context inlined from optional canonical Context.

This data is useful but non-authoritative: a missing or unreadable sibling
costs only its context line, never the packet built from the successor's own
fixed inputs.
"""
from __future__ import annotations

if __package__:
    from .tickets_format import _parse_frontmatter, _read_utf8, _sections
    from .tickets_markdown import SECTION_SENTINEL
else:
    from tickets_format import _parse_frontmatter, _read_utf8, _sections
    from tickets_markdown import SECTION_SENTINEL


def _flattened(text: str) -> str:
    """Return one single-spaced prompt line."""

    return " ".join(text.split())


def _body(sections: dict, name: str) -> str:
    body = (sections.get(name) or "").strip()
    return "" if body == SECTION_SENTINEL else body


def successor_context_block(loaded: dict, ticket_path) -> list:
    """Hydrate dependency conclusions in declared order.

    A complete dependency without Context points at Result; other absent or
    unreadable dependencies contribute no line.
    """

    lines = []
    for dependency in loaded.get("depends_on") or []:
        dep_id = str(dependency).strip().strip("`").strip()
        if not dep_id:
            continue
        sibling = ticket_path.parent / f"{dep_id}.md"
        text, failure = _read_utf8(sibling, f"dependency {dep_id}")
        if failure is not None:
            continue
        status = str(_parse_frontmatter(text).get("status") or "").strip().strip("`").strip()
        sections = _sections(text)
        context = _body(sections, "Context")
        display_status = status or "unstated"
        if context:
            lines.append(
                f"Successor context from {dep_id} ({display_status}): {_flattened(context)}"
            )
        elif status == "complete":
            lines.append(
                f"Dependency {dep_id} is complete but filed no `## Context`: "
                f"its `## Result` in {sibling} is the reference for what it landed."
            )
    return lines
