"""Closed result-artifact inventory and contained content reads."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from reader.scripts import ui_workflows_identity as contained


ROUTE_SPECS = (
    (
        "GET",
        "/api/v1/runs/{run}/tickets/{ticket}/artifacts",
        "project_artifact_inventory",
    ),
    (
        "GET",
        "/api/v1/runs/{run}/tickets/{ticket}/artifacts/{artifact_id}",
        "project_artifact",
    ),
)
INVENTORY_SCHEMA = "orchflows.ticket-artifacts.v1"
ARTIFACT_SCHEMA = "orchflows.ticket-artifact.v1"
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
ARTIFACT_ID_RE = re.compile(r"art_[A-Za-z0-9_-]{43}\Z")
RESULT_HEADING_RE = re.compile(r"^## Report[ \t]*\r?$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^## [^\r\n]+", re.MULTILINE)
WINDOWS_HOST_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\)[^`\"'<>\r\n]+"
)
POSIX_HOST_PATH_RE = re.compile(r"(?<![:/A-Za-z0-9_])/(?!/)[^`\"'<>\r\n]+")
REDACTED_HOST_PATH = "[redacted-host-path]"
NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
UNAVAILABLE = {
    "error": {
        "code": "unavailable_artifact",
        "message": "artifact is unavailable",
    }
}


class ArtifactIdentityError(ValueError):
    """A Result section does not carry one canonical artifact identity."""


def _name(value: object) -> str:
    if not isinstance(value, str) or NAME_RE.fullmatch(value) is None:
        raise ArtifactIdentityError("run or ticket identity is not canonical")
    return value


def _ticket_text(root: Path, run: object, ticket: object) -> str | None:
    try:
        path = root / "tickets" / _name(run) / (_name(ticket) + ".md")
        return contained.read_contained_bytes(root, path).decode("utf-8")
    except (
        ArtifactIdentityError,
        contained.ContainedFileError,
        UnicodeError,
    ):
        return None


def _result_section(text: str) -> str:
    headings = list(RESULT_HEADING_RE.finditer(text))
    if len(headings) != 1:
        raise ArtifactIdentityError("ticket does not have one Result section")
    start = headings[0].end()
    following = NEXT_HEADING_RE.search(text, start)
    return text[start : following.start() if following else len(text)]


def _identity(text: str) -> dict:
    section = _result_section(text)
    candidates = [line for line in section.splitlines() if line.startswith("result:")]
    if len(candidates) != 1 or not candidates[0].startswith("result: "):
        raise ArtifactIdentityError("Result does not carry one structured identity")
    encoded = candidates[0][len("result: ") :]
    try:
        value = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ArtifactIdentityError("Result identity is not JSON") from error
    if not isinstance(value, dict) or set(value) != {"kind", "locator", "sha256"}:
        raise ArtifactIdentityError("Result identity has the wrong shape")
    if value["kind"] != "artifact":
        raise ArtifactIdentityError("Result identity is not an artifact")
    if json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) != encoded:
        raise ArtifactIdentityError("Result identity is not canonical JSON")
    if not isinstance(value["sha256"], str) or SHA256_RE.fullmatch(value["sha256"]) is None:
        raise ArtifactIdentityError("Result identity digest is not canonical")
    _artifact_path(value["locator"])
    return value


def _artifact_path(locator: object) -> PurePosixPath:
    if not isinstance(locator, str) or not locator.startswith("sink:"):
        raise ArtifactIdentityError("artifact locator is not state-sink relative")
    relative = locator[len("sink:") :]
    if not relative or "\\" in relative or relative.startswith("/"):
        raise ArtifactIdentityError("artifact locator is not portable")
    path = PurePosixPath(relative)
    if path.as_posix() != relative or any(part in {"", ".", ".."} for part in path.parts):
        raise ArtifactIdentityError("artifact locator escapes the state sink")
    return path


def _artifact_id(identity: dict) -> str:
    encoded = json.dumps(
        identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = base64.urlsafe_b64encode(hashlib.sha256(encoded).digest())
    return "art_" + digest.decode("ascii").rstrip("=")


def _read_identity(root: Path, identity: dict) -> bytes:
    relative = _artifact_path(identity["locator"])
    raw = contained.read_contained_bytes(root, root.joinpath(*relative.parts))
    if hashlib.sha256(raw).hexdigest() != identity["sha256"]:
        raise contained.ContainedFileUnavailable("artifact digest changed")
    raw.decode("utf-8")
    return raw


def _redact(text: str, root: Path) -> tuple[str, bool]:
    delivered = text
    markers = {str(root.resolve()), root.resolve().as_posix()}
    for marker in sorted(markers, key=len, reverse=True):
        delivered = delivered.replace(marker, REDACTED_HOST_PATH)
    delivered = WINDOWS_HOST_PATH_RE.sub(REDACTED_HOST_PATH, delivered)
    delivered = POSIX_HOST_PATH_RE.sub(REDACTED_HOST_PATH, delivered)
    return delivered, delivered != text


def _inventory(run: str, ticket: str, state: str, artifacts: list) -> dict:
    return {
        "schema": INVENTORY_SCHEMA,
        "run": run,
        "ticket": ticket,
        "state": state,
        "artifacts": artifacts,
    }


def project_artifact_inventory(
    root: Path,
    run: str = "",
    ticket: str = "",
) -> tuple[int, dict]:
    """Expose only a contained structured Result identity through an opaque ID."""

    root = Path(root)
    try:
        canonical_run, canonical_ticket = _name(run), _name(ticket)
    except ArtifactIdentityError:
        return 404, NOT_FOUND
    text = _ticket_text(root, canonical_run, canonical_ticket)
    if text is None:
        return 404, NOT_FOUND
    try:
        identity = _identity(text)
        _read_identity(root, identity)
    except (ArtifactIdentityError, contained.ContainedFileError, UnicodeError):
        return 200, _inventory(canonical_run, canonical_ticket, "unavailable", [])
    return 200, _inventory(
        canonical_run,
        canonical_ticket,
        "available",
        [{"id": _artifact_id(identity), "state": "available"}],
    )


def project_artifact(
    root: Path,
    run: str = "",
    ticket: str = "",
    artifact_id: str = "",
) -> tuple[int, dict]:
    """Return redacted text for one canonical opaque artifact identity."""

    root = Path(root)
    if not isinstance(artifact_id, str) or ARTIFACT_ID_RE.fullmatch(artifact_id) is None:
        return 404, NOT_FOUND
    try:
        canonical_run, canonical_ticket = _name(run), _name(ticket)
    except ArtifactIdentityError:
        return 404, NOT_FOUND
    text = _ticket_text(root, canonical_run, canonical_ticket)
    if text is None:
        return 404, NOT_FOUND
    try:
        identity = _identity(text)
    except ArtifactIdentityError:
        return 404, NOT_FOUND
    if artifact_id != _artifact_id(identity):
        return 404, NOT_FOUND
    try:
        raw = _read_identity(root, identity)
        decoded = raw.decode("utf-8")
    except (contained.ContainedFileUnavailable, UnicodeError):
        return 422, UNAVAILABLE
    except contained.ContainedFileError:
        return 404, NOT_FOUND
    delivered, redacted = _redact(decoded, root)
    return 200, {
        "schema": ARTIFACT_SCHEMA,
        "id": artifact_id,
        "text": delivered,
        "sha256": hashlib.sha256(delivered.encode("utf-8")).hexdigest(),
        "redacted": redacted,
    }


def http_endpoint(namespace: dict, response, internal_error):
    """Bind both fixed Starlette routes without moving response policy here."""

    async def endpoint(request):
        params = dict(request.path_params)
        name = "project_artifact" if "artifact_id" in params else "project_artifact_inventory"
        try:
            status, value = namespace[name](request.app.state.root, **params)
        except Exception:
            return response(request, internal_error, 500)
        return response(request, value, status)

    return endpoint
