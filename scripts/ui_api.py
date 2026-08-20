"""Frozen read-only JSON projections and the Starlette reader application."""

from __future__ import annotations

import hashlib
import json
import socket
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

try:
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    from starlette.requests import Request
    from starlette.responses import RedirectResponse, Response
    from starlette.routing import Route
except ModuleNotFoundError:  # The installed CLI runs under the private runtime.
    uvicorn = Starlette = Middleware = BaseHTTPMiddleware = None
    TrustedHostMiddleware = Request = RedirectResponse = Response = Route = None

try:
    from scripts import (
        ui_friction_projection,
        ui_now_projection,
        ui_runs_projection,
        ui_sessions_projection,
        ui_workflows_projection,
    )
    from scripts.ui_assets import FallbackReaderServer, read_asset, resolve_asset_root, valid_host_headers
    from scripts.ui_discovery import (
        discover,
        find_session,
        find_ticket,
        graph_input,
        identity_diagnostics,
        read_events,
        read_friction,
        read_sessions,
        run_tickets,
    )
    from scripts.ui_model import ACTIVE_STATUS, _safe_name, parse_verification
    from scripts.ui_layout import graph_layout
    from scripts.ui_sessions import read_session
    from scripts.ui_experience import SPA_ROUTE_PATTERNS, browser_navigation, is_spa_path, project_experience
except ImportError:
    import ui_friction_projection
    import ui_now_projection
    import ui_runs_projection
    import ui_sessions_projection
    import ui_workflows_projection
    from ui_assets import FallbackReaderServer, read_asset, resolve_asset_root, valid_host_headers
    from ui_discovery import (
        discover,
        find_session,
        find_ticket,
        graph_input,
        identity_diagnostics,
        read_events,
        read_friction,
        read_sessions,
        run_tickets,
    )
    from ui_model import ACTIVE_STATUS, _safe_name, parse_verification
    from ui_layout import graph_layout
    from ui_sessions import read_session
    from ui_experience import SPA_ROUTE_PATTERNS, browser_navigation, is_spa_path, project_experience

API_VERSION = "v1"
JSON_TYPE = "application/json; charset=utf-8"
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; connect-src 'self'; "
        "font-src 'self'; frame-ancestors 'none'; img-src 'self' data:; "
        "object-src 'none'; script-src 'self'; style-src 'self'; worker-src 'self'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}

PROJECTOR_MODULES = (
    ui_now_projection,
    ui_runs_projection,
    ui_workflows_projection,
    ui_sessions_projection,
    ui_friction_projection,
)


def _projector_route_specs(modules=None) -> tuple:
    """Bind each pure domain table while refusing ambiguous HTTP ownership."""

    modules = PROJECTOR_MODULES if modules is None else modules
    assembled = []
    seen = set()
    for module in modules:
        for method, path, function_name in module.ROUTE_SPECS:
            key = (method, path)
            if key in seen:
                raise ValueError(
                    "duplicate projection route {0} {1}".format(method, path)
                )
            seen.add(key)
            assembled.append((method, path, module, function_name))
    return tuple(assembled)


def _ticket_record(ticket: dict) -> dict:
    verification = parse_verification(ticket["sections"].get("Verification", ""))
    return {
        "id": ticket["id"],
        "status": ticket["status"],
        "executor": ticket["executor"],
        "bound": ticket["bound"],
        "claimed_at": ticket["claimed_at"],
        "claimed_by": ticket["claimed_by"],
        "depends_on": list(ticket["depends_on"]),
        "evidence": {
            "state": verification["state"],
            "entries": len(verification["rows"]),
        },
        "source": {"file_id": ticket["file_id"], "unreadable": ticket["unreadable"]},
    }
def _run_record(root: Path, run: str, tickets: list) -> dict:
    nodes = [
        {"id": ticket["id"], "label": ticket["id"], "status": ticket["status"]}
        for ticket in tickets
    ]
    layout = graph_layout(*graph_input(tickets))
    edges = [
        {
            "id": "{0}->{1}".format(source, target),
            "source": source,
            "target": target,
        }
        for source, target in layout["edges"]
    ]
    events = read_events(root, run)
    return {
        "api_version": API_VERSION,
        "run": run,
        "active": any(ticket["status"] == ACTIVE_STATUS for ticket in tickets),
        "nodes": nodes,
        "edges": edges,
        "diagnostics": identity_diagnostics(tickets) + layout["diagnostics"],
        "events": {
            "present": events is not None,
            "entries": len(events["entries"]) if events else 0,
            "skipped": events["skipped"] if events else 0,
            "unreadable": bool(events and events["unreadable"]),
        },
    }
