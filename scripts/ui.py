#!/usr/bin/env python3
"""Read-only local HTTP view of orchflows run state in the state sink.

Stdlib-only, cross-platform, and offline: every CSS byte is inlined from a
module constant, so the page fetches nothing at view time. The process
opens no file under the sink for writing and creates no directory there.
The sink is untrusted data per ``rules/visibility.md`` §6, so every value
reaching the page passes ``html.escape`` and no ticket content is ever
emitted as markup. The root is the one user-scope sink
``scripts/state_root.py`` resolves, so every workspace of every repository
shows one run's tickets at one path and a run outlives the checkout it
started in. Binds loopback only, never ``0.0.0.0``.

It also lists the Claude Code sessions under ``~/.claude/projects``, as
labels and structure alone: a transcript holds the operator's prompts,
file contents and command output for every project on the machine, and
this is not a transcript reader. That tree is read-only, forever.

Usage:
    ui.py [--root <sink>] [--port <n>] [--transcripts <path>]
"""

from __future__ import annotations

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


def _svg_stroke(presentation: StatusPresentation) -> tuple:
    """``(stroke-width, stroke-dasharray)`` for one status's CSS border."""

    width, _, style = presentation.border.partition(" ")
    return width.replace("px", "").strip() or "1", SVG_DASH.get(style.strip(), "none")


def _status_css() -> str:
    """Derived from both presentation tables, so neither a ticket status nor
    a subagent's activity can carry one hue in the module and another in the
    stylesheet -- and so a state cannot be drawn in a class the stylesheet
    never declares, which renders as no state at all."""

    lines = [
        "  /* Hue tokens are names, not colours: the palette is the design",
        "     spec's deliverable. Until it lands every token resolves to the",
        "     inherited text colour, so this file asserts no colour at all. */",
        "  :root { " + " ".join("{0}: currentColor;".format(t) for t in HUE_TOKENS) + " }",
        "  .st { display: inline-block; padding: 0 .35rem; border-radius: .25rem;",
        "        white-space: nowrap; }",
        "  .st .glyph { font-style: normal; }",
    ]
    every = [STATUS_FALLBACK] + list(STATUS_PRESENTATION.values())
    every += [seen for seen in ACTIVITY_PRESENTATION.values() if seen not in every]
    for presentation in every:
        stroke_width, dash = _svg_stroke(presentation)
        lines.append(
            "  .st-{word} {{ border: {border} var({hue}); }}".format(
                word=presentation.word, border=presentation.border, hue=presentation.hue
            )
        )
        lines.append(
            "  .nd-{word} rect {{ stroke: var({hue}); stroke-width: {stroke_width};"
            " stroke-dasharray: {dash}; }}".format(
                word=presentation.word,
                hue=presentation.hue,
                stroke_width=stroke_width,
                dash=dash,
            )
        )
    return "\n".join(lines) + "\n"


# Structural only. Visual form is a later spec's deliverable; this is the
# minimum that keeps a table legible. Carried as a constant rather than a
# sidecar file because install.py's SCRIPT_NAMES ships flat filenames, so a
# sidecar asset would never reach ~/.orchflows/bin.
PAGE_CSS = (
    """
  body { margin: 0; font: 15px/1.5 system-ui, sans-serif; }
  main { max-width: 64rem; margin: 0 auto; padding: 1.5rem; }
  h1 { font-size: 1.2rem; }
  h2 { font-size: 1rem; margin-top: 1.75rem; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border-bottom: 1px solid #ccc; padding: .3rem .5rem;
           text-align: left; vertical-align: top; }
  th { font-weight: 600; white-space: nowrap; }
  .root { font-family: ui-monospace, monospace; font-size: .85rem; }
  .empty { font-style: italic; }
  pre { white-space: pre-wrap; margin: .25rem 0; font-size: .9rem; }
  .meta, .claim, .count, .back { margin: .25rem 0; }
  .count { font-size: .85rem; }
  .diagnostics { margin: .5rem 0; padding-left: 1.2rem; font-size: .9rem; }
  .band { list-style: none; margin: .5rem 0; padding: 0; }
  .band li { padding: .2rem 0; border-bottom: 1px solid #ccc; }
  .feed { list-style: none; margin: .5rem 0; padding: 0; }
  .entry, .event { padding: .4rem 0; border-bottom: 1px solid #ccc; }
  .entry p, .event p { margin: .1rem 0; }
  .ts { font-family: ui-monospace, monospace; font-size: .85rem; }
  .canvas { overflow: auto; max-width: 100%; }
  .graph { max-width: 100%; height: auto; }
  .graph .edge { stroke: currentColor; stroke-width: 1; fill: none; }
  .graph .arrow { fill: currentColor; }
  .graph rect { fill: none; }
  .graph text { font: 12px/1 ui-monospace, monospace; fill: currentColor; }
  .graph .nd-state { font-size: 11px; }
  .graph a { text-decoration: none; }
  /* An edge that is a guess is drawn like one. The page says so in words
     too: a dash pattern alone is not a channel a reader can decode. */
  .graph .edge-inferred { stroke-dasharray: 5 3; }
  /* The session flowchart's own node. It is not in an activity state, so
     it borrows no state's presentation. */
  .graph .nd-root rect { stroke: currentColor; stroke-width: 2; }
"""
    + _status_css()
)

# A ticket under one of these is a ticket something is about to happen to.
# Under every other status the run only moves once one of these does, so
# there is nothing for a one-second poll to catch. `suspended` holds the
# lease with nobody at the keyboard and belongs on the slow interval.
POLL_FAST_STATUSES = ("claimed", "ready")
POLL_LIVE_MS = 1000
POLL_IDLE_MS = 5000
POLL_HIDDEN_MS = 15000

# Inline for the same reason as the CSS: `install.py` ships flat filenames,
# so a sidecar asset would never reach ~/.orchflows/bin -- and a remote one
# is forbidden outright. Interpolated as a `.format` *value*, so its braces
# are never a format field.
_POLL_CONSTANTS = "  var LIVE_MS = {0}, IDLE_MS = {1}, HIDDEN_MS = {2};\n".format(
    POLL_LIVE_MS, POLL_IDLE_MS, POLL_HIDDEN_MS
)

PAGE_JS = (
    "\n(function () {\n"
    + _POLL_CONSTANTS
    + """  var tag = null;
  var timer = null;
  function delay() {
    if (document.hidden) { return HIDDEN_MS; }
    var here = document.querySelector('main');
    return here && here.dataset.live === 'yes' ? LIVE_MS : IDLE_MS;
  }
  function schedule() {
    window.clearTimeout(timer);
    // A timeout the answer reschedules, never a fixed repeating timer: a
    // slow answer must not queue the next request behind it, and the
    // stdlib server serves one at a time.
    timer = window.setTimeout(poll, delay());
  }
  function poll() {
    var headers = tag ? {'If-None-Match': tag} : {};
    window.fetch(window.location.href, {headers: headers}).then(function (r) {
      var seen = r.headers.get('ETag');
      if (seen) { tag = seen; }
      return r.status === 304 ? null : r.text();
    }).then(function (text) {
      if (text === null) { return; }
      var doc = new DOMParser().parseFromString(text, 'text/html');
      var fresh = doc.querySelector('main');
      var here = document.querySelector('main');
      if (fresh && here) { here.replaceWith(fresh); }
    }).catch(function () {
      // The viewer outlives the server it reads: keep the loop alive so a
      // restarted server is picked up without a manual reload.
    }).then(schedule);
  }
  document.addEventListener('visibilitychange', schedule);
  schedule();
})();
"""
)


# --- discovery ---------------------------------------------------------------


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
    yields the same shape with empty values -- never an exception."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
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
        "objective": sections.get("Objective", ""),
        "sections": sections,
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
    """The wall clock, read in exactly one place.

    Every value on the page that moves while no file moves comes through
    here, so the digest that validates the page and the render that draws
    it read one clock -- and a test can hold it still.
    """

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
    now = _now() if now is None else now
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
UNSAFE_NAME_RE = re.compile(r"[\x00-\x1f\x7f/\\]")


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


def find_ticket(root: Path, run: str, ticket_id: str):
    """One ticket by run and id, or ``None``. Never walks the whole tree,
    and never resolves outside the sink's ``tickets/``."""

    run, ticket_id = _safe_name(run), _safe_name(ticket_id)
    # The name a lookup uses carries the suffix, so it is that name -- not
    # the id it came from -- that has to clear the component ceiling.
    if not run or not ticket_id or not _safe_name(ticket_id + TICKET_SUFFIX):
        return None
    path = _in_tree(Path(root).joinpath(*TICKETS_DIR), run, ticket_id + TICKET_SUFFIX)
    try:
        found = path is not None and path.is_file()
    except OSError:
        return None
    return read_ticket(path) if found else None


def run_tickets(root: Path, run: str):
    """Every ticket in one run, or ``None`` when the run does not resolve.
    Guarded like ``find_ticket``: the run name is client-supplied."""

    run = _safe_name(run)
    if not run:
        return None
    run_dir = _in_tree(Path(root).joinpath(*TICKETS_DIR), run)
    try:
        found = run_dir is not None and run_dir.is_dir()
    except OSError:
        return None
    if not found:
        return None
    return [read_ticket(path) for path in sorted(run_dir.glob("*" + TICKET_SUFFIX))]


def graph_input(tickets) -> tuple:
    """``(node ids, edges)`` for one run. An edge runs from a dependency to
    the ticket that declares it, so it points up the layers."""

    ids = tuple(ticket["id"] for ticket in tickets)
    edges = tuple(
        (dependency, ticket["id"])
        for ticket in tickets
        for dependency in ticket["depends_on"]
    )
    return ids, edges


# Named for the same reason the layout's DIAGNOSTIC_CYCLE and
# DIAGNOSTIC_DANGLING are: this reader says what it cannot honour. A ticket
# whose frontmatter `id:` is not its file name is reachable from nothing
# the page draws -- the index row, the graph node and the active band all
# link `id`, and every lookup resolves `<file name>.md` -- and two files
# declaring one id collapse onto one node, hiding the other ticket
# outright. Nothing on the write path prevents either: a ticket copied or
# renamed between runs keeps the id it was written with.
DIAGNOSTIC_ID_MISMATCH = "frontmatter id does not name its own file"
DIAGNOSTIC_ID_COLLISION = "one id declared by two files"


def identity_diagnostics(tickets) -> list:
    """Every place a run's tickets disagree about their own identity."""

    diagnostics = [
        "{0}: {1} in {2}{3}".format(
            DIAGNOSTIC_ID_MISMATCH, ticket["id"], ticket["file_id"], TICKET_SUFFIX
        )
        for ticket in tickets
        if ticket["id"] != ticket["file_id"]
    ]
    files = {}
    for ticket in tickets:
        files.setdefault(ticket["id"], []).append(ticket["file_id"] + TICKET_SUFFIX)
    for ticket_id in sorted(name for name, seen in files.items() if len(seen) > 1):
        diagnostics.append(
            "{0}: {1} declared by {2}".format(
                DIAGNOSTIC_ID_COLLISION, ticket_id, ", ".join(sorted(files[ticket_id]))
            )
        )
    return diagnostics


FRICTION_KEYS = ("ts", "observed", "expected", "category", "host")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _stamp_order(entry: dict) -> tuple:
    """Newest first. An entry whose ``ts`` will not parse sorts last rather
    than jumping the queue on a string comparison."""

    stamp = _parse_iso(_scalar(entry.get("ts")))
    return (stamp is not None, stamp or _EPOCH)


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


