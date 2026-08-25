"""Carried context: dependency conclusions inlined into a dispatch prompt.

Why this exists: a packet hands a fresh executor ~2k tokens while the
executor then re-gathers two orders of magnitude more, most of it
conclusions its dependencies already paid for. contracts/work-item.md's
blame rule makes that cost the caller's defect — work the child had to do
because a packet part was missing — so the packet inlines each
dependency's `## Carry` digest rather than pointing at it: a pointer is
the re-gathering it was meant to end.

Filing a `## Carry` never invalidates an admission receipt: v1 receipts
hash only the cut-time sections of self and cohort plus each dependency's
`## Result` sha (`tickets_admission._canonical_cut`), and the v2 seal
covers the six caller-owned assignment facets alone
(`tickets_generations.assignment_payload`). The section is context, not
authority — so a missing or unreadable sibling here degrades to silence
rather than refusing the packet, which stands on its own fixed inputs.
"""
from __future__ import annotations
if __package__:
    from .tickets_format import _parse_frontmatter, _read_utf8, _sections
    from .tickets_markdown import SECTION_SENTINEL
else:
    from tickets_format import _parse_frontmatter, _read_utf8, _sections
    from tickets_markdown import SECTION_SENTINEL


def _flattened(text: str) -> str:
    """One single-spaced line: a digest travels inside one prompt line."""
    return ' '.join(text.split())


def carry_block(loaded: dict, ticket_path) -> list:
    """Prompt lines carrying each dependency's `## Carry`, frontmatter order.

    Three shapes per dependency, and nothing else: its Carry, flattened,
    with its status beside it; for a complete dependency that filed none,
    one line naming that gap and its `## Result` as the reference, so the
    successor reads the dependency's record rather than re-deriving it;
    and for a sibling that is missing or unreadable, no line at all.
    """
    lines = []
    for dependency in loaded.get('depends_on') or []:
        dep_id = str(dependency).strip().strip('`').strip()
        if not dep_id:
            continue
        sibling = ticket_path.parent / f'{dep_id}.md'
        text, failure = _read_utf8(sibling, f'dependency {dep_id}')
        if failure is not None:
            continue
        status = str(_parse_frontmatter(text).get('status') or '').strip().strip('`').strip()
        carry = (_sections(text).get('Carry') or '').strip()
        if carry == SECTION_SENTINEL:
            carry = ''
        if carry:
            lines.append(f'Carried context from {dep_id} ({status or "unstated"}): {_flattened(carry)}')
        elif status == 'complete':
            lines.append(f'Dependency {dep_id} is complete but filed no `## Carry`: its `## Result` in {sibling} is the reference for what it landed.')
    return lines
