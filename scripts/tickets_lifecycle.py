"""Ticket lifecycle support."""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
if __package__:
    from .tickets_format import GRANTED_SCOPE_KEY, RESULT_TOKEN_SPLIT_RE, RESULT_TOKEN_STRIP, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_bound_minutes, _parse_frontmatter, _parse_iso, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _split_commas, effective_write_scope
else:
    from tickets_format import GRANTED_SCOPE_KEY, RESULT_TOKEN_SPLIT_RE, RESULT_TOKEN_STRIP, ROOT_EXECUTOR, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_flag, _parse_bound_minutes, _parse_frontmatter, _parse_iso, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _split_commas, effective_write_scope
if __package__:
    from .tickets_store import NO_SINK_ERROR, UTC_STAMP, _iter_run_dirs, _load_ticket, _run_lock, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically
else:
    from tickets_store import NO_SINK_ERROR, UTC_STAMP, _iter_run_dirs, _load_ticket, _run_lock, _segment_error, _terminal_identity_update, _tickets_root, _write_identity, _write_text_atomically
if __package__:
    from .tickets_worklog import _run_goal, _run_tickets
else:
    from tickets_worklog import _run_goal, _run_tickets

CLAIM_USAGE = 'claim <run> <id> --by <name>'
SET_STATUS_USAGE = 'set-status <run> <id> <status>'
GRANT_USAGE = 'grant <run> <id> --write-scope <path>[,<path>] --by <name>'
GRANTED_BY_KEY = 'granted_by'
GRANTED_AT_KEY = 'granted_at'
GRANTABLE_STATUSES = frozenset({'claimed', 'suspended'})
CHECK_USAGE = 'check <run> <id> --by <name>'
CHECKED_BY_KEY = 'checked_by'
CHECKABLE_STATUSES = GRANTABLE_STATUSES
def _cited_paths(section_text: str, write_scope=()):
    """Every existing file one section cites, absolutely, inside
    ``write_scope``, as ``(paths, unreadable)``.

    A ``## Result`` names what changed by identity, and a file's identity is
    its path, so the candidates are the section's tokens: split on
    whitespace and the markdown punctuation a citation is wrapped in, then
    kept only when the filesystem agrees the name exists. A candidate with
    neither a separator nor a suffix is dropped before that -- ordinary
    prose words would otherwise stat a same-named file in the caller's
    directory and read it as this ticket's artifact.

    Only absolute citations count. A relative one names a different file
    from every directory it is read in, and this reader is the frontier's,
    not the executor's: under ``isolation: required`` the writer moves the
    file in its own worktree while the reader stats the same relative path
    in the main checkout -- a live lane read as dead, or a sibling's motion
    counted as this one's.

    A ticket with a ``write_scope`` counts only citations inside it, so a
    Result naming a shared or always-moving path -- a log, the friction
    stream, a sibling's output -- cannot keep a dead lane unreclaimable.
    """
    scope = [_scope_segments(entry) for entry in _scope_entries(write_scope)]
    scope = [entry for entry in scope if entry]
    found = []
    unreadable = []
    for token in RESULT_TOKEN_SPLIT_RE.split(section_text or ''):
        candidate = token.strip(RESULT_TOKEN_STRIP)
        if not candidate:
            continue
        if '/' not in candidate and '\\' not in candidate and ('.' not in candidate[1:]):
            continue
        try:
            path = Path(candidate)
            if not path.is_absolute() or not path.is_file():
                continue
            if scope and (not any((_inside_scope(path, entry) for entry in scope))):
                continue
            found.append(path)
        except (OSError, ValueError) as error:
            unreadable.append(f'could not look at the cited {candidate}: {error}')
    return (found, unreadable)
def _scope_segments(entry) -> list:
    """One `write_scope` entry as path segments, separator-neutral."""
    text = str(entry or '').strip().strip('`').strip()
    return [part for part in text.replace('\\', '/').split('/') if part and part != '.']
