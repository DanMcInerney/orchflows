"""The friction a window recorded, grouped and clustered.

`reader/scripts/ui_discovery.read_friction` owns the reading -- one bad line
costs that line and nothing else -- so this module only counts.
"""

from __future__ import annotations

import re

# `research/orchflows-speed-spec-2026-08-23.md` item 0 (d): a fixed
# keyword-cluster table, in the specification's own order, so two reports
# over two windows have the same rows and can be subtracted. The table is
# a coarse instrument by construction -- it reads the words an author
# happened to use -- which is why `unclustered` is reported beside it
# rather than the clusters being made to add up to the total.
CLUSTERS = (
    ("powershell-quoting", r"powershell.{0,40}(quot|escap|here-string|backtick)"
                           r"|(quot|escap|here-string|backtick).{0,40}powershell"),
    ("rg-wildcard", r"\brg\b.{0,60}(wildcard|glob|\*)|ripgrep.{0,60}(wildcard|glob)"),
    ("guessed-path", r"guessed (the )?path|path .{0,20}guess|assumed .{0,20}path"
                     r"|wrong path|no such file"),
    ("truncated-escaped-result", r"truncat|escaped result|result .{0,20}escap"),
    ("workspace-vantage", r"vantage|wrong worktree|main checkout|integrating checkout"),
    ("missing-node-modules", r"node_modules|pnpm install"),
    ("word-ceiling", r"word ceiling|300-word|word budget|instruction_words"),
    ("sealed-assignment", r"sealed assignment|assignment .{0,20}seal"),
    ("isolation", r"isolation"),
    ("missing-flag", r"missing flag|unknown flag|unrecognized argument|no such option"
                     r"|does not exist for|--\w[\w-]* .{0,30}(not exist|not supported)"),
    ("full-suite-flake", r"flake|flaky|spurious|intermittent"),
)
CLUSTER_RES = tuple((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in CLUSTERS)

# Which of a record's fields the cluster patterns read. The two the
# friction law makes mandatory, and nothing else: a category or a skill
# name matching `isolation` would cluster a record by its label rather
# than by what was observed.
CLUSTERED_FIELDS = ("observed", "expected")

GROUPINGS = ("category", "skill", "host", "run")
UNSET = "unset"


def _text_of(entry: dict) -> str:
    return "\n".join(str(entry.get(field) or "") for field in CLUSTERED_FIELDS)


def _grouped(entries, field: str) -> list:
    """Commonest first, then alphabetical, so the order is a property of
    the records and not of the walk."""

    counts = {}
    for entry in entries:
        value = entry.get(field)
        key = value if isinstance(value, str) and value else UNSET
        counts[key] = counts.get(key, 0) + 1
    rows = [{field: key, "count": count} for key, count in counts.items()]
    rows.sort(key=lambda row: (-row["count"], row[field]))
    return rows


def clusters_of(entries) -> tuple:
    """``(rows, unclustered)`` over the fixed table. A record may land in
    more than one cluster, so the counts do not sum to the total."""

    counts = {name: 0 for name, _ in CLUSTER_RES}
    unclustered = 0
    for entry in entries:
        text = _text_of(entry)
        matched = [name for name, pattern in CLUSTER_RES if pattern.search(text)]
        for name in matched:
            counts[name] += 1
        if not matched:
            unclustered += 1
    return [{"cluster": name, "count": counts[name]} for name, _ in CLUSTER_RES], unclustered


def friction_section(log: dict, keeps, top: int) -> dict:
    """Section (d) for one window, from ``read_friction``'s payload.

    ``keeps`` decides whether one record's ``ts`` is in the window and is
    handed in rather than imported: ``model`` owns what a window is, and
    this module owns only the counting. ``top`` bounds the four groupings,
    whose longest -- by run -- is one row per run in the window; it is the
    same bound the ranked tables take and it is required, because a ``top``
    that meant "all rows" here and "no rows" there would make one flag
    print two different reports. The cluster table is fixed and is never
    bounded, so two windows' tables stay subtractable.
    """

    inside = [entry for entry in log["entries"] if keeps(entry.get("ts"))]
    rows, unclustered = clusters_of(inside)
    section = {"total": len(inside), "clusters": rows, "unclustered": unclustered}
    for field in GROUPINGS:
        rows = _grouped(inside, field)
        section["by_" + field] = rows[: max(top, 0)]
    return section
