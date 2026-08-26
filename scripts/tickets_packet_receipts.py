"""One-shot receipts for opt-in gate-only root packet emission."""

from __future__ import annotations

import hashlib
import json
import re

if __package__:
    from .tickets_format import ROOT_EXECUTOR, _executor_of
    from .tickets_inputs import parse_input_records
    from .tickets_store import NO_SINK_ERROR, _create_text_exclusively, _runs_root
else:
    from tickets_format import ROOT_EXECUTOR, _executor_of
    from tickets_inputs import parse_input_records
    from tickets_store import NO_SINK_ERROR, _create_text_exclusively, _runs_root


PACKET_CLAIMS_DIR = 'packet-claims'


def _gate_only_bundle_claim(loaded: dict, text: str, run: str, cut_subtree) -> bool:
    """Whether this root claim is the opt-in zero-unit decomposition route."""
    if _executor_of(loaded) != ROOT_EXECUTOR or not str(loaded.get('assignment_seal') or '').strip():
        return False
    records = parse_input_records(text)
    if records['findings'] or not any(
        item.get('name') == 'ordered-lens-bundle' for item in records['records']
    ):
        return False
    root_id = str(loaded.get('id') or '')
    unit = re.compile(rf'^{re.escape(root_id)}\.[0-9][0-9]$')
    return not any(unit.fullmatch(item_id) for item_id, _ in cut_subtree(run, root_id))


def _consume_gate_only_bundle_claim(loaded: dict, text: str, run: str, cut_subtree):
    """Record one successful packet emission for this exact live claim."""
    if not _gate_only_bundle_claim(loaded, text, run, cut_subtree):
        return None
    runs_root = _runs_root()
    if runs_root is None:
        return {'error': NO_SINK_ERROR}
    claim = '\0'.join((
        str(loaded.get('id') or ''), str(loaded.get('claimed_by') or ''),
        str(loaded.get('claimed_at') or ''),
    ))
    digest = hashlib.sha256(claim.encode('utf-8')).hexdigest()
    receipt = runs_root / run / PACKET_CLAIMS_DIR / f"{loaded['id']}.{digest}.json"
    try:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        _create_text_exclusively(receipt, json.dumps({
            'claimed_at': loaded.get('claimed_at'),
            'claimed_by': loaded.get('claimed_by'),
            'ticket': loaded.get('id'),
        }, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + '\n')
    except FileExistsError:
        return {'error': f"gate-only root packet for {run}/{loaded['id']} was already emitted for this claim: decomposition cannot be redispatched"}
    except OSError as error:
        return {'error': f"unable to record gate-only root packet consumption: {error}"}
    return None


__all__ = ('PACKET_CLAIMS_DIR', '_consume_gate_only_bundle_claim', '_gate_only_bundle_claim')
