"""The bound grammar, and `bound-check` over one run's live claims.

A bound is the one field that says when a claim stops protecting anything,
and every reader of one -- the dispatch window, the viewer's meter, and the
engine's re-check -- reads it through the one grammar here. `<= 40 tool
calls` and `banana` both aged a claim at the same substituted 60 minutes,
so a bound the cut had actually stated was indistinguishable from one
nobody had; `parse_bound` names the kind beside the minutes.

A claim exists only as a dispatch attempt (contracts/dispatch.md): the
attempt's absolute lease window decides overdue, motion cannot extend it,
and a claimed ticket with no record is over every bound. `_last_motion`
still reports whether anything moved, so a row says not only that a claim
is overdue but whether its holder stopped.

Imported at module scope by nothing here: `_cmd_bound_check`'s siblings are
reached inside the call, because `tickets_format` imports this module for
the parser and the pair would otherwise close a cycle at import time.
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_BOUND_MINUTES = 60
# A tool call is not a duration and never becomes one; this is the stated
# conversion that lets a tool-call bound be aged at all, named so a reader
# who disagrees with it can see the number they are disagreeing with.
TOOL_CALL_MINUTES = 2
# An iteration is not a duration either, and its conversion is its own fact,
# not a reuse of the unparsed-bound substitute above -- the two happen to
# share a value today, and nothing ties them together if one changes.
ITERATION_MINUTES = 60
DURATION_KIND = 'duration'
TOOL_CALLS_KIND = 'tool-calls'
ITERATIONS_KIND = 'iterations'
OTHER_BOUND_KIND = 'other'
BOUND_KINDS = (DURATION_KIND, TOOL_CALLS_KIND, ITERATIONS_KIND, OTHER_BOUND_KIND)
# `<= 30m` and `at most 30m` are the same bound written twice; the ceiling
# is what a bound already means, so the prefix carries no information the
# rest of the string does not.
AT_MOST_RE = re.compile('^(?:<=|at\\s+most)\\s*', re.IGNORECASE)
COMPACT_RE = re.compile('^(\\d+)(m|h)$')
WORDED_RE = re.compile('^(\\d+)\\s+(min(?:s|ute|utes)?|hours?)$')
TOOL_CALLS_RE = re.compile('^(\\d+)\\s+tool\\s+calls?$')
ITERATIONS_RE = re.compile('^(\\d+)\\s+iterations?$')


def parse_bound(bound) -> tuple:
    """``(minutes, kind)`` for one ``bound`` field, kind in ``BOUND_KINDS``.

    Every branch answers; a bound this grammar cannot read is ``other`` at
    ``DEFAULT_BOUND_MINUTES``, which is what the lease has always
    substituted. The kind is what is new: a caller that must not draw a
    meter against an invented denominator can now tell the substituted
    number from a stated one, which no minutes-only answer allowed.
    """
    text = AT_MOST_RE.sub('', bound.strip(), count=1) if isinstance(bound, str) else ''
    match = COMPACT_RE.match(text) or WORDED_RE.match(text)
    if match:
        return (int(match.group(1)) * (60 if match.group(2).startswith('h') else 1), DURATION_KIND)
    match = TOOL_CALLS_RE.match(text)
    if match:
        return (int(match.group(1)) * TOOL_CALL_MINUTES, TOOL_CALLS_KIND)
    match = ITERATIONS_RE.match(text)
    if match:
        return (int(match.group(1)) * ITERATION_MINUTES, ITERATIONS_KIND)
    return (DEFAULT_BOUND_MINUTES, OTHER_BOUND_KIND)


def _parse_bound_minutes(bound) -> int:
    """The minutes alone, for the callers that hold this name already."""
    return parse_bound(bound)[0]


def _last_motion(ticket_path: Path):
    """The ticket file is the durable motion record; result writes update it."""
    try:
        return datetime.fromtimestamp(Path(ticket_path).stat().st_mtime, timezone.utc), []
    except OSError as error:
        return None, [f"could not stat {ticket_path}: {error}"]


def _bound_row(item: dict, now: datetime, support: dict) -> tuple:
    """``(row, unreadable)`` for one claimed ticket."""
    minutes, kind = parse_bound(item.get('bound'))
    motion, unreadable = _last_motion(Path(item['path']))
    claimed = None
    lease_expires_at = None
    if item.get('dispatch_v1'):
        window, failure = support['attempt_window'](item)
        if failure is not None:
            unreadable.append(failure['error'])
            overdue, park = True, False
        else:
            claimed = window['opened_at']
            expires = window['lease_expires_at']
            lease_expires_at = expires.strftime(support['UTC_STAMP'])
            minutes = max(int((expires - claimed).total_seconds() // 60), 0)
            overdue = now > expires
            park = overdue
    else:
        # A claim exists only as a dispatch attempt (contracts/dispatch.md);
        # a claimed ticket with no record is over every bound.
        unreadable.append(f"claimed ticket carries no dispatch record: {item.get('id')}")
        overdue, park = True, False
    elapsed = None if claimed is None else max(int((now - claimed).total_seconds() // 60), 0)
    return ({
        'id': item.get('id'),
        'bound': item.get('bound'),
        'bound_kind': kind,
        'bound_minutes': minutes,
        'claimed_at': None if claimed is None else claimed.strftime(support['UTC_STAMP']),
        'lease_expires_at': lease_expires_at,
        'last_motion_at': None if motion is None else motion.strftime(support['UTC_STAMP']),
        'elapsed_minutes': elapsed,
        # The absolute lease deadline, not the floored minutes the row
        # displays: 30m30s into a `30m` lease is past it. An unreadable
        # claim is over every bound rather than inside one: the lease
        # already hands such a claim to the next taker.
        'overdue': overdue,
        'park': park,
    }, unreadable)


def _bound_support() -> dict:
    """The siblings this command reads, imported at call time.

    ``tickets_format`` imports this module for the parser, so a sibling
    named at module scope here would close a cycle at import time.
    """
    if __package__:
        from .tickets_dispatch_schema import attempt_window
        from .tickets_commands import BOUND_CHECK_USAGE
        from .tickets_format import _extract_flag, _parse_iso
        from .tickets_store import UTC_STAMP
        from .tickets_transitions import CLAIMED
        from .tickets_worklog import _run_tickets
    else:
        from tickets_dispatch_schema import attempt_window
        from tickets_commands import BOUND_CHECK_USAGE
        from tickets_format import _extract_flag, _parse_iso
        from tickets_store import UTC_STAMP
        from tickets_transitions import CLAIMED
        from tickets_worklog import _run_tickets
    return {'BOUND_CHECK_USAGE': BOUND_CHECK_USAGE, 'CLAIMED': CLAIMED, 'UTC_STAMP': UTC_STAMP, 'attempt_window': attempt_window, '_extract_flag': _extract_flag,
            '_parse_iso': _parse_iso, '_run_tickets': _run_tickets}


def _cmd_bound_check(rest):
    """Every live claim in one run, measured against its own bound.

    Exit 1 when any is overdue, so the engine's re-check reads the answer
    off the status alone; the rows say which, by how much, and whether
    anything has moved since the bound elapsed.
    """
    support = _bound_support()
    args = list(rest)
    now_text = support['_extract_flag'](args, '--now')
    if len(args) != 1:
        return {'error': f"usage: {support['BOUND_CHECK_USAGE']}"}
    now = datetime.now(timezone.utc) if now_text is None else support['_parse_iso'](now_text)
    if now is None:
        return {'error': f"unreadable --now: {now_text}. usage: {support['BOUND_CHECK_USAGE']}"}
    items, failure = support['_run_tickets'](args[0])
    if failure is not None:
        return failure
    rows, unreadable = ([], [])
    for item in items:
        if item.get('status') != support['CLAIMED']:
            continue
        row, problems = _bound_row(item, now, support)
        rows.append(row)
        unreadable.extend(problems)
    overdue = sum(1 for row in rows if row['overdue'])
    payload = {'run': args[0], 'now': now.strftime(support['UTC_STAMP']), 'tickets': rows, 'overdue': overdue}
    if unreadable:
        payload['unreadable'] = unreadable
    return {'bound_check': payload, 'exit_code': 1 if overdue else 0}