def project_runs(root: Path) -> dict:
    found = discover(root)
    runs = []
    for item in found["runs"]:
        counts = Counter(ticket["status"] for ticket in item["tickets"])
        runs.append(
            {
                "id": item["run"],
                "ticket_count": len(item["tickets"]),
                "active": bool(counts.get(ACTIVE_STATUS)),
                "statuses": dict(sorted(counts.items())),
            }
        )
    return {"api_version": API_VERSION, "runs": runs, "empty": found["empty"]}
def project_run(root: Path, run: str):
    tickets = run_tickets(root, run)
    return None if tickets is None else _run_record(root, run, tickets)
def project_ticket(root: Path, run: str, ticket_id: str):
    ticket = find_ticket(root, run, ticket_id)
    if ticket is None:
        return None
    friction = read_friction(root)
    linked = sum(
        1
        for entry in friction["entries"]
        if entry.get("run") == run and entry.get("ticket") == ticket_id
    )
    return {
        "api_version": API_VERSION,
        "run": run,
        "ticket": _ticket_record(ticket),
        "linked_friction": linked,
        "friction_health": {
            "skipped": friction["skipped"],
            "unreadable": list(friction["unreadable"]),
        },
    }
def project_friction(root: Path) -> dict:
    log = read_friction(root)
    return {
        "api_version": API_VERSION,
        "entries": len(log["entries"]),
        "skipped": log["skipped"],
        "unreadable": len(log["unreadable"]),
    }
def _session_record(session: dict) -> dict:
    return {
        "id": session["id"],
        "title": session.get("title", ""),
        "modified": session["modified"],
        "size": session["size"],
        "agent_count": session["agent_count"],
        "diagnostics": list(session.get("diagnostics", ())),
    }
def project_sessions(transcripts) -> dict:
    found = read_sessions(transcripts)
    return {
        "api_version": API_VERSION,
        "sessions": [_session_record(item) for item in found["sessions"]],
        "diagnostics": list(found["diagnostics"]),
        "empty": found["empty"],
    }
def project_session(transcripts, session_id: str):
    found = find_session(transcripts, session_id)
    if found is None:
        return None
    session = read_session(found)
    projected = _session_record(session)
    projected["agents"] = [
        {
            "id": agent["id"],
            "type": agent["type"],
            "depth": agent["depth"],
            "parent": agent["parent"],
            "modified": agent["modified"],
            "state": agent["state"],
            "evidence": agent["evidence"],
            "unreadable": agent["unreadable"],
        }
        for agent in session["agents"]
    ]
    return {"api_version": API_VERSION, "session": projected}
def project_observe(root: Path, requested_run: str) -> dict:
    found = discover(root)
    names = [item["run"] for item in found["runs"]]
    selected = requested_run if requested_run in names else ""
    if not selected:
        selected = next(
            (
                item["run"]
                for item in found["runs"]
                if any(ticket["status"] == ACTIVE_STATUS for ticket in item["tickets"])
            ),
            names[0] if names else "",
        )
    graph = project_run(root, selected) if selected else None
    nodes, edges, active = [], [], False
    if graph is not None:
        nodes, edges, active = graph["nodes"], graph["edges"], graph["active"]
    basis = {"active": active, "nodes": nodes, "edges": edges}
    revision = hashlib.sha256(_json_bytes(basis)).hexdigest()
    return {"revision": revision, **basis}


def _json_bytes(value) -> bytes:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    encoded = encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return encoded.encode("utf-8")


def _etag_matches(header: str, etag: str) -> bool:
    if not header:
        return False
    sent = [item.strip() for item in header.split(",") if item.strip()]
    target = etag[2:] if etag.startswith("W/") else etag
    return "*" in sent or any(
        (item[2:] if item.startswith("W/") else item) == target for item in sent
    )


def _bytes_response(request: Request, body: bytes, media_type: str, cache: str, tag=None):
    etag = tag or '"{0}"'.format(hashlib.sha256(body).hexdigest())
    headers = {"Cache-Control": cache, "ETag": etag}
    if _etag_matches(request.headers.get("If-None-Match", ""), etag):
        return Response(status_code=304, headers=headers)
    headers["Content-Length"] = str(len(body))
    return Response(body, media_type=media_type, headers=headers)


def _json_response(request: Request, value, status=200):
    if status != 200:
        return Response(_json_bytes(value), status_code=status, media_type="application/json")
    return _bytes_response(request, _json_bytes(value), JSON_TYPE, "no-cache")


def _context(request: Request):
    return request.app.state.root, request.app.state.transcripts


async def runs_endpoint(request: Request):
    return _json_response(request, project_runs(_context(request)[0]))


async def run_endpoint(request: Request):
    root, _ = _context(request)
    run = request.path_params["run"]
    value = project_run(root, run)
    return _json_response(request, value if value is not None else {"error": "not found"}, 200 if value is not None else 404)


