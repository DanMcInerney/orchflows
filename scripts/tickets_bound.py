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

Imported at module scope by nothing here: `_cmd_bound_check`'s siblings are
reached inside the call, because `tickets_format` imports this module for
the parser and the pair would otherwise close a cycle at import time.
"""
from __future__ import annotations
import re

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
