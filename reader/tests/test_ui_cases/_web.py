"""Shared HTML, route, clock, and server helpers."""

from reader.tests.test_ui_cases._base import *  # noqa: F401,F403
def row_for(page: str, ticket_id: str) -> str:
    """The table row carrying ``ticket_id``, so a field is proved to sit
    with its own ticket rather than merely somewhere on the page."""

    for fragment in page.split("<tr")[1:]:
        row = fragment.split("</tr>")[0]
        if ">{0}<".format(ticket_id) in row:
            return row
    return ""


# The id is a link now that `/session` exists, and an empty cell is still a
# cell: both shapes have to reach `session_ids` or an ordering assertion
# quietly stops seeing rows.
SESSION_ID_RE = re.compile(r'<td class="sid">(?:<a [^>]*>)?([^<]*)')


def session_ids(page: str) -> list:
    """The session index's rows, in the order it drew them."""

    return SESSION_ID_RE.findall(page)


def session_cell(page: str, session: str, name: str) -> str:
    """One named cell of one session's own row.

    The page inlines its own stylesheet and its own script, so a substring
    search over it is weak in both directions -- `U3`'s `node_for` exists
    for the same reason.
    """

    row = row_for(page, session)
    found = re.search(r'<td class="{0}">(.*?)</td>'.format(name), row, re.S)
    return found.group(1) if found else ""


ROW_COLUMN_RE = re.compile(r'<td class="([a-z-]+)"')


def row_columns(page: str, row_id: str) -> list:
    """The column names one rendered row actually carried, in order.

    Read off the page rather than off the constant that is supposed to fix
    it: a cell written beside the closed renderable set is invisible to a
    guard that only ever reads the set.
    """

    return ROW_COLUMN_RE.findall(row_for(page, row_id))


def block_for(page: str, class_name: str, close: str = "</section>") -> str:
    """The element carrying ``class_name``, so an assertion about one part
    of the page cannot be satisfied by another part of it."""

    fragments = page.split('class="{0}"'.format(class_name))[1:]
    return fragments[0].split(close)[0] if fragments else ""


def detail_url(run: str, ticket_id: str) -> str:
    return "/ticket?run={0}&id={1}".format(run, ticket_id)


def graph_url(run: str) -> str:
    return "/graph?run={0}".format(run)


def session_url(session: str) -> str:
    return "/session?id={0}".format(session)


NODE_RE = re.compile(
    r'<g class="nd (nd-[a-z]+)"[^>]*>.*?<text class="nd-id"[^>]*>([^<]+)</text>'
)


def node_for(page: str, ticket_id: str) -> str:
    """The status class the graph drew on ``ticket_id``'s own node. Every
    status name also appears in the stylesheet, so a bare substring search
    over the page proves nothing about what was drawn."""

    for status_class, drawn in NODE_RE.findall(page):
        if drawn == ticket_id:
            return status_class
    return ""


SESSION_NODE_RE = re.compile(
    r'<a href="#(?P<anchor>[^"]*)" aria-label="(?P<label>[^"]*)">'
    r'<g class="nd (?P<state>nd-[a-z-]+)"[^>]*>(?P<body>.*?)</g></a>',
    re.S,
)
INFERRED_EDGE_RE = re.compile(r'<line class="edge edge-inferred"')
EDGE_RE = re.compile(r'<line class="edge')


def session_anchors(page: str) -> list:
    """What the flowchart drew, in order, by the row each node links to."""

    return [found.group("anchor") for found in SESSION_NODE_RE.finditer(page)]


def session_node(page: str, anchor: str) -> dict:
    """One flowchart node by the row it links to: its state class, its
    accessible label and the text drawn inside it. Every state word also
    appears in the stylesheet and every label also appears in the table, so
    a substring search over the page proves nothing about what was drawn."""

    for found in SESSION_NODE_RE.finditer(page):
        if found.group("anchor") == anchor:
            return found.groupdict()
    return {}


def section_for(page: str, run: str) -> str:
    for fragment in page.split('<section class="run">')[1:]:
        body = fragment.split("</section>")[0]
        if ">{0}<".format(run) in body:
            return body
    return ""


# A bare route name exercises almost none of a route's behaviour: `/ticket`
# with no query is the one branch that never reads a file. Each served route
# is paired with the concrete URLs that reach its real work, so the whole-page
# guarantees -- writes nothing, fetches nothing -- are proved where the page
# is actually built.
ROUTE_EXAMPLES = {
    ui.INDEX_ROUTE: ("/",),
    ui.TICKET_ROUTE: (
        "/ticket",
        detail_url("run-gamma", "G1"),
        detail_url("run-gamma", "G6"),
        detail_url("run-gamma", "G7"),
        detail_url("run-gamma", "no-such-ticket"),
        detail_url("run-empty", "G1"),
    ),
    ui.GRAPH_ROUTE: (
        "/graph",
        graph_url(SETTLED_RUN),
        graph_url(CYCLIC_RUN),
        graph_url("run-gamma"),
        graph_url(EMPTY_RUN),
        graph_url("no-such-run"),
    ),
    ui.FRICTION_ROUTE: ("/friction",),
    ui.SESSIONS_ROUTE: ("/sessions",),
    ui.SESSION_ROUTE: (
        "/session",
        session_url(TITLED_SESSION),
        session_url(MARKUP_SESSION),
        session_url(TRUNCATED_SESSION),
        session_url(UNTITLED_SESSION),
        session_url(EMPTY_SESSION),
        session_url("no-such-session"),
    ),
}


