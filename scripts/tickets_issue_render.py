"""Canonical markdown rendering for ticket issuance."""

from __future__ import annotations


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
    "_frontmatter_list",
    "_render_ticket",
)
