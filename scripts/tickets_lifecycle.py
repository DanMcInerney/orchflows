"""Ticket lifecycle support."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_format import TERMINAL_STATES, VALID_STATUSES, _extract_flag, _parse_frontmatter, _read_utf8, _sections, _set_frontmatter_field, dequote
else:
    from tickets_format import TERMINAL_STATES, VALID_STATUSES, _extract_flag, _parse_frontmatter, _read_utf8, _sections, _set_frontmatter_field, dequote
if __package__:
    from .tickets_store import NO_SINK_ERROR, UTC_STAMP, TicketWriteRefused, _iter_run_dirs, _load_ticket, _run_lock, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically, locked_ticket_write
else:
    from tickets_store import NO_SINK_ERROR, UTC_STAMP, TicketWriteRefused, _iter_run_dirs, _load_ticket, _run_lock, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically, locked_ticket_write
if __package__:
    from .tickets_worklog import _run_goal, _run_tickets
else:
    from tickets_worklog import _run_goal, _run_tickets
if __package__:
    from .tickets_context import graded_admission, run_snapshot
else:
    from tickets_context import graded_admission, run_snapshot
if __package__:
    from .tickets_assignment import _claim_is_stale
else:
    from tickets_assignment import _claim_is_stale
if __package__:
    from .tickets_transitions import ADMISSION_OWNED_TARGETS, CLAIMED, PENDING, READY, lifecycle_rows as _declared_lifecycle_rows, refusal, set_status_blanks
else:
    from tickets_transitions import ADMISSION_OWNED_TARGETS, CLAIMED, PENDING, READY, lifecycle_rows as _declared_lifecycle_rows, refusal, set_status_blanks
# The claim-admission seam lives in `tickets_project`, where the project
# binding it now grades also lives.
if __package__:
    from .tickets_project import TERMINAL_REMEDY, binding_refusal
else:
    from tickets_project import TERMINAL_REMEDY, binding_refusal
if __package__:
    from .tickets_attempts import _classification
else:
    from tickets_attempts import _classification
if __package__:
    from .tickets_readiness import readiness_facts
else:
    from tickets_readiness import readiness_facts
if __package__:
    from .tickets_dispatch_schema import status_ownership_returned
else:
    from tickets_dispatch_schema import status_ownership_returned
SET_STATUS_USAGE = 'set-status <run> <id> <status>'


def lifecycle_rows() -> tuple:
    """Public lifecycle declaration consumed by the documentation renderer."""
    return _declared_lifecycle_rows()
def _run_snapshot(run_dir: Path):
    """The shared run snapshot, with each unreadable member phrased as a skip."""
    texts, failures = run_snapshot(run_dir)
    return texts, [{'id': stem, 'reason': 'ticket unreadable before claimed-state grading: ' + failure['error']} for stem, failure in failures]
def _snapshot_matches(run_dir: Path, snapshot: dict, _ids=None) -> bool:
    """Whether the bytes this grade was taken over are still on disk."""
    current, failures = _run_snapshot(run_dir)
    if _ids is None:
        return not failures and current == snapshot
    scope = {str(value) for value in _ids}
    if any(str(failure.get('id') or '') in scope for failure in failures):
        return False
    return all(current.get(key) == snapshot.get(key) for key in scope)
def _admit_ready_cas(run: str, ticket_id: str, prior_text: str, snapshot: dict, grade: dict):
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    ticket_path = run_dir / f'{ticket_id}.md'
    try:
        with _run_lock(run):
            if not _snapshot_matches(run_dir, snapshot, grade.get('snapshot_ids') or [ticket_id]):
                return {'error': 'ticket or dependencies changed since admission grade; lost the ready race'}
            updated = _set_frontmatter_field(prior_text, 'admission', grade['receipt'])
            updated = _set_frontmatter_field(updated, 'status', 'ready')
            _write_text_atomically(ticket_path, updated)
    except OSError as error:
        return {'error': f'eligible to promote to ready, and the write failed: {error}'}
    return {'text': updated}
def _cmd_list(rest):
    args = list(rest)
    run_filter = _extract_flag(args, '--run')
    if args:
        return {'error': f"unexpected arguments: {' '.join(args)}"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    items = []
    for run_dir in _iter_run_dirs(tickets_root, run_filter):
        for ticket_path in sorted(run_dir.glob('*.md')):
            loaded = _load_ticket(ticket_path)
            items.append(loaded.get('summary') or loaded)
    return {'tickets': items}
def _cmd_show(rest):
    if len(rest) != 2:
        return {'error': 'usage: show <run> <id>'}
    run, ticket_id = rest
    for kind, value in (('run id', run), ('ticket id', ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    path = tickets_root / run / f'{ticket_id}.md'
    text, failure = _read_utf8(path, f'ticket {run}/{ticket_id}')
    if failure is not None:
        return failure
    loaded = _load_ticket(path)
    if 'error' in loaded:
        return {'error': loaded['error']}
    loaded.pop('summary', None)
    loaded['sections'] = _sections(text)
    return {'ticket': loaded}
def _cmd_ready(rest):
    args = list(rest)
    run_filter = _extract_flag(args, '--run')
    if args:
        return {'error': f"unexpected arguments: {' '.join(args)}"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    now = datetime.now(timezone.utc)
    ready_items, skipped = [], []
    for run_dir in _iter_run_dirs(tickets_root, run_filter):
        snapshot, read_failures = _run_snapshot(run_dir)
        skipped.extend(read_failures)
        tickets = {}
        for ticket_path in sorted(run_dir.glob('*.md')):
            loaded = _load_ticket(ticket_path)
            tickets[loaded['id']] = loaded
        for data in tickets.values():
            if 'error' in data:
                skipped.append({'id': data['id'], 'reason': 'ticket unreadable before claimed-state grading: ' + data['error']})
                continue
            facts = readiness_facts(data, tickets)
            dangling = facts['dangling']
            ticket_id = str(data.get('id') or '')
            text = snapshot.get(ticket_id)
            status = data.get('status')
            if dangling and status not in (PENDING, READY):
                skipped.append({'id': data['id'], 'reason': 'depends_on names no ticket in this run: ' + ', '.join((str(dep) for dep in dangling))})
                continue
            if not facts['status_valid']:
                skipped.append({'id': data['id'], 'reason': f"status '{status}' is none of {sorted(VALID_STATUSES)}, so readiness cannot be graded"})
                continue
            deps_complete = facts['dependencies_complete']
            if not deps_complete and status not in (PENDING, READY):
                continue
            eligible = False
            if text is not None and status in (PENDING, READY):
                if read_failures:
                    skipped.append({'id': ticket_id, 'reason': 'admission refused: run snapshot is not closed', 'failures': read_failures})
                    continue
                grade = graded_admission(ticket_id, text, snapshot, run_dir.name)
                if grade['findings']:
                    skipped.append({'id': ticket_id, 'reason': 'admission refused', 'findings': grade['findings']})
                    continue
                if status == PENDING or str(data.get('admission') or '') != grade['receipt']:
                    result = _admit_ready_cas(run_dir.name, ticket_id, text, snapshot, grade)
                    if 'error' in result:
                        skipped.append({'id': ticket_id, 'reason': result['error']})
                        continue
                    snapshot[ticket_id] = result['text']
                    data['summary']['status'] = 'ready'
                    data['summary']['admission'] = grade['receipt']
                eligible = True
            elif text is not None and status == CLAIMED:
                stale, unreadable = _claim_is_stale(data['path'], text, data, now)
                if stale:
                    skipped.append({'id': ticket_id, 'reason': refusal('stale claim', 'claim', CLAIMED)})
                elif unreadable:
                    skipped.append({'id': ticket_id, 'reason': 'claim graded without a full look at its motion: ' + '; '.join(unreadable)})
            if eligible:
                ready_items.append(data['summary'])
    return {'ready': ready_items, 'skipped': skipped}
def _cmd_set_status(rest):
    if len(rest) != 3:
        return {'error': f'usage: {SET_STATUS_USAGE}'}
    try:
        with locked_ticket_write(rest[0], rest[1]) as ticket_path:
            return _set_status_under_run_lock(rest, ticket_path=ticket_path)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {'error': f'unable to record status and terminal timing: {error}'}

def _set_status_under_run_lock(rest, *, ticket_path=None):
    args = list(rest)
    if len(args) != 3:
        return {'error': f'usage: {SET_STATUS_USAGE}'}
    run, ticket_id, status = args
    if status not in VALID_STATUSES:
        return {'error': f"invalid status '{status}'; must be one of {sorted(VALID_STATUSES)}"}
    if status in ADMISSION_OWNED_TARGETS:
        return {'error': f"set-status cannot create '{status}': ready and claim transitions require the admission boundary"}
    # A terminal status is the run's own verdict, and the identity write
    # beside it stamps timing onto the run document itself. Both belong to
    # the project the run belongs to; graded before the ticket is read.
    if status in TERMINAL_STATES:
        held = binding_refusal(run, TERMINAL_REMEDY)
        if held is not None:
            return {'error': held}
    if ticket_path is None:
        tickets_root = _tickets_root()
        if tickets_root is None:
            return {'error': NO_SINK_ERROR}
        ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    data = _parse_frontmatter(text)
    # The one exception is a lone attempt with no join left to come: it was
    # retired -- whatever it launched -- or it never launched at all, and
    # nothing else can release the status it holds. Its width is
    # `status_ownership_returned`'s, beside the records it reads.
    if data.get('dispatch_v1') and not status_ownership_returned(data):
        return _classification(
            'dispatch-join-required',
            'dispatch-v1 lifecycle is owned by dispatch-open, dispatch-replace, dispatch-retire, and dispatch-join',
        )
    items, run_error = _run_tickets(run)
    terminal_transition = False
    terminal_now = False
    terminal_id = ticket_id
    terminal_status = status
    if run_error is None:
        before_root, _ = _run_goal(items)
        simulated = []
        for item in items:
            changed = dict(item)
            if str(changed.get('id') or '') == ticket_id:
                changed['status'] = status
            simulated.append(changed)
        after_root, _ = _run_goal(simulated)
        before_terminal = str(before_root.get('status') or '') in TERMINAL_STATES
        after_status = str(after_root.get('status') or '')
        terminal_transition = not before_terminal and after_status in TERMINAL_STATES
        terminal_now = after_status in TERMINAL_STATES
        if terminal_now:
            terminal_id = str(after_root.get('id') or ticket_id)
            terminal_status = after_status
    identity_dir = None
    identity = None
    if terminal_now:
        identity_dir, identity, refusal = _terminal_identity_update(run, terminal_id, terminal_status, datetime.now(timezone.utc))
        if refusal is not None:
            return refusal
    updated = _set_frontmatter_field(text, 'status', status)
    for field in set_status_blanks(status):
        updated = _set_frontmatter_field(updated, field, '')
    try:
        _write_text_atomically(ticket_path, updated)
        if identity is not None:
            identity_dir.mkdir(parents=True, exist_ok=True)
            _write_identity(identity_dir, identity)
    except OSError as error:
        # The two-file write keeps its order -- ticket first, identity second
        # -- so a failed identity write is rolled back off the ticket. When
        # the rollback fails too, the pair is genuinely split and nothing may
        # swallow the second error: the caller is told both, and told the one
        # command that lands the pair, which replays idempotently.
        try:
            _write_text_atomically(ticket_path, text)
        except OSError as rollback:
            return {'error': (
                f'unable to record status and terminal timing: {error}; and '
                f'the ticket could not be rolled back: {rollback}. The ticket '
                f"may now read status '{status}' with no terminal timing "
                f'beside it. Replay `tickets.py set-status {run} {ticket_id} '
                f'{status}` to record both.'
            )}
        return {'error': f'unable to record status and terminal timing: {error}'}
    return {'set_status': {'run': run, 'id': ticket_id, 'status': status}}
