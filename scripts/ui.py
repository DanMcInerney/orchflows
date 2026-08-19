#!/usr/bin/env python3
"""Read-only loopback application for orchflows state and session metadata.

The installed immutable application is served offline from ``~/.orchflows/ui``
and the checkout uses its committed ``web/dist`` only as a development seam.
State-sink values are untrusted per ``rules/visibility.md`` §6: projections
carry a closed metadata set, JSON is safe for an HTML origin, and neither a
sink path nor ticket body reaches the application shell. The sink and any
configured transcript tree are opened read-only. Session projections expose
metadata and subagent structure only; Claude/Codex prompts, tool input, tool
output, file contents, command output, and conversation text remain behind a
hard content wall. The unauthenticated server binds ``127.0.0.1`` only,
accepts only GET/HEAD, enables no CORS, and applies restrictive local-reader
security headers to every response.

Usage:
    ui.py [--root <sink>] [--port <n>] [--transcripts <path>]
"""

from __future__ import annotations

import sys as _bootstrap_sys
from pathlib import Path as _BootstrapPath

_SIBLING_DIR = str(_BootstrapPath(__file__).resolve().parent)
if _SIBLING_DIR not in _bootstrap_sys.path:
    _bootstrap_sys.path.append(_SIBLING_DIR)

if __package__:
    from scripts import state_root
    from scripts.ui_model import *
    from scripts.ui_model import _facade_value, _in_tree, _now, _safe_name
else:
    import state_root
    from ui_model import *
    from ui_model import _facade_value, _in_tree, _now, _safe_name


def default_root():
    """Resolve the sink through its owner while retaining this patch seam."""

    return state_root.state_root()

def _svg_stroke(presentation: StatusPresentation) -> tuple:
    """``(stroke-width, stroke-dasharray)`` for one status's CSS border."""

    width, _, style = presentation.border.partition(" ")
    return width.replace("px", "").strip() or "1", SVG_DASH.get(style.strip(), "none")


def _status_css() -> str:
    """Derived from both presentation tables, so neither a ticket status nor
    a subagent's activity can carry one hue in the module and another in the
    stylesheet -- and so a state cannot be drawn in a class the stylesheet
    never declares, which renders as no state at all."""

    lines = [
        "  /* Hue tokens are names, not colours: the palette is the design",
        "     spec's deliverable. Until it lands every token resolves to the",
        "     inherited text colour, so this file asserts no colour at all. */",
        "  :root { " + " ".join("{0}: currentColor;".format(t) for t in HUE_TOKENS) + " }",
        "  .st { display: inline-block; padding: 0 .35rem; border-radius: .25rem;",
        "        white-space: nowrap; }",
        "  .st .glyph { font-style: normal; }",
    ]
    every = [STATUS_FALLBACK] + list(STATUS_PRESENTATION.values())
    every += [seen for seen in ACTIVITY_PRESENTATION.values() if seen not in every]
    for presentation in every:
        stroke_width, dash = _svg_stroke(presentation)
        lines.append(
            "  .st-{word} {{ border: {border} var({hue}); }}".format(
                word=presentation.word, border=presentation.border, hue=presentation.hue
            )
        )
        lines.append(
            "  .nd-{word} rect {{ stroke: var({hue}); stroke-width: {stroke_width};"
            " stroke-dasharray: {dash}; }}".format(
                word=presentation.word,
                hue=presentation.hue,
                stroke_width=stroke_width,
                dash=dash,
            )
        )
    return "\n".join(lines) + "\n"


# Structural only. Visual form is a later spec's deliverable; this is the
# minimum that keeps a table legible. Carried as a constant rather than a
# sidecar file because install.py's SCRIPT_NAMES ships flat filenames, so a
# sidecar asset would never reach ~/.orchflows/bin.
PAGE_CSS = (
    """
  body { margin: 0; font: 15px/1.5 system-ui, sans-serif; }
  main { max-width: 64rem; margin: 0 auto; padding: 1.5rem; }
  h1 { font-size: 1.2rem; }
  h2 { font-size: 1rem; margin-top: 1.75rem; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border-bottom: 1px solid #ccc; padding: .3rem .5rem;
           text-align: left; vertical-align: top; }
  th { font-weight: 600; white-space: nowrap; }
  .root { font-family: ui-monospace, monospace; font-size: .85rem; }
  .empty { font-style: italic; }
  pre { white-space: pre-wrap; margin: .25rem 0; font-size: .9rem; }
  .meta, .claim, .count, .back { margin: .25rem 0; }
  .count { font-size: .85rem; }
  .diagnostics { margin: .5rem 0; padding-left: 1.2rem; font-size: .9rem; }
  .band { list-style: none; margin: .5rem 0; padding: 0; }
  .band li { padding: .2rem 0; border-bottom: 1px solid #ccc; }
  .feed { list-style: none; margin: .5rem 0; padding: 0; }
  .entry, .event { padding: .4rem 0; border-bottom: 1px solid #ccc; }
  .entry p, .event p { margin: .1rem 0; }
  .ts { font-family: ui-monospace, monospace; font-size: .85rem; }
  .canvas { overflow: auto; max-width: 100%; }
  .graph { max-width: 100%; height: auto; }
  .graph .edge { stroke: currentColor; stroke-width: 1; fill: none; }
  .graph .arrow { fill: currentColor; }
  .graph rect { fill: none; }
  .graph text { font: 12px/1 ui-monospace, monospace; fill: currentColor; }
  .graph .nd-state { font-size: 11px; }
  .graph a { text-decoration: none; }
  /* An edge that is a guess is drawn like one. The page says so in words
     too: a dash pattern alone is not a channel a reader can decode. */
  .graph .edge-inferred { stroke-dasharray: 5 3; }
  /* The session flowchart's own node. It is not in an activity state, so
     it borrows no state's presentation. */
  .graph .nd-root rect { stroke: currentColor; stroke-width: 2; }
"""
    + _status_css()
)