def _read_jsonl(text: str, entries: list) -> int:
    """Append every JSON object in ``text`` to ``entries``; return the count
    of lines that were not one.

    One bad line costs that line and nothing else: the friction law's whole
    point is that observations survive, and the events seam is held to the
    same handling by sharing this code rather than by resembling it.
    """

    skipped = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        entry = _json_object(line)
        if entry is None:
            skipped += 1
        else:
            entries.append(entry)
    return skipped


def read_friction(root) -> dict:
    """Every friction entry under ``root``, newest first, with a count of
    the lines that could not be read as one."""

    directory = Path(root).joinpath(*FRICTION_DIR)
    entries = []
    skipped = 0
    for path in sorted(directory.glob("*" + JSONL_SUFFIX)) if directory.is_dir() else ():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Unreadable this poll; the next one tries again.
            continue
        skipped += _read_jsonl(text, entries)
    entries.sort(key=_stamp_order, reverse=True)
    return {"entries": entries, "skipped": skipped}


def read_events(root, run: str):
    """One run's hook events, newest first, or ``None`` when it has no log.

    The deferred hooks seam the spec's ``binding_constraints`` fix so v2 is
    additive: ``<sink>/events/<run>.jsonl``, one JSON object per line,
    carrying ``ts``, ``run``, ``ticket``, ``agent``, ``event``, ``tool`` and
    ``detail``. No hook writes it in this version, so ``None`` is the
    ordinary answer and it has to stay silent -- a heading over an empty
    feed would promise a stream nothing produces.
    """

    run = _safe_name(run)
    if not run or not _safe_name(run + JSONL_SUFFIX):
        return None
    path = _in_tree(Path(root).joinpath(*EVENTS_DIR), run + JSONL_SUFFIX)
    try:
        found = path is not None and path.is_file()
    except OSError:
        return None
    if not found:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        # Unreadable this poll; the next one tries again. Silence is the
        # documented answer for an absent log, and this is not that.
        return {"entries": [], "skipped": 0}
    entries = []
    skipped = _read_jsonl(text, entries)
    entries.sort(key=_stamp_order, reverse=True)
    return {"entries": entries, "skipped": skipped}


def active_claims(discovery: dict) -> list:
    """Every ticket under way, paired with the run it belongs to.

    Ticket ids are unique only within a run, so an id alone would not say
    which claim it is.
    """

    return [
        {"run": run["run"], "ticket": ticket}
        for run in discovery["runs"]
        for ticket in run["tickets"]
        if ticket["status"] == ACTIVE_STATUS
    ]


def default_root() -> Path:
    """The sink this viewer reads when ``--root`` names none.

    One fact, one owner (``rules/visibility.md`` §3): the path comes from
    ``scripts/state_root.py`` and is read at call time, never cached, so a
    caller may redirect ``$ORCHFLOWS_STATE_HOME`` after import.
    """

    return state_root.state_root()


def _resolve_root(start) -> Path:
    """The sink root to read.

    No git walk: run state is not in the repository any more, so where the
    viewer was launched decides nothing. ``start`` is used as given, which
    also lets the viewer be pointed at a copy of a sink.
    """

    return Path(start).resolve()


def discover(start) -> dict:
    """Every run and ticket in the sink at ``start``."""

    root = _resolve_root(start)
    tickets_root = root.joinpath(*TICKETS_DIR)
    runs = []
    if not root.is_dir():
        empty = EMPTY_NO_SINK
    else:
        if tickets_root.is_dir():
            for run_dir in sorted(p for p in tickets_root.iterdir() if p.is_dir()):
                runs.append(
                    {
                        "run": run_dir.name,
                        "tickets": [read_ticket(p) for p in sorted(run_dir.glob("*.md"))],
                    }
                )
        empty = "" if runs else EMPTY_NO_RUNS
    return {"root": root, "empty": empty, "runs": runs}


# --- dependency graph layout -------------------------------------------------

# A layered layout with a Coffman-Graham sorter, computed here rather than
# in the browser: Argo Workflows ships the same two phases hand-rolled in
# 56 + 48 lines with zero dependencies for graphs far larger than this
# project's 3-12 tickets (`lane-ui-patterns.md` §3), and in Python it falls
# under `unittest discover`, so a layout bug is a failing test rather than
# a visual regression nobody catches.

# Coffman-Graham's width bound W. Four keeps a run inside a laptop viewport;
# a wider fan spills onto further layers instead of off the right edge.
LAYER_WIDTH = 4
NODE_WIDTH = 132
NODE_HEIGHT = 44
GAP_X = 24
GAP_Y = 52
MARGIN = 16

# Coordinates are integers, so "two calls return byte-equal coordinates" is
# a fact about the layout rather than about float formatting.
LayoutNode = namedtuple("LayoutNode", ("id", "layer", "order", "x", "y"))

# What the layout cannot honour it names. Both shapes occur on real data:
# nothing on the write path proves a `depends_on` set is acyclic, and a
# ticket copied between runs keeps a `depends_on` its new run cannot
# resolve.
DIAGNOSTIC_CYCLE = "dependency cycle"
DIAGNOSTIC_DANGLING = "depends_on names no ticket in this run"


def layout_key(node_ids, edges) -> tuple:
    """The node-and-edge set, normalized, and nothing else.

    Nothing derived from a ticket's *state* may reach this key: re-laying
    out a graph on a refresh that moved no node is the live defect
    `lane-ui-patterns.md` §6(3) records in Argo, whose own fix sits in the
    source commented out. Sorting here is also what makes the layout
    independent of the order the tickets happened to be read in.
    """

    return (tuple(sorted(set(node_ids))), tuple(sorted(set(edges))))


def _rotated(cycle) -> list:
    """A reported cycle restated from its lexicographically smallest node,
    so the diagnostic reads the same however the detector entered it."""

    ring = list(cycle[:-1]) if len(cycle) > 1 and cycle[0] == cycle[-1] else list(cycle)
    if not ring:
        return []
    start = ring.index(min(ring))
    ring = ring[start:] + ring[:start]
    return ring + [ring[0]]


def _break_cycles(node_ids, edges) -> tuple:
    """``(edges with every back arc withheld, one diagnostic per cycle)``.

    ``graphlib.TopologicalSorter`` exists at the 3.9 floor and reports the
    offending nodes rather than leaving them to be guessed. Only an arc the
    detector itself named is withheld, so each pass makes progress; the
    loop is bounded by the edge count, so the pathological set costs time
    and never the process.
    """

    kept = list(edges)
    diagnostics = []
    for _ in range(len(edges) + 1):
        sorter = graphlib.TopologicalSorter()
        for node in node_ids:
            sorter.add(node)
        for source, target in kept:
            sorter.add(target, source)
        try:
            sorter.prepare()
            return kept, diagnostics
        except graphlib.CycleError as error:
            ring = _rotated(list(error.args[1]))
            arcs = set()
            for index in range(len(ring) - 1):
                arcs.add((ring[index], ring[index + 1]))
                arcs.add((ring[index + 1], ring[index]))
            droppable = sorted(arc for arc in arcs if arc in kept)
            if not droppable:
                break
            kept.remove(droppable[0])
            diagnostics.append(
                "{0}: {1}; edge {2} -> {3} not drawn".format(
                    DIAGNOSTIC_CYCLE,
                    " -> ".join(ring),
                    droppable[0][0],
                    droppable[0][1],
                )
            )
    return kept, diagnostics


def _predecessors(node_ids, edges) -> dict:
    """``{node: sorted dependencies}``, every node present."""

    preds = dict((node, set()) for node in node_ids)
    for source, target in edges:
        preds[target].add(source)
    return dict((node, sorted(values)) for node, values in preds.items())


def _coffman_graham_order(node_ids, preds) -> list:
    """Coffman-Graham phase 1: label each node only once every predecessor
    carries a label, taking the candidate whose predecessor labels are
    lexicographically smallest. The tie-break on the id is load-bearing --
    without it the whole layout depends on iteration order."""

    labels = {}
    order = []
    remaining = list(node_ids)
    while remaining:
        best = None
        for node in remaining:
            if any(p not in labels for p in preds[node]):
                continue
            key = (sorted((labels[p] for p in preds[node]), reverse=True), node)
            if best is None or key < best:
                best = key
        if best is None:
            # No candidate means a cycle reached this far. Unreachable once
            # `_break_cycles` has run; kept so a caller that skipped it
            # degrades to input order rather than looping forever.
            order.extend(remaining)
            break
        labels[best[1]] = len(labels)
        order.append(best[1])
        remaining.remove(best[1])
    return order


def _layer_assignment(order, preds, width) -> dict:
    """Coffman-Graham phase 2: each node lands on the lowest layer that is
    strictly above every predecessor's and is not already full. Every edge
    is therefore upward by construction, not by a later repair pass."""

    layers = {}
    occupancy = {}
    for node in order:
        layer = max((layers[p] + 1 for p in preds[node] if p in layers), default=0)
        while occupancy.get(layer, 0) >= width:
            layer += 1
        layers[node] = layer
        occupancy[layer] = occupancy.get(layer, 0) + 1
    return layers


def _barycenter(node, preds, placed) -> Fraction:
    """The mean position of a node's already-placed predecessors, exactly.
    A float mean sorts the same today and is one rounding change away from
    not doing so. A node with no placed predecessor floats left."""

    positions = [placed[p] for p in preds[node] if p in placed]
    if not positions:
        return Fraction(-1)
    return Fraction(sum(positions), len(positions))


def _within_layer_order(node_ids, layers, preds) -> dict:
    """One barycenter sweep down the layers. Crossing reduction is one of
    the two things dagre buys over Argo's hand-rolled layout, and one sweep
    is most of it at this size; ties break on the id."""

    members = {}
    for node in node_ids:
        members.setdefault(layers[node], []).append(node)
    placed = {}
    for layer in sorted(members):
        ordered = sorted(
            members[layer], key=lambda node: (_barycenter(node, preds, placed), node)
        )
        for index, node in enumerate(ordered):
            placed[node] = index
    return placed


def graph_layout(node_ids, edges) -> dict:
    """Coordinates for one run's dependency graph.

    ``edges`` run from a dependency to the ticket that declares it, so an
    edge always points up the layers. Returns ``nodes``, the ``edges``
    actually drawn, any ``diagnostics``, and the canvas size.

    O(V^2 log V + E) -- the Coffman-Graham labelling is the quadratic term,
    which at 3-12 tickets is a few hundred comparisons.
    """

    ids, given = layout_key(node_ids, edges)
    known = set(ids)
    diagnostics = []
    missing = sorted({end for edge in given for end in edge} - known)
    if missing:
        diagnostics.append("{0}: {1}".format(DIAGNOSTIC_DANGLING, ", ".join(missing)))
    kept, cycles = _break_cycles(
        ids, [edge for edge in given if edge[0] in known and edge[1] in known]
    )
    diagnostics.extend(cycles)
    preds = _predecessors(ids, kept)
    order = _coffman_graham_order(ids, preds)
    layers = _layer_assignment(order, preds, LAYER_WIDTH)
    placed = _within_layer_order(ids, layers, preds)
    nodes = [
        LayoutNode(
            node,
            layers[node],
            placed[node],
            MARGIN + placed[node] * (NODE_WIDTH + GAP_X),
            MARGIN + layers[node] * (NODE_HEIGHT + GAP_Y),
        )
        for node in ids
    ]
    columns = max((node.order for node in nodes), default=-1) + 1
    rows = max((node.layer for node in nodes), default=-1) + 1
    return {
        "nodes": nodes,
        "edges": list(kept),
        "diagnostics": diagnostics,
        "width": MARGIN * 2 + columns * NODE_WIDTH + max(columns - 1, 0) * GAP_X,
        "height": MARGIN * 2 + rows * NODE_HEIGHT + max(rows - 1, 0) * GAP_Y,
    }


