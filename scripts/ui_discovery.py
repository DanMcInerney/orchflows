"""State-sink and transcript discovery."""

from __future__ import annotations

try:
    from scripts.ui_model import *
    from scripts.ui_model import _facade_value, _in_tree, _json_object, _parse_iso, _safe_name, _scalar
    from scripts.ui_sessions import *
    from scripts.ui_sessions import _agent_count, _label_session, _stat_identity, _subagent_files, _subagent_identities
except ImportError:
    from ui_model import *
    from ui_model import _facade_value, _in_tree, _json_object, _parse_iso, _safe_name, _scalar
    from ui_sessions import *
    from ui_sessions import _agent_count, _label_session, _stat_identity, _subagent_files, _subagent_identities

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
    """Every ticket in one safely resolved run, or ``None``."""

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
    paths = (_in_tree(run_dir, path.name) for path in sorted(run_dir.glob("*" + TICKET_SUFFIX)))
    return [read_ticket(path) for path in paths if path is not None]
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
    """Every place a run's tickets disagree about their own identity, and
    every one the walk found and could not read."""

    diagnostics = [
        "{0}: {1}{2}".format(
            DIAGNOSTIC_UNREADABLE, ticket["file_id"], TICKET_SUFFIX
        )
        for ticket in tickets
        if ticket.get("unreadable")
    ]
    diagnostics += [
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
FRICTION_KEYS = ("ts", "observed", "expected", "host")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _stamp_order(entry: dict) -> tuple:
    """Newest first. An entry whose ``ts`` will not parse sorts last rather
    than jumping the queue on a string comparison."""

    stamp = _parse_iso(_scalar(entry.get("ts")))
    return (stamp is not None, stamp or _EPOCH)


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
    the lines that could not be read as one and the names of the month
    files that could not be read at all."""

    directory = _in_tree(Path(root), *FRICTION_DIR)
    entries = []
    skipped = 0
    unreadable = []
    entries_on_disk = sorted(directory.glob("*" + JSONL_SUFFIX)) if directory is not None and directory.is_dir() else ()
    for entry_path in entries_on_disk:
        path = _in_tree(directory, entry_path.name)
        if path is None:
            unreadable.append(entry_path.name)
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Unreadable this poll; the next one tries again -- but a whole
            # month dropping out of the feed with no note reads as a month
            # with no friction in it, which is the one thing this log exists
            # to disprove.
            unreadable.append(path.name)
            continue
        skipped += _read_jsonl(text, entries)
    entries.sort(key=_stamp_order, reverse=True)
    return {"entries": entries, "skipped": skipped, "unreadable": unreadable}


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
        # documented answer for an absent log, and this is not that -- nor
        # is "0 events", which is what an empty payload draws.
        return {"entries": [], "skipped": 0, "unreadable": True}
    entries = []
    skipped = _read_jsonl(text, entries)
    entries.sort(key=_stamp_order, reverse=True)
    return {"entries": entries, "skipped": skipped, "unreadable": False}


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
            candidates = (_in_tree(tickets_root, p.name) for p in tickets_root.iterdir())
            for run_dir in sorted(p for p in candidates if p is not None and p.is_dir()):
                ticket_paths = (_in_tree(run_dir, p.name) for p in sorted(run_dir.glob("*.md")))
                runs.append(
                    {
                        "run": run_dir.name,
                        "tickets": [read_ticket(p) for p in ticket_paths if p is not None],
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
        present, refused = root.is_dir(), False
    except OSError:
        # "no transcript root at this path" is a fact about the path; a
        # listing the host refused is a fact about this poll, and an
        # operator can act on exactly one of them.
        present, refused = False, True
    if not present:
        return {
            "root": root,
            "present": False,
            "projects": (),
            "sessions": [],
            "unaddressable": (),
            "diagnostics": [DIAGNOSTIC_UNREADABLE] if refused else [],
            "empty": EMPTY_NO_TRANSCRIPTS,
        }
    projects = _project_directories(root)
    sessions = []
    unaddressable = []
    diagnostics = []
    for project in projects:
        cwd = decode_slug(project.name)
        if not cwd:
            # The legacy page needs the local entry identity to explain what could not be decoded.
            # Browser projections sanitize this diagnostic at their own boundary.
            diagnostics.append("{0}: {1}".format(DIAGNOSTIC_UNDECODABLE_SLUG, project.name))
        transcript_paths = (_in_tree(project, path.name) for path in sorted(project.glob("*" + JSONL_SUFFIX)))
        for path in (path for path in transcript_paths if path is not None and path.is_file()):
            identity = _facade_value("_stat_identity", _stat_identity)(path)
            if identity is None:
                # A session the walk found and the path layer will not
                # describe. Dropping the row silently leaves a shorter
                # listing that looks complete.
                diagnostics.append(
                    "{0}: {1}".format(DIAGNOSTIC_UNREADABLE, path.name)
                )
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


def read_sessions(transcripts=None) -> dict:
    """Every session under one transcript root, labelled.

    ``discover_sessions`` lists; this labels. The parse is the expensive
    half and it is cached on each transcript's stat identity, so a poll over
    an unchanged root costs one directory listing and no parse at all.
    """

    found = _facade_value("discover_sessions", discover_sessions)(transcripts)
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
    for session in _facade_value("discover_sessions", discover_sessions)(transcripts)[
        "sessions"
    ]:
        if session["id"] == session_id:
            return session
    return None


def _plural(count: int, singular: str, plural: str) -> str:
    return "{0} {1}".format(count, singular if count == 1 else plural)


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
                href=_facade_value("ticket_href", None)(claim["run"], ticket["id"]),
                id=html.escape(ticket["id"]),
                run=html.escape(claim["run"]),
                executor=_facade_value("_cell", None)(ticket["executor"], EMPTY_UNSET),
                claimed_by=_facade_value("_cell", None)(ticket["claimed_by"], EMPTY_UNSET),
                meter=_facade_value("_meter", None)(ticket),
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
                name=html.escape(run["run"]),
                href=_facade_value("graph_href", None)(run["run"]),
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
                        href=_facade_value("ticket_href", None)(
                            run["run"], ticket["id"]
                        ),
                        id=html.escape(ticket["id"]),
                        status=_facade_value("render_status", None)(ticket["status"]),
                        executor=_facade_value("_cell", None)(ticket["executor"], EMPTY_UNSET),
                        objective=_facade_value("_cell", None)(ticket["objective"], EMPTY_NO_OBJECTIVE),
                    )
                )
            parts.append("</tbody>\n</table>\n")
        parts.append("</section>\n")
    return _facade_value("_page", None)(
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
