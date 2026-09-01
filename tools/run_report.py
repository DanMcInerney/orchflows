#!/usr/bin/env python3
"""Retrospective speed report over the orchflows state sink.

For one UTC window, prints:

- runs, longest first, by the exact ``elapsed_ms`` their identity document
  recorded and by the observed opened-at to last-sink-write span where it
  recorded none, with the terminal status and ticket that closed each one,
  its ticket counts, and whether it ever claimed a non-decompose ticket;
- run families -- the name stem after the timestamp and any retry marker --
  with physical-run count, span and statuses;
- ticket durations by executor, ``claimed_at`` to the ticket file's own
  mtime, as median, p90 and max, plus the longest tickets and every live
  claim's elapsed-against-bound;
- the window's friction by category, skill, host and run, and against the
  fixed keyword-cluster table;
- and, per family, the three metrics of
  ``research/orchflows-speed-spec-2026-08-23.md`` §1: wall-clock per
  objective, physical runs per objective, oracle minutes per objective.

Read-only. Nothing here opens a file for writing, and
``tests/test_run_report.py`` holds the sink byte-identical across a run of
both formats. Stdlib only, no network, Python 3.9+, POSIX and Windows.

Usage:
    python tools/run_report.py [--root DIR] [--since ISO] [--until ISO]
                               [--format text|json] [--top N]

Exit 0 with the report -- including for a window no record falls in, which
is an answer -- and 2 for an argument this cannot read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# This is the entry point that puts the repository on sys.path for the
# `reader.*` and `tools.*` imports below, so it cannot read
# `scripts._bootstrap.ROOT` for the same fact -- nothing is importable yet.
_REPORT_ROOT = Path(__file__).resolve().parent.parent
for _import_root in (_REPORT_ROOT, _REPORT_ROOT / "scripts"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

import reader.scripts.ui_discovery as ui_discovery  # noqa: E402

from tools.run_report_support import model, render  # noqa: E402

FORMATS = ("text", "json")
USAGE_EXIT = 2


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Retrospective speed report over the state sink.")
    parser.add_argument("--root", default=None, help="the state sink to read; defaults to the installed one")
    parser.add_argument("--since", default=None, help="window start, ISO-8601 UTC, inclusive")
    parser.add_argument("--until", default=None, help="window end, ISO-8601 UTC, exclusive")
    parser.add_argument("--format", default="text", choices=FORMATS, dest="format_name")
    parser.add_argument("--top", type=int, default=model.DEFAULT_TOP, help="rows per ranked table")
    return parser.parse_args(argv)


def _refuse(parser_name: str, value: str) -> int:
    sys.stderr.write(
        "{0}: {1!r} is not an ISO-8601 UTC instant (for example 2026-08-15T00:00:00Z)\n".format(parser_name, value)
    )
    return USAGE_EXIT


def main(argv=None) -> int:
    args = parse_args(argv)
    for name, value in (("--since", args.since), ("--until", args.until)):
        if value is not None and model.parse_instant(value) is None:
            return _refuse(name, value)
    root = Path(args.root) if args.root else ui_discovery.default_root()
    report = model.build_report(root, since=args.since, until=args.until, top=args.top)
    if args.format_name == "json":
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render.render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
