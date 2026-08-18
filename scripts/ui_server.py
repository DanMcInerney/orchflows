"""Route rendering, validators, and the loopback HTTP server."""

from __future__ import annotations

try:
    from scripts.ui_model import *
    from scripts.ui_model import _facade_value, _in_tree, _parse_frontmatter, _safe_name, _scalar
    from scripts.ui_sessions import *
    from scripts.ui_discovery import *
    from scripts.ui_discovery import _plural, _resolve_root
    from scripts.ui_layout import *
    from scripts.ui_render import *
    from scripts.ui_render import _cell, _meter, _page
except ImportError:
    from ui_model import *
    from ui_model import _facade_value, _in_tree, _parse_frontmatter, _safe_name, _scalar
    from ui_sessions import *
    from ui_discovery import *
    from ui_discovery import _plural, _resolve_root
    from ui_layout import *
    from ui_render import *
    from ui_render import _cell, _meter, _page

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
        render_diagnostics([DIAGNOSTIC_UNREADABLE] if log.get("unreadable") else []),
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
        render_diagnostics(
            [
                "{0}: {1}".format(DIAGNOSTIC_UNREADABLE, name)
                for name in log["unreadable"]
            ]
        ),
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
    elif not log["skipped"] and not log["unreadable"]:
        # With skipped lines or an unread month the lines above already say a
        # log was found and what became of it; claiming there is none would
        # be the wrong story.
        body.append('<p class="empty">{0}</p>\n'.format(html.escape(EMPTY_NO_FRICTION)))
    body.append('<p class="back"><a href="/">all runs</a></p>\n')
    return _page("friction", "".join(body))


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
            # The index and the run page name an unread ticket through
            # `identity_diagnostics`; this page is where a reader lands from
            # either, and "unset" with no sections is what an empty one draws.
            render_diagnostics(
                [DIAGNOSTIC_UNREADABLE] if ticket.get("unreadable") else []
            ),
            render_claim(ticket),
            render_sections(ticket["sections"]),
            '<p class="back"><a href="/">all runs</a></p>\n',
        ]
    )
    return _page("{0} · {1}".format(ticket["id"], run), body, [ticket])


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
    status, page = _facade_value("render_route", None)(root, path, transcripts)
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
        server = _facade_value("create_server", create_server)(
            root, args.port, transcript_root(args.transcripts)
        )
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