async def ticket_endpoint(request: Request):
    root, _ = _context(request)
    value = project_ticket(root, request.path_params["run"], request.path_params["ticket"])
    return _json_response(request, value if value is not None else {"error": "not found"}, 200 if value is not None else 404)


async def friction_endpoint(request: Request):
    return _json_response(request, project_friction(_context(request)[0]))


async def sessions_endpoint(request: Request):
    return _json_response(request, project_sessions(_context(request)[1]))


async def session_endpoint(request: Request):
    value = project_session(_context(request)[1], request.path_params["session"])
    return _json_response(request, value if value is not None else {"error": "not found"}, 200 if value is not None else 404)


async def observe_endpoint(request: Request):
    return _json_response(request, project_observe(_context(request)[0], request.query_params.get("run", "")))


async def experience_endpoint(request: Request):
    root, transcripts = _context(request)
    return _json_response(request, project_experience(root, transcripts, dict(request.query_params)))


def _starlette_projector_routes():
    endpoints = {
        (ui_now_projection, "project_observe"): observe_endpoint,
        (ui_runs_projection, "project_runs"): runs_endpoint,
        (ui_runs_projection, "project_run"): run_endpoint,
        (ui_runs_projection, "project_ticket"): ticket_endpoint,
        (ui_sessions_projection, "project_sessions"): sessions_endpoint,
        (ui_sessions_projection, "project_session"): session_endpoint,
        (ui_friction_projection, "project_friction"): friction_endpoint,
    }
    return [
        Route(path, endpoints[(module, function_name)], methods=[method])
        for method, path, module, function_name in _projector_route_specs()
    ]


async def index_endpoint(request: Request):
    asset = read_asset(request.app.state.assets, "index.html")
    if asset is None:
        return Response("reader application unavailable", status_code=503)
    return _bytes_response(request, asset[0], asset[1], "no-cache", asset[2])


async def spa_endpoint(request: Request):
    if browser_navigation(request.url.path, request.headers):
        return await index_endpoint(request)
    return await legacy_endpoint(request)


async def asset_endpoint(request: Request):
    asset = read_asset(request.app.state.assets, "assets/" + request.path_params["asset"])
    if asset is None:
        return Response("not found", status_code=404)
    return _bytes_response(
        request, asset[0], asset[1], "public, max-age=31536000, immutable", asset[2]
    )


def _legacy_location(path: str, query, root=None, transcripts=None) -> str:
    if path == "/ticket":
        run, ticket = query.get("run", ""), query.get("id", "")
        if root is not None and find_ticket(root, run, ticket) is not None:
            return "/?run={0}&ticket={1}".format(quote(run, safe=""), quote(ticket, safe=""))
    elif path == "/graph":
        run = query.get("run", "")
        if root is not None and run_tickets(root, run) is not None:
            return "/?run={0}".format(quote(run, safe=""))
    elif path == "/session":
        session = query.get("id", "")
        if find_session(transcripts, session) is not None:
            return "/?session={0}".format(quote(session, safe=""))
    elif path == "/sessions":
        return "/?view=sessions"
    elif path == "/friction":
        return "/?view=friction"
    return ""


async def legacy_endpoint(request: Request):
    responder = request.app.state.legacy_respond
    if responder is None:
        return Response("not found", status_code=404)
    target = request.url.path
    if request.url.query:
        target += "?" + request.url.query
    root, transcripts = _context(request)
    status, tag, page = responder(
        root, target, request.headers.get("If-None-Match"), transcripts
    )
    headers = {"Cache-Control": "no-cache"}
    if tag:
        headers["ETag"] = tag
    return Response(page, status_code=status, media_type="text/html", headers=headers)


if BaseHTTPMiddleware is not None:
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            for name, value in SECURITY_HEADERS.items():
                response.headers[name] = value
            return response
else:
    SecurityHeadersMiddleware = None


def create_application(root, transcripts=None, assets=None, legacy_respond=None):
    if Starlette is None:
        raise RuntimeError("Starlette is available only in the installed private runtime")
    routes = [
        *_starlette_projector_routes(),
        Route("/api/v1/experience", experience_endpoint, methods=["GET"]),
        Route("/assets/{asset:path}", asset_endpoint, methods=["GET"]),
        *[Route(pattern, spa_endpoint, methods=["GET"]) for pattern in SPA_ROUTE_PATTERNS],
        Route("/{path:path}", legacy_endpoint, methods=["GET"]),
    ]
    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(SecurityHeadersMiddleware),
            Middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"]),
        ],
    )
    app.state.root = Path(root).resolve()
    app.state.transcripts = transcripts
    app.state.assets = resolve_asset_root() if assets is None else Path(assets).resolve()
    app.state.legacy_respond = legacy_respond
    return app


