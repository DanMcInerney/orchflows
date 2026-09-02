"""The one fixture sink every speed-report case reads.

Three runs, two families and a friction month that crosses both window
edges, all with pinned mtimes: every duration this suite asserts is a
subtraction of two stated instants, never of a stated instant and
whenever the fixture happened to be written.
"""

from __future__ import annotations

import json
import os
import sys
import unittest  # noqa: F401  (re-exported to the case modules)
from datetime import datetime, timezone
from pathlib import Path

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import reader.scripts.ui_discovery as ui_discovery  # noqa: E402

RUN_REPORT_PY = ROOT / "tools" / "run_report.py"

SINCE = "2026-08-15T00:00:00Z"
UNTIL = "2026-08-23T00:00:00Z"

COMPLETE_RUN = "20260816T090000Z-alpha-thing"
BLOCKED_RUN = "20260817T090000Z-alpha-thing-retry"
OPEN_RUN = "20260818T090000Z-beta-thing"
ALPHA_FAMILY = "alpha-thing"
BETA_FAMILY = "beta-thing"

TICKET = """---
id: {tid}
run: {run}
status: {status}
executor: {executor}
bound: 30m
{claimed}---

## Objective

Fixture ticket.

## Verification

{verification}
"""


def stamp(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def at(path: Path, when: str) -> Path:
    """Pin one path's mtime to a stated UTC instant."""

    seconds = stamp(when).timestamp()
    os.utime(path, (seconds, seconds))
    return path


def write_run(sink: Path, run: str, identity, *, notes: str = "", notes_at: str = None):
    """One run directory: its identity document and optional free notes.

    ``identity`` of a string is written verbatim, which is how the
    malformed-document case reaches the reader.
    """

    run_dir = sink / "runs" / run
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run.json"
    if isinstance(identity, str):
        path.write_text(identity, encoding="utf-8")
    else:
        path.write_text(json.dumps(identity, indent=2), encoding="utf-8")
    at(path, identity["opened_at"] if isinstance(identity, dict) else "2026-08-19T09:00:00Z")
    if notes:
        notes_path = run_dir / "notes.md"
        notes_path.write_text(notes, encoding="utf-8")
        at(notes_path, notes_at or UNTIL)
    return run_dir


def write_ticket(
    sink: Path,
    run: str,
    tid: str,
    *,
    status: str,
    executor: str,
    claimed_at: str = None,
    modified: str,
    verification: str = "",
) -> Path:
    run_dir = sink / "tickets" / run
    run_dir.mkdir(parents=True, exist_ok=True)
    claimed = ""
    if claimed_at:
        state = {"protocol": "orchflows.dispatch.v1", "attempts": [{
            "assignment_seal": "sha256:sealed", "dispatch_id": "D1",
            "lease_expires_at": "2099-01-01T00:00:00Z",
            "opened_at": claimed_at,
            "outcome_record_id": "outcome", "owner": "unit_01",
            "records": [], "state": "live",
        }]}
        claimed = "dispatch_v1: " + json.dumps(state, separators=(",", ":"), sort_keys=True) + "\n"
    path = run_dir / (tid + ".md")
    path.write_text(
        TICKET.format(tid=tid, run=run, status=status, executor=executor, claimed=claimed, verification=verification),
        encoding="utf-8",
    )
    return at(path, modified)


FRICTION = (
    # Before ``SINCE``: in the log, out of the window.
    {"ts": "2026-08-14T12:00:00Z", "category": "host-defect", "skill": "orch-tdd",
     "host": "claude-code", "run": COMPLETE_RUN, "observed": "before the window",
     "expected": "excluded"},
    {"ts": "2026-08-16T09:30:00Z", "category": "host-defect", "skill": "orch-tdd",
     "host": "claude-code", "run": COMPLETE_RUN,
     "observed": "PowerShell here-string quoting broke the payload",
     "expected": "the payload should have survived the shell"},
    {"ts": "2026-08-18T09:30:00Z", "category": "contract-gap", "skill": "orch-tdd",
     "host": "claude-code", "run": OPEN_RUN,
     "observed": "the full suite was flaky and reported a spurious failure",
     "expected": "a green suite should stay green"},
    # After ``UNTIL``: likewise in the log, out of the window.
    {"ts": "2026-08-24T00:00:00Z", "category": "host-defect", "skill": "orch-tdd",
     "host": "claude-code", "run": OPEN_RUN, "observed": "after the window",
     "expected": "excluded"},
)


def build_sink(tmp: Path) -> Path:
    """The three-run, two-family fixture sink.

    ``COMPLETE_RUN`` and ``BLOCKED_RUN`` share the ``alpha-thing`` family
    across the ``-retry`` suffix; ``BLOCKED_RUN``'s one non-decompose
    ticket is never claimed, which is the shape 36 of the baseline's 159
    runs had.
    """

    sink = (tmp / "state-sink").resolve()
    write_run(sink, COMPLETE_RUN, {
        "run": COMPLETE_RUN, "sink_convention": 2, "opened_at": "2026-08-16T09:00:00Z",
        "terminal_at": "2026-08-16T10:30:00Z", "terminal_ticket_id": "00-root",
        "terminal_status": "complete", "elapsed_ms": 5400000,
    })
    write_ticket(sink, COMPLETE_RUN, "00-root", status="complete", executor="orch-slice",
                 claimed_at="2026-08-16T09:00:00Z", modified="2026-08-16T09:05:00Z")
    write_ticket(sink, COMPLETE_RUN, "00-root.01", status="complete", executor="orch-tdd",
                 claimed_at="2026-08-16T09:10:00Z", modified="2026-08-16T09:40:00Z",
                 verification="`python tools/run_tests.py` exit 0 in 120.0s")
    write_ticket(sink, COMPLETE_RUN, "00-root.02", status="failed", executor="orch-tdd",
                 claimed_at="2026-08-16T09:10:00Z", modified="2026-08-16T10:10:00Z")

    write_run(sink, BLOCKED_RUN, {
        "run": BLOCKED_RUN, "sink_convention": 2, "opened_at": "2026-08-17T09:00:00Z",
        "terminal_at": "2026-08-17T09:20:00Z", "terminal_ticket_id": "00-root",
        "terminal_status": "blocked", "elapsed_ms": 1200000,
    }, notes="`pnpm test` finished in 60s\n", notes_at="2026-08-17T09:20:00Z")
    write_ticket(sink, BLOCKED_RUN, "00-root", status="complete", executor="orch-slice",
                 claimed_at="2026-08-17T09:00:00Z", modified="2026-08-17T09:05:00Z")
    write_ticket(sink, BLOCKED_RUN, "00-root.01", status="pending", executor="orch-tdd",
                 modified="2026-08-17T09:20:00Z")

    write_run(sink, OPEN_RUN, {
        "run": OPEN_RUN, "sink_convention": 2, "opened_at": "2026-08-18T09:00:00Z",
    })
    write_ticket(sink, OPEN_RUN, "00-root.01", status="claimed", executor="orch-tdd",
                 claimed_at="2026-08-18T09:05:00Z", modified="2026-08-18T09:35:00Z")

    friction = sink / "friction"
    friction.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entry) for entry in FRICTION]
    lines.insert(2, "{not a record")
    (friction / "2026-08.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sink


def report_of(sink: Path, **options) -> dict:
    """The JSON document the CLI would print, built in this process."""

    from tools.run_report_support import model

    return model.build_report(
        sink,
        since=options.get("since", SINCE),
        until=options.get("until", UNTIL),
        top=options.get("top", model.DEFAULT_TOP),
    )


def run_named(report: dict, run: str) -> dict:
    return next(row for row in report["runs"] if row["run"] == run)


def family_named(report: dict, family: str) -> dict:
    return next(row for row in report["families"] if row["family"] == family)
