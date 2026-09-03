"""The established workspace's one owner: the dispatch attempt.

`contracts/dispatch.md` gives the tree an isolated item runs in to the
attempt that dispatched it, and nothing else records it: a second home for
that path is how a launch comes to name a tree no establishment created.

Both directions live here, in one module both families import: the
workspace family writes the path when it establishes the tree, and the
ticket family reads it when it grades a projection against the
establishment. Neither spells the read or the write for itself.
"""

from __future__ import annotations

PATH_KEY = "workspace_path"


def _schema():
    """The dispatch state reader, imported at call time."""

    try:
        from . import tickets_dispatch_schema
    except ImportError:  # pragma: no cover - the flat installed layout
        import tickets_dispatch_schema
    return tickets_dispatch_schema


def _format():
    try:
        from . import tickets_format
    except ImportError:  # pragma: no cover - the flat installed layout
        import tickets_format
    return tickets_format


def recorded_workspace(attempt: dict):
    """The tree one attempt recorded, or ``None``."""

    return str((attempt or {}).get(PATH_KEY) or "").strip() or None


def attempt_workspace(data: dict):
    """The tree this ticket's dispatch attempt recorded, or ``None``."""

    state, failure = _schema().stored_state(data)
    if failure is not None or not isinstance(state, dict):
        return None
    attempts = state.get("attempts") or []
    live = [item for item in attempts if item.get("state") == "live"]
    for attempt in (live or list(reversed(attempts))):
        recorded = recorded_workspace(attempt)
        if recorded:
            return recorded
    return None


def recorded_on_attempt(text: str, workspace_path: str):
    """``(text, recorded)`` with the established tree on the live attempt."""

    formats = _format()
    data = formats._parse_frontmatter(text)
    state, failure = _schema().stored_state(data)
    if failure is not None or not isinstance(state, dict):
        return text, False
    live = next(
        (item for item in state.get("attempts") or [] if item.get("state") == "live"),
        None,
    )
    if live is None:
        return text, False
    live[PATH_KEY] = workspace_path
    return formats._set_frontmatter_field(
        text, "dispatch_v1", formats.canonical_json(state)
    ), True


__all__ = (
    "PATH_KEY", "attempt_workspace", "recorded_on_attempt", "recorded_workspace",
)
