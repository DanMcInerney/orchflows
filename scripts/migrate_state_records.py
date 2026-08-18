"""Record attribution and transformation for state migration."""

from __future__ import annotations

import json
from pathlib import Path

try:  # in-repo; the installed copies sit flat together
    from scripts import friction, state_root, tickets
except ImportError:  # pragma: no cover - the installed copy's path
    import friction
    import state_root
    import tickets

FRICTION_SUFFIX = ".jsonl"
MIGRATED_FROM = "migrated_from"
# The convention a record predates. Live writers stamp
# `tickets.SINK_CONVENTION`; a record that carries no convention at all
# was written before the field existed, and that is what this says. A
# record that already carries one keeps it — restamping would be a lie.
LEGACY_CONVENTION = 1


def _project_of(root: Path):
    """The project a directory belongs to, in item 03's three fields."""

    repo = state_root.find_repo_root(root)
    if repo is None:
        return None
    return {"root": str(repo), "origin": tickets._origin_url(repo), "name": repo.name}


def _project_label(project):
    return tickets._project_key(project) if isinstance(project, dict) else None


def _recorded_project(identity_path: Path):
    """The project a run's own identity document names, or ``None``.

    A document that is absent, unreadable or carries no project answers
    ``None`` — the caller falls back to the source's own project, which
    is a weaker answer to the same question, never a different one.
    """

    document, error = tickets._read_identity(identity_path)
    if error is not None or not isinstance(document, dict):
        return None
    project = document.get("project")
    if isinstance(project, dict) and (project.get("root") or project.get("origin")):
        return project
    return None


def _backfilled_project(cwd):
    """``(project, project_source)`` for a legacy entry, from its own ``cwd``.

    A directory that no longer resolves answers ``(None, "none")``. The
    entry says it does not know rather than naming a project it was
    never in: a guess here is indistinguishable from evidence later.
    """

    if not cwd or not isinstance(cwd, str):
        return None, friction.SOURCE_NONE
    try:
        path = Path(cwd).expanduser()
        if not path.exists():
            return None, friction.SOURCE_NONE
        project = _project_of(path)
    except OSError:
        return None, friction.SOURCE_NONE
    if project is None:
        return None, friction.SOURCE_NONE
    return project, friction.SOURCE_CWD


# --- line streams ------------------------------------------------------------


def _existing_lines(path: Path):
    """Every line the destination already holds, for identity deduplication.

    A destination that is not there yet holds nothing, which is a reading.
    One that is there and cannot be read is not: read as empty, every line
    the source holds is new, so the whole stream is queued and appended a
    second time under a payload reporting ``duplicates: 0``. The failure
    raises here and the planner names it, because the only two answers this
    tool may give about a destination are what it holds and that it could
    not be read.
    """

    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _migrated_friction_line(line: str, source_root: Path):
    """``(line, note)`` — one legacy entry, stamped and backfilled.

    A line that is not a JSON object is carried across exactly as it
    stands and reported: a stream's own record of a broken write is
    evidence too, and dropping it would be the one destructive act this
    tool exists to avoid.
    """

    try:
        entry = json.loads(line)
    except ValueError:
        return line, "unparsed"
    if not isinstance(entry, dict):
        return line, "unparsed"
    migrated = dict(entry)
    note = "stamped"
    if migrated.get("sink_convention") is None:
        migrated["sink_convention"] = LEGACY_CONVENTION
        if migrated.get("project") is None:
            project, source = _backfilled_project(entry.get("cwd"))
            migrated["project"] = project
            migrated["project_source"] = source
            note = "backfilled" if project is not None else "unattributed"
    migrated[MIGRATED_FROM] = str(source_root)
    return json.dumps(migrated, ensure_ascii=False), note


def _migrated_covered_line(line: str, source_root: Path, project):
    """``(line, note)`` — one coverage record, gaining the project it arose in."""

    try:
        entry = json.loads(line)
    except ValueError:
        return line, "unparsed"
    if not isinstance(entry, dict):
        return line, "unparsed"
    migrated = dict(entry)
    note = "stamped"
    if migrated.get("project") is None:
        migrated["project"] = project
        note = "backfilled" if project is not None else "unattributed"
    migrated[MIGRATED_FROM] = str(source_root)
    return json.dumps(migrated, ensure_ascii=False), note