LAYOUT_CACHE = {}
LAYOUT_CACHE_LIMIT = 32


def _make_room(cache: dict, limit: int):
    """Evict oldest-first until one insertion fits under ``limit``.

    Insertion-ordered and bounded, because the process outlives every run
    and every session it is ever asked about. A cache already below its
    limit evicts nothing: a negative slice here would drop the *newest*
    entries instead, which is the opposite of the policy.
    """

    excess = len(cache) - limit + 1
    for stale in list(cache)[:excess] if excess > 0 else ():
        cache.pop(stale, None)


def cached_layout(node_ids, edges) -> dict:
    """``graph_layout`` memoized on the node-and-edge set alone.

    Status is deliberately absent from the key: a poll that repaints a
    ticket from claimed to complete moved no node, so it must not pay for
    a layout.
    """

    key = layout_key(node_ids, edges)
    layout = LAYOUT_CACHE.get(key)
    if layout is None:
        layout = graph_layout(node_ids, edges)
        _make_room(LAYOUT_CACHE, LAYOUT_CACHE_LIMIT)
        LAYOUT_CACHE[key] = layout
    return layout


# --- Claude Code sessions -----------------------------------------------------

# A second data source, and a far more dangerous one than the sink. A
# transcript holds the operator's prompts, the contents of the files they
# opened and the output of the commands they ran, for every project on the
# machine. The spec's `binding_constraints` close the renderable set to
# labels and structure: ``sessionId``, ``aiTitle``, the ``worktree-state``
# fields, timestamps, sizes, counts, and a subagent's own metadata. So the
# reader below parses *for* the two record types it renders and drops every
# other line before anything is taken from it -- there is no render-time
# filter to get wrong, because nothing else is ever held.
#
# The layout is an undocumented implementation detail of another program,
# not a contract. Every field access degrades to a named diagnostic, so a
# Claude Code release that moves a key produces a visibly degraded page
# rather than a traceback or a silently empty one that looks correct.

DEFAULT_TRANSCRIPTS = (".claude", "projects")
SUBAGENTS_DIR = "subagents"
# Two files carry one subagent: its metadata, which is read, and its own
# conversation, which is only ever stat'd. Both are listed, because the
# later of the two mtimes is when the subagent was last heard from.
AGENT_FILE_GLOB = "agent-*"
AGENT_META_SUFFIX = ".meta.json"

RECORD_TYPE_KEY = "type"
AI_TITLE_RECORD = "ai-title"
AI_TITLE_KEY = "aiTitle"
WORKTREE_RECORD = "worktree-state"
# Observed on a live host: the worktree fields sit one level down under
# ``worktreeSession``, though the spec's evidence records them flat. Both
# shapes are read, because neither is anybody's contract.
WORKTREE_SESSION_KEY = "worktreeSession"
# ``worktreePath`` first: a session inside a linked worktree runs there, and
# that is the path the project directory name encodes.
WORKTREE_CWD_KEYS = ("worktreePath", "originalCwd")

# The one piece of evidence in the tree that a subagent ever ran. Observed
# on a live host over 305 subagents, and nobody's contract: an `assistant`
# record carries a `tool_use` block named `Agent` whose `id` is the
# subagent's `toolUseId`, and a later `user` record carries a `tool_result`
# block quoting that same id back once it has returned. Nothing else says
# it -- `tool-results/` names no subagent's id at all.
MESSAGE_KEY = "message"
CONTENT_KEY = "content"
TOOL_USE_BLOCK = "tool_use"
TOOL_RESULT_BLOCK = "tool_result"
TOOL_USE_ID_KEY = "tool_use_id"
BLOCK_ID_KEY = "id"
BLOCK_NAME_KEY = "name"
AGENT_TOOL_NAME = "Agent"

DIAGNOSTIC_UNREADABLE_TRANSCRIPT = "transcript could not be read"
DIAGNOSTIC_UNREADABLE_LINES = "unreadable transcript lines"
DIAGNOSTIC_NO_RECORDS = "transcript holds no records"
DIAGNOSTIC_UNDECODABLE_SLUG = "project directory name is not an encoded path"
DIAGNOSTIC_UNRENDERABLE_STAMP = "last activity time is outside the calendar"
# A row is a promise that the link on it opens. `/session` takes its id in a
# query string and `_safe_name` is the boundary that query crosses, so a
# filename the walk finds and the boundary refuses is named here instead of
# being listed under a link that answers "no such session" about a file this
# very page just drew.
DIAGNOSTIC_UNADDRESSABLE_SESSION = "session file cannot be addressed by name"

# Where a working directory came from, said on the page. The two are not
# equally trustworthy and the difference is not the reader's to hide.
CWD_FROM_RECORD = "from worktree-state"
CWD_FROM_NAME = "decoded from the directory name"

# The row, named once. Widening it is how the content wall gets breached, so
# it is a constant a test can hold rather than a shape spread over a format
# string.
SESSION_COLUMNS = ("sid", "title", "cwd", "when", "size", "agents", "notes")
SESSION_HEADINGS = (
    "session",
    "title",
    "working directory",
    "last activity",
    "bytes",
    "subagents",
    "notes",
)

# The subagent metadata this reader draws, named once for the same reason
# as SESSION_COLUMNS. `parentAgentId` is read and is deliberately not here:
# what it resolves to is drawn as an edge between two nodes already on the
# page, so the field's own value never reaches a reader.
AGENT_TYPE_KEY = "agentType"
AGENT_DESCRIPTION_KEY = "description"
AGENT_TOOL_USE_KEY = "toolUseId"
AGENT_DEPTH_KEY = "spawnDepth"
AGENT_PARENT_KEY = "parentAgentId"

AGENT_COLUMNS = ("agent", "type", "description", "depth", "state", "attached", "when")
AGENT_HEADINGS = (
    "subagent",
    "agent type",
    "description",
    "spawn depth",
    "activity",
    "attached to",
    "last activity",
)

DIAGNOSTIC_UNREADABLE_AGENT = "subagent metadata could not be read"
DIAGNOSTIC_INFERRED_EDGE = (
    "a dashed edge is inferred: the subagent records no parent, so it is "
    "drawn on the orchestrator by its spawn depth alone"
)
# The second guess, which is not the first one. Saying "records no parent"
# of a subagent that recorded one would be a false statement about another
# program's data, and it is the reader who would go looking for the parent
# that was supposedly never written down. No clause about spawn depth here
# either: a depth-3 record drawn on the orchestrator is not drawn by its
# depth, and a sentence claiming so contradicts the number beside it.
DIAGNOSTIC_UNRESOLVED_PARENT = (
    "a dashed edge is inferred: the subagent records a parent that names no "
    "other subagent of this session, so it is drawn on the orchestrator"
)

# The flowchart's own node, which is the session itself. Every subagent
# node is named for a file matching ``agent-*``, so no metadata file can
# collide with it.
ORCHESTRATOR_NODE = "orchestrator"
ORCHESTRATOR_ANCHOR = "session"

# What an edge was read off, said on the row it belongs to. A subagent at
# depth 1 was spawned by the session and nothing else could have spawned
# it; a recorded parent that resolves to a node on this page is a fact; a
# depth-2 subagent that records no parent is neither, and the guess is
# labelled a guess.
EDGE_FROM_DEPTH = "spawn depth 1"
EDGE_FROM_PARENT = "recorded parent"
EDGE_INFERRED = "inferred: no parent recorded"
# A fourth case, and the one the other three are not: a pointer was
# written down and resolved to nothing on this page. One sentence covers
# every shape that reaches here -- a stranger, the agent itself, and the
# orchestrator, which `agent_ids` deliberately withholds.
EDGE_PARENT_UNRESOLVED = (
    "inferred: recorded parent names no other subagent of this session"
)

# What the state was read off, said beside it. A state whose evidence is
# not on the page is indistinguishable from a guess.
EVIDENCE_CALLED = "called, no result yet"
EVIDENCE_RETURNED = "result recorded"
EVIDENCE_NONE = "no call in this transcript"


def transcript_root(value=None) -> Path:
    """The transcript root: ``value`` when given, else ``~/.claude/projects``.

    Path arithmetic and nothing else -- the tree is never opened here. This
    is also the only place the default is resolved, and ``main`` is its only
    caller, so a reader handed no root renders a named empty state instead
    of falling back to the operator's real transcripts.
    """

    if value:
        return Path(value).expanduser()
    return Path.home().joinpath(*DEFAULT_TRANSCRIPTS)


def decode_slug(slug) -> str:
    """A project directory name as the working directory it encodes, or ``""``.

    Claude Code names the directory after the working directory with every
    separator replaced by ``-``, which is not invertible: ``.`` encodes to
    ``-`` as well, and a ``-`` already in a directory name is
    indistinguishable from either, so ``…-orchflows--claude-worktrees-a-b``
    decodes wrong in three places. What comes back is a guess, named as one
    wherever it is the only source; a name that does not even open with the
    separator marker is refused rather than guessed at.
    """

    if not isinstance(slug, str) or not slug.startswith("-"):
        return ""
    return "/" + slug[1:].replace("-", "/")


def _stat_identity(path: Path):
    """``(name, size, mtime)`` for one file, or ``None`` when the path layer
    will not answer. The parse cache's key and the validator's contribution
    are these same three facts, so the page and the tag it is served under
    cannot disagree about which file they saw."""

    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path), stat.st_size, stat.st_mtime_ns)


def _worktree_cwd(record: dict) -> str:
    """The working directory one ``worktree-state`` record states, or ``""``."""

    nested = record.get(WORKTREE_SESSION_KEY)
    holders = (nested, record) if isinstance(nested, dict) else (record,)
    for holder in holders:
        for key in WORKTREE_CWD_KEYS:
            value = holder.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _content_blocks(record: dict) -> list:
    """The content blocks of one conversation record, or none.

    Observed shape: the blocks sit under ``message.content``. The record is
    another program's JSON, so anything else there is not a block list.
    """

    message = record.get(MESSAGE_KEY)
    blocks = message.get(CONTENT_KEY) if isinstance(message, dict) else None
    if not isinstance(blocks, list):
        return []
    return [block for block in blocks if isinstance(block, dict)]


def _agent_evidence(record: dict, calls: set, returns: set) -> None:
    """Fold one record into the call and return sets.

    The tool *name* is the discriminator and dropping it is the whole bug
    this guards: a subagent's ``toolUseId`` is a tool-use id like any other,
    and a finished ``Bash`` command under that id is not a finished
    subagent. A return is only counted for a call already seen, which is
    also the order a transcript writes them in.
    """

    for block in _content_blocks(record):
        kind = block.get(RECORD_TYPE_KEY)
        if kind == TOOL_USE_BLOCK and block.get(BLOCK_NAME_KEY) == AGENT_TOOL_NAME:
            identifier = block.get(BLOCK_ID_KEY)
            if isinstance(identifier, str) and identifier:
                calls.add(identifier)
        elif kind == TOOL_RESULT_BLOCK:
            identifier = block.get(TOOL_USE_ID_KEY)
            if identifier in calls:
                returns.add(identifier)


