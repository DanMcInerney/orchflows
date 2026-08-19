"""Shared UI model, parsing, and safe-path primitives."""


import argparse
import graphlib
import hashlib
import html
import json
import re
import sys
from collections import namedtuple
from datetime import datetime, timezone
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

# ``scripts/ui.py`` and ``scripts/tickets.py`` are siblings in the
# repository and again in ``~/.orchflows/bin`` after ``install.py`` copies
# them, so neither is ever a package member and a plain sibling import is
# the only shape that works in both. Appended, never prepended: this
# directory also holds ``trace.py``, which at sys.path[0] would shadow the
# stdlib ``trace`` module for the whole process.
_SIBLING_DIR = str(Path(__file__).resolve().parent)
if _SIBLING_DIR not in sys.path:
    sys.path.append(_SIBLING_DIR)

import state_root  # noqa: E402
from tickets import (  # noqa: E402
    DURATION_RE,
    _parse_frontmatter,
    _parse_iso,
)

LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
INDEX_ROUTE = "/"
TICKET_ROUTE = "/ticket"
GRAPH_ROUTE = "/graph"
FRICTION_ROUTE = "/friction"
SESSIONS_ROUTE = "/sessions"
SESSION_ROUTE = "/session"
# Every served path lives here. The read-only and no-network tests iterate
# this tuple, so a route added by branching inside ``render_route`` instead
# would be silently unguarded.
ROUTES = (
    INDEX_ROUTE,
    TICKET_ROUTE,
    GRAPH_ROUTE,
    FRICTION_ROUTE,
    SESSIONS_ROUTE,
    SESSION_ROUTE,
)

# Every directory the reader reads, named once, sink-relative -- the layout
# ``scripts/state_root.py`` owns, in the same relative shape it had inside a
# repository's own state directory. The conditional request's digest and the
# readers that render these have to agree about what is observed: where they
# disagree the page moves and the validator does not, and a poll is answered
# 304 against state that already changed. ``SINK_DIR`` is the root itself,
# observed for its presence alone.
SINK_DIR = ()
TICKETS_DIR = ("tickets",)
FRICTION_DIR = ("friction",)
EVENTS_DIR = ("events",)
TICKET_SUFFIX = ".md"
JSONL_SUFFIX = ".jsonl"

# Named empty states. Absent data is normal in a live sink -- a run can be
# cut before any ticket lands, a ticket can predate a section -- so every
# absence renders as one of these rather than raising or vanishing. None of
# them carries a character ``escape`` rewrites: a test asserting one of these
# is in a page compares against the page, which is escaped.
EMPTY_NO_SINK = "no state sink at this root"
EMPTY_NO_RUNS = "no runs under this sink"
EMPTY_NO_TICKETS = "no tickets in this run"
EMPTY_NO_OBJECTIVE = "no objective recorded"
EMPTY_SECTION = "section is empty"
EMPTY_NO_METER = "no elapsed meter"
EMPTY_NO_RUN = "no run by that name under this root"
EMPTY_NO_FRICTION = "no friction log under this root"
EMPTY_UNSET = "unset"
EMPTY_NO_TRANSCRIPTS = "no transcript root at this path"
EMPTY_NO_SESSIONS = "no sessions under this transcript root"
EMPTY_NO_TITLE = "no title recorded"
EMPTY_NO_CWD = "no working directory recorded"
EMPTY_NO_SESSION = "no session by that id under this transcript root"
EMPTY_NO_AGENTS = "this session spawned no subagents"
EMPTY_NO_TYPE = "no agent type recorded"
EMPTY_NO_DESCRIPTION = "no description recorded"
EMPTY_NO_DEPTH = "no spawn depth recorded"

# The one marker for the other thing: not absent, unread. Every EMPTY_ above
# is a claim about what the sink holds, and rendering one of them because a
# read failed states that claim on no evidence -- an empty ticket, a friction
# month that never happened, zero events, no transcript root. This says which
# it was, once, in the words every reader of these pages already knows the
# shape of.
DIAGNOSTIC_UNREADABLE = "could not be read"

