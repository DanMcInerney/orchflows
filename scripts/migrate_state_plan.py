"""Migration planning, collision handling, and application."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

try:  # in-repo; the installed copies sit flat together
    from scripts import tickets
    from scripts.migrate_state_records import (
        FRICTION_SUFFIX,
        _existing_lines,
        _migrated_covered_line,
        _migrated_friction_line,
        _project_label,
        _project_of,
        _recorded_project,
    )
except ImportError:  # pragma: no cover - the installed copy's path
    import tickets
    from migrate_state_records import (
        FRICTION_SUFFIX,
        _existing_lines,
        _migrated_covered_line,
        _migrated_friction_line,
        _project_label,
        _project_of,
        _recorded_project,
    )

# What migrates and what stays. The stream names are the sink layout's,
# so a source written under that layout maps onto it by name.
MIGRATED_STREAMS = ("runs", "tickets", "friction", "improvement")
# `bin/` is the legacy per-project landing zone `installer/foundation.py`
# places, so it is recognised and deliberately left where it stands --
# reporting it as unrecognised would say the migration does not know what it
# is. The sink-itself branch below is the second thing named retained, so
# one entry here is a truthful set and not a vestige of a two-entry concept.
RETAINED_DIRS = ("bin",)


class _Plan:
    """The actions to take, and what a reader is told about them.

    ``actions`` carries private keys for the executor; ``public`` strips
    them, so the plan printed by a dry run and by a real run is the same
    document.
    """

    def __init__(self, sink: Path):
        self.sink = sink
        self.actions = []
        self.seen = {}  # destination -> the lines it will hold
        self.claimed = {}  # destination -> the source already copying there
        self.refusals = []  # what could not be planned, and why

    def copy(self, stream, source: Path, dest: Path):
        self.claimed[str(dest)] = source
        self.actions.append({
            "action": "copy", "stream": stream,
            "source": str(source), "dest": str(dest),
            "_source": source, "_dest": dest,
        })

    def claimant_of(self, dest: Path):
        """The source an earlier action in this plan already copies to ``dest``.

        A destination two sources claim does not exist yet when the second is
        planned, so the on-disk test cannot see it. Without this the later
        action would overwrite the earlier one's bytes at apply time.
        """

        return self.claimed.get(str(dest))

    def append(self, stream, source: Path, dest: Path, lines):
        self.actions.append({
            "action": "append", "stream": stream,
            "source": str(source), "dest": str(dest), "lines": len(lines),
            "_dest": dest, "_payload": lines,
        })

    def lines_at(self, dest: Path):
        key = str(dest)
        if key not in self.seen:
            self.seen[key] = set(_existing_lines(dest))
        return self.seen[key]

    def public(self):
        return [
            {key: value for key, value in action.items() if not key.startswith("_")}
            for action in self.actions
        ]


def _copy_tree(plan: _Plan, stream, source: Path, dest: Path, counts, differing):
    """Plan one directory's files. Existing destinations are left alone."""

    for child in sorted(source.iterdir(), key=lambda path: path.name):
        if child.is_symlink():
            counts["symlinks"] += 1
            continue
        target = dest / child.name
        if child.is_dir():
            _copy_tree(plan, stream, child, target, counts, differing)
            continue
        if not child.is_file():
            counts["skipped_other"] += 1
            continue
        claimant = plan.claimant_of(target)
        held = target if target.exists() else claimant
        if held is not None:
            counts["existing"] += 1
            record = {"source": str(child), "dest": str(target)}
            if claimant is not None and not target.exists():
                # Two sources, one destination, within a single run. The first
                # planned wins; this one is named rather than silently losing.
                record["claimed_by"] = str(claimant)
            try:
                if held.read_bytes() != child.read_bytes():
                    differing.append(record)
            except OSError as error:
                counts["unreadable"] += 1
                record["error"] = str(error)
                differing.append(record)
            continue
        plan.copy(stream, child, target)
        counts["files"] += 1


def _plan_runs(plan, root, stream, collided, report):
    """Plan ``runs/`` or ``tickets/``: one directory per run id."""

    base = root / stream
    counts = report[stream]
    if not base.is_dir():
        return
    for child in sorted(base.iterdir(), key=lambda path: path.name):
        if child.is_symlink():
            counts["symlinks"] += 1
            continue
        if not child.is_dir():
            report["unrecognised"].append(f"{stream}/{child.name}")
            continue
        if child.name in collided:
            counts["skipped_collision"].append(child.name)
            continue
        counts["ids"] += 1
        _copy_tree(plan, stream, child, plan.sink / stream / child.name,
                   counts, report["differing"])