def _transcript_summary(path: Path) -> dict:
    """The two labels the index draws from one transcript, the evidence that
    each subagent ever ran, and nothing else.

    Streamed a line at a time, and every line that is not one of the
    rendered record types is dropped before a single value is taken from it.
    A real transcript is megabytes of conversation; none of it is ever held
    long enough to be filtered later, and what survives this pass is a
    handful of tool-use ids -- one per subagent the session spawned.
    """

    calls, returns = set(), set()
    summary = {
        "title": "",
        "cwd": "",
        "records": 0,
        "skipped": 0,
        "unreadable": False,
        "agent_calls": calls,
        "agent_returns": returns,
    }
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = _json_object(line)
                if record is None:
                    summary["skipped"] += 1
                    continue
                summary["records"] += 1
                kind = record.get(RECORD_TYPE_KEY)
                if kind == AI_TITLE_RECORD:
                    title = record.get(AI_TITLE_KEY)
                    # Last one wins: the title is rewritten as the session
                    # goes on, and the reader wants the current one.
                    if isinstance(title, str) and title.strip():
                        summary["title"] = title.strip()
                elif kind == WORKTREE_RECORD:
                    cwd = _worktree_cwd(record)
                    if cwd:
                        summary["cwd"] = cwd
                else:
                    _agent_evidence(record, calls, returns)
    except OSError:
        # Unreadable, or gone between the listing and the open. Whatever was
        # read before that stands; the absence is named, not guessed at.
        summary["unreadable"] = True
    return summary


TRANSCRIPT_CACHE = {}
TRANSCRIPT_CACHE_LIMIT = 256


def cached_transcript(path: Path, identity) -> dict:
    """``_transcript_summary`` memoized on the file's stat identity.

    The index draws one title and one working directory out of a file that
    is routinely megabytes, for every session on the machine, and the poll
    asks for the page every second. Keyed on name, size and mtime -- the
    same three facts the page's own validator is built from -- so an
    unchanged transcript is parsed once and a changed one is parsed again.
    """

    summary = TRANSCRIPT_CACHE.get(identity)
    if summary is None:
        summary = _transcript_summary(path)
        _make_room(TRANSCRIPT_CACHE, TRANSCRIPT_CACHE_LIMIT)
        TRANSCRIPT_CACHE[identity] = summary
    return summary


def _subagent_files(path: Path) -> tuple:
    """Every subagent file beside one transcript, metadata and conversation
    alike.

    The conversation is listed and never opened: it is megabytes of the
    same content the transcript holds, and the only thing read off it is
    the mtime the flowchart draws as a last activity. A session directory
    that does not exist is no subagents, not an error -- most sessions
    spawn nothing.
    """

    directory = _in_tree(path.parent, path.stem, SUBAGENTS_DIR)
    if directory is None:
        return ()
    try:
        return tuple(sorted(directory.glob(AGENT_FILE_GLOB))) if directory.is_dir() else ()
    except OSError:
        return ()


def _agent_id(path: Path) -> str:
    """The subagent one of its files is named for: ``agent-aa11.meta.json``
    and ``agent-aa11.jsonl`` are two files about one subagent."""

    for suffix in (AGENT_META_SUFFIX, JSONL_SUFFIX):
        if path.name.endswith(suffix):
            return path.name[: -len(suffix)]
    return path.name


def _subagent_identities(files) -> tuple:
    """The stat identity of every subagent file beside one transcript.

    This is the validator's contribution for the subagent tree, so it
    covers what the pages read: the metadata they parse and the mtime they
    draw. A narrower basis would answer 304 to a flowchart that has moved.
    """

    return tuple(
        identity
        for identity in (_stat_identity(file) for file in files)
        if identity is not None
    )


def _agent_count(files) -> int:
    """How many subagents one session spawned: one per metadata file, not
    one per file."""

    return sum(1 for file in files if file.name.endswith(AGENT_META_SUFFIX))


def _agent_text(value) -> str:
    """One metadata string field, or ``""``. Another program's undocumented
    JSON can hold anything at any key, so a value of the wrong type is an
    absence rather than something to render."""

    return value.strip() if isinstance(value, str) and value.strip() else ""


def _agent_depth(value):
    """``spawnDepth`` as an integer, or ``None``. ``True`` is an ``int`` in
    Python and is not a depth."""

    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _agent_record(meta: Path, modified: int) -> dict:
    """The named metadata fields of one subagent, each degrading to an
    absence rather than to a traceback."""

    record = {
        "id": _agent_id(meta),
        "type": "",
        "description": "",
        "tool_use_id": "",
        "depth": None,
        "parent": "",
        "modified": modified,
        "unreadable": False,
    }
    try:
        parsed = _json_object(meta.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        parsed = None
    if parsed is None:
        record["unreadable"] = True
        return record
    record["type"] = _agent_text(parsed.get(AGENT_TYPE_KEY))
    record["description"] = _agent_text(parsed.get(AGENT_DESCRIPTION_KEY))
    record["tool_use_id"] = _agent_text(parsed.get(AGENT_TOOL_USE_KEY))
    record["depth"] = _agent_depth(parsed.get(AGENT_DEPTH_KEY))
    record["parent"] = _agent_text(parsed.get(AGENT_PARENT_KEY))
    return record


def read_agents(path: Path) -> list:
    """Every subagent recorded beside one transcript, in the tree's order.

    A metadata file is a few hundred bytes and a session has a few dozen of
    them, so this is the one place the detail view reads that the index
    does not. Its cost is a directory listing plus one small read per
    subagent -- no transcript is opened here at all.
    """

    activity = {}
    metas = []
    for file in _subagent_files(path):
        identity = _stat_identity(file)
        if identity is not None:
            agent = _agent_id(file)
            activity[agent] = max(activity.get(agent, 0), identity[2])
        if file.name.endswith(AGENT_META_SUFFIX):
            metas.append(file)
    return [_agent_record(meta, activity.get(_agent_id(meta), 0)) for meta in metas]


def _project_directories(root: Path) -> list:
    """Every project directory that is actually inside the transcript root.

    A directory *entry* is not the same thing as a directory in this tree.
    `~/.claude/projects` is a path anything on the machine can be linked
    into, and a symlink there answers ``is_dir`` like any other project and
    would then be walked for transcripts -- which is how a viewer whose whole
    defence is a closed renderable set starts rendering titles out of files
    outside its own root. Containment is the same question `_subagent_files`
    asks one level down, so it is asked with the same helper. The entry's own
    name is what is kept: that is the name the operator sees in the listing
    and the slug this reader decodes.
    """

    try:
        entries = sorted(path for path in root.iterdir() if path.is_dir())
    except OSError:
        return []
    return [path for path in entries if _in_tree(root, path.name) is not None]


def discover_sessions(transcripts=None) -> dict:
    """Every session under one transcript root, newest activity first.

    Listing only: no transcript is opened here, so this is what the
    validator can afford to walk on a request it answers 304. ``None`` is
    the case where no root was configured at all, and it reads nothing.
    """

    if transcripts is None:
        return {
            "root": None,
            "present": False,
            "projects": (),
            "sessions": [],
            "unaddressable": (),
            "diagnostics": [],
            "empty": EMPTY_NO_TRANSCRIPTS,
        }
    root = Path(transcripts)
    try:
        present = root.is_dir()
    except OSError:
        present = False
    if not present:
        return {
            "root": root,
            "present": False,
            "projects": (),
            "sessions": [],
            "unaddressable": (),
            "diagnostics": [],
            "empty": EMPTY_NO_TRANSCRIPTS,
        }
    projects = _project_directories(root)
    sessions = []
    unaddressable = []
    diagnostics = []
    for project in projects:
        cwd = decode_slug(project.name)
        if not cwd:
            diagnostics.append(
                "{0}: {1}".format(DIAGNOSTIC_UNDECODABLE_SLUG, project.name)
            )
        for path in sorted(project.glob("*" + JSONL_SUFFIX)):
            identity = _stat_identity(path)
            if identity is None:
                continue
            if not _safe_name(path.stem):
                # The detail route looks a session up by this id and
                # `find_session` refuses the name before it gets there, so
                # listing the row would offer a link to a 404 about a file
                # this walk just found. Named once, here, where the name is.
                unaddressable.append(identity)
                diagnostics.append(
                    "{0}: {1}".format(DIAGNOSTIC_UNADDRESSABLE_SESSION, path.name)
                )
                continue
            files = _subagent_files(path)
            sessions.append(
                {
                    "id": path.stem,
                    "path": path,
                    "project": project.name,
                    "named_cwd": cwd,
                    "identity": identity,
                    "size": identity[1],
                    "modified": identity[2],
                    "subagents": _subagent_identities(files),
                    "agent_count": _agent_count(files),
                }
            )
    # Newest first, and on the id where two files share a timestamp, so the
    # order is a property of the tree rather than of the walk.
    sessions.sort(key=lambda session: (-session["modified"], session["id"]))
    return {
        "root": root,
        "present": True,
        "projects": tuple(project.name for project in projects),
        "sessions": sessions,
        # Not sessions, and not nothing: a file whose diagnostic is on the
        # page is part of what the page was rendered from, so the validator
        # has to be able to see it arrive and leave.
        "unaddressable": tuple(unaddressable),
        "diagnostics": diagnostics,
        "empty": "" if sessions else EMPTY_NO_SESSIONS,
    }


def _session_diagnostics(summary: dict) -> list:
    """What one transcript could not be read to say."""

    diagnostics = []
    if summary["unreadable"]:
        diagnostics.append(DIAGNOSTIC_UNREADABLE_TRANSCRIPT)
    if summary["skipped"]:
        diagnostics.append(
            "{0}: {1}".format(DIAGNOSTIC_UNREADABLE_LINES, summary["skipped"])
        )
    # An empty transcript and a healthy one must not look alike: a layout
    # change that stopped every line parsing would otherwise render a page
    # of blanks that reads as "nothing happened here".
    if not summary["records"] and not summary["unreadable"]:
        diagnostics.append(DIAGNOSTIC_NO_RECORDS)
    return diagnostics


def _label_session(session: dict) -> dict:
    """One session's labels, from the cached parse of its own transcript.
    Returns the summary, so a caller that needs more than the labels does
    not parse the file a second time."""

    summary = cached_transcript(session["path"], session["identity"])
    session["title"] = summary["title"]
    session["cwd"] = summary["cwd"] or session["named_cwd"]
    if summary["cwd"]:
        session["cwd_source"] = CWD_FROM_RECORD
    else:
        session["cwd_source"] = CWD_FROM_NAME if session["named_cwd"] else ""
    session["diagnostics"] = _session_diagnostics(summary)
    return summary


def read_sessions(transcripts=None) -> dict:
    """Every session under one transcript root, labelled.

    ``discover_sessions`` lists; this labels. The parse is the expensive
    half and it is cached on each transcript's stat identity, so a poll over
    an unchanged root costs one directory listing and no parse at all.
    """

    found = discover_sessions(transcripts)
    for session in found["sessions"]:
        _label_session(session)
    return found


def find_session(transcripts, session_id: str):
    """One session by id, or ``None``.

    The listing is the lookup: a session id names a file, but the project
    directory it sits under is not derivable from the id, and the slug is
    not invertible. Listing costs no parse, which is what the detail view
    can afford -- it then parses exactly the one transcript it draws.
    """

    if not _safe_name(session_id):
        return None
    for session in discover_sessions(transcripts)["sessions"]:
        if session["id"] == session_id:
            return session
    return None


def _agent_activity(agent: dict, summary: dict) -> tuple:
    """``(state, what it was read off)`` for one subagent.

    Ordered by strength of evidence, and it runs out fast: a result quoting
    the call is the only thing that says finished, an unanswered call is the
    only thing that says running, and everything else is `unknown`. Nothing
    here has a default branch that claims a state -- the absence of evidence
    is the third state, not a reason to pick one of the other two.
    """

    called = agent["tool_use_id"]
    if called and called in summary["agent_returns"]:
        return ACTIVITY_FINISHED, EVIDENCE_RETURNED
    if called and called in summary["agent_calls"]:
        return ACTIVITY_RUNNING, EVIDENCE_CALLED
    return ACTIVITY_UNKNOWN, EVIDENCE_NONE


def read_session(session: dict) -> dict:
    """One session, labelled, with every subagent recorded beside it and
    each subagent's activity read off the session's own transcript.

    The parse is the one ``_label_session`` already made and cached, so the
    states cost no second pass over the file.
    """

    summary = _label_session(session)
    session["agents"] = read_agents(session["path"])
    for agent in session["agents"]:
        agent["state"], agent["evidence"] = _agent_activity(agent, summary)
    return session


def agent_ids(agents) -> frozenset:
    """The nodes a recorded parent is allowed to resolve to: the session's
    own subagents, and not the orchestrator, which no metadata names."""

    return frozenset(agent["id"] for agent in agents)


def _recorded_parent(agent: dict, known: frozenset) -> str:
    """The node one subagent's own ``parentAgentId`` resolves to, or ``""``.

    ``parentAgentId`` was observed on every depth-2 record and no depth-1
    one, holding the bare id whose file is ``agent-<id>``; both spellings
    are accepted because neither is anybody's contract. A pointer to an
    agent this session does not have, or to the agent itself, resolves to
    nothing rather than to a node that is not there or an edge nobody can
    lay out.
    """

    for candidate in (agent["parent"], "agent-" + agent["parent"]):
        if agent["parent"] and candidate in known and candidate != agent["id"]:
            return candidate
    return ""


def _agent_parent(agent: dict, known: frozenset) -> str:
    """The node one subagent hangs off, or ``""`` when nothing says.

    Depth 1 is read before the pointer and outranks it: the session spawned
    it and nothing else could have, so spec criterion 8's edge from the
    orchestrator to *every* depth-1 agent holds even where the metadata also
    names a sibling. Ordering the two the other way makes that criterion
    hold only for the records that happen to omit the key.
    """

    if agent["depth"] == 1:
        return ORCHESTRATOR_NODE
    return _recorded_parent(agent, known)


def session_graph(agents) -> tuple:
    """``(node ids, edges, the subset of edges that is inferred)``.

    The orchestrator is the session itself. A subagent at depth 1 was
    spawned by it and nothing else could have been; a recorded parent that
    resolves to a node on this page is a fact. Everything left over -- a
    subagent that names no parent, and one whose named parent is not on this
    page -- hangs off the orchestrator too, and that edge is returned as a
    guess so the page can draw it as one. Inventing a parent for it would be
    the one lie a flowchart of another program's tree must not tell. Which
    of the two guesses was made is `edge_source`'s to say; the shape here is
    the same either way.
    """

    nodes = (ORCHESTRATOR_NODE,) + tuple(agent["id"] for agent in agents)
    known = agent_ids(agents)
    edges, inferred = [], []
    for agent in agents:
        parent = _agent_parent(agent, known)
        edges.append((parent or ORCHESTRATOR_NODE, agent["id"]))
        if not parent:
            inferred.append(edges[-1])
    return nodes, tuple(edges), tuple(inferred)


def edge_source(agent: dict, known: frozenset) -> str:
    """What one subagent's edge was read off, said on its own row.

    Two of the four are guesses and they are not the same guess. A record
    that never named a parent and a record whose named parent is on no other
    row here both land on the orchestrator; calling the second the first is
    a false statement about another program's data, and the reader it
    misleads goes looking for a pointer that was written down all along.
    """

    parent = _agent_parent(agent, known)
    if parent == ORCHESTRATOR_NODE:
        return EDGE_FROM_DEPTH
    if parent:
        return EDGE_FROM_PARENT
    return EDGE_PARENT_UNRESOLVED if agent["parent"] else EDGE_INFERRED


def transcript_state(transcripts=None) -> tuple:
    """The stat identity of everything the session views read.

    The same three facts per file the sink walk contributes, over the
    set this reader actually opens -- and the project directory names, so a
    directory appearing empty is a change too. Naming the validator's basis
    as the route's whole read set, rather than one directory, is `U3`'s
    lesson from the friction feed.
    """

    found = discover_sessions(transcripts)
    # Configured or not, and present or not, before any file: three pages
    # differ here -- no root configured, a root that is not there yet, and a
    # root holding nothing -- and none of the three has a file to stat, so a
    # walk alone cannot tell them apart. The middle-to-last transition is the
    # ordinary one: a viewer left open from before Claude Code first ran.
    root = found["root"]
    state = [("transcripts", int(found["present"]), "" if root is None else str(root))]
    state.extend(("projects", 0, name) for name in found["projects"])
    for session in found["sessions"]:
        state.append(session["identity"])
        state.extend(session["subagents"])
    # A file that is not a session still renders: it renders a diagnostic.
    # No directory is stat'd on this walk, so without these the row-shaped
    # hole in the page appears and disappears under an unchanged tag.
    state.extend(found["unaddressable"])
    return tuple(state)


# --- rendering ---------------------------------------------------------------


def _plural(count: int, singular: str, plural: str) -> str:
    return "{0} {1}".format(count, singular if count == 1 else plural)


def _cell(value: str, fallback: str) -> str:
    """One table cell. Every branch escapes: the sink is untrusted data."""

    if value:
        return html.escape(value)
    return '<span class="empty">{0}</span>'.format(html.escape(fallback))


def _row(columns, values: dict, anchor: str = "") -> str:
    """One table row, its cells derived from the tuple that closes the
    renderable set.

    The row is built *from* the constant rather than beside it, so a column
    cannot reach the page without being admitted to the closed set first --
    which is the whole mechanism behind the content wall. A tuple that
    names a column with no value here fails at the first render rather than
    emitting a blank cell nobody asked about; the two are module state and
    can only disagree by a mistake made in this file.

    ``anchor``, where given, is the element id the row's first cell carries
    -- the target a flowchart node links to.
    """

    cells = []
    for name in columns:
        identifier = (
            ' id="{0}"'.format(html.escape(anchor))
            if anchor and name == columns[0]
            else ""
        )
        cells.append(
            '<td class="{name}"{id}>{value}</td>'.format(
                name=name, id=identifier, value=values[name]
            )
        )
    return "<tr>{0}</tr>\n".format("".join(cells))


def _pill(seen: StatusPresentation, text: str) -> str:
    """One state pill: glyph, word, and a class binding the hue token and
    the border style.

    The glyph is aria-hidden because the word beside it says the same
    thing; a screen reader announcing the code point would only add noise.
    ``text`` arrives escaped -- a caller that appends an untrusted value to
    the word is the only reason this takes one at all.
    """

    return (
        '<span class="st st-{word}">'
        '<span class="glyph" aria-hidden="true">{glyph}</span> {text}</span>'
    ).format(word=seen.word, glyph=seen.glyph, text=text)


def render_status(status: str) -> str:
    """The status pill. A value outside the contract's set keeps its own
    text, escaped, beside the named fallback -- hiding an unrecognized
    status would hide exactly the state a reader came to see. An absent
    status is an empty state rather than a state."""

    if not status:
        return _cell("", EMPTY_UNSET)
    seen = status_presentation(status)
    text = html.escape(seen.word)
    if status not in STATUS_PRESENTATION:
        text = "{0} {1}".format(text, html.escape(status))
    return _pill(seen, text)


def is_live(tickets) -> bool:
    """Whether anything on this page can move without a human first moving
    something else. It sets the poll interval, so it is a property of what
    the page shows rather than of the root."""

    return any(ticket["status"] in POLL_FAST_STATUSES for ticket in tickets)


def _page(title: str, body: str, tickets=()) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>{title}</title>\n<style>{css}</style>\n</head>\n"
        '<body>\n<main data-live="{live}">\n{body}</main>\n'
        "<script>{js}</script>\n</body>\n</html>\n"
    ).format(
        title=html.escape(title),
        css=PAGE_CSS,
        live="yes" if is_live(tickets) else "no",
        body=body,
        js=PAGE_JS,
    )


