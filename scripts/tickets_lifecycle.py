"""Ticket lifecycle support."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
if __package__:
    from .tickets_format import CHECKED_BY_KEY, GRANTED_SCOPE_KEY, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _split_commas, effective_write_scope, parse_return_size
else:
    from tickets_format import CHECKED_BY_KEY, GRANTED_SCOPE_KEY, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _split_commas, effective_write_scope, parse_return_size
if __package__:
    from .tickets_store import NO_SINK_ERROR, UTC_STAMP, _iter_run_dirs, _load_ticket, _run_lock, _runs_root, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically
else:
    from tickets_store import NO_SINK_ERROR, UTC_STAMP, _iter_run_dirs, _load_ticket, _run_lock, _runs_root, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically
if __package__:
    from .tickets_worklog import _run_goal, _run_tickets
else:
    from tickets_worklog import _run_goal, _run_tickets
if __package__:
    from .tickets_admission import ADMISSION_PENDING, grade_admission, grade_result, is_receipt, is_v1, is_v2
else:
    from tickets_admission import ADMISSION_PENDING, grade_admission, grade_result, is_receipt, is_v1, is_v2
if __package__:
    from .tickets_packet import _claim_is_stale
else:
    from tickets_packet import _claim_is_stale
if __package__:
    from .tickets_transitions import ADMISSION_OWNED_TARGETS, CHECKABLE_STATUSES, GRANTABLE_STATUSES, refusal, set_status_blanks
else:
    from tickets_transitions import ADMISSION_OWNED_TARGETS, CHECKABLE_STATUSES, GRANTABLE_STATUSES, refusal, set_status_blanks
CLAIM_USAGE = 'claim <run> <id> --by <name>'
SET_STATUS_USAGE = 'set-status <run> <id> <status>'
RESULT_GRADE_USAGE = 'result-grade <run> <id>'
GRANT_USAGE = 'grant <run> <id> --write-scope <path>[,<path>] --by <name>'
GRANTED_BY_KEY = 'granted_by'
GRANTED_AT_KEY = 'granted_at'
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
    texts = {}
    failures = []
    for ticket_path in sorted(run_dir.glob('*.md')):
        text, failure = _read_utf8(ticket_path)
        if failure is not None:
            failures.append({'id': ticket_path.stem, 'reason': 'ticket unreadable before claimed-state grading: ' + failure['error']})
        else:
            texts[ticket_path.stem] = text
    return texts, failures
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
                return {'error': 'ticket, dependencies, or cohort changed since admission grade; lost the ready race'}
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
            versioned = text is not None and (is_v1(_parse_frontmatter(text)) or is_v2(_parse_frontmatter(text)))
            status = data.get('status')
            if dangling and not (versioned and status in ('pending', 'ready')):
                skipped.append({'id': data['id'], 'reason': 'depends_on names no ticket in this run: ' + ', '.join((str(dep) for dep in dangling))})
                continue
            if not facts['status_valid']:
                skipped.append({'id': data['id'], 'reason': f"status '{status}' is none of {sorted(VALID_STATUSES)}, so readiness cannot be graded"})
                continue
            deps_complete = facts['dependencies_complete']
            if not deps_complete and not (versioned and status in ('pending', 'ready')):
                continue
            eligible = False
            if versioned and status in ('pending', 'ready'):
                if read_failures:
                    skipped.append({'id': ticket_id, 'reason': 'admission refused: run snapshot is not closed', 'failures': read_failures})
                    continue
                grade = grade_admission(ticket_id, text, snapshot, context={'runs_root': str(_runs_root() or ''), 'run': run_dir.name})
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
            elif versioned and status == 'claimed':
                stale, unreadable = _claim_is_stale(data['path'], text, data, now)
                if stale:
                    skipped.append({'id': ticket_id, 'reason': refusal('stale v1 claim', 'claim', 'claimed')})
                elif unreadable:
                    skipped.append({'id': ticket_id, 'reason': 'claim graded without a full look at its motion: ' + '; '.join(unreadable)})
            elif status == 'ready':
                # Listing preserves the observable historical queue; claim is
                # the admission boundary and refuses this v0 item until recut.
                eligible = True
            elif status == 'pending':
                skipped.append({'id': ticket_id, 'reason': refusal('pending legacy ticket requires `recut` before v1 admission', 'recut', 'pending')})
            elif status == 'claimed':
                text, failure = _read_utf8(data['path'])
                if failure is not None:
                    skipped.append({'id': data['id'], 'reason': f"claimed, and unreadable at the moment its claim was graded: {failure['error']}"})
                    continue
                stale, unreadable = _claim_is_stale(data['path'], text, data, now)
                if unreadable:
                    skipped.append({'id': data['id'], 'reason': 'claim graded without a full look at its motion: ' + '; '.join(unreadable)})
                elif stale:
                    skipped.append({'id': ticket_id, 'reason': refusal('stale legacy claim', 'recut', 'claimed')})
            if eligible:
                ready_items.append(data['summary'])
    return {'ready': ready_items, 'skipped': skipped}
def _do_claim(ticket_path: Path, prior_text: str, claimed_by: str, now: datetime, receipt=None) -> dict:
    current_text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    if current_text != prior_text:
        return {'error': 'ticket changed since read; lost the claim race, retry'}
    data = _load_ticket(ticket_path)
    if 'error' in data:
        return {'error': data['error']}
    status = data.get('status')
    skipped = []
    if status == 'claimed':
        stale, unreadable = _claim_is_stale(ticket_path, prior_text, data, now)
        if not stale:
            return {'error': f'ticket already claimed and not stale: {ticket_path.stem}'}
        if unreadable:
            skipped.append({'id': data['id'], 'reason': 'claim taken as stale without a full look at its motion: ' + '; '.join(unreadable)})
    elif status == 'pending' and receipt is not None:
        pass
    elif status != 'ready':
        return {'error': f"ticket is not claimable in status '{status}': {ticket_path.stem}"}
    timestamp = now.strftime(UTC_STAMP)
    updated = prior_text
    if receipt is not None:
        updated = _set_frontmatter_field(updated, 'admission', receipt)
    updated = _set_frontmatter_field(updated, 'status', 'claimed')
    updated = _set_frontmatter_field(updated, 'claimed_by', claimed_by)
    updated = _set_frontmatter_field(updated, 'claimed_at', timestamp)
    _write_text_atomically(ticket_path, updated)
    claimed = {'id': ticket_path.stem, 'claimed_by': claimed_by, 'claimed_at': timestamp}
    return {'claimed': claimed, 'skipped': skipped} if skipped else {'claimed': claimed}
def _cmd_claim(rest):
    probe = list(rest)
    _extract_flag(probe, '--by')
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _claim_under_run_lock(rest)
    run, ticket_id = probe
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    snapshot, failures = _run_snapshot(run_dir)
    if failures:
        return {'error': 'run snapshot is not closed', 'failures': failures}
    prior_text = snapshot.get(ticket_id)
    grade = None
    if prior_text is not None:
        data = _parse_frontmatter(prior_text)
        status = str(data.get('status') or '')
        if (is_v1(data) or is_v2(data)) and status in ('pending', 'ready'):
            grade = grade_admission(ticket_id, prior_text, snapshot, context={'runs_root': str(_runs_root() or ''), 'run': run})
            if grade['findings']:
                return {'error': 'admission refused', 'findings': grade['findings']}
    try:
        with _run_lock(run):
            return _claim_under_run_lock(rest, prior_text=prior_text, snapshot=snapshot, grade=grade)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
def _claim_under_run_lock(rest, prior_text=None, snapshot=None, grade=None):
    """The claim half of grade-then-swap: compare-and-swap one graded snapshot into a
    live claim, landing only while that exact snapshot still matches, so a moved ticket,
    dependency, or cohort loses the race instead of claiming on a stale receipt. `ready`
    grades on the same `grade_admission` and swaps the same way in `_admit_ready_cas`."""
    args = list(rest)
    claimed_by = _extract_flag(args, '--by')
    if claimed_by is None:
        return {'error': 'claim requires --by <name>'}
    if len(args) != 2:
        return {'error': f'usage: {CLAIM_USAGE}'}
    run, ticket_id = args
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    loaded = _load_ticket(ticket_path)
    if 'error' in loaded:
        return {'error': loaded['error']}
    if prior_text is None:
        prior_text, failure = _read_utf8(ticket_path)
        if failure is not None:
            return failure
    data = _parse_frontmatter(prior_text)
    status = str(data.get('status') or '')
    if (is_v1(data) or is_v2(data)) and status in ('pending', 'ready'):
        if snapshot is None:
            snapshot, failures = _run_snapshot(ticket_path.parent)
            if failures:
                return {'error': 'run snapshot is not closed', 'failures': failures}
        if grade is None:
            grade = grade_admission(ticket_id, prior_text, snapshot, context={'runs_root': str(_runs_root() or ''), 'run': run})
        if grade['findings']:
            return {'error': 'admission refused', 'findings': grade['findings']}
        if not _snapshot_matches(ticket_path.parent, snapshot, grade.get('snapshot_ids') or [ticket_id]):
            return {'error': 'ticket, dependencies, or cohort changed since admission grade; lost the claim race'}
    elif status == 'pending':
        return {'error': refusal('pending legacy ticket requires `recut` before v1 admission', 'recut', 'pending')}
    elif (is_v1(data) or is_v2(data)) and status == 'claimed':
        return {'error': refusal('a v1 claim is live on this ticket', 'claim', 'claimed')}
    elif not (is_v1(data) or is_v2(data)) and status in ('ready', 'claimed'):
        return {'error': refusal(f'{status} legacy ticket requires `recut` before v1 admission or reclaim', 'recut', status)}
    now = datetime.now(timezone.utc)
    result = _do_claim(ticket_path, prior_text, claimed_by, now, grade['receipt'] if grade is not None else None)
    if 'error' in result:
        return result
    claimed = dict(result['claimed'])
    claimed['run'] = run
    payload = {'claimed': claimed}
    if result.get('skipped'):
        payload['skipped'] = result['skipped']
    return payload
def _cmd_grant(rest):
    probe = list(rest)
    for flag in ('--write-scope', '--by'):
        _extract_flag(probe, flag)
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _grant_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _grant_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
def _grant_under_run_lock(rest):
    args = list(rest)
    scope = _extract_flag(args, '--write-scope')
    granted_by = _extract_flag(args, '--by')
    if len(args) != 2:
        return {'error': f'usage: {GRANT_USAGE}'}
    run, ticket_id = args
    entries = _split_commas(scope)
    if not entries:
        return {'error': f'grant requires --write-scope <path>[,<path>], the paths this widening adds. usage: {GRANT_USAGE}'}
    if not (granted_by or '').strip():
        return {'error': f"grant requires --by <name>: the widening is the granting caller's, and an unattributed one is the unrecorded edit this subcommand exists to replace. usage: {GRANT_USAGE}"}
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
    if status not in GRANTABLE_STATUSES:
        return {'error': refusal(f"ticket is not claimed (status '{status}')", 'grant', status, note=f"A grant widens the authority of an item already being worked. Before a claim the cut owns the scope — re-place the ticket through `new --file` — and after a terminal status the verdict was already read against the authority the work was done under. ticket: {ticket_path}")}
    if is_v2(data):
        return {'error': 'a sealed v2 assignment cannot widen authority in place: suspend it and create a newly validated generation'}
    original_scope = _scope_entries(data.get('write_scope'))
    new_paths = [
        entry for entry in entries
        if not any(
            entry.replace('\\', '/').rstrip('/') == scope.replace('\\', '/').rstrip('/')
            or entry.replace('\\', '/').rstrip('/').startswith(scope.replace('\\', '/').rstrip('/') + '/')
            for scope in original_scope if scope.strip()
        )
    ]
    if is_v1(data) and 'mutations' in data and new_paths:
        return {'error': refusal('a planned v1 ticket cannot widen operation authority from path-only grant input: ' + ', '.join(new_paths) + '; the widened operation needs an explicit mutation vector written at cut time', 'recut', status, note='Or suspend the item and let the join open a successor ticket.')}
    granted = _scope_entries(data.get(GRANTED_SCOPE_KEY))
    for entry in entries:
        if entry not in granted:
            granted.append(entry)
    timestamp = datetime.now(timezone.utc).strftime(UTC_STAMP)
    updated = _set_frontmatter_field(text, GRANTED_SCOPE_KEY, f"[{', '.join(granted)}]")
    updated = _set_frontmatter_field(updated, GRANTED_BY_KEY, granted_by.strip())
    updated = _set_frontmatter_field(updated, GRANTED_AT_KEY, timestamp)
    try:
        _write_text_atomically(ticket_path, updated)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
    return {'grant': {'run': data.get('run') or run, 'id': data.get('id') or ticket_id, 'granted_scope': granted, 'granted_by': granted_by.strip(), 'granted_at': timestamp, 'write_scope': effective_write_scope(_parse_frontmatter(updated))}}
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
        return {'error': refusal(f"ticket is not claimed (status '{status}')", 'check', status, note=f"The §10 checker passes over a result an executor has produced under a claim. Before a claim there is nothing to check, and after a terminal status the join has already read the acceptance this field feeds. ticket: {ticket_path}")}
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
def _result_snapshot(run_dir):
    snapshot = {}
    for path in sorted(run_dir.glob('*.md')):
        text, failure = _read_utf8(path)
        if failure is not None:
            return (None, failure)
        snapshot[path.stem] = text
    return (snapshot, None)
def _result_grade_snapshot(ticket_path):
    text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return (None, None, failure)
    clause, _ = parse_return_size(_sections(text).get('Return fields', ''))
    if clause is None:
        return (text, {ticket_path.stem: text}, None)
    snapshot, failure = _result_snapshot(ticket_path.parent)
    return (text, snapshot, failure)
def _cmd_result_grade(rest):
    if len(rest) != 2:
        return {'error': f'usage: {RESULT_GRADE_USAGE}'}
    run, ticket_id = rest
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    text, snapshot, failure = _result_grade_snapshot(ticket_path)
    if failure is not None:
        return failure
    grade = grade_result(
        ticket_id, text, snapshot,
        context={'tickets_root': str(tickets_root), 'run': run},
    )
    return {'result_grade': {'run': run, 'id': ticket_id, **grade}}
def _set_status_under_run_lock(rest):
    args = list(rest)
    if len(args) != 3:
        return {'error': f'usage: {SET_STATUS_USAGE}'}
    run, ticket_id, status = args
    if status not in VALID_STATUSES:
        return {'error': f"invalid status '{status}'; must be one of {sorted(VALID_STATUSES)}"}
    if status in ADMISSION_OWNED_TARGETS:
        return {'error': f"set-status cannot create '{status}': ready and claim transitions require the admission boundary"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    if status == 'complete':
        _, snapshot, failure = _result_grade_snapshot(ticket_path)
        if failure is not None:
            return failure
        grade = grade_result(
            ticket_id, text, snapshot,
            context={'tickets_root': str(tickets_root), 'run': run},
        )
        if grade['findings']:
            return {
                'error': f'ticket {run}/{ticket_id} result does not satisfy return-size',
                'findings': grade['findings'],
            }
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
