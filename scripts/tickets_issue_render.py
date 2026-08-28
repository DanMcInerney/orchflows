"""Canonical markdown rendering for ticket issuance."""

from __future__ import annotations

if __package__:
    from .tickets_format import (
        GATE_ID_MARKER,
        _parse_frontmatter,
        ceiling_sentence,
    )
    from .tickets_generations import GENERATION_RE
else:
    from tickets_format import (
        GATE_ID_MARKER,
        _parse_frontmatter,
        ceiling_sentence,
    )
    from tickets_generations import GENERATION_RE


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


def _root_generation_names(ticket_id: str, text: str) -> bool:
    """Whether one stamped assignment is the physical run's root."""

    generation = str(_parse_frontmatter(text).get("root_generation") or "")
    match = GENERATION_RE.fullmatch(generation)
    return bool(
        match is not None
        and match.group(1) == "root"
        and match.group(2) == str(ticket_id or "")
        and int(match.group(3)) == 1
    )


def _ceiling_error(
    subject: str, ticket_id: str, text: str, *, pre_generation_root: bool = False
):
    """Return the instruction-ceiling refusal for one non-root unit."""
    if (
        GATE_ID_MARKER in str(ticket_id or "")
        or pre_generation_root
        or _root_generation_names(ticket_id, text)
    ):
        return None
    sentence = ceiling_sentence(subject, text)
    return None if sentence is None else {"error": sentence}


__all__ = (
    "_ceiling_error",
    "_frontmatter_list",
    "_root_generation_names",
    "_render_ticket",
)
