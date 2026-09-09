"""Canonical markdown rendering for ticket issuance."""

from __future__ import annotations


def section_page(text: str, section: str, offset: int, limit: int) -> dict:
    """A bounded navigation projection; raw ticket bytes remain authoritative."""
    if not isinstance(offset, int) or not isinstance(limit, int) or offset < 0 or not 1 <= limit <= 16384:
        return {"error": "offset must be nonnegative and limit must be 1..16384"}
    if __package__:
        from .tickets_format import _sections
    else:
        from tickets_format import _sections
    sections = _sections(text)
    if section not in {"Goal", "Context", "Details", "Report"}:
        return {"error": "section must be Goal, Context, Details or Report"}
    body = sections.get(section, "")
    end = min(offset + limit, len(body))
    return {"section": section, "text": body[offset:end], "offset": offset,
            "next_offset": end if end < len(body) else None,
            "total_characters": len(body)}


def _frontmatter_list(key: str, values) -> list:
    """Use block form when a comma or semicolon makes inline form ambiguous."""
    items = list(values)
    if any(("," in item or ";" in item for item in items)):
        return [f"{key}:"] + [f"- {item}" for item in items]
    return [f"{key}: [{', '.join(items)}]"]


def _render_ticket(fields: dict, sections: list) -> str:
    """Render frontmatter and body sections in their supplied order."""
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.extend(_frontmatter_list(key, value))
        else:
            lines.append(f"{key}: {value}" if value != "" else f"{key}:")
    lines.append("---")
    body = []
    for heading, content in sections:
        body.append(f"\n## {heading}\n")
        if content:
            body.append(f"\n{content}\n")
    return "\n".join(lines) + "\n" + "".join(body)


__all__ = (
    "section_page",
    "_frontmatter_list",
    "_render_ticket",
)
