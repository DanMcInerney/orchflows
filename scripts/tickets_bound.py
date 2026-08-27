"""The bound grammar, and `bound-check` over one run's live claims.

A bound is the one field that says when a claim stops protecting anything,
and every reader of one -- the staleness check that hands a claim to the
next taker, the viewer's meter, and now the engine's re-check -- had to
read it through a pattern that admitted two shapes. `<= 40 tool calls` and
`banana` both aged a claim at the same substituted 60 minutes, so a bound
the cut had actually stated was indistinguishable from one nobody had.

This module owns the widened grammar and the two questions the engine asks
of it, kept apart on purpose: `overdue` is about the bound alone, and
`should_park` is about whether anything moved after the bound elapsed. A
ticket that is over its bound and still moving is a report; one that is
over its bound and still is a decision for its caller.

It therefore owns when a claim goes stale, which contracts/work-item.md
states only as a field: a claim is stale when no write to the ticket file
has landed for longer than the minutes `parse_bound` reads
off that item's bound -- a stated duration as itself, a tool-call or
iteration count at its stated conversion, and 60 minutes,
`DEFAULT_BOUND_MINUTES`, only for a bound this grammar cannot read at all.
Substituting the default for every non-duration bound is the defect the
paragraph above names, not the rule. Staleness never rests on wall clock
alone, and `should_park` is the reading of that rule: `_last_motion`
supplies the motion, and a claim still writing past its deadline is
reported, not taken.

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
        return (int(match.group(1)) * DEFAULT_BOUND_MINUTES, ITERATIONS_KIND)
    return (DEFAULT_BOUND_MINUTES, OTHER_BOUND_KIND)


def _parse_bound_minutes(bound) -> int:
    """The minutes alone, for the callers that hold this name already."""
    return parse_bound(bound)[0]


def should_park(claimed_at, bound_minutes: int, last_motion, now) -> bool:
    """True when the bound elapsed and nothing moved after it did.

    Pure, and on datetimes rather than a row, because it is the one rule
    the engine's prose states and a rule stated in two places drifts. Being
    over the bound is not enough: an item still moving past its bound is a
    report, and only one that stopped inside it is a decision its caller
    has to make. A claim whose start cannot be read has no deadline that
    can be said to have passed, so it is reported and never parked.
    """
    if claimed_at is None:
        return False
    deadline = claimed_at + timedelta(minutes=bound_minutes)
    if now <= deadline:
        return False
    return last_motion is None or last_motion <= deadline


def _bound_row(item: dict, now: datetime, support: dict) -> tuple:
    """``(row, unreadable)`` for one claimed ticket."""
    minutes, kind = parse_bound(item.get('bound'))
    motion, unreadable = support['_last_motion'](Path(item['path']))
    claimed = support['_parse_iso'](item.get('claimed_at'))
    elapsed = None if claimed is None else max(int((now - claimed).total_seconds() // 60), 0)
    return ({
        'id': item.get('id'),
        'bound': item.get('bound'),
        'bound_kind': kind,
        'bound_minutes': minutes,
        'claimed_at': item.get('claimed_at'),
        'last_motion_at': None if motion is None else motion.strftime(support['UTC_STAMP']),
        'elapsed_minutes': elapsed,
        # The deadline `should_park` reads, not the whole minutes the row
        # displays: 30m30s into a `30m` bound is past that bound, and a row
        # that floored it answered `park: true` beside `overdue: false` and
        # left the run at exit 0 -- the engine's rule and the exit status its
        # re-check reads on opposite sides of one deadline. An unreadable
        # start is over every bound rather than inside one: the lease already
        # hands such a claim to the next taker.
        'overdue': claimed is None or now > claimed + timedelta(minutes=minutes),
        'park': should_park(claimed, minutes, motion, now),
    }, unreadable)


def _bound_support() -> dict:
    """The siblings this command reads, imported at call time.

    ``tickets_format`` imports this module for the parser, so a sibling
    named at module scope here would close a cycle at import time.
    """
    if __package__:
        from .tickets_commands import BOUND_CHECK_USAGE
        from .tickets_format import _extract_flag, _parse_iso
        from .tickets_packet import _last_motion
        from .tickets_store import UTC_STAMP
        from .tickets_worklog import _run_tickets
    else:
        from tickets_commands import BOUND_CHECK_USAGE
        from tickets_format import _extract_flag, _parse_iso
        from tickets_packet import _last_motion
        from tickets_store import UTC_STAMP
        from tickets_worklog import _run_tickets
    return {'BOUND_CHECK_USAGE': BOUND_CHECK_USAGE, 'UTC_STAMP': UTC_STAMP, '_extract_flag': _extract_flag,
            '_last_motion': _last_motion, '_parse_iso': _parse_iso, '_run_tickets': _run_tickets}


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
        if item.get('status') != 'claimed':
            continue
        row, problems = _bound_row(item, now, support)
        rows.append(row)
        unreadable.extend(problems)
    overdue = sum(1 for row in rows if row['overdue'])
    payload = {'run': args[0], 'now': now.strftime(support['UTC_STAMP']), 'tickets': rows, 'overdue': overdue}
    if unreadable:
        payload['unreadable'] = unreadable
    return {'bound_check': payload, 'exit_code': 1 if overdue else 0}
