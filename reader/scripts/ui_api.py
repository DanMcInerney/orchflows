"""The sole frozen ``orchflows.reader.v1`` HTTP API boundary.

The reader is deliberately a consumer of the state sink: this module owns
the versioned route table, query validation, security policy, and response
encoding while the sibling projection modules own individual closed shapes.
There is one server implementation and one public route version.
"""

from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from reader.scripts import (
    ui_artifacts_projection,
    ui_friction_projection,
    ui_now_projection,
    ui_runs_projection,
    ui_sessions_projection,
    ui_workflows_projection,
)
from reader.scripts.ui_assets import read_asset, resolve_asset_root
from reader.scripts import ui_experience

PUBLIC_API_VERSION = "v1"
PUBLIC_API_SCHEMA = "orchflows.reader.v1"
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
    ui_artifacts_projection,
    ui_now_projection,
    ui_runs_projection,
    ui_workflows_projection,
    ui_sessions_projection,
    ui_friction_projection,
)
VIEW_QUERY_FIELDS = {
    "now": frozenset(),
    "run-map": frozenset(("run",)),
    "inspector": frozenset(("run", "ticket")),
    "sessions": frozenset(),
    "session-graph": frozenset(("session",)),
    "friction": frozenset(),
}
VIEW_REQUIRED_FIELDS = {
    "inspector": frozenset(("run", "ticket")),
    "session-graph": frozenset(("session",)),
}
INVALID_REQUEST = {
    "error": {"code": "invalid_request", "message": "request could not be served"}
}
NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
INTERNAL_ERROR = {"error": {"code": "internal_error", "message": "projection failed"}}


def _projector_route_specs(modules=None) -> tuple:
    """Bind each pure domain table while refusing ambiguous HTTP ownership."""

    include_public_workflows = modules is None
    modules = PROJECTOR_MODULES if modules is None else modules
    tables = [(module, module.ROUTE_SPECS) for module in modules]
    if include_public_workflows:
        tables.append((ui_workflows_projection, ui_workflows_projection.PUBLIC_ROUTE_SPECS))
    assembled = []
    seen = set()
    for module, specs in tables:
        for method, path, function_name in specs:
            key = (method, path)
            if key in seen:
                raise ValueError("duplicate projection route {0} {1}".format(method, path))
            seen.add(key)
            assembled.append((method, path, module, function_name))
    return tuple(assembled)


def _validated_view_query(view: str, values):
    if view not in ui_experience.VIEW_SLICES or view not in VIEW_QUERY_FIELDS:
        return None
    if not set(values).issubset(VIEW_QUERY_FIELDS[view]):
        return None
    if not VIEW_REQUIRED_FIELDS.get(view, frozenset()).issubset(values):
        return None
    if any(len(items) != 1 or not items[0] for items in values.values()):
        return None
    return {key: items[0] for key, items in values.items()}


def _view_projection(root, transcripts, view: str, query) -> tuple:
    if view == "run-map" and query.get("run"):
        if ui_runs_projection.project_run(root, query["run"]) is None:
            return 404, NOT_FOUND
    elif view == "inspector":
        if ui_runs_projection.project_ticket(root, query["run"], query["ticket"]) is None:
            return 404, NOT_FOUND
    elif view == "session-graph":
        if ui_sessions_projection.project_session(transcripts, query["session"]) is None:
            return 404, NOT_FOUND
    return 200, ui_experience.project_view(root, transcripts, view, query)


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


artifact_endpoint = ui_artifacts_projection.http_endpoint(
    {
        "project_artifact_inventory": ui_artifacts_projection.project_artifact_inventory,
        "project_artifact": ui_artifacts_projection.project_artifact,
    },
    _json_response,
    INTERNAL_ERROR,
)


def _context(request: Request):
    return request.app.state.root, request.app.state.transcripts


def _projected_response(request: Request, projector, *args):
    try:
        value = projector(*args)
    except Exception:
        return _json_response(request, INTERNAL_ERROR, 500)
    if value is None:
        return _json_response(request, NOT_FOUND, 404)
    return _json_response(request, value)


async def runs_endpoint(request: Request):
    return _projected_response(request, ui_runs_projection.project_runs, _context(request)[0])


async def run_endpoint(request: Request):
    return _projected_response(request, ui_runs_projection.project_run, _context(request)[0], request.path_params["run"])


async def ticket_endpoint(request: Request):
    root, _ = _context(request)
    return _projected_response(request, ui_runs_projection.project_ticket, root, request.path_params["run"], request.path_params["ticket"])


async def friction_endpoint(request: Request):
    return _projected_response(request, ui_friction_projection.project_friction, _context(request)[0])


async def sessions_endpoint(request: Request):
    return _projected_response(request, ui_sessions_projection.project_sessions, _context(request)[1])


