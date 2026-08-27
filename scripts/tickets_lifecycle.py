"""Ticket lifecycle support."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_format import CHECKED_BY_KEY, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field
else:
    from tickets_format import CHECKED_BY_KEY, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field
if __package__:
    from .tickets_store import NO_SINK_ERROR, _iter_run_dirs, _load_ticket, _run_lock, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically
else:
    from tickets_store import NO_SINK_ERROR, _iter_run_dirs, _load_ticket, _run_lock, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically
if __package__:
    from .tickets_worklog import _run_goal, _run_tickets
else:
    from tickets_worklog import _run_goal, _run_tickets
if __package__:
    from .tickets_context import graded_admission, run_snapshot
else:
    from tickets_context import graded_admission, run_snapshot
if __package__:
    from .tickets_packet import _claim_is_stale
else:
    from tickets_packet import _claim_is_stale
if __package__:
    from .tickets_transitions import ADMISSION_OWNED_TARGETS, CHECKABLE_STATUSES, refusal, set_status_blanks
else:
    from tickets_transitions import ADMISSION_OWNED_TARGETS, CHECKABLE_STATUSES, refusal, set_status_blanks
# The claim-admission seam lives in `tickets_project`, where the project
# binding it now grades also lives; re-exported here because the facade and
# `tickets_dispatch` import these three names from this module.
if __package__:
    from .tickets_project import CLAIM_USAGE, TERMINAL_REMEDY, _claim_under_run_lock, _cmd_claim, _do_claim, binding_refusal
else:
    from tickets_project import CLAIM_USAGE, TERMINAL_REMEDY, _claim_under_run_lock, _cmd_claim, _do_claim, binding_refusal
SET_STATUS_USAGE = 'set-status <run> <id> <status>'
CHECK_USAGE = 'check <run> <id> --by <name>'
def readiness_facts(ticket: dict, tickets: dict) -> dict:
    dependencies = [str(value) for value in (ticket.get('depends_on') or [])]
    dangling = [value for value in dependencies if value not in tickets]
    incomplete = [
        value for value in dependencies
        if value in tickets and tickets[value].get('status') != 'complete'
    ]
    status = str(ticket.get('status') or '')
    return {
        'status_valid': status in VALID_STATUSES,
        'dangling': dangling,
        'incomplete': incomplete,
        'dependencies_complete': not dangling and not incomplete,
    }
def _run_snapshot(run_dir: Path):
    """The shared run snapshot, with each unreadable member phrased as a skip."""
    texts, failures = run_snapshot(run_dir)
    return texts, [{'id': stem, 'reason': 'ticket unreadable before claimed-state grading: ' + failure['error']} for stem, failure in failures]
def _snapshot_matches(run_dir: Path, snapshot: dict, _ids=None) -> bool:
    current, failures = _run_snapshot(run_dir)
    return not failures and current == snapshot
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
def _unchecked_cut(ticket_id: str, tickets: dict) -> str:
    """Sealed cut validation is the sole pre-dispatch cut check."""
    del ticket_id, tickets
    return ''


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
            if dangling and status not in ('pending', 'ready'):
                skipped.append({'id': data['id'], 'reason': 'depends_on names no ticket in this run: ' + ', '.join((str(dep) for dep in dangling))})
                continue
            if not facts['status_valid']:
                skipped.append({'id': data['id'], 'reason': f"status '{status}' is none of {sorted(VALID_STATUSES)}, so readiness cannot be graded"})
                continue
            unchecked = _unchecked_cut(ticket_id, tickets)
            if unchecked:
                skipped.append({'id': ticket_id, 'reason': f"cut root '{unchecked}' carries no {CHECKED_BY_KEY}: a cut is checked before its first unit is dispatched, and readiness is what makes a dispatch possible. `check` the root first"})
                continue
            deps_complete = facts['dependencies_complete']
            if not deps_complete and status not in ('pending', 'ready'):
                continue
            eligible = False
            if text is not None and status in ('pending', 'ready'):
                if read_failures:
                    skipped.append({'id': ticket_id, 'reason': 'admission refused: run snapshot is not closed', 'failures': read_failures})
                    continue
                grade = graded_admission(ticket_id, text, snapshot, run_dir.name)
                if grade['findings']:
                    skipped.append({'id': ticket_id, 'reason': 'admission refused', 'findings': grade['findings']})
                    continue
                if status == 'pending' or str(data.get('admission') or '') != grade['receipt']:
                    result = _admit_ready_cas(run_dir.name, ticket_id, text, snapshot, grade)
                    if 'error' in result:
                        skipped.append({'id': ticket_id, 'reason': result['error']})
                        continue
                    snapshot[ticket_id] = result['text']
                    data['summary']['status'] = 'ready'
                    data['summary']['admission'] = grade['receipt']
                eligible = True
            elif text is not None and status == 'claimed':
                stale, unreadable = _claim_is_stale(data['path'], text, data, now)
                if stale:
                    skipped.append({'id': ticket_id, 'reason': refusal('stale claim', 'claim', 'claimed')})
                elif unreadable:
                    skipped.append({'id': ticket_id, 'reason': 'claim graded without a full look at its motion: ' + '; '.join(unreadable)})
            if eligible:
                ready_items.append(data['summary'])
    return {'ready': ready_items, 'skipped': skipped}
def _cmd_check(rest):
    probe = list(rest)
    _extract_flag(probe, '--by')
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _check_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _check_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unable to record check: {error}'}
def _check_under_run_lock(rest):
    args = list(rest)
    checked_by = _extract_flag(args, '--by')
    if len(args) != 2:
        return {'error': f'usage: {CHECK_USAGE}'}
    if not (checked_by or '').strip():
        return {'error': f"check requires --by <name>: the pass is a named further context's, and an unattributed one is the executor's own word again. usage: {CHECK_USAGE}"}
    run, ticket_id = args
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
    status = str(data.get('status') or '').strip().strip('`').strip()
    if status not in CHECKABLE_STATUSES:
        return {'error': refusal(f"ticket is not claimed (status '{status}')", 'check', status, note=f"The checker evaluates a result produced under a claim against Goal. ticket: {ticket_path}")}
    independence = str(data.get('independence') or 'checker').strip().strip('`')
    if independence == 'gate' and _executor_of(data) != ROOT_EXECUTOR:
        return {'error': f'ticket {run}/{ticket_id} defers independence to its downstream gate: a non-root gate-deferred ticket has no checker path and cannot carry checked_by'}
    prior_checker = str(data.get(CHECKED_BY_KEY) or '').strip().strip('`')
    if prior_checker:
        return {'error': f"ticket {run}/{ticket_id} is already checked by '{prior_checker}': one ticket has one checker identity. An additional adversarial reviewer must be a distinctly named root-gate lens"}
    try:
        updated = _set_frontmatter_field(text, CHECKED_BY_KEY, checked_by.strip())
    except ValueError as error:
        return {'error': str(error)}
    try:
        _write_text_atomically(ticket_path, updated)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
    return {'check': {'run': data.get('run') or run, 'id': data.get('id') or ticket_id, 'checked_by': checked_by.strip()}}
def _cmd_set_status(rest):
    if len(rest) != 3 or _segment_error('run id', rest[0]) is not None:
        return _set_status_under_run_lock(rest)
    try:
        with _run_lock(rest[0]):
            return _set_status_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unable to record status and terminal timing: {error}'}
def _set_status_under_run_lock(rest):
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
    # the project the run belongs to; graded before the ticket is read, so
    # a foreign workspace is refused for what it is.
    if status in TERMINAL_STATES:
        held = binding_refusal(run, TERMINAL_REMEDY)
        if held is not None:
            return {'error': held}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
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
        try:
            _write_text_atomically(ticket_path, text)
        except OSError:
            pass
        return {'error': f'unable to record status and terminal timing: {error}'}
    return {'set_status': {'run': run, 'id': ticket_id, 'status': status}}
