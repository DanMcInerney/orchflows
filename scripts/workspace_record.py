"""The established workspace's one owner: the dispatch attempt.

`contracts/dispatch.md` gives the tree an isolated item runs in to the
attempt that dispatched it, and nothing else records it. The ticket
frontmatter used to carry a projection of the same path, and a second home
is how a packet came to name a tree the establishment had not created.

Both directions live here, in one module both families import: the
workspace family writes the path when it establishes the tree, and the
ticket family reads it when it grades a projection against the
establishment. Neither spells the read or the write for itself.
"""

from __future__ import annotations

PATH_KEY = "workspace_path"


def _schema():
    """The dispatch state reader, imported at call time.

    These two families are loaded as a package in the source tree and as flat
    scripts once installed, and in neither layout may this module's import
    order decide whether a workspace can be recorded.
    """

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


def attempt_workspace(data: dict):
    """The tree this ticket's dispatch attempt recorded, or ``None``.

    The live attempt answers while one is open; once it has been retired or
    replaced, the most recent attempt that recorded a tree answers, because
    the join grades the tree the item was actually executed in.
    """

    state, failure = _schema().stored_state(data)
    if failure is not None or not isinstance(state, dict):
        return None
    attempts = state.get("attempts") or []
    live = [item for item in attempts if item.get("state") == "live"]
    for attempt in (live or list(reversed(attempts))):
        recorded = str(attempt.get(PATH_KEY) or "").strip()
        if recorded:
            return recorded
    return None


def recorded_on_attempt(text: str, workspace_path: str):
    """``(text, recorded)`` with the established tree on the live attempt.

    ``recorded`` is False when there is no live attempt to carry it, which is
    an ordinary case: ``workspace.py start`` is a verb of its own and runs
    outside a dispatch as well as inside one. Then the tree is reported in
    that call's own response and persisted nowhere -- there is no attempt for
    it to belong to, and the frontmatter home it used to take was exactly the
    second owner this field no longer has.
    """

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


__all__ = ("PATH_KEY", "attempt_workspace", "recorded_on_attempt")
