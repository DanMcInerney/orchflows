"""HTML and SVG rendering primitives and session views."""

from __future__ import annotations

try:
    from scripts.ui_model import *
    from scripts.ui_model import _facade_value
    from scripts.ui_sessions import *
    from scripts.ui_discovery import *
    from scripts.ui_discovery import _plural
    from scripts.ui_layout import *
    from scripts.ui_layout import _agent_parent
except ImportError:
    from ui_model import *
    from ui_model import _facade_value
    from ui_sessions import *
    from ui_discovery import *
    from ui_discovery import _plural
    from ui_layout import *
    from ui_layout import _agent_parent

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

    fast_statuses = _facade_value("POLL_FAST_STATUSES", ())
    return any(ticket["status"] in fast_statuses for ticket in tickets)


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
        css=_facade_value("PAGE_CSS", ""),
        live="yes" if is_live(tickets) else "no",
        body=body,
        js=_facade_value("PAGE_JS", ""),
    )


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
                    _facade_value("SESSION_COLUMNS", SESSION_COLUMNS),
                    {
                        "sid": '<a href="{href}">{sid}</a>'.format(
                            href=_facade_value("session_href", None)(session["id"]),
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
                href=_facade_value("anchor_href", None)(face["anchor"]),
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
                _facade_value("AGENT_COLUMNS", AGENT_COLUMNS),
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
                    "when": html.escape(
                        DIAGNOSTIC_UNREADABLE
                        if agent["modified"] is None
                        else _stamp(agent["modified"])
                    ),
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