# `contracts/work-item.md`: `suspended` "stays claimed", so the lease keeps
# running and elapsed-against-bound still measures something. Under every
# other status the claim is not live and a growing meter would be a lie --
# no ticket records when work stopped.
LIVE_CLAIM_STATUSES = ("claimed", "suspended")

# The band answers "who is working right now", which `suspended` is not: it
# holds the lease with nobody at the keyboard. A wider set here would read
# as more parallelism than the run has.
ACTIVE_STATUS = "claimed"

VERIFICATION_SECTION = "Verification"
VERIFICATION_COLUMNS = ("#", "verdict", "oracle", "class", "evidence")
VERIFICATION_ROWS = "rows"
VERIFICATION_UNPARSED = "unparsed"
VERIFICATION_UNPARSED_NOTE = (
    "unparsed: not a five-column verdict table, shown verbatim"
)

SECTION_RE = re.compile(r"^## +(.+?)[ \t]*$", re.MULTILINE)
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")
# Tickets quote markdown at each other -- a handoff record, a spec excerpt --
# so a fenced block whose content starts with `## ` is ordinary corpus
# content. Up to three leading spaces open a fence; deeper indentation is
# already an indented code block, whose lines cannot match ``SECTION_RE``.
FENCE_RE = re.compile(r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")


# --- status presentation -----------------------------------------------------

# Four channels per status, because colour alone excludes a colourblind or
# monochrome reader: the glyph carries the state on its own, the word names
# it, the border separates the states that share a hue, and hue is
# reinforcement only. Argo Workflows' graph node is icon + label + genre for
# the same reason (`lane-ui-patterns.md` §2.3).
StatusPresentation = namedtuple("StatusPresentation", ("glyph", "word", "hue", "border"))

# Hue tokens are CSS custom property *names*, never colour values: the
# palette is the design spec's deliverable and has to pass a contrast
# oracle. The family recorded against each token is the part this module
# does fix, sourced to Airflow 2.10.5 `airflow/utils/state.py` via
# `lane-ui-patterns.md` §2 -- `upstream_failed: orange` is deliberately not
# `failed: red`, and `running: lime` is deliberately not `success: green`.
HUE_TOKENS = {
    "--st-waiting": "slate",
    "--st-ready": "blue",
    "--st-running": "cyan",
    "--st-attention": "amber",
    "--st-ok": "green",
    "--st-failed": "red",
    # Not a state and deliberately not coloured as one: an unrecognized
    # status tinted slate would read as a wait. See STATUS_FALLBACK.
    "--st-unknown": "neutral",
}

# Eight statuses onto six hues, so exactly two pairs share one. The pairs
# are the contract's own groupings (`contracts/work-item.md`): `pending` and
# `suspended` are its two non-terminal waits, `blocked` and `limited` its
# two terminal halts that are not failures. Red is reserved for `failed`
# alone, so red anywhere on the page means one thing.
#
# Glyphs are single text-presentation code points from the system font
# stack -- no icon font, no SVG, and nothing from the emoji blocks, which
# render as colour images on Windows and would smuggle in a seventh hue.
STATUS_PRESENTATION = {
    # U+25CB WHITE CIRCLE: deps unmet, not eligible.
    "pending": StatusPresentation("○", "pending", "--st-waiting", "1px dotted"),
    # U+25D4 CIRCLE WITH UPPER RIGHT QUADRANT BLACK: eligible, unclaimed.
    "ready": StatusPresentation("◔", "ready", "--st-ready", "1px solid"),
    # U+25D0 CIRCLE WITH LEFT HALF BLACK: in flight.
    "claimed": StatusPresentation("◐", "claimed", "--st-running", "2px solid"),
    # U+2016 DOUBLE VERTICAL LINE: paused, resumable from its `## Handoff`.
    "suspended": StatusPresentation("‖", "suspended", "--st-waiting", "2px dashed"),
    # U+2713 CHECK MARK: terminal, every required criterion PASS.
    "complete": StatusPresentation("✓", "complete", "--st-ok", "1px solid"),
    # U+2298 CIRCLED DIVISION SLASH: halted by something upstream.
    "blocked": StatusPresentation("⊘", "blocked", "--st-attention", "2px dashed"),
    # U+2715 MULTIPLICATION X: terminal, bad.
    "failed": StatusPresentation("✕", "failed", "--st-failed", "1px solid"),
    # U+25A4 SQUARE WITH HORIZONTAL FILL: stopped at a bound, hence the
    # doubled border -- a wall, and the channel that separates it from
    # `blocked` on the shared amber.
    "limited": StatusPresentation("▤", "limited", "--st-attention", "3px double"),
    # U+21BB CLOCKWISE OPEN CIRCLE ARROW: iterating without progress and
    # stopped for it. Amber like the other two ends that are neither a
    # success nor a fault, and told apart from them by glyph and border.
    "stalled": StatusPresentation("↻", "stalled", "--st-attention", "2px dotted"),
}

# The sink is untrusted data, so the status field can hold anything. It gets
# a hue of its own: borrowing a real state's colour would render an
# unreadable value as a state the ticket is not in.
STATUS_FALLBACK = StatusPresentation("?", "unknown", "--st-unknown", "1px dotted")


def status_presentation(status: str) -> StatusPresentation:
    """Total over every possible field value; never raises."""

    return STATUS_PRESENTATION.get(status, STATUS_FALLBACK)


# A subagent's activity is not a ticket status: nobody writes it down, and
# it is read off whatever evidence the session transcript happens to carry.
# `unknown` is the honest answer for most of a real tree and it is a state,
# not a failure to have one, so it reuses the fallback's own presentation
# rather than being dressed as a wait.
ACTIVITY_RUNNING = "running"
ACTIVITY_FINISHED = "finished"
ACTIVITY_UNKNOWN = STATUS_FALLBACK.word
ACTIVITY_STATES = (ACTIVITY_RUNNING, ACTIVITY_FINISHED, ACTIVITY_UNKNOWN)

# Four channels and the same closed set of hue tokens as above; no palette
# is invented here. U+25D0 and cyan for in flight, U+2713 and green for
# terminal-good -- what both families already mean elsewhere on the page.
ACTIVITY_PRESENTATION = {
    ACTIVITY_RUNNING: StatusPresentation(
        "◐", ACTIVITY_RUNNING, "--st-running", "2px solid"
    ),
    ACTIVITY_FINISHED: StatusPresentation(
        "✓", ACTIVITY_FINISHED, "--st-ok", "1px solid"
    ),
    ACTIVITY_UNKNOWN: STATUS_FALLBACK,
}


def activity_presentation(state: str) -> StatusPresentation:
    """Total over every state, and over anything that is not one."""

    return ACTIVITY_PRESENTATION.get(state, STATUS_FALLBACK)


# An SVG rect has no `border`, so the border style that separates the two
# pairs sharing a hue is restated as a stroke pattern. Same four channels,
# same owner: both renderings are generated from STATUS_PRESENTATION.
SVG_DASH = {"solid": "none", "dashed": "5 3", "dotted": "1 3", "double": "9 2 1 2"}


def _scalar(value) -> str:
    """Frontmatter values are scalars or lists; presentation wants a scalar."""

    return value.strip() if isinstance(value, str) else ""


def _sequence(value) -> tuple:
    """A frontmatter list as a tuple of non-empty strings. A key written as
    a bare scalar where the contract says list is one item, not an error:
    The sink is untrusted data and the graph reads what is there."""

    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _fenced_spans(text: str) -> list:
    """``(start, end)`` offsets of every fenced code block. An unclosed
    fence runs to the end of the text, as CommonMark says it does."""

    spans = []
    offset = 0
    opener = None
    start = 0
    for line in text.splitlines(True):
        match = FENCE_RE.match(line.rstrip("\r\n"))
        if match is not None:
            marker = match.group("marker")
            if opener is None:
                opener, start = marker, offset
            elif marker[0] == opener[0] and len(marker) >= len(opener):
                # A closing fence carries no info string.
                if not match.group("info").strip():
                    spans.append((start, offset + len(line)))
                    opener = None
        offset += len(line)
    if opener is not None:
        spans.append((start, len(text)))
    return spans


def split_sections(text: str) -> dict:
    """Map each ``## Heading`` to its body text; first occurrence wins.
    Headings inside a fenced block are content, not structure."""

    sections = {}
    spans = _fenced_spans(text)
    matches = [
        match
        for match in SECTION_RE.finditer(text)
        if not any(start <= match.start() < end for start, end in spans)
    ]
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        name = match.group(1)
        if name not in sections:
            sections[name] = text[match.end() : end].strip()
    return sections


def _row_cells(line: str):
    """The cells of one markdown table row, or ``None`` when the line is
    not a row. A ``\\|`` is escaped content rather than a column boundary:
    the corpus carries regexes with alternation in its evidence column."""

    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    cells = UNESCAPED_PIPE_RE.split(stripped)
    # A leading and a trailing pipe each produce one empty edge cell.
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [cell.replace("\\|", "|").strip() for cell in cells]


def _is_separator(cells) -> bool:
    return bool(cells) and all(set(c) <= set("-: ") and "-" in c for c in cells)


def parse_verification(body: str) -> dict:
    """One ``## Verification`` body as ``{"state", "rows"}``.

    Two shapes exist in the corpus and only one is machine-readable: the
    five-column verdict table parses, a numbered prose list does not. The
    unreadable shape is reported ``unparsed`` and shown verbatim, never as
    zero rows -- "verified nothing" and "verdicts I cannot read" are
    different facts, and a viewer must not hand a reader the wrong one. A
    row disagreeing with the header's width makes the whole section
    unparsed for the same reason: half a table is a wrong count of
    verdicts, not a partial one.
    """

    lines = body.splitlines()
    for index, line in enumerate(lines):
        header = _row_cells(line)
        if header is None or [c.lower() for c in header] != list(VERIFICATION_COLUMNS):
            continue
        rows = []
        for following in lines[index + 1 :]:
            cells = _row_cells(following)
            if cells is None:
                break
            if _is_separator(cells):
                continue
            if len(cells) != len(VERIFICATION_COLUMNS):
                return {"state": VERIFICATION_UNPARSED, "rows": []}
            rows.append(dict(zip(VERIFICATION_COLUMNS, cells)))
        if rows:
            return {"state": VERIFICATION_ROWS, "rows": rows}
        break
    return {"state": VERIFICATION_UNPARSED, "rows": []}


def read_ticket(path: Path) -> dict:
    """One ticket's presentation fields. An unreadable or malformed file
    yields the same shape with empty values -- never an exception -- and
    carries ``unreadable`` so the page can say which of the two it was."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        unreadable = False
    except OSError:
        text, unreadable = "", True
    front = _parse_frontmatter(text)
    sections = split_sections(text)
    return {
        "id": _scalar(front.get("id")) or path.stem,
        # The other identity. Every link the page emits is built from `id`,
        # but a lookup resolves `<file_id>.md`, so the two are carried
        # separately and `identity_diagnostics` names them where they
        # disagree instead of leaving the reader a dead link.
        "file_id": path.stem,
        "status": _scalar(front.get("status")),
        "executor": _scalar(front.get("executor")),
        "bound": _scalar(front.get("bound")),
        "claimed_at": _scalar(front.get("claimed_at")),
        "claimed_by": _scalar(front.get("claimed_by")),
        "depends_on": _sequence(front.get("depends_on")),
        "write_scope": _sequence(front.get("write_scope")), "pack": _scalar(front.get("pack")),
        "objective": sections.get("Objective", ""),
        "sections": sections, "raw": text,
        "unreadable": unreadable,
        "path": str(path),
    }


def bound_minutes(bound):
    """Minutes, or ``None`` when ``bound`` is not a duration.

    Deliberately unlike ``scripts/tickets.py``'s ``_parse_bound_minutes``,
    which substitutes ``DEFAULT_BOUND_MINUTES`` so a claim can still be
    aged: a lease needs some number, but a viewer does not. The observed
    real value is ``one session``, and a meter drawn against an invented
    60-minute denominator would report progress no ticket ever stated.
    """

    match = DURATION_RE.match(bound.strip()) if isinstance(bound, str) else None
    if match is None:
        return None
    return int(match.group(1)) * (60 if match.group(2) == "h" else 1)


def _now() -> datetime:
    """The one wall clock used by both validators and rendered meters."""

    return datetime.now(timezone.utc)


def claim_meter(front: dict, now=None):
    """Elapsed against bound for a live claim, or ``None``.

    ``None`` in every degraded case -- no live claim, no duration bound, no
    parsable ``claimed_at`` -- because a meter is a measurement and there is
    nothing here to measure. ``front`` is any mapping carrying ``status``,
    ``bound`` and ``claimed_at``: a ticket record or raw frontmatter.
    """

    if _scalar(front.get("status")) not in LIVE_CLAIM_STATUSES:
        return None
    minutes = bound_minutes(_scalar(front.get("bound")))
    if not minutes or minutes <= 0:
        return None
    started = _parse_iso(_scalar(front.get("claimed_at")))
    if started is None:
        return None
    now = _facade_value("_now", _now)() if now is None else now
    # A clock skewed behind the claim would otherwise render a negative bar.
    elapsed = max(int((now - started).total_seconds() // 60), 0)
    return {
        "elapsed_minutes": elapsed,
        "bound_minutes": minutes,
        "percent": min(int(round(elapsed * 100.0 / minutes)), 100),
        "over": elapsed > minutes,
    }


# One path component's byte ceiling. POSIX `NAME_MAX` is 255 on every
# filesystem this runs on and Windows caps a component at 255 characters,
# so a longer name is one no store can hold: the path layer answers
# `ENAMETOOLONG` rather than "no such file", and an `OSError` out of a
# lookup is not one of the two answers these functions promise.
MAX_NAME_BYTES = 255
# A control character is never part of a run name or a ticket id, and NUL
# is the one the path layer refuses outright -- `Path.resolve` raises
# `ValueError: embedded null byte`, which `BaseHTTPRequestHandler` does not
# catch, so the client gets no HTTP response at all and `socketserver`
# prints the absolute tickets path to stderr.
UNSAFE_NAME_RE = re.compile(r"[\x00-\x1f\x7f:/\\]")


def _safe_name(value) -> str:
    """One path component, or ``""``.

    The query string is the only untrusted input that becomes a path, so
    this is the whole boundary between it and the filesystem. A value that
    could climb out of the tickets tree, or that the path layer would
    refuse to look up at all, resolves to nothing here rather than raising
    somewhere below.
    """

    if not isinstance(value, str) or not value or value in (".", ".."):
        return ""
    if UNSAFE_NAME_RE.search(value):
        return ""
    if len(value.encode("utf-8", "replace")) > MAX_NAME_BYTES:
        return ""
    return value


def _in_tree(base: Path, *parts):
    """``base`` joined with ``parts`` and resolved, or ``None`` when the
    result escapes ``base`` or the host's path layer refuses the name.

    ``_safe_name`` rejects every value known to reach here badly; this is
    the same guarantee one layer down, for the shapes a single host cannot
    enumerate -- a total path over the platform's own limit, say. The
    callers promise a value or ``None``, never an exception, on any string
    a client can put in a query.
    """

    try:
        root = base.resolve()
        candidate = root.joinpath(*parts).resolve()
        return candidate if root in candidate.parents else None
    except (OSError, ValueError):
        return None


def _json_object(line: str):
    """One JSONL line as a JSON object, or ``None`` when it is not one.

    Every JSONL this module reads -- the friction log, the events seam, a
    Claude Code transcript -- is append-only and written by a process that
    may be killed mid-line, so a half-written tail is expected rather than
    exceptional, and so is a line that parses to something other than a
    record. A blank line is neither: the caller drops those before asking.
    """

    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry if isinstance(entry, dict) else None
def _facade_value(name, fallback):
    facade = next((module for module_name, module in tuple(sys.modules.items()) if
        module_name != __name__ and getattr(module, "_facade_value", None) is
        _facade_value and hasattr(module, "render_route")), None)
    facade = facade or sys.modules.get("scripts.ui") or sys.modules.get("ui") or sys.modules.get("__main__")
    return getattr(facade, name, fallback)
