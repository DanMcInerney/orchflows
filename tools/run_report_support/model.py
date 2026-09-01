"""What the sink says about how long the work took.

Read-only throughout: every function here opens files and stats them and
writes nothing, which is the one property `tools/run_report.py` promises
that a reader has to be able to check by inspection.

The sink's own readers own the parsing -- `reader/scripts/ui_discovery`'s
`read_run_identity` and `read_friction`, `reader/scripts/ui_model`'s
`read_ticket` and `claim_meter` -- so a frontmatter or identity-document
change lands in one place and this module inherits it.
"""

from __future__ import annotations

import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPORT_ROOT = Path(__file__).resolve().parent.parent.parent
for _import_root in (_REPORT_ROOT, _REPORT_ROOT / "scripts"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

import reader.scripts.ui_discovery as ui_discovery  # noqa: E402
import reader.scripts.ui_model as ui_model  # noqa: E402

from tools.run_report_support import friction as friction_support  # noqa: E402

DEFAULT_TOP = 40
SLICE_EXECUTOR = "orch-slice"
COMPLETE_STATUS = "complete"
FAILED_STATUS = "failed"
TERMINAL_STATUSES = ("complete", "blocked", "stalled", "limited", "failed")
UNREADABLE = "unreadable"

# `research/orchflows-speed-spec-2026-08-23.md` §1: a run family is the
# name stem after the timestamp and any one of these retry markers. Both
# sets are the specification's verbatim, not a generalisation of it -- a
# wider suffix set would merge families the baseline counted apart.
RUN_STAMP_RE = re.compile(r"^(?:\d{8}T\d{6}Z|\d{8}|\d{4}-\d{2}-\d{2})-")
RUN_SUFFIX_RE = re.compile(
    r"-(?:v2|v3|retry|restart|corrected|direct|final|cut-ready|edge-ready|runnable|replacement)$"
)

# The oracles §1 counts minutes of, and the duration spellings a ticket or
# a run note actually records beside one. Nothing is inferred from an
# invocation with no duration written next to it: those are counted
# separately, so a family's oracle minutes never reads as complete when
# most of its invocations were never timed.
ORACLE_RE = re.compile(
    r"run_tests\.py|run_serial_compat\.py|playwright|pnpm\s+(?:test|build|lint|typecheck)",
    re.IGNORECASE,
)
DURATION_RES = (
    (re.compile(r"(\d+(?:\.\d+)?)\s*h(?:ours?|rs?)?\b", re.IGNORECASE), 60.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*m(?:in(?:ute)?s?)?\b"), 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?\b"), 1.0 / 60.0),
)


def parse_instant(value):
    """One ISO-8601 UTC instant, or ``None``. The sink's own parser."""

    return ui_model._parse_iso(value) if isinstance(value, str) and value else None


def format_instant(moment):
    return None if moment is None else moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def in_window(moment, since, until) -> bool:
    """Half-open ``[since, until)``. An unstamped record is never in a
    window: a window is a claim about when something happened."""

    if moment is None:
        return False
    if since is not None and moment < since:
        return False
    return not (until is not None and moment >= until)


def family_of(run: str) -> str:
    """The name stem a physical run belongs to."""

    stem = RUN_STAMP_RE.sub("", run, count=1)
    while True:
        shorter = RUN_SUFFIX_RE.sub("", stem, count=1)
        if shorter == stem:
            return stem or run
        stem = shorter


def _last_write(paths) -> float:
    """The newest mtime of any *file* under ``paths``, or ``0.0``.

    Files only: a directory's own mtime moves when an entry is added to
    it, so a sink copied or a run walked would date every run to the copy.
    """

    newest = 0.0
    for base in paths:
        try:
            entries = [child for child in base.rglob("*") if child.is_file()] if base.is_dir() else []
        except OSError:
            continue
        for entry in entries:
            try:
                newest = max(newest, entry.stat().st_mtime)
            except OSError:
                continue
    return newest


def _run_names(root: Path) -> list:
    """Every run the sink holds, by either of the two trees that name one."""

    names = set()
    for parts in (("runs",), ("tickets",)):
        directory = root.joinpath(*parts)
        try:
            entries = list(directory.iterdir()) if directory.is_dir() else []
        except OSError:
            entries = []
        names.update(entry.name for entry in entries if entry.is_dir() and ui_model._safe_name(entry.name))
    return sorted(names)


def _oracle_minutes(texts) -> tuple:
    """``(minutes, invocations, timed)`` over every line naming an oracle.

    A duration is only read off a line that names one, so a ticket's
    unrelated "90 minutes" bound is never summed into oracle time.
    """

    minutes, invocations, timed = 0.0, 0, 0
    for text in texts:
        for line in text.splitlines():
            if not ORACLE_RE.search(line):
                continue
            invocations += 1
            found = [
                float(match) * factor
                for pattern, factor in DURATION_RES
                for match in pattern.findall(line)
            ]
            if found:
                timed += 1
                minutes += sum(found)
    return round(minutes, 3), invocations, timed