def _fallback_response(status, body=b"", media_type="text/plain; charset=utf-8", cache="no-cache", request_headers=None, tag=None, extra=None):
    tag = tag or ('"{0}"'.format(hashlib.sha256(body).hexdigest()) if status < 400 else "")
    headers = {"Cache-Control": cache, "Content-Type": media_type}
    if tag:
        headers["ETag"] = tag
    if status < 400 and _etag_matches((request_headers or {}).get("If-None-Match", ""), tag):
        return 304, {"Cache-Control": cache, "ETag": tag}, b""
    headers["Content-Length"] = str(len(body))
    headers.update(extra or {})
    return status, headers, body


def _fallback_json(value, request_headers, status=200):
    return _fallback_response(status, _json_bytes(value), JSON_TYPE, request_headers=request_headers)


def _fallback_dispatch(server, method, target, headers):
    if not valid_host_headers(headers):
        return _fallback_response(400, b"invalid host")
    if method not in ("GET", "HEAD"):
        return _fallback_response(405, b"method not allowed", request_headers=headers, extra={"Allow": "GET, HEAD"})
    parsed = urlsplit(target)
    path, query = unquote(parsed.path), {key: values[0] for key, values in parse_qs(parsed.query).items()}
    root, transcripts = server.root, server.transcripts
    value = None
    if path == "/api/v1/runs":
        value = project_runs(root)
    elif path.startswith("/api/v1/runs/"):
        parts = path.strip("/").split("/")
        if len(parts) == 4:
            value = project_run(root, parts[3])
        elif len(parts) == 6 and parts[4] == "tickets":
            value = project_ticket(root, parts[3], parts[5])
        return _fallback_json(value if value is not None else {"error": "not found"}, headers, 200 if value is not None else 404)
    elif path == "/api/v1/friction":
        value = project_friction(root)
    elif path == "/api/v1/sessions":
        value = project_sessions(transcripts)
    elif path.startswith("/api/v1/sessions/"):
        value = project_session(transcripts, path.rsplit("/", 1)[-1])
        return _fallback_json(value if value is not None else {"error": "not found"}, headers, 200 if value is not None else 404)
    elif path == "/api/v1/experience":
        value = project_experience(root, transcripts, query)
    elif path == "/api/observe":
        value = project_observe(root, query.get("run", ""))
    if value is not None:
        return _fallback_json(value, headers)
    if is_spa_path(path) and browser_navigation(path, headers):
        asset = read_asset(server.assets, "index.html")
        return _fallback_response(503, b"reader application unavailable") if asset is None else _fallback_response(200, asset[0], asset[1] + "; charset=utf-8", request_headers=headers, tag=asset[2])
    if path.startswith("/assets/"):
        asset = read_asset(server.assets, path.lstrip("/"))
        return _fallback_response(404, b"not found") if asset is None else _fallback_response(200, asset[0], asset[1], "public, max-age=31536000, immutable", headers, asset[2])
    if server.legacy_respond is not None:
        status, tag, page = server.legacy_respond(
            root, target, headers.get("If-None-Match"), transcripts
        )
        body = page.encode("utf-8")
        extra = {"Cache-Control": "no-cache", "Content-Type": "text/html; charset=utf-8"}
        if tag:
            extra["ETag"] = tag
        extra["Content-Length"] = str(len(body))
        return status, extra, body
    return _fallback_response(404, b"not found")


class UvicornReaderServer:
    """Compatibility wrapper around one pre-bound Uvicorn socket."""

    def __init__(self, root, port: int, transcripts=None, assets=None, legacy_respond=None):
        self.root = Path(root)
        self.transcripts = transcripts
        self.application = create_application(root, transcripts, assets, legacy_respond)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", port))
        self._socket.listen(128)
        self._socket.setblocking(False)
        self.server_address = self._socket.getsockname()
        self._server = None

    def serve_forever(self, poll_interval=0.5):
        config = uvicorn.Config(self.application, log_level="critical", access_log=False)
        self._server = uvicorn.Server(config)
        self._server.run(sockets=[self._socket])

    def shutdown(self):
        if self._server is not None:
            self._server.should_exit = True

    def server_close(self):
        try:
            self._socket.close()
        except OSError:
            pass


def create_server(root, port: int, transcripts=None, assets=None, legacy_respond=None):
    resolved_assets = resolve_asset_root() if assets is None else Path(assets).resolve()
    if Starlette is None:
        return FallbackReaderServer(
            root,
            port,
            transcripts,
            resolved_assets,
            _fallback_dispatch,
            SECURITY_HEADERS,
            legacy_respond,
        )
    return UvicornReaderServer(
        root, port, transcripts, resolved_assets, legacy_respond
    )