def _inside_scope(path: Path, segments: list) -> bool:
    """Whether an absolute path names, or sits under, one scope entry.

    Matched on whole segments rather than by string prefix, because a
    `write_scope` is written relative to the workspace while the citation
    is absolute: the two meet only where the entry's segments occur in the
    path in order. Segment-wise, so `tests` never matches `tests-old` and
    `a/bc` is never read as inside `a/b`.
    """
    parts = [part for part in str(path).replace('\\', '/').split('/') if part]
    width = len(segments)
    return any((parts[start:start + width] == segments for start in range(len(parts) - width + 1)))
def _last_motion(ticket_path: Path, result_text: str, write_scope=()):
    """The most recent write to the ticket or to what its ``## Result``
    names inside ``write_scope``, as ``(moment, unreadable)``.

    ``moment`` is ``None`` when nothing is readable; ``unreadable`` names
    every place motion could not be looked for, so the caller reports the
    blind spot instead of the lease treating it as stillness.
    """
    latest = None
    cited, unreadable = _cited_paths(result_text, write_scope)
    for path in [ticket_path, *cited]:
        try:
            stamp = path.stat().st_mtime
        except OSError as error:
            unreadable.append(f'could not stat {path}: {error}')
            continue
        moment = datetime.fromtimestamp(stamp, timezone.utc)
        if latest is None or moment > latest:
            latest = moment
    return (latest, unreadable)
def _is_stale(claimed_at, bound_minutes: int, now: datetime, last_motion=None) -> bool:
    """Whether a claim may be taken away: nothing has moved for a lease.

    The lease runs from the later of the claim and ``last_motion`` -- the
    most recent write to the ticket's own sections or to any artifact its
    ``## Result`` names (REVIEW-2026-08-15.md T3). A lane still writing is
    never reclaimable however long ago it claimed, which is what stops one
    item having two live executors (rules/delegation.md §11); a lane that
    has stopped is reclaimable exactly as before.

    A claim with no timestamp or an unparsable one is stale whatever is
    moving: the lease it would be measured against has no start, so there
    is nothing for motion to extend.
    """
    parsed = _parse_iso(claimed_at)
    if parsed is None:
        return True
    if last_motion is not None and last_motion > parsed:
        parsed = last_motion
    return now - parsed > timedelta(minutes=bound_minutes)
def _claim_is_stale(ticket_path, text: str, data: dict, now: datetime):
    """``_is_stale`` for one ticket on disk, motion and all, as
    ``(stale, unreadable)``.

    The one place ``ready`` and ``claim`` both ask from, so the two cannot
    answer differently about one claim -- a listing that offers a ticket the
    claim path then refuses is a frontier that dispatches nothing. Both must
    hand it the same ``data``: ``ready``'s came through ``_load_ticket``,
    normalised and grant-merged, while ``claim``'s was raw frontmatter, so a
    ``write_scope`` written as a bare scalar was iterated by character on one
    path only and every cited artifact fell outside a scope of letters. Both
    now load it the same way.

    ``unreadable`` is every place motion could not be looked for. The verdict
    is unchanged by it -- a blind spot is not motion -- but the caller can
    say which answer rests on a full look.
    """
    motion, unreadable = _last_motion(Path(ticket_path), _sections(text).get('Result', ''), data.get('write_scope') or ())
    stale = _is_stale(data.get('claimed_at'), _parse_bound_minutes(data.get('bound')), now, motion)
    return (stale, unreadable)
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
    ready_items = []
    skipped = []
    for run_dir in _iter_run_dirs(tickets_root, run_filter):
        tickets = {}
        for ticket_path in sorted(run_dir.glob('*.md')):
            loaded = _load_ticket(ticket_path)
            tickets[loaded['id']] = loaded
        for data in tickets.values():
            if 'error' in data:
                skipped.append({'id': data['id'], 'reason': data['error']})
                continue
            depends_on = data.get('depends_on') or []
            dangling = [dep for dep in depends_on if dep not in tickets]
            if dangling:
                skipped.append({'id': data['id'], 'reason': 'depends_on names no ticket in this run: ' + ', '.join((str(dep) for dep in dangling))})
                continue
            status = data.get('status')
            if status not in VALID_STATUSES:
                skipped.append({'id': data['id'], 'reason': f"status '{status}' is none of {sorted(VALID_STATUSES)}, so readiness cannot be graded"})
                continue
            deps_complete = all((tickets.get(dep, {}).get('status') == 'complete' for dep in depends_on))
            if not deps_complete:
                continue
            eligible = False
            if status == 'ready':
                eligible = True
            elif status == 'pending':
                try:
                    ticket_path = Path(data['path'])
                    text = ticket_path.read_text(encoding='utf-8')
                    ticket_path.write_text(_set_frontmatter_field(text, 'status', 'ready'), encoding='utf-8')
                except (OSError, ValueError) as error:
                    skipped.append({'id': data['id'], 'reason': f'eligible to promote to ready, and the write failed: {error}'})
                    continue
                data['summary']['status'] = 'ready'
                eligible = True
            elif status == 'claimed':
                text, failure = _read_utf8(data['path'])
                if failure is not None:
                    skipped.append({'id': data['id'], 'reason': f"claimed, and unreadable at the moment its claim was graded: {failure['error']}"})
                    continue
                eligible, unreadable = _claim_is_stale(data['path'], text, data, now)
                if unreadable:
                    skipped.append({'id': data['id'], 'reason': 'claim graded without a full look at its motion: ' + '; '.join(unreadable)})
            if eligible:
                ready_items.append(data['summary'])
    return {'ready': ready_items, 'skipped': skipped}