# A ticket under one of these is a ticket something is about to happen to.
# Under every other status the run only moves once one of these does, so
# there is nothing for a one-second poll to catch. `suspended` holds the
# lease with nobody at the keyboard and belongs on the slow interval.
POLL_FAST_STATUSES = ("claimed", "ready")
POLL_LIVE_MS = 1000
POLL_IDLE_MS = 5000
POLL_HIDDEN_MS = 15000

# Inline for the same reason as the CSS: `install.py` ships flat filenames,
# so a sidecar asset would never reach ~/.orchflows/bin -- and a remote one
# is forbidden outright. Interpolated as a `.format` *value*, so its braces
# are never a format field.
_POLL_CONSTANTS = "  var LIVE_MS = {0}, IDLE_MS = {1}, HIDDEN_MS = {2};\n".format(
    POLL_LIVE_MS, POLL_IDLE_MS, POLL_HIDDEN_MS
)

PAGE_JS = (
    "\n(function () {\n"
    + _POLL_CONSTANTS
    + """  var tag = null;
  var timer = null;
  function delay() {
    if (document.hidden) { return HIDDEN_MS; }
    var here = document.querySelector('main');
    return here && here.dataset.live === 'yes' ? LIVE_MS : IDLE_MS;
  }
  function schedule() {
    window.clearTimeout(timer);
    // A timeout the answer reschedules, never a fixed repeating timer: a
    // slow answer must not queue the next request behind it, and the
    // stdlib server serves one at a time.
    timer = window.setTimeout(poll, delay());
  }
  function poll() {
    var headers = tag ? {'If-None-Match': tag} : {};
    window.fetch(window.location.href, {headers: headers}).then(function (r) {
      var seen = r.headers.get('ETag');
      if (seen) { tag = seen; }
      return r.status === 304 ? null : r.text();
    }).then(function (text) {
      if (text === null) { return; }
      var doc = new DOMParser().parseFromString(text, 'text/html');
      var fresh = doc.querySelector('main');
      var here = document.querySelector('main');
      if (fresh && here) { here.replaceWith(fresh); }
    }).catch(function () {
      // The viewer outlives the server it reads: keep the loop alive so a
      // restarted server is picked up without a manual reload.
    }).then(schedule);
  }
  document.addEventListener('visibilitychange', schedule);
  schedule();
})();
"""
)


# --- discovery ---------------------------------------------------------------


def ticket_href(run: str, ticket_id: str) -> str:
    """A same-origin relative link. Run and id are directory and file names
    from untrusted data, so both are percent-encoded whole -- nothing in
    them survives as URL structure -- and then escaped as markup."""

    return html.escape(
        "{route}?run={run}&id={id}".format(
            route=TICKET_ROUTE, run=quote(run, safe=""), id=quote(ticket_id, safe="")
        )
    )


def graph_href(run: str) -> str:
    return html.escape(
        "{route}?run={run}".format(route=GRAPH_ROUTE, run=quote(run, safe=""))
    )


def session_href(session_id: str) -> str:
    """A session id is a file name from another program's tree, so it is
    percent-encoded whole and then escaped as markup, like a ticket id."""

    return html.escape(
        "{route}?id={id}".format(route=SESSION_ROUTE, id=quote(session_id, safe=""))
    )


def anchor_href(anchor: str) -> str:
    """A link to a row on this same page."""

    return html.escape("#{0}".format(quote(anchor, safe="")))


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


def render_missing_session(session_id: str) -> str:
    """The id comes from the query string, so it is escaped before it is
    echoed back."""

    return _page(
        "not found",
        "<h1>not found</h1>\n<p>{empty}: {id}</p>\n"
        '<p class="back"><a href="{route}">all sessions</a></p>\n'.format(
            empty=html.escape(EMPTY_NO_SESSION),
            id=_cell(session_id, EMPTY_UNSET),
            route=SESSIONS_ROUTE,
        ),
    )


