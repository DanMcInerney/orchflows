"""Ordered review-bundle validation shared by gate construction."""

from __future__ import annotations

if __package__:
    from .tickets_format import _criteria, parse_canonical_json
    from .tickets_input_producers import input_groups
    from .tickets_issue import _distinct_gate_lenses
else:
    from tickets_format import _criteria, parse_canonical_json
    from tickets_input_producers import input_groups
    from tickets_issue import _distinct_gate_lenses


def _is_record(group: list) -> bool:
    """Whether ``group`` opens on a canonical ``- input:`` record line."""
    return bool(group) and group[0].startswith('- input: ')


def _ordered_bundle_carrier(body: str, lenses: list) -> dict:
    """The contract-owned root carrier, validated before it is copied."""
    records = []
    for group in input_groups(body or ''):
        if not _is_record(group):
            continue
        try:
            record = parse_canonical_json(group[0][len('- input: '):])
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    carriers = [record for record in records if record.get('name') == 'ordered-lens-bundle']
    if len(carriers) != 1:
        raise ValueError('ordered lens bundle requires the root\'s one canonical `ordered-lens-bundle` Fixed-input record')
    carrier = carriers[0]
    rows = carrier.get('value') if carrier.get('type') == 'literal' else None
    if not isinstance(rows, list) or not rows:
        raise ValueError('ordered-lens-bundle value must be a non-empty ordered list')
    identity_inputs = {
        record.get('name') for record in records if record.get('type') == 'identity'
    }
    identities = []
    used_evidence = set()
    for position, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != {'evidence', 'identity'}:
            raise ValueError(f'ordered-lens-bundle entry {position} must contain only identity and evidence')
        identity = row.get('identity')
        evidence = row.get('evidence')
        if not isinstance(identity, str) or not identity.strip() or identity in identities:
            raise ValueError(f'ordered-lens-bundle entry {position} identity must be non-empty and unique')
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(name, str) or name not in identity_inputs for name in evidence
        ):
            raise ValueError(f'ordered-lens-bundle entry {position} evidence must name root identity inputs')
        if len(evidence) != len(set(evidence)) or used_evidence.intersection(evidence):
            raise ValueError(f'ordered-lens-bundle entry {position} evidence must be separately attributable')
        identities.append(identity)
        used_evidence.update(evidence)
    if identities != lenses:
        raise ValueError('ordered-lens-bundle CLI order must equal the root carrier identities unchanged')
    return carrier


def _ordered_lens_bundle(value) -> list:
    lenses = [part.strip() for part in str(value or '').split(',')]
    if not lenses or any(not lens for lens in lenses):
        raise ValueError('ordered lens bundle must not contain an empty lens identity')
    return _distinct_gate_lenses(lenses)


def _gate_complete_coverage(root: dict, coverage: str) -> bool:
    rows = []
    for line in str(coverage or '').splitlines():
        cells = [cell.strip().strip('`') for cell in line.strip().strip('|').split('|')]
        if len(cells) >= 2 and cells[0].isdigit():
            rows.append((int(cells[0]), cells[1]))
    criteria = _criteria((root.get('sections') or {}).get('Completion test', ''))
    return bool(criteria) and rows == [(number, 'gate') for number in range(1, len(criteria) + 1)]


__all__ = ('_gate_complete_coverage', '_ordered_bundle_carrier', '_ordered_lens_bundle')