def ticket_href(run: str, ticket_id: str) -> str:
    """A same-origin relative link. Run and id are directory and file names
    from untrusted data, so both are percent-encoded whole -- nothing in
    them survives as URL structure -- and then escaped as markup."""

    return html.escape(
        "{route}?run={run}&id={id}".format(
            route=TICKET_ROUTE, run=quote(run, safe=""), id=quote(ticket_id, safe="")
        )
    )


def graph_href(run: str) -> str:
    return html.escape(
        "{route}?run={run}".format(route=GRAPH_ROUTE, run=quote(run, safe=""))
    )


def session_href(session_id: str) -> str:
    """A session id is a file name from another program's tree, so it is
    percent-encoded whole and then escaped as markup, like a ticket id."""

    return html.escape(
        "{route}?id={id}".format(route=SESSION_ROUTE, id=quote(session_id, safe=""))
    )


def anchor_href(anchor: str) -> str:
    """A link to a row on this same page."""

    return html.escape("#{0}".format(quote(anchor, safe="")))


def _meter(ticket: dict) -> str:
    """The elapsed bar, or the named reason there is none.

    Where a live claim has no meter the absence is named, because that is
    the common case on real data and a reader should not have to wonder
    whether the bar failed to draw.
    """

    meter = claim_meter(ticket)
    if meter is not None:
        return (
            ' · <progress max="100" value="{percent}">{percent}%</progress>'
            " {elapsed}m of {bound}m{over}".format(
                percent=meter["percent"],
                elapsed=meter["elapsed_minutes"],
                bound=meter["bound_minutes"],
                over=", over bound" if meter["over"] else "",
            )
        )
    if ticket["status"] in LIVE_CLAIM_STATUSES:
        reason = (
            "bound is not a duration"
            if bound_minutes(ticket["bound"]) is None
            else "no claim time to measure from"
        )
        return ' · <span class="empty">{0}: {1}</span>'.format(
            html.escape(EMPTY_NO_METER), html.escape(reason)
        )
    return ""


def render_active_band(claims) -> str:
    """Who is at work right now, across every run.

    Absent when nobody is: an empty band is furniture that says nothing,
    and the reader would still have to scan the tables to be sure.
    """

    if not claims:
        return ""
    parts = ['<ul class="band">\n']
    for claim in claims:
        ticket = claim["ticket"]
        parts.append(
            '<li class="claim"><a href="{href}">{id}</a> · {run} · {executor}'
            " · {claimed_by}{meter}</li>\n".format(
                href=ticket_href(claim["run"], ticket["id"]),
                id=html.escape(ticket["id"]),
                run=html.escape(claim["run"]),
                executor=_cell(ticket["executor"], EMPTY_UNSET),
                claimed_by=_cell(ticket["claimed_by"], EMPTY_UNSET),
                meter=_meter(ticket),
            )
        )
    parts.append("</ul>\n")
    return "".join(parts)


def render_index(discovery: dict) -> str:
    parts = [
        "<h1>orchflows runs</h1>\n",
        '<p class="root">{0}</p>\n'.format(html.escape(str(discovery["root"]))),
        '<p class="back"><a href="{0}">friction log</a></p>\n'.format(FRICTION_ROUTE),
        '<p class="back"><a href="{0}">claude sessions</a></p>\n'.format(SESSIONS_ROUTE),
        render_active_band(active_claims(discovery)),
    ]
    if discovery["empty"]:
        parts.append('<p class="empty">{0}</p>\n'.format(html.escape(discovery["empty"])))
    for run in discovery["runs"]:
        parts.append(
            '<section class="run">\n<h2>{name}</h2>\n'
            '<p class="back"><a href="{href}">dependency graph</a></p>\n'.format(
                name=html.escape(run["run"]), href=graph_href(run["run"])
            )
        )
        # Named here as well as on the graph, because every row below is a
        # link built from an id the lookup may not resolve.
        parts.append(render_diagnostics(identity_diagnostics(run["tickets"])))
        if not run["tickets"]:
            parts.append('<p class="empty">{0}</p>\n'.format(html.escape(EMPTY_NO_TICKETS)))
        else:
            parts.append(
                "<table>\n<thead>\n<tr><th>id</th><th>status</th>"
                "<th>executor</th><th>objective</th></tr>\n</thead>\n<tbody>\n"
            )
            for ticket in run["tickets"]:
                parts.append(
                    '<tr><td><a href="{href}">{id}</a></td><td>{status}</td>'
                    "<td>{executor}</td><td>{objective}</td></tr>\n".format(
                        href=ticket_href(run["run"], ticket["id"]),
                        id=html.escape(ticket["id"]),
                        status=render_status(ticket["status"]),
                        executor=_cell(ticket["executor"], EMPTY_UNSET),
                        objective=_cell(ticket["objective"], EMPTY_NO_OBJECTIVE),
                    )
                )
            parts.append("</tbody>\n</table>\n")
        parts.append("</section>\n")
    return _page(
        "orchflows runs",
        "".join(parts),
        [ticket for run in discovery["runs"] for ticket in run["tickets"]],
    )


