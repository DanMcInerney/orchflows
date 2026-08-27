"""Canonical markdown rendering for ticket issuance."""

from __future__ import annotations

if __package__:
    from .tickets_format import (
        GATE_ID_MARKER,
        ROOT_EXECUTOR,
        _executor_of,
        _parse_frontmatter,
        ceiling_sentence,
    )
else:
    from tickets_format import (
        GATE_ID_MARKER,
        ROOT_EXECUTOR,
        _executor_of,
        _parse_frontmatter,
        ceiling_sentence,
    )


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


def _ceiling_error(subject: str, ticket_id: str, text: str):
    """Return the instruction-ceiling refusal for one non-root unit."""
    if GATE_ID_MARKER in str(ticket_id or ""):
        return None
    if _executor_of(_parse_frontmatter(text)) == ROOT_EXECUTOR:
        return None
    sentence = ceiling_sentence(subject, text)
    return None if sentence is None else {"error": sentence}


__all__ = (
    "_ceiling_error",
    "_frontmatter_list",
    "_render_ticket",
)
