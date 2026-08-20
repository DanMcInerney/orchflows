"""Read-only projection boundary for session index and detail payloads."""

ROUTE_SPECS = (
    ("GET", "/api/v1/sessions", "project_sessions"),
    ("GET", "/api/v1/sessions/{session}", "project_session"),
)
