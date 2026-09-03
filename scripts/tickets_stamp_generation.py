"""Open the generation lifecycle on one root and its declared cut.

`stamp-generation` used to sit beside `instantiate` as its hand-authored
twin: one sealed a graph it rendered, the other opened the lifecycle on a
graph somebody wrote. `instantiate` and the template layer it read are
gone -- callables mint their own graphs at runtime now -- so only the
second half survives, here alone.

It is dead as a public subcommand (W3a removed the command from the
dispatch table) and alive as an internal call: `tickets_mint.py`'s
parentless-root path calls it directly to open the one-member cut a
standalone `do`/`judge` callable takes on itself.
"""

from __future__ import annotations

if __package__:
    from .tickets_format import _parse_frontmatter, _set_frontmatter_field, lease_of
    from .tickets_store import (
        NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )
    from .tickets_emission import grade_run_emission
    from .tickets_context import run_snapshot
    from .tickets_generations import _root_payload, generation_identity
    from .tickets_transitions import PENDING, READY, pending_admission
else:  # pragma: no cover - direct/installed flat script path
    from tickets_format import _parse_frontmatter, _set_frontmatter_field, lease_of
    from tickets_store import (
        NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )
    from tickets_emission import grade_run_emission
    from tickets_context import run_snapshot
    from tickets_generations import _root_payload, generation_identity
    from tickets_transitions import PENDING, READY, pending_admission


STAMP_GENERATION_USAGE = "stamp-generation <run> <root-id>"


def _cmd_stamp_generation(rest):
    """Open the generation lifecycle on one root and its declared cut."""
    args = list(rest)
    if len(args) != 2:
        return {'error': f'usage: {STAMP_GENERATION_USAGE}'}
    run, root_id = args
    for kind, value in (('run id', run), ('ticket id', root_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None: return invalid
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    try:
        with _run_lock(run):
            snapshot, unreadable = run_snapshot(run_dir) if run_dir.is_dir() else ({}, [])
            if unreadable:
                return {'error': f'unreadable ticket: {unreadable[0][0]}'}
            if root_id not in snapshot:
                return {'error': f'root ticket not found in exact snapshot: {root_id}'}
            members = [root_id] + sorted(i for i in snapshot if i.startswith(root_id + '.'))
            for member_id in members:
                data = _parse_frontmatter(snapshot[member_id])
                status = str(data.get('status') or '')
                if status not in (PENDING, READY) or lease_of(data)[0]:
                    return {'error': f"stamp-generation refused: {run}/{member_id} is '{status or '<missing>'}', and a stamp rewrites the assignment it would be working against (rules/verification.md §3). Nothing was written"}
                if str(data.get('root_generation') or '').strip():
                    return {'error': f'stamp-generation refused: {run}/{member_id} already carries a generation; the lifecycle is opened once. Nothing was written'}
            identity = generation_identity('root', root_id, 1, _root_payload(root_id, snapshot))
            stamped = {}
            for member_id in members:
                text = _set_frontmatter_field(snapshot[member_id], 'root_generation', identity)
                text = _set_frontmatter_field(text, 'admission', pending_admission())
                stamped[member_id] = text
            emission = grade_run_emission('stamp-generation', run, run_dir, stamped, repairs=True)
            if emission is not None:
                return {**emission, 'error': emission['error'] + '. Nothing was written'}
            written = {}
            try:
                for member_id, text in stamped.items():
                    written[member_id] = snapshot[member_id]
                    _write_text_atomically(run_dir / f'{member_id}.md', text)
            except OSError:
                for member_id, text in written.items():
                    _write_text_atomically(run_dir / f'{member_id}.md', text)
                raise
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return {'error': str(error)}
    return {'stamp_generation': {'root_generation': identity, 'run': run, 'root_id': root_id, 'ids': members, 'state': 'drafting'}}


__all__ = ("STAMP_GENERATION_USAGE", "_cmd_stamp_generation")