def _plan_line_file(plan, stream, source_file, dest_file, migrate, counts):
    """Plan one jsonl merge: read, migrate each line, drop exact duplicates."""

    try:
        seen = plan.lines_at(dest_file)
    except OSError as error:
        # Refused rather than planned: appending against a destination whose
        # contents are unknown is how the same records land twice.
        plan.refusals.append(f"unreadable destination {dest_file}: {error}")
        return
    queued = []
    try:
        raw = source_file.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        counts["unreadable"].append(f"{source_file}: {error}")
        return
    for line in raw.splitlines():
        if not line.strip():
            continue
        counts["read"] += 1
        migrated, note = migrate(line)
        counts[note] = counts.get(note, 0) + 1
        if migrated in seen:
            counts["duplicates"] += 1
            continue
        seen.add(migrated)
        queued.append(migrated)
    if queued:
        plan.append(stream, source_file, dest_file, queued)
        counts["write"] += len(queued)


def _plan_friction(plan, root, report):
    base = root / "friction"
    counts = report["friction"]
    if not base.is_dir():
        return
    for child in sorted(base.iterdir(), key=lambda path: path.name):
        if child.is_symlink():
            counts["symlinks"] += 1
            continue
        if not child.is_file() or child.suffix != FRICTION_SUFFIX:
            report["unrecognised"].append(f"friction/{child.name}")
            continue
        counts["files"] += 1
        _plan_line_file(
            plan, "friction", child, plan.sink / "friction" / child.name,
            lambda line: _migrated_friction_line(line, root), counts,
        )


def _plan_improvement(plan, root, project, report):
    base = root / "improvement"
    counts = report["improvement"]
    if not base.is_dir():
        return
    for child in sorted(base.iterdir(), key=lambda path: path.name):
        if child.is_symlink():
            counts["symlinks"] += 1
            continue
        if child.is_dir() and child.name == tickets.PROPOSALS_DIR:
            _copy_tree(plan, "proposals", child,
                       plan.sink / "improvement" / tickets.PROPOSALS_DIR,
                       counts, report["differing"])
            continue
        if child.is_file() and child.name == tickets.COVERAGE_RECORD_NAME:
            _plan_line_file(
                plan, "covered", child,
                plan.sink / "improvement" / tickets.COVERAGE_RECORD_NAME,
                lambda line: _migrated_covered_line(line, root, project), counts,
            )
            continue
        report["unrecognised"].append(f"improvement/{child.name}")


def _source_report(root: Path, project):
    return {
        "root": str(root),
        "project": _project_label(project),
        "runs": {"ids": 0, "files": 0, "existing": 0, "symlinks": 0,
                 "skipped_other": 0, "unreadable": 0, "skipped_collision": []},
        "tickets": {"ids": 0, "files": 0, "existing": 0, "symlinks": 0,
                    "skipped_other": 0, "unreadable": 0, "skipped_collision": []},
        "friction": {"files": 0, "read": 0, "write": 0, "duplicates": 0,
                     "symlinks": 0, "unreadable": []},
        "improvement": {"files": 0, "read": 0, "write": 0, "duplicates": 0,
                        "existing": 0, "symlinks": 0, "skipped_other": 0,
                        "unreadable": []},
        "retained": [],
        "unrecognised": [],
        "differing": [],
    }


def _classify(root: Path, sink: Path, report):
    """Name every child of a source root: migrated, retained, or neither."""

    try:
        children = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError as error:
        report["unrecognised"].append(f"unreadable: {error}")
        return
    for child in children:
        if child == sink:
            # A source may hold the sink as a child -- `~/.orchflows` holds
            # both `friction/` and `state/`. Name it as seen and not copied
            # rather than as something unrecognised.
            report["retained"].append(f"{child.name}/ (the sink itself)")
        elif child.name in RETAINED_DIRS:
            report["retained"].append(f"{child.name}/")
        elif child.name not in MIGRATED_STREAMS:
            report["unrecognised"].append(
                f"{child.name}/" if child.is_dir() else child.name
            )


