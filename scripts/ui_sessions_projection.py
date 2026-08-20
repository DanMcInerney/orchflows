"""Read-only projection boundary for session index and detail payloads."""

from __future__ import annotations

try:
    from scripts.ui_discovery import find_session, read_sessions
    from scripts.ui_sessions import read_session
except ImportError:
    from ui_discovery import find_session, read_sessions
    from ui_sessions import read_session

ROUTE_SPECS = (
    ("GET", "/api/v1/sessions", "project_sessions"),
    ("GET", "/api/v1/sessions/{session}", "project_session"),
)


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
        "api_version": "v1",
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
    return {"api_version": "v1", "session": projected}
