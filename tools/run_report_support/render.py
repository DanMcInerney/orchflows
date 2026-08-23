"""The report as plain text.

Fixed-width columns computed from the rows themselves, so a run name that
grew does not shear the table, and one named empty line per section: an
absent table and a table of nothing are different answers, and only one of
them means the window was quiet.
"""

from __future__ import annotations

EMPTY_ROWS = "no records in this window"
NOT_MEASURED = "-"


def _cell(value) -> str:
    if value is None or value == "":
        return NOT_MEASURED
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _minutes(milliseconds) -> str:
    if milliseconds is None:
        return NOT_MEASURED
    return "{0:.1f}".format(milliseconds / 60000.0)


def table(heading: str, columns, rows) -> list:
    """One headed table, or the heading and one named empty line."""

    lines = ["", heading, "-" * len(heading)]
    if not rows:
        return lines + [EMPTY_ROWS]
    names = [name for name, _ in columns]
    cells = [[_cell(read(row)) for _, read in columns] for row in rows]
    widths = [max(len(names[index]), *(len(row[index]) for row in cells)) for index in range(len(names))]
    lines.append("  ".join(name.ljust(widths[index]) for index, name in enumerate(names)))
    for row in cells:
        lines.append("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    return lines


def _statuses(row) -> str:
    return ", ".join("{0}={1}".format(name, count) for name, count in sorted(row["statuses"].items()))


RUN_COLUMNS = (
    ("run", lambda row: row["run"]),
    ("minutes", lambda row: _minutes(row["rank_ms"])),
    ("from", lambda row: row["rank_source"]),
    ("terminal", lambda row: row["terminal_status"]),
    ("tickets", lambda row: row["tickets"]),
    ("complete", lambda row: row["complete"]),
    ("failed", lambda row: row["failed"]),
    ("claimed no work", lambda row: row["claimed_no_work"]),
    ("opened", lambda row: row["opened_at"]),
    ("last write", lambda row: row["last_write_at"]),
)
FAMILY_COLUMNS = (
    ("family", lambda row: row["family"]),
    ("physical runs", lambda row: row["physical_runs"]),
    ("wall-clock minutes", lambda row: _minutes(row["wall_clock_ms"])),
    ("oracle minutes", lambda row: row["oracle_minutes"]),
    ("oracle calls", lambda row: row["oracle_invocations"]),
    ("timed", lambda row: row["oracle_invocations_timed"]),
    ("span from", lambda row: row["span_from"]),
    ("span to", lambda row: row["span_to"]),
    ("statuses", _statuses),
)
EXECUTOR_COLUMNS = (
    ("executor", lambda row: row["executor"]),
    ("tickets", lambda row: row["tickets"]),
    ("median", lambda row: row["median_minutes"]),
    ("p90", lambda row: row["p90_minutes"]),
    ("max", lambda row: row["max_minutes"]),
)
LONGEST_COLUMNS = (
    ("run", lambda row: row["run"]),
    ("ticket", lambda row: row["id"]),
    ("executor", lambda row: row["executor"]),
    ("status", lambda row: row["status"]),
    ("minutes", lambda row: row["minutes"]),
    ("claimed", lambda row: row["claimed_at"]),
)
LIVE_COLUMNS = (
    ("run", lambda row: row["run"]),
    ("ticket", lambda row: row["id"]),
    ("executor", lambda row: row["executor"]),
    ("elapsed", lambda row: row["elapsed_minutes"]),
    ("bound", lambda row: row["bound_minutes"]),
    ("percent", lambda row: row["percent"]),
    ("over", lambda row: row["over"]),
)
CLUSTER_COLUMNS = (
    ("cluster", lambda row: row["cluster"]),
    ("records", lambda row: row["count"]),
)


def _by(field: str):
    return (("count", lambda row: row["count"]), (field, lambda row: row[field]))


def render(report: dict) -> str:
    """The whole report, in the order item 0 states its sections."""

    totals = report["totals"]
    lines = [
        "orchflows speed report",
        "root: {0}".format(report["root"]),
        "window: {0} .. {1}".format(_cell(report["window"]["since"]), _cell(report["window"]["until"])),
        "runs: {runs} ({runs_terminal} terminal, {runs_complete} complete, "
        "{runs_that_claimed_no_work} never claimed a non-decompose ticket); families: {families}; "
        "tickets measured: {tickets_measured}".format(**totals),
    ]
    if report["empty"]:
        lines.append(report["empty"])
    lines += table("runs (longest first, top {0})".format(report["top"]), RUN_COLUMNS, report["runs"])
    lines += table("families", FAMILY_COLUMNS, report["families"])
    lines += table("ticket durations by executor", EXECUTOR_COLUMNS, report["tickets"]["by_executor"])
    lines += table("longest tickets (top {0})".format(report["top"]), LONGEST_COLUMNS, report["tickets"]["longest"])
    lines += table("live claims", LIVE_COLUMNS, report["tickets"]["live_claims"])
    friction = report["friction"]
    lines += ["", "friction: {0} in window, {1} outside, {2} matched no cluster".format(
        friction["total"], friction["outside_window"], friction["unclustered"])]
    for field in ("category", "skill", "host", "run"):
        lines += table("friction by " + field, _by(field), friction["by_" + field])
    lines += table("friction clusters", CLUSTER_COLUMNS, friction["clusters"])
    unreadable = report["unreadable"]
    lines += [
        "",
        "unreadable",
        "----------",
        "runs: {0}".format(", ".join(unreadable["runs"]) or NOT_MEASURED),
        "tickets: {0}".format(", ".join(unreadable["tickets"]) or NOT_MEASURED),
        "friction files: {0}".format(", ".join(unreadable["friction_files"]) or NOT_MEASURED),
        "friction lines: {0}".format(unreadable["friction_lines"]),
        "",
    ]
    return "\n".join(lines)