def render_diagnostics(diagnostics) -> str:
    """What the layout could not honour, named on the page. Silent when
    there is nothing to say -- an empty list rendered as an empty box would
    read as a warning nobody can act on."""

    if not diagnostics:
        return ""
    return '<ul class="diagnostics">\n{0}</ul>\n'.format(
        "".join("<li>{0}</li>\n".format(html.escape(line)) for line in diagnostics)
    )


def render_graph_svg(run: str, tickets, layout: dict) -> str:
    """The dependency graph as inline SVG at natural size inside a
    scrollable box. No canvas and no pan/zoom: at 3-12 nodes both are
    machinery with no keyboard path (`lane-ui-patterns.md` §3.2)."""

    at = dict((node.id, node) for node in layout["nodes"])
    state = dict((ticket["id"], ticket["status"]) for ticket in tickets)
    parts = [
        '<div class="canvas">\n<svg class="graph" viewBox="0 0 {width} {height}" '
        'width="{width}" height="{height}" role="img" '
        'aria-label="dependency graph for {run}">\n'.format(
            width=layout["width"], height=layout["height"], run=html.escape(run)
        ),
        '<defs><marker id="dep-arrow" viewBox="0 0 8 8" refX="8" refY="4" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<path class="arrow" d="M0 0 L8 4 L0 8 z" /></marker></defs>\n',
    ]
    for source, target in layout["edges"]:
        tail, head = at[source], at[target]
        parts.append(
            '<line class="edge" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'marker-end="url(#dep-arrow)" />\n'.format(
                x1=tail.x + NODE_WIDTH // 2,
                y1=tail.y + NODE_HEIGHT,
                x2=head.x + NODE_WIDTH // 2,
                y2=head.y,
            )
        )
    for node in layout["nodes"]:
        seen = status_presentation(state.get(node.id, ""))
        parts.append(
            '<a href="{href}"><g class="nd nd-{word}" transform="translate({x},{y})">'
            '<rect width="{w}" height="{h}" rx="5" />'
            '<text class="nd-id" x="10" y="19">{id}</text>'
            '<text class="nd-state" x="10" y="35">{glyph} {word}</text>'
            "</g></a>\n".format(
                href=ticket_href(run, node.id),
                word=seen.word,
                glyph=seen.glyph,
                x=node.x,
                y=node.y,
                w=NODE_WIDTH,
                h=NODE_HEIGHT,
                id=html.escape(node.id),
            )
        )
    parts.append("</svg>\n</div>\n")
    return "".join(parts)


def render_events(log) -> str:
    """One run's hook events, newest first, or nothing at all.

    ``None`` is the seam's "the file does not exist" half, and it renders
    as silence: no heading, no count, no empty state. A malformed line is
    skipped and counted, exactly as the friction feed reports one.
    """

    if log is None:
        return ""
    entries = log["entries"]
    counted = _plural(len(entries), "event", "events")
    if log["skipped"]:
        counted = "{0} · {1}".format(
            counted, _plural(log["skipped"], "unreadable line", "unreadable lines")
        )
    parts = [
        '<section class="events">\n<h2>events</h2>\n',
        '<p class="count">{0}</p>\n'.format(html.escape(counted)),
    ]
    if entries:
        parts.append('<ul class="feed">\n')
        for entry in entries:
            parts.append(
                '<li class="event">\n<p class="meta">'
                '<span class="ts">{ts}</span> · {run} · {event}</p>\n'
                '<p class="who">{agent} · {ticket}</p>\n'
                '<p class="did">{tool} · {detail}</p>\n</li>\n'.format(
                    ts=html.escape(_scalar(entry.get("ts"))),
                    run=_cell(_scalar(entry.get("run")), EMPTY_UNSET),
                    event=_cell(_scalar(entry.get("event")), EMPTY_UNSET),
                    agent=_cell(_scalar(entry.get("agent")), EMPTY_UNSET),
                    ticket=_cell(_scalar(entry.get("ticket")), EMPTY_UNSET),
                    tool=_cell(_scalar(entry.get("tool")), EMPTY_UNSET),
                    detail=_cell(_scalar(entry.get("detail")), EMPTY_UNSET),
                )
            )
        parts.append("</ul>\n")
    parts.append("</section>\n")
    return "".join(parts)


def render_graph(run: str, tickets, events=None) -> str:
    """One run's dependency graph, its coordinates computed here rather
    than in the browser."""

    layout = cached_layout(*graph_input(tickets))
    body = [
        "<h1>{0}</h1>\n".format(html.escape(run)),
        '<p class="count">{0} · {1}</p>\n'.format(
            _plural(len(tickets), "ticket", "tickets"),
            _plural(len(layout["edges"]), "dependency", "dependencies"),
        ),
        render_diagnostics(identity_diagnostics(tickets) + layout["diagnostics"]),
    ]
    if not tickets:
        body.append('<p class="empty">{0}</p>\n'.format(html.escape(EMPTY_NO_TICKETS)))
    else:
        body.append(render_graph_svg(run, tickets, layout))
    body.append(render_events(events))
    body.append('<p class="back"><a href="/">all runs</a></p>\n')
    return _page("{0} · graph".format(run), "".join(body), tickets)


def render_missing_run(run: str) -> str:
    """The run name comes from the query string, so it is escaped before it
    is echoed back."""

    return _page(
        "not found",
        "<h1>not found</h1>\n<p>{empty}: {run}</p>\n"
        '<p class="back"><a href="/">all runs</a></p>\n'.format(
            empty=html.escape(EMPTY_NO_RUN), run=_cell(run, EMPTY_UNSET)
        ),
    )


def render_friction(log: dict) -> str:
    """The friction log, newest first, over every month it spans."""

    entries = log["entries"]
    counted = _plural(len(entries), "entry", "entries")
    if log["skipped"]:
        counted = "{0} · {1} skipped".format(
            counted, _plural(log["skipped"], "unreadable line", "unreadable lines")
        )
    body = [
        "<h1>friction</h1>\n",
        '<p class="count">{0}</p>\n'.format(html.escape(counted)),
    ]
    if entries:
        body.append('<ul class="feed">\n')
        for entry in entries:
            body.append(
                '<li class="entry">\n<p class="meta">'
                '<span class="ts">{ts}</span> · {category} · {host}</p>\n'
                '<p class="observed">observed: {observed}</p>\n'
                '<p class="expected">expected: {expected}</p>\n</li>\n'.format(
                    ts=html.escape(_scalar(entry.get("ts"))),
                    category=_cell(_scalar(entry.get("category")), EMPTY_UNSET),
                    host=_cell(_scalar(entry.get("host")), EMPTY_UNSET),
                    observed=_cell(_scalar(entry.get("observed")), EMPTY_UNSET),
                    expected=_cell(_scalar(entry.get("expected")), EMPTY_UNSET),
                )
            )
        body.append("</ul>\n")
    elif not log["skipped"]:
        # With skipped lines the count line already says a log was found and
        # what became of it; claiming there is none would be the wrong story.
        body.append('<p class="empty">{0}</p>\n'.format(html.escape(EMPTY_NO_FRICTION)))
    body.append('<p class="back"><a href="/">all runs</a></p>\n')
    return _page("friction", "".join(body))


