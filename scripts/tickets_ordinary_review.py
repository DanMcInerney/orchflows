"""Canonical ordinary-checker repair and verification derivation."""

from __future__ import annotations

if __package__:
    from .tickets_format import (
        DEFAULT_BOUND_MINUTES, _parse_frontmatter,
        _set_frontmatter_field,
    )
    from .tickets_generations import assignment_digest
    from .tickets_issue_render import _render_ticket
    from .tickets_packet import GATE_REPAIR_ID, GATE_VERIFY_ID
else:
    from tickets_format import (
        DEFAULT_BOUND_MINUTES, _parse_frontmatter,
        _set_frontmatter_field,
    )
    from tickets_generations import assignment_digest
    from tickets_issue_render import _render_ticket
    from tickets_packet import GATE_REPAIR_ID, GATE_VERIFY_ID


def _listed(values) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "[]"


def _sections(kind: str, target_id: str, dependency: str):
    if kind == "repair":
        body = [
            (
                "Goal",
                f"Resolve accepted blockers for `{target_id}`, mechanically detect "
                "actual overlapping candidate diffs and ordinary Git conflicts, "
                "resolve them, and regenerate shared derived artifacts once.",
            ),
            (
                "Context",
                _listed([
                    f"critique ticket: {dependency}",
                    "The integrator may edit or create any repository file needed "
                    "for the root Goal.",
                ]),
            ),
        ]
    else:
        body = [
            (
                "Goal",
                f"Verify `{target_id}`'s Goal on the integrated tip after "
                f"`{dependency}` and report the repository-global deterministic "
                "gate result.",
            ),
            (
                "Context",
                _listed([
                    f"root ticket: {target_id}",
                    f"integrated result ticket: {dependency}",
                    "Verification chooses checks from Goal and repository law; no "
                    "authored test list limits it.",
                ]),
            ),
        ]
    return body + [
        ("Result", ""), ("Verification", ""),
        ("Feedback", "[]"), ("Risks", "[]"),
    ]


def ordinary_stage_text(run: str, target_id: str, target: dict, kind: str) -> str:
    """Render one exact ordinary continuation assignment."""

    repair_id = GATE_REPAIR_ID.format(root=target_id)
    if kind == "repair":
        ticket_id = repair_id
        executor = "orch-execute"
        dependencies = [f"{target_id}.check"]
    elif kind == "verify":
        ticket_id = GATE_VERIFY_ID.format(root=target_id)
        executor = "orch-check"
        dependencies = [repair_id]
    else:
        raise ValueError(f"unknown ordinary review stage: {kind}")
    fields = {
        "id": ticket_id, "run": run, "status": "pending",
        "admission": "pending", "executor": executor,
        "sequence": None, "pack": target.get("pack"),
        "independence": "gate", "depends_on": dependencies,
        "isolation": "none", "bound": f"{DEFAULT_BOUND_MINUTES}m",
        "review_order": None, "claimed_by": "", "claimed_at": "",
        "root_generation": target.get("root_generation"),
        "review_kind": kind,
    }
    text = _render_ticket(
        fields, _sections(kind, target_id, dependencies[0]),
    )
    text = _set_frontmatter_field(
        text, "cut_generation", target.get("cut_generation"),
    )
    return _set_frontmatter_field(
        text, "assignment_seal", assignment_digest(ticket_id, text),
    )


def ordinary_stages(run: str, target_id: str, target: dict):
    return [
        (
            GATE_REPAIR_ID.format(root=target_id),
            ordinary_stage_text(run, target_id, target, "repair"),
        ),
        (
            GATE_VERIFY_ID.format(root=target_id),
            ordinary_stage_text(run, target_id, target, "verify"),
        ),
    ]


def ordinary_stage_matches(ticket_id: str, actual: str, expected: str) -> bool:
    """Match the canonical semantics, generation, and derived seal."""

    actual_data = _parse_frontmatter(actual)
    expected_data = _parse_frontmatter(expected)
    return (
        assignment_digest(ticket_id, actual)
        == assignment_digest(ticket_id, expected)
        and all(
            str(actual_data.get(field) or "")
            == str(expected_data.get(field) or "")
            for field in (
                "root_generation", "cut_generation", "assignment_seal",
            )
        )
    )


__all__ = (
    "ordinary_stage_matches", "ordinary_stage_text", "ordinary_stages",
)
