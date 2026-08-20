"""Read-only projection boundary for run and ticket payloads."""

ROUTE_SPECS = (
    ("GET", "/api/v1/runs", "project_runs"),
    ("GET", "/api/v1/runs/{run}", "project_run"),
    ("GET", "/api/v1/runs/{run}/tickets/{ticket}", "project_ticket"),
)