async def session_endpoint(request: Request):
    return _projected_response(request, ui_sessions_projection.project_session, _context(request)[1], request.path_params["session"])


async def experience_endpoint(request: Request):
    root, transcripts = _context(request)
    return _projected_response(
        request, ui_experience.project_experience, root, transcripts, dict(request.query_params)
    )


async def view_endpoint(request: Request):
    root, transcripts = _context(request)
    view = request.path_params["view"]
    values = {key: request.query_params.getlist(key) for key in request.query_params}
    query = _validated_view_query(view, values)
    if query is None:
        return _json_response(request, INVALID_REQUEST, 422)
    try:
        status, value = _view_projection(root, transcripts, view, query)
    except Exception:
        return _json_response(request, INTERNAL_ERROR, 500)
    return _json_response(request, value, status)


def _workflow_root():
    return ui_workflows_projection.ROOT


async def workflows_endpoint(request: Request):
    return _projected_response(request, ui_workflows_projection.project_workflow_catalog, _workflow_root())


async def workflow_endpoint(request: Request):
    try:
        value = ui_workflows_projection.project_workflow(_workflow_root(), request.path_params["workflow_id"])
    except Exception:
        return _json_response(request, INTERNAL_ERROR, 500)
    return _json_response(request, NOT_FOUND, 404) if value is None else _json_response(request, value)


async def workflow_source_endpoint(request: Request):
    try:
        status, value = ui_workflows_projection.project_workflow_source(
            _workflow_root(), request.path_params["workflow_id"], request.path_params["source_id"]
        )
    except Exception:
        return _json_response(request, INTERNAL_ERROR, 500)
    return _json_response(request, value, status)


def _starlette_projector_routes():
    endpoints = {
        (ui_artifacts_projection, "project_artifact_inventory"): artifact_endpoint,
        (ui_artifacts_projection, "project_artifact"): artifact_endpoint,
        (ui_runs_projection, "project_runs"): runs_endpoint,
        (ui_runs_projection, "project_run"): run_endpoint,
        (ui_runs_projection, "project_ticket"): ticket_endpoint,
        (ui_sessions_projection, "project_sessions"): sessions_endpoint,
        (ui_sessions_projection, "project_session"): session_endpoint,
        (ui_friction_projection, "project_friction"): friction_endpoint,
        (ui_workflows_projection, "project_workflow_catalog"): workflows_endpoint,
        (ui_workflows_projection, "project_workflow"): workflow_endpoint,
        (ui_workflows_projection, "project_workflow_source"): workflow_source_endpoint,
    }
    return [
        Route(path, endpoints[(module, function_name)], methods=[method])
        for method, path, module, function_name in _projector_route_specs()
        if (module, function_name) in endpoints
    ]


async def index_endpoint(request: Request):
    asset = read_asset(request.app.state.assets, "index.html")
    if asset is None:
        return Response("reader application unavailable", status_code=503)
    return _bytes_response(request, asset[0], asset[1], "no-cache", asset[2])


async def spa_endpoint(request: Request):
    if ui_experience.browser_navigation(request.url.path, request.headers):
        return await index_endpoint(request)
    return Response("not found", status_code=404)


async def asset_endpoint(request: Request):
    asset = read_asset(request.app.state.assets, "assets/" + request.path_params["asset"])
    if asset is None:
        return Response("not found", status_code=404)
    return _bytes_response(request, asset[0], asset[1], "public, max-age=31536000, immutable", asset[2])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response


def create_application(root, transcripts=None, assets=None):
    routes = [
        *_starlette_projector_routes(),
        Route("/api/v1/views/{view}", view_endpoint, methods=["GET"]),
        Route("/api/v1/experience", experience_endpoint, methods=["GET"]),
        Route("/assets/{asset:path}", asset_endpoint, methods=["GET"]),
        *[Route(pattern, spa_endpoint, methods=["GET"]) for pattern in ui_experience.SPA_ROUTE_PATTERNS],
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
    return app


class UvicornReaderServer:
    """Serve one pre-bound loopback socket using the v1 application."""

    def __init__(self, root, port: int, transcripts=None, assets=None):
        self.root = Path(root)
        self.transcripts = transcripts
        self.application = create_application(root, transcripts, assets)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", port))
        self._socket.listen(128)
        self._socket.setblocking(False)
        self.server_address = self._socket.getsockname()
        self._server = None

    def serve_forever(self, poll_interval=0.5):
        del poll_interval
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


def create_server(root, port: int, transcripts=None, assets=None):
    _projector_route_specs()
    resolved_assets = resolve_asset_root() if assets is None else Path(assets).resolve()
    return UvicornReaderServer(root, port, transcripts, resolved_assets)