def _stamp(mtime_ns: int) -> str:
    """A file's mtime as a UTC instant, or a named diagnostic.

    Rendered in UTC rather than local time because the sessions listed here
    were opened in whatever zone the machine was in at the time, and a stamp
    that silently means two things is worse than one that plainly means one.

    An mtime is the filesystem's number, not this process's: APFS clamps at
    2262, but an NTFS FILETIME reaches the year 30828 and ``datetime``
    refuses anything past 9999. Unguarded that is a ``ValueError`` inside the
    handler -- no HTTP response on the wire at all and the absolute module
    path on stderr, which is the failure `U3` already shipped once. A time
    that cannot be rendered is a named diagnostic like every other absence
    on these pages.
    """

    try:
        seconds = mtime_ns // 1000000000
        return datetime.fromtimestamp(seconds, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except (OSError, OverflowError, ValueError):
        return DIAGNOSTIC_UNRENDERABLE_STAMP


def _session_cwd(session: dict) -> str:
    """The working directory cell: the path, and where it came from.

    The provenance is on the page because the two sources are not equally
    good. A ``worktree-state`` record states the path; a directory name only
    encodes it, through a substitution that is not invertible. Presenting a
    guess as a fact is how a reader ends up looking for a repository that
    was never there.
    """

    if not session["cwd"]:
        return _cell("", EMPTY_NO_CWD)
    return '{path} <span class="src">{source}</span>'.format(
        path=html.escape(session["cwd"]), source=html.escape(session["cwd_source"])
    )


def render_sessions(found: dict) -> str:
    """The Claude Code session index: one row per session, newest first.

    Every cell here is a label, a count or a file fact. Nothing a session
    said is on this page, and the reader behind it never held any of it --
    see the section comment on the parser.
    """

    root = found["root"]
    body = [
        "<h1>claude sessions</h1>\n",
        '<p class="root">{0}</p>\n'.format(
            html.escape(str(root)) if root is not None else html.escape(EMPTY_UNSET)
        ),
    ]
    sessions = found["sessions"]
    if sessions:
        body.append(
            '<p class="count">{0} · {1}</p>\n'.format(
                html.escape(_plural(len(sessions), "session", "sessions")),
                html.escape(
                    _plural(len(found["projects"]), "project directory", "project directories")
                ),
            )
        )
    body.append(render_diagnostics(found["diagnostics"]))
    if found["empty"]:
        body.append('<p class="empty">{0}</p>\n'.format(html.escape(found["empty"])))
    else:
        body.append(
            "<table>\n<thead>\n<tr>{0}</tr>\n</thead>\n<tbody>\n".format(
                "".join("<th>{0}</th>".format(html.escape(h)) for h in SESSION_HEADINGS)
            )
        )
        for session in sessions:
            body.append(
                _row(
                    SESSION_COLUMNS,
                    {
                        "sid": '<a href="{href}">{sid}</a>'.format(
                            href=session_href(session["id"]),
                            sid=html.escape(session["id"]),
                        ),
                        "title": _cell(session["title"], EMPTY_NO_TITLE),
                        "cwd": _session_cwd(session),
                        "when": html.escape(_stamp(session["modified"])),
                        "size": session["size"],
                        "agents": session["agent_count"],
                        # Empty on a healthy session: a permanent warning
                        # slot would train the reader to stop reading it.
                        "notes": html.escape(" · ".join(session["diagnostics"])),
                    },
                )
            )
        body.append("</tbody>\n</table>\n")
    body.append('<p class="back"><a href="/">all runs</a></p>\n')
    return _page("claude sessions", "".join(body))


# A node box is NODE_WIDTH wide in a 12px monospace face, so this is what
# fits on its first line. Everything cut here is on the row the node links
# to, untruncated.
NODE_LABEL_CHARS = 16


def _clipped(value: str) -> str:
    """A label cut to what a node box holds, with the cut marked.

    Cut before escaping, never after: an escape sequence sliced in half is
    not markup, but it is not the value either.
    """

    if len(value) <= NODE_LABEL_CHARS:
        return value
    return value[: NODE_LABEL_CHARS - 1] + "…"


def _depth_label(agent: dict) -> str:
    """One subagent's spawn depth, spelled out, or the named absence."""

    if agent["depth"] is None:
        return EMPTY_NO_DEPTH
    return "depth {0}".format(agent["depth"])


def _node_faces(session: dict, agents) -> dict:
    """What each flowchart node draws, by node id.

    Built here rather than inside the drawing loop: the orchestrator and a
    subagent carry different facts through the same four presentation
    channels, and the SVG must not be where that difference is decided.
    ``label`` is the accessible name, and it is what makes the truncation
    on the face of the node safe to do at all.
    """

    faces = {
        ORCHESTRATOR_NODE: {
            "anchor": ORCHESTRATOR_ANCHOR,
            "css": "root",
            "top": ORCHESTRATOR_NODE,
            "bottom": _plural(len(agents), "subagent", "subagents"),
            "label": "{0}: {1}".format(
                ORCHESTRATOR_NODE, session["title"] or EMPTY_NO_TITLE
            ),
        }
    }
    for agent in agents:
        seen = activity_presentation(agent["state"])
        kind = agent["type"] or EMPTY_NO_TYPE
        faces[agent["id"]] = {
            "anchor": agent["id"],
            "css": seen.word,
            "top": _clipped(kind),
            "bottom": "{0} {1} · d{2}".format(
                seen.glyph, seen.word, "?" if agent["depth"] is None else agent["depth"]
            ),
            "label": "{0}: {1} · {2} · {3} ({4})".format(
                kind,
                agent["description"] or EMPTY_NO_DESCRIPTION,
                _depth_label(agent),
                seen.word,
                agent["evidence"],
            ),
        }
    return faces


def render_session_svg(session: dict, layout: dict, inferred) -> str:
    """One session's flowchart, drawn with the dependency graph's own
    geometry, node idiom and arrow marker. An inferred edge is dashed and
    the page says what a dashed edge means -- a guess drawn like a fact is
    the failure this whole view exists to avoid."""

    at = dict((node.id, node) for node in layout["nodes"])
    faces = _node_faces(session, session["agents"])
    parts = [
        '<div class="canvas">\n<svg class="graph" viewBox="0 0 {width} {height}" '
        'width="{width}" height="{height}" role="img" '
        'aria-label="subagents of session {id}: {title}">\n'.format(
            width=layout["width"],
            height=layout["height"],
            id=html.escape(session["id"]),
            title=html.escape(session["title"] or EMPTY_NO_TITLE),
        ),
        '<defs><marker id="dep-arrow" viewBox="0 0 8 8" refX="8" refY="4" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<path class="arrow" d="M0 0 L8 4 L0 8 z" /></marker></defs>\n',
    ]
    for source, target in layout["edges"]:
        tail, head = at[source], at[target]
        parts.append(
            '<line class="edge{guess}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'marker-end="url(#dep-arrow)" />\n'.format(
                guess=" edge-inferred" if (source, target) in inferred else "",
                x1=tail.x + NODE_WIDTH // 2,
                y1=tail.y + NODE_HEIGHT,
                x2=head.x + NODE_WIDTH // 2,
                y2=head.y,
            )
        )
    for node in layout["nodes"]:
        face = faces[node.id]
        parts.append(
            '<a href="{href}" aria-label="{label}">'
            '<g class="nd nd-{css}" transform="translate({x},{y})">'
            '<rect width="{w}" height="{h}" rx="5" />'
            '<text class="nd-id" x="10" y="19">{top}</text>'
            '<text class="nd-state" x="10" y="35">{bottom}</text>'
            "</g></a>\n".format(
                href=anchor_href(face["anchor"]),
                label=html.escape(face["label"]),
                css=face["css"],
                x=node.x,
                y=node.y,
                w=NODE_WIDTH,
                h=NODE_HEIGHT,
                top=html.escape(face["top"]),
                bottom=html.escape(face["bottom"]),
            )
        )
    parts.append("</svg>\n</div>\n")
    return "".join(parts)


def _attachment(agent: dict, known: frozenset) -> str:
    """The attachment cell: the node this subagent hangs off, and how that
    was known -- the same provenance idiom, and for the same reason, as the
    working directory's."""

    return '{parent} <span class="src">{source}</span>'.format(
        parent=html.escape(_agent_parent(agent, known) or ORCHESTRATOR_NODE),
        source=html.escape(edge_source(agent, known)),
    )


def render_agents(session: dict) -> str:
    """The row behind each node: everything the box was too small to hold,
    untruncated, and the anchor its node links to."""

    agents = session["agents"]
    if not agents:
        return '<p class="agents empty">{0}</p>\n'.format(html.escape(EMPTY_NO_AGENTS))
    known = agent_ids(agents)
    rows = [
        "<table>\n<thead>\n<tr>{0}</tr>\n</thead>\n<tbody>\n".format(
            "".join("<th>{0}</th>".format(html.escape(h)) for h in AGENT_HEADINGS)
        )
    ]
    for agent in agents:
        seen = activity_presentation(agent["state"])
        rows.append(
            _row(
                AGENT_COLUMNS,
                {
                    "agent": html.escape(agent["id"]),
                    "type": _cell(agent["type"], EMPTY_NO_TYPE),
                    "description": _cell(agent["description"], EMPTY_NO_DESCRIPTION),
                    "depth": _cell(
                        "" if agent["depth"] is None else str(agent["depth"]),
                        EMPTY_NO_DEPTH,
                    ),
                    "state": _pill(seen, html.escape(seen.word))
                    + ' <span class="src">{0}</span>'.format(
                        html.escape(agent["evidence"])
                    ),
                    "attached": _attachment(agent, known),
                    "when": html.escape(_stamp(agent["modified"])),
                },
                agent["id"],
            )
        )
    rows.append("</tbody>\n</table>\n")
    return "".join(rows)


def _agent_diagnostics(agents) -> list:
    """What a subagent's metadata could not be read to say, how much of the
    tree below is therefore a guess, and which guess it was.

    Counted off the same ``edge_source`` the rows carry rather than off the
    graph's edge list, so the sentence at the top of the page and the cell
    partway down it cannot come to disagree.
    """

    lines = [
        "{0}: {1}".format(DIAGNOSTIC_UNREADABLE_AGENT, agent["id"])
        for agent in agents
        if agent["unreadable"]
    ]
    known = agent_ids(agents)
    guesses = [edge_source(agent, known) for agent in agents]
    for label, diagnostic in (
        (EDGE_INFERRED, DIAGNOSTIC_INFERRED_EDGE),
        (EDGE_PARENT_UNRESOLVED, DIAGNOSTIC_UNRESOLVED_PARENT),
    ):
        drawn = guesses.count(label)
        if drawn:
            lines.append(
                "{0} ({1})".format(diagnostic, _plural(drawn, "edge", "edges"))
            )
    return lines


def render_session(session: dict) -> str:
    """One Claude Code session as a flowchart: the orchestrator, every
    subagent it spawned, and what each of them is doing.

    Same content wall as the index. Every value here is a label, a count or
    a file fact out of the subagent metadata; nothing any session or any
    subagent said is on this page.
    """

    nodes, edges, inferred = session_graph(session["agents"])
    layout = cached_layout(nodes, edges)
    body = [
        "<h1>{0}</h1>\n".format(html.escape(session["id"])),
        '<p class="title" id="{anchor}">{title}</p>\n'.format(
            anchor=ORCHESTRATOR_ANCHOR, title=_cell(session["title"], EMPTY_NO_TITLE)
        ),
        '<p class="root">{0}</p>\n'.format(_session_cwd(session)),
        '<p class="count">{0} · {1}</p>\n'.format(
            html.escape(_plural(len(session["agents"]), "subagent", "subagents")),
            html.escape(_stamp(session["modified"])),
        ),
        render_diagnostics(
            session["diagnostics"]
            + _agent_diagnostics(session["agents"])
            + layout["diagnostics"]
        ),
        render_session_svg(session, layout, inferred),
        render_agents(session),
        '<p class="back"><a href="{0}">all sessions</a></p>\n'.format(SESSIONS_ROUTE),
    ]
    return _page("{0} · session".format(session["id"]), "".join(body))


def render_missing_session(session_id: str) -> str:
    """The id comes from the query string, so it is escaped before it is
    echoed back."""

    return _page(
        "not found",
        "<h1>not found</h1>\n<p>{empty}: {id}</p>\n"
        '<p class="back"><a href="{route}">all sessions</a></p>\n'.format(
            empty=html.escape(EMPTY_NO_SESSION),
            id=_cell(session_id, EMPTY_UNSET),
            route=SESSIONS_ROUTE,
        ),
    )


def _prose(body: str) -> str:
    """Ticket bodies are markdown, and rendering untrusted markdown as
    markup is what ``rules/visibility.md`` §6 forbids. The text goes out
    escaped inside a ``pre``, so its own structure survives without any of
    it becoming an element."""

    if not body.strip():
        return '<p class="empty">{0}</p>\n'.format(html.escape(EMPTY_SECTION))
    return "<pre>{0}</pre>\n".format(html.escape(body))


def render_verification(body: str) -> str:
    """The verdict table, or the section verbatim under the explicit state
    ``unparsed``. The count is emitted only where rows were actually read,
    so no reader is ever shown a verdict count the ticket does not have."""

    parsed = parse_verification(body)
    parts = ['<section class="verification">\n<h2>{0}</h2>\n'.format(VERIFICATION_SECTION)]
    if parsed["state"] == VERIFICATION_ROWS:
        rows = parsed["rows"]
        parts.append('<p class="count">{0} entries</p>\n'.format(len(rows)))
        parts.append(
            "<table>\n<thead>\n<tr>{0}</tr>\n</thead>\n<tbody>\n".format(
                "".join("<th>{0}</th>".format(html.escape(c)) for c in VERIFICATION_COLUMNS)
            )
        )
        for row in rows:
            parts.append(
                "<tr>{0}</tr>\n".format(
                    "".join(
                        "<td>{0}</td>".format(html.escape(row[c]))
                        for c in VERIFICATION_COLUMNS
                    )
                )
            )
        parts.append("</tbody>\n</table>\n")
    else:
        parts.append('<p class="empty">{0}</p>\n'.format(html.escape(VERIFICATION_UNPARSED_NOTE)))
        parts.append(_prose(body))
    parts.append("</section>\n")
    return "".join(parts)


def render_sections(sections: dict) -> str:
    """Every section the ticket carries, in the order it carries them.

    A section the ticket omits is absent here too: a heading with nothing
    under it would claim the ticket says something it does not. A name the
    contract does not fix still renders -- ``contracts/work-item.md`` lets a
    domain extend the section set, so dropping an unrecognized heading would
    hide real state.
    """

    parts = []
    for name, body in sections.items():
        if name == VERIFICATION_SECTION:
            parts.append(render_verification(body))
        else:
            parts.append(
                '<section class="body">\n<h2>{0}</h2>\n{1}</section>\n'.format(
                    html.escape(name), _prose(body)
                )
            )
    return "".join(parts)


def render_claim(ticket: dict) -> str:
    """The claim: its bound, its start, and an elapsed meter only where both
    operands exist."""

    return '<p class="claim">bound {bound} · claimed {claimed}{meter}</p>\n'.format(
        bound=_cell(ticket["bound"], EMPTY_UNSET),
        claimed=_cell(ticket["claimed_at"], EMPTY_UNSET),
        meter=_meter(ticket),
    )