def render_missing_ticket(run: str, ticket_id: str) -> str:
    """Both values come from the query string, so both are escaped before
    they are echoed back."""

    return _page(
        "not found",
        "<h1>not found</h1>\n<p>no ticket {id} in run {run} under this root</p>\n"
        '<p class="back"><a href="/">all runs</a></p>\n'.format(
            id=_cell(ticket_id, EMPTY_UNSET), run=_cell(run, EMPTY_UNSET)
        ),
    )


def render_not_found(route: str) -> str:
    """The requested path is client-supplied, so it is escaped like any
    other untrusted value before it is echoed back."""

    return _page(
        "not found",
        "<h1>not found</h1>\n<p>no route serves {0}</p>\n".format(html.escape(route)),
    )


def render_route(start, path: str, transcripts=None) -> tuple:
    """``(status, html)`` for one request path. Pure: reads, never writes.

    ``transcripts`` is threaded rather than resolved: passing ``None`` reads
    no transcript at all, so nothing short of the entry point can reach the
    operator's real ``~/.claude/projects``.
    """

    parsed = urlsplit(path)
    if parsed.path == INDEX_ROUTE:
        return 200, render_index(discover(start))
    if parsed.path == TICKET_ROUTE:
        query = parse_qs(parsed.query)
        run = query.get("run", [""])[0]
        ticket_id = query.get("id", [""])[0]
        ticket = find_ticket(_resolve_root(start), run, ticket_id)
        if ticket is None:
            return 404, render_missing_ticket(run, ticket_id)
        return 200, render_ticket(run, ticket)
    if parsed.path == GRAPH_ROUTE:
        run = parse_qs(parsed.query).get("run", [""])[0]
        root = _resolve_root(start)
        tickets = run_tickets(root, run)
        if tickets is None:
            return 404, render_missing_run(run)
        return 200, render_graph(run, tickets, read_events(root, run))
    if parsed.path == FRICTION_ROUTE:
        return 200, render_friction(read_friction(_resolve_root(start)))
    if parsed.path == SESSIONS_ROUTE:
        return 200, render_sessions(read_sessions(transcripts))
    if parsed.path == SESSION_ROUTE:
        session_id = parse_qs(parsed.query).get("id", [""])[0]
        session = find_session(transcripts, session_id)
        if session is None:
            return 404, render_missing_session(session_id)
        return 200, render_session(read_session(session))
    return 404, render_not_found(parsed.path)


# --- conditional requests ----------------------------------------------------

# Walked for their contents. The sink root itself is observed for its
# presence alone: `discover` renders a different named empty state for "no
# sink at all" than for "a sink carrying neither tickets nor friction", so a
# digest that could not tell the two apart would answer 304 across the very
# transition a viewer left open before the first write is waiting for.

if __package__:
    from scripts import ui_render as _render_impl
    from scripts import ui_server as _server_impl
    from scripts.ui_sessions import *
    from scripts.ui_sessions import _make_room, _stat_identity, _transcript_summary
    from scripts.ui_discovery import *
    from scripts.ui_discovery import _project_directories, _resolve_root
    from scripts.ui_layout import *
    from scripts.ui_render import *
    from scripts.ui_render import _cell, _meter, _page, _stamp
    from scripts.ui_server import *
else:
    import ui_render as _render_impl
    import ui_server as _server_impl
    from ui_sessions import *
    from ui_sessions import _make_room, _stat_identity, _transcript_summary
    from ui_discovery import *
    from ui_discovery import _project_directories, _resolve_root
    from ui_layout import *
    from ui_render import *
    from ui_render import _cell, _meter, _page, _stamp
    from ui_server import *


def cached_layout(node_ids, edges) -> dict:
    """The shared cache wrapper retained at the public compatibility seam."""

    key = layout_key(node_ids, edges)
    layout = LAYOUT_CACHE.get(key)
    if layout is None:
        layout = graph_layout(node_ids, edges)
        _make_room(LAYOUT_CACHE, LAYOUT_CACHE_LIMIT)
        LAYOUT_CACHE[key] = layout
    return layout


def render_graph(run: str, tickets, events=None) -> str:
    cached_layout(*graph_input(tickets))
    return _server_impl.render_graph(run, tickets, events)


def render_session(session: dict) -> str:
    nodes, edges, _ = session_graph(session["agents"])
    cached_layout(nodes, edges)
    return _render_impl.render_session(session)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=None,
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
        server = create_server(root, args.port, transcript_root(args.transcripts))
    except OSError as error:
        print("cannot bind port {0}: {1}".format(args.port, error), file=sys.stderr)
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


if __name__ == "__main__":
    raise SystemExit(main())