def _resolve_roots(values, sink: Path):
    """``(roots, errors)`` — each source resolved once, refusals named."""

    roots, errors, seen = [], [], set()
    for value in values:
        try:
            resolved = Path(value).expanduser().resolve()
        except OSError as error:
            errors.append(f"unusable source {value}: {error}")
            continue
        if str(resolved) in seen:
            continue
        seen.add(str(resolved))
        if not resolved.is_dir():
            errors.append(f"source {resolved} is not a directory")
            continue
        if resolved == sink or sink in resolved.parents:
            errors.append(
                f"source {resolved} is the sink {sink}, or sits inside it; "
                "a sink cannot be migrated into itself"
            )
            continue
        # A source that merely *contains* the sink is fine: `~/.orchflows`
        # holds `friction/` beside `state/`, and the sink is skipped as a
        # child. The hazard is a sink inside a stream that gets copied.
        buried = [name for name in MIGRATED_STREAMS
                  if (resolved / name) == sink or (resolved / name) in sink.parents]
        if buried:
            errors.append(
                f"the sink {sink} is inside source {resolved}'s "
                f"{buried[0]}/ stream; a sink cannot be migrated into itself"
            )
            continue
        roots.append(resolved)
    return roots, errors


def _claims(root: Path, project):
    """``{run id: the project claiming it}`` for one source."""

    claimed = {}
    for stream in ("runs", "tickets"):
        base = root / stream
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir(), key=lambda path: path.name):
            if child.is_symlink() or not child.is_dir():
                continue
            recorded = None
            if stream == "runs":
                recorded = _recorded_project(child / tickets.RUN_IDENTITY_NAME)
            if recorded is not None or child.name not in claimed:
                claimed[child.name] = recorded if recorded is not None else project
    return claimed


def _collisions(per_source, sink: Path):
    """Run ids two projects both claim. Item 03's rule, applied at copy time.

    A claim with no project is ignored rather than counted against
    another: unknown is not a second project, and refusing on it would
    strand a run nothing disagrees about.
    """

    grouped = {}
    for label, claimed in per_source:
        for run, project in claimed.items():
            grouped.setdefault(run, []).append((label, project))
    collided = {}
    for run, claims in sorted(grouped.items()):
        recorded = _recorded_project(sink / "runs" / run / tickets.RUN_IDENTITY_NAME)
        if recorded is not None:
            claims = claims + [(str(sink), recorded)]
        known = [(label, p) for label, p in claims if isinstance(p, dict)]
        for index, (label, project) in enumerate(known):
            if any(not tickets._same_project(project, other)
                   for _, other in known[index + 1:]):
                collided[run] = [
                    {"source": source, "project": _project_label(each)}
                    for source, each in known
                ]
                break
    return collided


def plan_migration(values, sink: Path, dry_run: bool):
    """``(plan, report)``. Identical inputs and destination, identical plan."""

    plan = _Plan(sink)
    roots, errors = _resolve_roots(values, sink)
    projects = {str(root): _project_of(root) for root in roots}
    collided = _collisions(
        [(str(root), _claims(root, projects[str(root)])) for root in roots], sink
    )
    sources = []
    for root in roots:
        project = projects[str(root)]
        report = _source_report(root, project)
        _classify(root, sink, report)
        _plan_runs(plan, root, "runs", collided, report)
        _plan_runs(plan, root, "tickets", collided, report)
        _plan_friction(plan, root, report)
        _plan_improvement(plan, root, project, report)
        sources.append(report)
    document = {
        "sink": str(sink),
        "dry_run": dry_run,
        "sources": sources,
        "collisions": [{"run": run, "claims": claims}
                       for run, claims in sorted(collided.items())],
        "errors": errors + plan.refusals,
        "plan": plan.public(),
    }
    return plan, document


# --- execution ---------------------------------------------------------------


def _needs_newline(path: Path) -> bool:
    """Whether an existing file's last byte leaves a line unterminated.

    A file it cannot open raises, because False is the answer "no separator
    needed" and that answer glues the first record onto the unterminated
    line. ``apply_plan`` names the action instead, and appends nothing.
    """

    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            return False
        handle.seek(-1, os.SEEK_END)
        return handle.read(1) != b"\n"


def apply_plan(plan: _Plan, document):
    """Execute the plan. A failed action is reported and the rest proceed."""

    for action in plan.actions:
        dest = action["_dest"]
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if action["action"] == "copy":
                if dest.exists():
                    # The plan excludes destinations already spoken for, so
                    # reaching here means the sink changed under the run. Never
                    # overwrite; say so, and leave both copies where they are.
                    document["errors"].append(
                        f"copy {dest}: refused, a record appeared at the "
                        f"destination after the plan was made")
                    continue
                shutil.copy2(str(action["_source"]), str(dest))
                continue
            prefix = "\n" if dest.exists() and _needs_newline(dest) else ""
            with open(dest, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(prefix + "".join(line + "\n" for line in action["_payload"]))
        except OSError as error:
            document["errors"].append(f"{action['action']} {dest}: {error}")
    return document