def _do_claim(ticket_path: Path, prior_text: str, claimed_by: str, now: datetime) -> dict:
    """Claim against the ``prior_text`` snapshot the caller read.

    Re-reads the file and compares it to ``prior_text`` before writing: if
    another claim already landed since ``prior_text`` was read, this attempt
    loses the race and reports an error instead of silently overwriting the
    winner (claim was previously a blind read-modify-write with no such
    check, so two concurrent claimants could both believe they had won).
    """
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
    elif status != 'ready':
        return {'error': f"ticket is not claimable in status '{status}': {ticket_path.stem}"}
    timestamp = now.strftime(UTC_STAMP)
    updated = _set_frontmatter_field(prior_text, 'status', 'claimed')
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
    try:
        with _run_lock(probe[0]):
            return _claim_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
def _claim_under_run_lock(rest):
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
    prior_text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    now = datetime.now(timezone.utc)
    result = _do_claim(ticket_path, prior_text, claimed_by, now)
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
    """Record one caller-side widening of a claimed item's write scope.

    The gap this closes: a lane finds a file it must change that the cut did
    not name, the caller agrees, and nothing on the ticket says so —
    ``amend`` writes cut-time sections and refuses a claimed ticket, and the
    item may not widen itself. So the widening was a direct sink edit plus a
    message, and the result that used it read as a scope breach at the join
    (friction 2026-08-16T05:29). Written as frontmatter bookkeeping of the
    ``claimed_*`` class, never a body section: those stay the executor's.
    """
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
        return {'error': f"ticket is not claimed (status '{status}'): a grant widens the authority of an item already being worked. Before a claim the cut owns the scope — re-place the ticket through `new --file` — and after a terminal status the verdict was already read against the authority the work was done under. ticket: {ticket_path}"}
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
    """Record the §10 checker's pass on one claimed item.

    The gap this closes: contracts/work-item.md:44 gave `checked_by` to "the
    §10 checker on its pass", orch-critique's body told the checker to set
    it, and orch-integrate refused a `checker`-independence return without
    it — while no script wrote it and :72-74 makes frontmatter script-written
    bookkeeping the executor may not touch. So the field was either absent,
    failing the join, or hand-edited, which the join cannot tell from an
    executor writing its own acceptance (rules/verification.md §10 exists to
    make exactly that distinguishable). Written as `claimed_*`-class
    bookkeeping, never a body section: those stay the executor's, and the
    checker's own findings go to `## Result` through `result --append`.
    """
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
        return {'error': f"ticket is not claimed (status '{status}'): the §10 checker passes over a result an executor has produced under a claim. Before a claim there is nothing to check, and after a terminal status the join has already read the acceptance this field feeds. ticket: {ticket_path}"}
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
