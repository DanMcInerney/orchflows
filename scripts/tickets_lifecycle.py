"""Ticket lifecycle support."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_format import CHECKED_BY_KEY, REPORT_SECTION, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _section_body, _sections, _set_frontmatter_field, _write_section, canonical_json, dequote
else:
    from tickets_format import CHECKED_BY_KEY, REPORT_SECTION, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _section_body, _sections, _set_frontmatter_field, _write_section, canonical_json, dequote
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
    from .tickets_transitions import ADMISSION_OWNED_TARGETS, CHECKABLE_STATUSES, lifecycle_rows as _declared_lifecycle_rows, refusal, set_status_blanks
else:
    from tickets_transitions import ADMISSION_OWNED_TARGETS, CHECKABLE_STATUSES, lifecycle_rows as _declared_lifecycle_rows, refusal, set_status_blanks
# The claim-admission seam lives in `tickets_project`, where the project
# binding it now grades also lives; re-exported here because the facade and
# `tickets_dispatch` import these three names from this module.
if __package__:
    from .tickets_project import CLAIM_REMEDY, TERMINAL_REMEDY, binding_refusal
else:
    from tickets_project import CLAIM_REMEDY, TERMINAL_REMEDY, binding_refusal
if __package__:
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
else:
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
if __package__:
    from .tickets_attempts import _classification
else:
    from tickets_attempts import _classification
if __package__:
    from .tickets_readiness import readiness_facts
else:
    from tickets_readiness import readiness_facts
if __package__:
    from .tickets_review import REVIEW_FIELD, ReviewError, launch_state, repair_outcome, review_records, state_from_text
    from .tickets_dispatch_schema import state as _dispatch_state
    from .tickets_dispatch_schema import status_ownership_returned
else:
    from tickets_review import REVIEW_FIELD, ReviewError, launch_state, repair_outcome, review_records, state_from_text
    from tickets_dispatch_schema import state as _dispatch_state
    from tickets_dispatch_schema import status_ownership_returned
SET_STATUS_USAGE = 'set-status <run> <id> <status>'
CHECK_USAGE = 'check <run> <id> --stage <id.check>'
JOIN_NOOP_REPAIR_USAGE = 'join-noop-repair <run> <id> --by <join_name>'
NOOP_REPAIR_NOTE = 'No repair: every critique lens accepted an empty blocker set.'


def lifecycle_rows() -> tuple:
    """Public lifecycle declaration consumed by the documentation renderer."""
    return _declared_lifecycle_rows()
def _run_snapshot(run_dir: Path):
    """The shared run snapshot, with each unreadable member phrased as a skip."""
    texts, failures = run_snapshot(run_dir)
    return texts, [{'id': stem, 'reason': 'ticket unreadable before claimed-state grading: ' + failure['error']} for stem, failure in failures]
def _snapshot_matches(run_dir: Path, snapshot: dict, _ids=None) -> bool:
    """Whether the bytes this grade was taken over are still on disk.

    Scoped to ``_ids`` -- the graded ticket and the dependencies its grade
    actually read (`grade_admission`'s ``snapshot_ids``). A whole-run
    comparison made every promotion lose to any concurrent sibling write:
    a run of eight refused seven readies because the eighth ticket had been
    touched, and none of the seven had read it. What the compare-and-swap
    is protecting is the grade, so its scope is what the grade consulted.

    ``None`` keeps the whole-run comparison for a caller that names no
    scope; an unreadable member inside the scope refuses, one outside it is
    not this promotion's business.
    """
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
            if dangling and status not in ('pending', 'ready'):
                skipped.append({'id': data['id'], 'reason': 'depends_on names no ticket in this run: ' + ', '.join((str(dep) for dep in dangling))})
                continue
            if not facts['status_valid']:
                skipped.append({'id': data['id'], 'reason': f"status '{status}' is none of {sorted(VALID_STATUSES)}, so readiness cannot be graded"})
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
    _extract_flag(probe, '--stage')
    if len(probe) != 2:
        return {'error': f'usage: {CHECK_USAGE}'}
    try:
        with locked_ticket_write(probe[0], probe[1]) as ticket_path:
            return _check_under_run_lock(rest, ticket_path=ticket_path)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {'error': f'unable to record check: {error}'}
def _check_under_run_lock(rest, *, ticket_path=None):
    args = list(rest)
    stage_id = _extract_flag(args, '--stage')
    if len(args) != 2 or not (stage_id or '').strip():
        return {'error': f'usage: {CHECK_USAGE}'}
    run, ticket_id = args
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
    status = dequote(data.get('status'))
    if status != 'complete':
        return {'error': f"check requires the target executor outcome to be joined complete (status '{status}')"}
    independence = dequote(data.get('independence') or 'checker')
    if independence == 'gate' and _executor_of(data) != ROOT_EXECUTOR:
        return {'error': f'ticket {run}/{ticket_id} defers independence to its downstream gate: a non-root gate-deferred ticket has no checker path and cannot carry checked_by'}
    prior_checker = dequote(data.get(CHECKED_BY_KEY))
    if prior_checker:
        return {'error': f"ticket {run}/{ticket_id} is already checked by '{prior_checker}': one ticket has one checker identity. An additional adversarial reviewer must be a distinctly named root-gate lens"}
    stage_id = stage_id.strip()
    if stage_id != f'{ticket_id}.check':
        return {'error': f"check stage must be the target's explicit review ticket {ticket_id}.check"}
    stage_path = ticket_path.with_name(f'{stage_id}.md')
    stage_text, failure = _read_utf8(stage_path)
    if failure is not None:
        return failure
    stage = _parse_frontmatter(stage_text)
    if (str(stage.get('status') or '') != 'complete'
            or _executor_of(stage) != 'orch-judge'
            or str(stage.get('review_kind') or '') != 'critique'
            or list(stage.get('depends_on') or []) != [ticket_id]):
        return {'error': f'checker stage is not a completed review of {ticket_id}: {stage_id}'}
    dispatch_state, dispatch_failure = _dispatch_state(stage)
    if dispatch_failure is not None:
        return dispatch_failure
    try:
        review = state_from_text(stage_text, required=True)
        records = review_records(review)
        if [record['kind'] for record in records] != ['GatePlan', 'CritiqueAdjudication']:
            raise ReviewError('checker stage has no closed adjudication')
        plan, adjudication = records
        if (plan['mode'] != 'checker' or plan['root'] != ticket_id
                or [item['ticket'] for item in plan['criteria']] != [stage_id]
                or adjudication['lens'] != 'checker'):
            raise ReviewError('checker stage ledger names a different target or lens')
        checked_by = adjudication['adjudicated_by']
        attempts = dispatch_state['attempts']
        joined = next((
            attempt for attempt in attempts
            if any(record.get('kind') == 'join' for record in attempt['records'])
        ), None)
        if joined is None or joined['owner'] != checked_by:
            raise ReviewError('checker adjudication is not owned by the accepted receiver')
    except ReviewError as error:
        return _classification('review-invalid', str(error))
    try:
        updated = _set_frontmatter_field(text, CHECKED_BY_KEY, checked_by)
        updated = _set_frontmatter_field(updated, 'review_stage', stage_id)
    except ValueError as error:
        return {'error': str(error)}
    try:
        _write_text_atomically(ticket_path, updated)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
    return {'check': {'run': data.get('run') or run, 'id': data.get('id') or ticket_id, 'checked_by': checked_by, 'stage': stage_id}}
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

def _cmd_join_noop_repair(rest):
    probe = list(rest)
    _extract_flag(probe, '--by')
    if len(probe) != 2:
        return {'error': f'usage: {JOIN_NOOP_REPAIR_USAGE}'}
    try:
        with locked_ticket_write(probe[0], probe[1]) as ticket_path:
            held = binding_refusal(probe[0], CLAIM_REMEDY)
            if held is not None:
                return {'error': held}
            return _join_noop_repair_under_run_lock(rest, ticket_path=ticket_path)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {'error': f'unable to complete clean repair at join: {error}'}

def _join_noop_repair_under_run_lock(rest, *, ticket_path=None):
    args = list(rest)
    written_by = _extract_flag(args, '--by')
    if len(args) != 2 or not (written_by or '').strip():
        return {'error': f'usage: {JOIN_NOOP_REPAIR_USAGE}'}
    written_by = written_by.strip()
    if any(mark in written_by for mark in ('`', '\r', '\n')):
        return {'error': 'join-noop-repair --by contains backticks or line breaks'}
    run, ticket_id = args
    if not ticket_id.endswith('.gate.repair'):
        return {'error': 'join-noop-repair requires a .gate.repair ticket'}
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
    if str(data.get('status') or '') != 'ready':
        return {'error': f'join-noop-repair requires a ready ticket: {run}/{ticket_id}'}
    if _executor_of(data) != 'orch-do' or str(data.get('review_kind') or '') != 'repair':
        return {'error': 'join-noop-repair requires review_kind repair on an orch-do ticket'}
    dependencies = [str(value) for value in (data.get('depends_on') or [])]
    if not dependencies:
        return {'error': 'join-noop-repair requires completed critique dependencies'}
    critique_prefix = ticket_id[:-len('repair')] + 'critique.'
    for dependency in dependencies:
        loaded = _load_ticket(ticket_path.with_name(f'{dependency}.md'))
        if ('error' in loaded or not dependency.startswith(critique_prefix)
                or _executor_of(loaded) != 'orch-judge'
                or str(loaded.get('review_kind') or '') != 'critique'
                or str(loaded.get('status') or '') != 'complete'):
            return {'error': f'join-noop-repair dependency is not a completed gate critique: {dependency}'}
    if _section_body(text, REPORT_SECTION):
        return {'error': f'join-noop-repair requires an empty repair {REPORT_SECTION}'}
    try:
        review = launch_state(ticket_path, text, None, None)
        review = repair_outcome(review, '', NOOP_REPAIR_NOTE, written_by, no_op=True)
    except ReviewError as error:
        return _classification('review-invalid', str(error))
    timestamp = datetime.now(timezone.utc).strftime(UTC_STAMP)
    updated = _set_frontmatter_field(text, 'status', 'claimed')
    updated = _write_section(updated, REPORT_SECTION, f'{RESULT_ATTRIBUTION_PREFIX}`{written_by}`\n\n{NOOP_REPAIR_NOTE}')
    updated = _set_frontmatter_field(updated, REVIEW_FIELD, canonical_json(review))
    updated = _set_frontmatter_field(updated, 'status', 'complete')
    try:
        _write_text_atomically(ticket_path, updated)
    except OSError as error:
        return {'error': f'unable to complete clean repair at join: {error}'}
    return {'join_noop_repair': {'run': run, 'id': ticket_id, 'status': 'complete', 'by': written_by, 'at': timestamp}}

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
    # the project the run belongs to; graded before the ticket is read, so
    # a foreign workspace is refused for what it is.
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
    # The one exception is a lifecycle that never started executing: a lone
    # attempt opened and retired before any launch owns a status it has no
    # way to release, and the ticket is wedged -- no join can exist without
    # an outcome, and retirement refuses an already-ended attempt. Its
    # width is `status_ownership_returned`'s, beside the records it reads.
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
        # command that lands the pair, which replays idempotently from either
        # half's state.
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