def every_route() -> tuple:
    """Every served route by concrete example, plus one that is not served,
    so the 404 page is held to the same guarantees as the index."""

    urls = tuple(url for route in ui.ROUTES for url in ROUTE_EXAMPLES.get(route, ()))
    return urls + ("/no-such-route",)


# `run-gamma/G4.md` is claimed at this instant with a 90m bound: the only
# fixture from which an elapsed meter may be drawn.
CLAIMED_AT = datetime(2026, 1, 1, 0, 20, 0, tzinfo=timezone.utc)
FROZEN_NOW = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)


@contextlib.contextmanager
def frozen_clock(now=FROZEN_NOW):
    """Hold the reader's clock still.

    A live elapsed meter is an input to the page and therefore to the
    validator the page is served under, so two requests straddling a minute
    boundary honestly disagree. A test about an unchanged *directory* must
    not also be a test about the second it happened to run in.
    """

    with patch.object(ui, "_now", return_value=now):
        yield


def freeze(case, now=FROZEN_NOW):
    """`frozen_clock` for a whole case, for the cases whose every assertion
    spans two requests."""

    stack = contextlib.ExitStack()
    case.addCleanup(stack.close)
    stack.enter_context(frozen_clock(now))


@contextlib.contextmanager
def serving(root: Path, transcripts=None):
    """The real server on an ephemeral loopback port.

    ``transcripts`` is passed explicitly or not at all: the reader resolves
    the `~/.claude/projects` default in `main` alone, so a caller that omits
    it gets the named empty state rather than the operator's real tree.
    """

    server = ui.create_server(root, 0, transcripts)
    # `serve_forever`'s default 0.5s poll interval is what `shutdown` below
    # waits out, once per server: the poll period, not the work, dominated
    # this module's wall time.
    thread = threading.Thread(target=server.serve_forever, args=(0.01,))
    thread.daemon = True
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def write_ticket(run_dir: Path, ticket_id: str, **fields) -> Path:
    """One ticket with exactly the frontmatter a test names, for cases the
    shared fixtures deliberately do not carry."""

    run_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "id: {0}".format(ticket_id)]
    lines.extend("{0}: {1}".format(key, value) for key, value in fields.items())
    lines.extend(["---", ""])
    path = run_dir / "{0}.md".format(ticket_id)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def request(server, route: str, method="GET", headers=None) -> tuple:
    """``(status, headers, body)`` over the real socket."""

    host, port = server.server_address[0], server.server_address[1]
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.request(method, route, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.headers, response.read().decode("utf-8")
    finally:
        connection.close()


def fetch(server, route: str, headers=None) -> tuple:
    return request(server, route, headers=headers)


def get(server, route: str) -> tuple:
    status, _headers, body = fetch(server, route)
    return status, body


def snapshot(tree: Path) -> dict:
    """Name, size and mtime of every entry under ``tree``, recursively."""

    entries = {}
    for path in sorted(tree.rglob("*")):
        stat = path.stat()
        key = path.relative_to(tree).as_posix()
        entries[key] = (path.is_dir(), stat.st_size, stat.st_mtime_ns)
    return entries


def coordinates(layout: dict) -> bytes:
    """Render graph-layout coordinates as bytes for identity comparisons."""

    return "\n".join(
        "{0} {1} {2} {3} {4}".format(node.id, node.layer, node.order, node.x, node.y)
        for node in layout["nodes"]
    ).encode("utf-8")


def fan_graph(width: int) -> tuple:
    """One root, ``width`` middles, and one sink."""

    ids = ("R",) + tuple("M{0}".format(i) for i in range(width)) + ("S",)
    edges = tuple(("R", "M{0}".format(i)) for i in range(width))
    edges += tuple(("M{0}".format(i), "S") for i in range(width))
    return ids, edges


def write_raw_ticket(run_dir: Path, file_name: str, declared_id: str, **fields) -> Path:
    """Write a ticket whose filename and declared identity may disagree."""

    run_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "id: {0}".format(declared_id)]
    lines.extend("{0}: {1}".format(key, value) for key, value in fields.items())
    lines.extend(["---", ""])
    path = run_dir / file_name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