def _run_texts(root: Path, run: str, tickets) -> list:
    """Every text a run recorded an oracle invocation in: its own free
    notes and worklog, and its tickets' bodies."""

    texts = [ticket["raw"] for ticket in tickets]
    run_dir = ui_model._in_tree(root.joinpath("runs"), run)
    try:
        entries = sorted(run_dir.rglob("*.md")) if run_dir is not None and run_dir.is_dir() else []
    except OSError:
        entries = []
    for entry in entries:
        try:
            texts.append(entry.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return texts


def read_runs(root: Path) -> tuple:
    """``(rows, unreadable)`` -- one row per run in the sink, unranked and
    unfiltered, plus the names whose identity document would not parse."""

    rows, unreadable = [], []
    for run in _run_names(root):
        identity = ui_discovery.read_run_identity(root, run)
        broken = isinstance(identity, dict) and bool(identity.get(UNREADABLE))
        if broken:
            unreadable.append(run)
            identity = {}
        identity = identity or {}
        tickets = ui_discovery.run_tickets(root, run) or []
        opened = parse_instant(identity.get("opened_at"))
        newest = _last_write([root.joinpath("runs", run), root.joinpath("tickets", run)])
        last_write = datetime.fromtimestamp(newest, timezone.utc) if newest else None
        elapsed = identity.get("elapsed_ms")
        elapsed = int(elapsed) if isinstance(elapsed, int) and elapsed >= 0 else None
        observed = None
        if opened is not None and last_write is not None:
            observed = max(int((last_write - opened).total_seconds() * 1000), 0)
        work = [ticket for ticket in tickets if ticket["executor"] != SLICE_EXECUTOR]
        rows.append({
            "run": run,
            "family": family_of(run),
            "identity": UNREADABLE if broken else ("present" if identity else "absent"),
            "opened_at": format_instant(opened),
            "last_write_at": format_instant(last_write),
            "elapsed_ms": elapsed,
            "observed_ms": observed,
            "rank_ms": elapsed if elapsed is not None else observed,
            "rank_source": "elapsed_ms" if elapsed is not None else ("observed" if observed is not None else None),
            "terminal_at": identity.get("terminal_at"),
            "terminal_status": identity.get("terminal_status"),
            "terminal_ticket_id": identity.get("terminal_ticket_id"),
            "tickets": len(tickets),
            "complete": sum(1 for ticket in tickets if ticket["status"] == COMPLETE_STATUS),
            "failed": sum(1 for ticket in tickets if ticket["status"] == FAILED_STATUS),
            "claimed_no_work": not any(ticket["claimed_at"] for ticket in work),
            "_at": opened or last_write,
            "_tickets": tickets,
            "_texts_of": (root, run, tickets),
        })
    return rows, unreadable


def _rank_key(row) -> tuple:
    """Longest first; a run with neither figure last; ties by name, so the
    order is a property of the sink and not of the walk."""

    return (row["rank_ms"] is None, -(row["rank_ms"] or 0), row["run"])


def ticket_rows(runs) -> list:
    """One row per ticket that was claimed: ``claimed_at`` to the ticket
    file's own mtime, which is when its executor last wrote into it."""

    rows = []
    for run in runs:
        for ticket in run["_tickets"]:
            started = parse_instant(ticket["claimed_at"])
            if started is None:
                continue
            try:
                modified = datetime.fromtimestamp(Path(ticket["path"]).stat().st_mtime, timezone.utc)
            except OSError:
                continue
            rows.append({
                "run": run["run"],
                "id": ticket["id"],
                "executor": ticket["executor"] or None,
                "status": ticket["status"] or None,
                "claimed_at": ticket["claimed_at"],
                "modified_at": format_instant(modified),
                "minutes": round(max((modified - started).total_seconds(), 0.0) / 60.0, 2),
                "_ticket": ticket,
            })
    rows.sort(key=lambda row: (-row["minutes"], row["run"], row["id"]))
    return rows


def _percentile(values, fraction: float) -> float:
    """Nearest-rank percentile: the smallest observation at or above the
    fraction. No interpolation, so every figure printed is one a ticket
    actually took."""

    ordered = sorted(values)
    index = max(int(-(-len(ordered) * fraction // 1)) - 1, 0)
    return ordered[min(index, len(ordered) - 1)]


def ticket_section(rows, now, top: int) -> dict:
    by_executor = {}
    for row in rows:
        by_executor.setdefault(row["executor"] or ui_model.EMPTY_UNSET, []).append(row["minutes"])
    summary = [
        {
            "executor": executor,
            "tickets": len(minutes),
            "median_minutes": round(statistics.median(minutes), 2),
            "p90_minutes": round(_percentile(minutes, 0.9), 2),
            "max_minutes": round(max(minutes), 2),
        }
        for executor, minutes in sorted(by_executor.items())
    ]
    live = []
    for row in rows:
        meter = ui_model.claim_meter(row["_ticket"], now)
        if meter is not None:
            live.append({"run": row["run"], "id": row["id"], "executor": row["executor"], **meter})
    return {
        "by_executor": summary,
        "longest": [
            {key: value for key, value in row.items() if not key.startswith("_")}
            for row in rows[: max(top, 0)]
        ],
        "live_claims": live,
        "over_bound": [claim for claim in live if claim["over"]],
    }


def family_section(runs) -> list:
    """Section (b) and the three §1 metrics, one row per family.

    ``wall_clock_ms`` is the family's own first opening to the terminal
    instant of its last **complete** run: a family with no complete run
    has not reached an accepted result, and reporting its span as though
    it had is the one number this report exists to stop guessing at.
    """

    families = {}
    for row in runs:
        families.setdefault(row["family"], []).append(row)
    section = []
    for family, rows in sorted(families.items()):
        opened = [parse_instant(row["opened_at"]) for row in rows]
        opened = [moment for moment in opened if moment is not None]
        writes = [parse_instant(row["last_write_at"]) for row in rows]
        writes = [moment for moment in writes if moment is not None]
        accepted = [
            parse_instant(row["terminal_at"])
            for row in rows
            if row["terminal_status"] == COMPLETE_STATUS
        ]
        accepted = [moment for moment in accepted if moment is not None]
        first = min(opened) if opened else None
        wall_clock = None
        if first is not None and accepted:
            wall_clock = max(int((max(accepted) - first).total_seconds() * 1000), 0)
        minutes, invocations, timed = _oracle_minutes(
            [text for row in rows for text in _run_texts(*row["_texts_of"])]
        )
        statuses = {}
        for row in rows:
            statuses[row["terminal_status"] or "open"] = statuses.get(row["terminal_status"] or "open", 0) + 1
        section.append({
            "family": family,
            "physical_runs": len(rows),
            "span_from": format_instant(first),
            "span_to": format_instant(max(writes)) if writes else None,
            "statuses": statuses,
            "runs": [row["run"] for row in rows],
            "wall_clock_ms": wall_clock,
            "oracle_minutes": minutes,
            "oracle_invocations": invocations,
            "oracle_invocations_timed": timed,
        })
    section.sort(key=lambda row: (row["wall_clock_ms"] is None, -(row["wall_clock_ms"] or 0), row["family"]))
    return section


def build_report(root, since=None, until=None, top: int = DEFAULT_TOP) -> dict:
    """The whole report as one JSON-ready document.

    ``since`` and ``until`` are ISO-8601 UTC strings or ``None``. A window
    later than every record yields empty tables rather than an error: no
    records in a window is an answer.
    """

    root = Path(root)
    since_at, until_at = parse_instant(since), parse_instant(until)
    now = until_at or datetime.now(timezone.utc)
    if not root.is_dir():
        rows, unreadable_runs = [], []
        empty = ui_model.EMPTY_NO_SINK
    else:
        rows, unreadable_runs = read_runs(root)
        empty = ""
    windowed = [row for row in rows if in_window(row["_at"], since_at, until_at)]
    windowed.sort(key=_rank_key)
    tickets = ticket_rows(windowed)
    log = ui_discovery.read_friction(root)
    return {
        "root": str(root),
        "window": {"since": since, "until": until},
        "empty": empty,
        "top": top,
        "runs": [
            {key: value for key, value in row.items() if not key.startswith("_")}
            for row in windowed[: max(top, 0)]
        ],
        "families": family_section(windowed)[: max(top, 0)],
        "tickets": ticket_section(tickets, now, top),
        "friction": friction_support.friction_section(
            log, lambda stamp: in_window(parse_instant(stamp), since_at, until_at), top
        ),
        "totals": {
            "runs": len(windowed),
            "runs_terminal": sum(1 for row in windowed if row["terminal_status"] in TERMINAL_STATUSES),
            "runs_complete": sum(1 for row in windowed if row["terminal_status"] == COMPLETE_STATUS),
            "runs_that_claimed_no_work": sum(1 for row in windowed if row["claimed_no_work"]),
            "families": len(set(row["family"] for row in windowed)),
            "tickets_measured": len(tickets),
        },
        "unreadable": {
            "runs": sorted(name for name in unreadable_runs if any(row["run"] == name for row in windowed)),
            "tickets": sorted(
                "{0}/{1}".format(row["run"], ticket["file_id"])
                for row in windowed
                for ticket in row["_tickets"]
                if ticket["unreadable"]
            ),
            "friction_files": list(log["unreadable"]),
            "friction_lines": log["skipped"],
        },
    }