def render_ticket(run: str, ticket: dict) -> str:
    body = "".join(
        [
            "<h1>{0}</h1>\n".format(html.escape(ticket["id"])),
            '<p class="meta">{run} · {status} · {executor}</p>\n'.format(
                run=html.escape(run),
                status=render_status(ticket["status"]),
                executor=_cell(ticket["executor"], EMPTY_UNSET),
            ),
            '<p class="root">{0}</p>\n'.format(html.escape(ticket["path"])),
            render_claim(ticket),
            render_sections(ticket["sections"]),
            '<p class="back"><a href="/">all runs</a></p>\n',
        ]
    )
    return _page("{0} · {1}".format(ticket["id"], run), body, [ticket])


def render_missing_ticket(run: str, ticket_id: str) -> str:
    """Both values come from the query string, so both are escaped before
    they are echoed back."""

    return _page(
        "not found",
        "<h1>not found</h1>\n<p>no ticket {id} in run {run} under this root</p>\n"
        '<p class="back"><a href="/">all runs</a></p>\n'.format(
            id=_cell(ticket_id, EMPTY_UNSET), run=_cell(run, EMPTY_UNSET)
        ),
    )


def render_not_found(route: str) -> str:
    """The requested path is client-supplied, so it is escaped like any
    other untrusted value before it is echoed back."""

    return _page(
        "not found",
        "<h1>not found</h1>\n<p>no route serves {0}</p>\n".format(html.escape(route)),
    )


def render_route(start, path: str, transcripts=None) -> tuple:
    """``(status, html)`` for one request path. Pure: reads, never writes.

    ``transcripts`` is threaded rather than resolved: passing ``None`` reads
    no transcript at all, so nothing short of the entry point can reach the
    operator's real ``~/.claude/projects``.
    """

    parsed = urlsplit(path)
    if parsed.path == INDEX_ROUTE:
        return 200, render_index(discover(start))
    if parsed.path == TICKET_ROUTE:
        query = parse_qs(parsed.query)
        run = query.get("run", [""])[0]
        ticket_id = query.get("id", [""])[0]
        ticket = find_ticket(_resolve_root(start), run, ticket_id)
        if ticket is None:
            return 404, render_missing_ticket(run, ticket_id)
        return 200, render_ticket(run, ticket)
    if parsed.path == GRAPH_ROUTE:
        run = parse_qs(parsed.query).get("run", [""])[0]
        root = _resolve_root(start)
        tickets = run_tickets(root, run)
        if tickets is None:
            return 404, render_missing_run(run)
        return 200, render_graph(run, tickets, read_events(root, run))
    if parsed.path == FRICTION_ROUTE:
        return 200, render_friction(read_friction(_resolve_root(start)))
    if parsed.path == SESSIONS_ROUTE:
        return 200, render_sessions(read_sessions(transcripts))
    if parsed.path == SESSION_ROUTE:
        session_id = parse_qs(parsed.query).get("id", [""])[0]
        session = find_session(transcripts, session_id)
        if session is None:
            return 404, render_missing_session(session_id)
        return 200, render_session(read_session(session))
    return 404, render_not_found(parsed.path)


# --- conditional requests ----------------------------------------------------

# Walked for their contents. The sink root itself is observed for its
# presence alone: `discover` renders a different named empty state for "no
# sink at all" than for "a sink carrying neither tickets nor friction", so a
# digest that could not tell the two apart would answer 304 across the very
# transition a viewer left open before the first write is waiting for.
STATE_DIRS = (TICKETS_DIR, FRICTION_DIR, EVENTS_DIR)
OBSERVED_DIRS = (SINK_DIR,) + STATE_DIRS


def live_meter_state(root, now=None) -> tuple:
    """``(ticket file, elapsed minutes)`` for every meter now on screen.

    The elapsed meter is the one thing the page draws that moves while no
    file moves: ``claim_meter`` measures against the wall clock. A digest
    built from file state alone therefore answers 304 to a bar that is
    visibly wrong, and it does so worst in exactly the state the
    one-second poll exists for -- a claim running past its bound never
    reaches ", over bound" because the page never repaints.

    A ticket with no live measurable claim contributes nothing, so a run
    whose every ticket is terminal digests to one value forever and keeps
    its 304. What is contributed is the rendered minute count rather than
    the clock, so the validator changes when the reader would see a
    different number and not once a second.
    """

    tickets_root = Path(root).joinpath(*TICKETS_DIR)
    if not tickets_root.is_dir():
        return ()
    measured = []
    for path in sorted(tickets_root.rglob("*" + TICKET_SUFFIX)):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        meter = claim_meter(_parse_frontmatter(text), now)
        if meter is not None:
            measured.append(
                (path.relative_to(tickets_root).as_posix(), meter["elapsed_minutes"])
            )
    return tuple(measured)


def state_digest(root, now=None, transcripts=None) -> str:
    """A fingerprint of everything the served page depends on under ``root``.

    Each file contributes its name, its size and its ``st_mtime_ns``. Size
    is in the digest because a filesystem that records mtime to the second
    -- every FAT volume, and HFS+ before APFS -- would otherwise call two
    writes in the same second one state, and the view would sit stale until
    some unrelated edit moved the clock on.

    Each observed directory contributes whether it exists at all, because
    an absence and an empty presence are two different pages. Each live
    elapsed meter contributes the minute it currently renders, because the
    clock is an input the filesystem does not record.

    The transcript root contributes on the same terms. `U3` recorded the
    lesson: a validator built over one directory while the reader had grown
    a route reading another served a 304 to a page that had moved. The
    basis is the whole read set, not the first tree that needed one.
    """

    base = Path(root)
    digest = hashlib.sha256()
    for parts in OBSERVED_DIRS:
        digest.update(
            "{0}\0{1}\n".format(
                "/".join(parts), int(base.joinpath(*parts).is_dir())
            ).encode("utf-8")
        )
    for parts in STATE_DIRS:
        directory = base.joinpath(*parts)
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            try:
                stat = path.stat()
            except OSError:
                # Gone between the walk and the stat. Its absence is itself
                # a change, which the next poll digests.
                continue
            digest.update(
                "{0}\0{1}\0{2}\n".format(
                    path.relative_to(base).as_posix(), stat.st_size, stat.st_mtime_ns
                ).encode("utf-8")
            )
    for name, elapsed in live_meter_state(base, now):
        digest.update("{0}\0{1}\n".format(name, elapsed).encode("utf-8"))
    for entry in transcript_state(transcripts):
        digest.update(
            "{0}\0{1}\0{2}\n".format(entry[0], entry[1], entry[2]).encode("utf-8")
        )
    return digest.hexdigest()


# The routes whose body is a function of the transcript tree. Every other
# route renders the sink alone.
TRANSCRIPT_ROUTES = (SESSIONS_ROUTE, SESSION_ROUTE)


def reads_transcripts(path: str) -> bool:
    """Whether the page served for one request path reads the transcript
    tree at all. ``render_route`` is the owner of that fact and this is the
    same dispatch on the same parsed path."""

    return urlsplit(path).path in TRANSCRIPT_ROUTES


def entity_tag(root, path: str, now=None, transcripts=None) -> str:
    """One page's validator: the state of everything *this page* read, bound
    to the resource it was read for, quoted as RFC 7232 requires.

    `U3`'s lesson cuts both ways. A basis narrower than the route's read set
    serves a 304 to a page that has already moved. A basis wider than it
    denies the 304 to a page that has not -- and here that is not a corner:
    a live Claude Code session rewrites its transcript continuously, so a
    sink page carrying the whole tree in its tag would never answer 304
    again, and the one-second poll would swap `main` once a second over a
    byte-identical body for as long as the viewer is open.
    """

    digest = hashlib.sha256(path.encode("utf-8"))
    read = transcripts if reads_transcripts(path) else None
    digest.update(state_digest(root, now, read).encode("ascii"))
    return '"{0}"'.format(digest.hexdigest()[:32])


def _unweighted(tag: str) -> str:
    return tag[2:] if tag.startswith("W/") else tag


def _etag_matches(header, etag: str) -> bool:
    """RFC 7232 §3.2: ``If-None-Match`` is ``*`` or a list of tags, and the
    comparison is weak, so a ``W/`` prefix on either side is not a mismatch.

    Splitting the list on commas is safe because the only tags that can
    match are the ones minted here, and those are hex.
    """

    if not header:
        return False
    sent = [item.strip() for item in header.split(",") if item.strip()]
    if "*" in sent:
        return True
    return any(_unweighted(item) == _unweighted(etag) for item in sent)


def respond(start, path: str, if_none_match=None, transcripts=None) -> tuple:
    """``(status, etag, html)`` for one request.

    A page whose validator the client already holds costs no ticket read
    and no layout -- which is what makes a one-second poll affordable.
    Only a 200 carries a tag: a 404 offers nothing to revalidate, and a
    client holding no tag for a path can never be answered 304 for it.
    """

    root = _resolve_root(start)
    etag = entity_tag(root, path, None, transcripts)
    if _etag_matches(if_none_match, etag):
        return 304, etag, ""
    status, page = render_route(root, path, transcripts)
    return (status, etag, page) if status == 200 else (status, "", page)


# --- serving -----------------------------------------------------------------


class ReaderServer(ThreadingHTTPServer):
    """Carries the roots, so the handler needs neither a global nor a
    closure. ``transcripts`` is ``None`` where none was configured, and the
    session views read nothing at all in that case."""

    daemon_threads = True

    def __init__(self, address, handler_class, root: Path, transcripts=None):
        self.root = root
        self.transcripts = transcripts
        ThreadingHTTPServer.__init__(self, address, handler_class)


class ReaderHandler(BaseHTTPRequestHandler):
    server_version = "orchflows-ui"
    sys_version = ""

    def do_GET(self):
        status, etag, page = respond(
            self.server.root,
            self.path,
            self.headers.get("If-None-Match"),
            self.server.transcripts,
        )
        self.send_response(status)
        if etag:
            self.send_header("ETag", etag)
        # A live view of a directory that changes underneath it: hold the
        # page but revalidate every time. `no-store` would forbid holding
        # it at all, so no client would ever send `If-None-Match` and the
        # 304 would be unreachable.
        self.send_header("Cache-Control", "no-cache")
        if status == 304:
            self.end_headers()
            return
        body = page.encode("utf-8")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Silent. The one line worth reading is the URL printed at start."""


def create_server(root, port: int, transcripts=None) -> ReaderServer:
    """Bind loopback only. Nothing here authenticates a request, and neither
    the sink nor a transcript is public data -- the second emphatically so
    -- therefore the socket never leaves this host. Port 0 asks the OS for a
    free port; the caller reads back ``server_address``.
    """

    return ReaderServer((LOOPBACK_HOST, port), ReaderHandler, Path(root), transcripts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=None,
        # The default is shown, never restated: `scripts/state_root.py` owns
        # the path, and a second statement of it here would drift from it.
        help="the state sink to view; defaults to {0}".format(default_root()),
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="loopback port; 0 picks a free one"
    )
    parser.add_argument(
        "--transcripts",
        default=None,
        help="Claude Code transcript root; defaults to ~/.claude/projects",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        root = default_root() if args.root is None else Path(args.root)
        server = create_server(root, args.port, transcript_root(args.transcripts))
    except OSError as error:
        # DEFAULT_PORT is fixed, so a second viewer on one host lands here.
        print(
            "cannot bind port {0}: {1}".format(args.port, error),
            file=sys.stderr,
        )
        return 2
    host, port = server.server_address[0], server.server_address[1]
    print("orchflows ui on http://{0}:{1}/ -- ctrl-c to stop".format(host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
