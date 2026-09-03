"""Window front door: one closed phrase grammar for a question's timeframe.

A caller holds a question spelled in words — "past week", "since the vote",
nothing at all — and a manifest whose steps take two instants. This module is
the one place that turns the first into the second, so the turn happens in a
grammar a reader can audit rather than in whichever sentence each caller
improvised. Three laws, each the reason a piece of this file exists:

**No timeframe means no window.** The empty phrase parses to the unbounded
:class:`Window`, and nothing here defaults to thirty days or to anything
else: a bound the caller never asked for would spend the cap on a window
nobody chose. The reference tool this package superseded was hard-wired to
thirty days, which is the defect, not the convention.

**An unknown phrase is refused, never guessed.** ``parse_phrase`` raises
:class:`WindowPhraseError` naming the grammar for any phrase outside it —
"since the election" names a moment this module has no calendar for, and
answering with a guess would put an invented bound on every step downstream.
The refusal is the front door working: the caller resolves the phrase to a
date it can defend and comes back with ``since 2026-11-03``.

**The anchor is the caller's ``as_of``, never a wall clock.** Every relative
phrase is arithmetic on the instant the caller passes, in
:data:`super_research.schema.INSTANT_FORMAT`, so parsing the same phrase at
the same ``as_of`` yields the same window on any host at any hour — the same
reason no ordering in this package reads the machine's own clock.

What the result means downstream is the manifest's law, not this module's:
set ``window_start``/``window_end`` on every step of a windowed question,
the core drops dated records outside the bound before the cap counts them,
and ``_support/window_reach.WINDOW_REACH`` decides per operation whether the
bound also travels to the origin or the step carries ``window_not_honored``.
This module computes instants and nothing else — it reads no roster, makes
no call, and decides no drop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import schema


class WindowPhraseError(ValueError):
    """A timeframe phrase outside the closed grammar, refused with the grammar."""


@dataclass(frozen=True)
class Window:
    """Two instants in the manifest's spelling, either or both empty.

    Exactly the shape ``window_start``/``window_end`` take on an
    :class:`super_research.schema.AcquisitionStep`: empty means unbounded on
    that side, and a phrase that bounds only the past leaves ``window_end``
    empty rather than pinning it to ``as_of`` — the question was "since
    when", not "until when", and an end nobody asked for would drop a record
    an origin dates a moment after the anchor was frozen.
    """

    window_start: str = ""
    window_end: str = ""


# The unbounded window, spelled once: what the empty phrase means.
NO_WINDOW = Window()

# The grammar, stated as the refusal states it. One phrase form per line, so
# the error message *is* the enumeration and cannot drift from the parser
# below the way a paraphrase would.
PHRASE_GRAMMAR = (
    "<empty>            no window",
    "past N hours|days|weeks|months|years   (also `last`; N optional at 1)",
    "today | yesterday",
    "on YYYY-MM-DD",
    "since YYYY-MM-DD | since YYYY-MM-DDTHH:MM:SSZ",
    "between A and B | from A to B          (A, B dates or instants)",
)

# One unit name per timedelta the arithmetic takes literally. Months and
# years are not here because a month is not a number of hours: those two are
# calendar arithmetic below, with the day clamped into the shorter month
# rather than overflowing into the next one. No regular expression anywhere
# in this module — the package admits none, so the grammar is token
# comparisons a reader steps through in the order the refusal lists them.
_UNIT_HOURS = {"hour": 1, "day": 24, "week": 24 * 7}
_CALENDAR_MONTHS = {"month": 1, "year": 12}
_DATE_FORMAT = "%Y-%m-%d"


def _refused(phrase: str) -> WindowPhraseError:
    return WindowPhraseError(
        "timeframe phrase {0!r} is outside the grammar; the grammar is:\n  {1}".format(
            phrase, "\n  ".join(PHRASE_GRAMMAR)
        )
    )


def _is_date(spelling: str) -> bool:
    """Whether this spelling is a bare calendar date and nothing more."""

    try:
        datetime.strptime(spelling, _DATE_FORMAT)
    except ValueError:
        return False
    return True


def _instant(spelling: str, phrase: str) -> datetime:
    """One date or instant as an aware moment, or the phrase's refusal.

    A bare date reads as its own midnight, which is the only instant a date
    names without inventing a time of day; a full instant reads exactly. Both
    parse under :data:`schema.INSTANT_FORMAT`'s clock so a spelling the
    manifest would refuse is refused here first, by the same door.
    """

    if _is_date(spelling):
        spelling = spelling + "T00:00:00Z"
    try:
        parsed = datetime.strptime(spelling, schema.INSTANT_FORMAT)
    except ValueError:
        raise _refused(phrase) from None
    return parsed.replace(tzinfo=timezone.utc)


def _spelled(moment: datetime) -> str:
    return moment.strftime(schema.INSTANT_FORMAT)


def _months_back(anchor: datetime, months: int) -> datetime:
    """Calendar months before the anchor, day clamped, never overflowed.

    January 31 minus one month is December 31; March 31 minus one month is
    February 28 or 29 — the last day the shorter month has, not an overflow
    into March 2 that would quietly narrow a "past month" window by two days
    of the very period it names.
    """

    index = anchor.year * 12 + (anchor.month - 1) - months
    year, month = divmod(index, 12)
    month += 1
    # The last day this month has: day 28 exists in every month, and stepping
    # from it four days is always across the boundary.
    last = ((datetime(year, month, 28, tzinfo=timezone.utc) + timedelta(days=4)).replace(day=1)
            - timedelta(days=1)).day
    return anchor.replace(year=year, month=month, day=min(anchor.day, last))


def parse_phrase(phrase: str, as_of: str) -> Window:
    """One timeframe phrase to the two instants a manifest step takes.

    ``phrase`` is compared case-insensitively with whitespace collapsed,
    because "Past  Week" and "past week" are one question; nothing else is
    normalized, and nothing outside :data:`PHRASE_GRAMMAR` is answered.
    ``as_of`` must be the manifest's own anchor in
    :data:`schema.INSTANT_FORMAT` — the same instant the replay is frozen at
    — and is refused in any other spelling for the same reason
    ``parse_manifest`` refuses it: a relative window computed off an
    unparseable anchor would be no window at all.
    """

    try:
        # Strict: no date promotion here. `parse_manifest` refuses a bare-date
        # `as_of`, so an anchor this module promoted to midnight would compute
        # a window for a manifest that can never run.
        anchor = datetime.strptime(as_of, schema.INSTANT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        raise WindowPhraseError(
            "as_of {0!r} is not in the manifest's instant spelling {1}".format(
                as_of, schema.INSTANT_FORMAT
            )
        ) from None
    words = phrase.lower().split()
    if not words:
        return NO_WINDOW

    if words[0] in ("past", "last") and len(words) in (2, 3):
        count_spelling = words[1] if len(words) == 3 else "1"
        unit = words[-1][:-1] if words[-1].endswith("s") else words[-1]
        if count_spelling.isdigit() and int(count_spelling) > 0:
            count = int(count_spelling)
            if unit in _CALENDAR_MONTHS:
                return Window(
                    window_start=_spelled(
                        _months_back(anchor, count * _CALENDAR_MONTHS[unit])
                    )
                )
            if unit in _UNIT_HOURS:
                return Window(
                    window_start=_spelled(
                        anchor - timedelta(hours=count * _UNIT_HOURS[unit])
                    )
                )
        raise _refused(phrase)

    if words == ["today"]:
        return Window(window_start=_spelled(anchor.replace(hour=0, minute=0, second=0)))
    if words == ["yesterday"]:
        midnight = anchor.replace(hour=0, minute=0, second=0)
        return Window(
            window_start=_spelled(midnight - timedelta(days=1)),
            window_end=_spelled(midnight),
        )

    if words[0] == "on" and len(words) == 2:
        if not _is_date(words[1]):
            # "on <instant>" names a day by a moment inside it, which is two
            # readings; the grammar takes dates only.
            raise _refused(phrase)
        day = _instant(words[1], phrase)
        return Window(
            window_start=_spelled(day), window_end=_spelled(day + timedelta(days=1))
        )

    if words[0] == "since" and len(words) == 2:
        return Window(window_start=_spelled(_instant(words[1], phrase)))

    span = None
    if len(words) == 4 and words[0] == "between" and words[2] == "and":
        span = (words[1], words[3])
    if len(words) == 4 and words[0] == "from" and words[2] == "to":
        span = (words[1], words[3])
    if span:
        start = _instant(span[0], phrase)
        end = _instant(span[1], phrase)
        if _is_date(span[1]):
            # A span *through* a named date includes that date: "between the
            # 3rd and the 5th" that ended at the 5th's midnight would hold
            # none of the 5th it names.
            end = end + timedelta(days=1)
        if start > end:
            raise WindowPhraseError(
                "timeframe phrase {0!r} ends before it starts: {1} > {2}".format(
                    phrase, _spelled(start), _spelled(end)
                )
            )
        return Window(window_start=_spelled(start), window_end=_spelled(end))

    raise _refused(phrase)
