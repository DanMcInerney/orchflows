"""Receiver identity checks and byte-safe packet input carriage."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__:
    from .tickets_adapters import AdapterError, adapter_spec
    from .tickets_dispatch_schema import (
        RECEIPT_RECORD_ID, accepted_receipt_failure, classification,
        identity_failure, state as _state,
    )
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _read_utf8, parse_canonical_json,
    )
    from .tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root
else:
    from tickets_adapters import AdapterError, adapter_spec
    from tickets_dispatch_schema import (
        RECEIPT_RECORD_ID, accepted_receipt_failure, classification,
        identity_failure, state as _state,
    )
    from tickets_format import _extract_flag, _parse_frontmatter, _read_utf8, parse_canonical_json
    from tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root


DISPATCH_RECEIPT_USAGE = "dispatch-receipt <run> <id> --dispatch-id <id>"


def _workspace_git_module():
    """Load Git mechanics after the flat ticket importer has initialized."""

    if __package__:
        from . import workspace_git
    else:
        import workspace_git
    return workspace_git


def _same_path(left, right) -> bool:
    """Compare two authority paths after each side's platform normalization."""

    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def _workspace_failure(packet: dict):
    """Derive and authenticate the receiver's workspace authority.

    ``workspace`` in a packet is an established fact committed by the
    dispatcher.  The receiver must prove that fact from its own mechanism;
    accepting a second path argument here would let the receiver choose the
    authority it is supposed to authenticate.
    """

    try:
        adapter = adapter_spec(packet.get("pack"))
    except AdapterError as error:
        return classification(
            "authority-mismatch",
            f"cannot derive workspace authority from packet adapter: {error.detail}",
        )

    expected = packet.get("workspace")
    strategy = adapter.workspace_strategy
    if strategy == "git":
        if not isinstance(expected, str) or not expected.strip():
            return classification(
                "authority-mismatch",
                "Git packet has no established workspace authority",
            )
        workspace_git = _workspace_git_module()
        try:
            actual = workspace_git.actual_top_level()
        except (OSError, RuntimeError, ValueError) as error:
            return classification(
                "authority-mismatch",
                f"receiver is not standing in a Git workspace: {error}",
            )
        except workspace_git.Refused as error:
            return classification(
                "authority-mismatch",
                f"receiver is not standing in a Git workspace: {error}",
            )
        if not _same_path(actual, expected):
            return classification(
                "authority-mismatch",
                "receiver Git top-level does not match the established packet workspace",
            )
        return None

    if strategy == "evidence-store":
        if not isinstance(expected, str) or not expected.strip():
            return classification(
                "authority-mismatch",
                "evidence-store packet has no established workspace authority",
            )
        try:
            available = Path(expected).expanduser().is_dir()
        except (OSError, RuntimeError, ValueError):
            available = False
        if not available:
            return classification(
                "state-inaccessible",
                "authoritative evidence-store workspace is unavailable",
            )
        return None

    # A document-tree adapter deliberately does not establish an isolated
    # receiver workspace.  Its packet authority remains the committed state
    # sink and is not guessed from the receiver's current directory.
    if strategy == "document-tree":
        return None
    return classification(
        "authority-mismatch",
        f"adapter workspace strategy is not supported: {strategy}",
    )


def actual_mismatch(packet: dict, role, profile, owner, reply_to):
    for key, expected, actual, code in (
        ("assigned_name", packet["assigned_name"], owner, "identity-mismatch"),
        ("role", packet["role"], role, "role-mismatch"),
        ("profile", packet["profile"], profile, "profile-mismatch"),
        ("reply_to", packet["reply_to"], reply_to, "authority-mismatch"),
    ):
        if expected != actual:
            return classification(code, f"received {key} does not match packet")
    return _workspace_failure(packet)


def read_packet_payload(content, source_file):
    if source_file is None:
        return content, None
    if source_file == "-":
        try:
            return sys.stdin.buffer.read().decode("utf-8"), None
        except (AttributeError, OSError, UnicodeDecodeError, ValueError) as error:
            return None, classification(
                "packet-invalid", f"unreadable UTF-8 packet input: {error}"
            )
    content, failure = _read_utf8(Path(source_file), "packet file")
    if failure is not None:
        return None, classification("packet-invalid", failure["error"])
    return content, None


def _cmd_dispatch_receipt(rest):
    """Read one accepted dispatch receipt without changing ticket state.

    The ticket's complete dispatch ledger is validated before selecting the
    named attempt. Missing state and missing records stay distinct structured
    refusals so callers cannot downgrade an unknown result to a negative
    answer.
    """
    args = list(rest)
    dispatch_id = _extract_flag(args, "--dispatch-id")
    if len(args) != 2 or not dispatch_id:
        return {"error": f"usage: {DISPATCH_RECEIPT_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        failure = _segment_error(kind, value)
        if failure is not None:
            return failure
    failure = identity_failure("dispatch-id", dispatch_id)
    if failure is not None:
        return failure

    root = _tickets_root()
    if root is None:
        return classification("state-inaccessible", NO_SINK_ERROR)
    path = root / run / f"{ticket_id}.md"
    text, failure = _read_utf8(path, "ticket")
    if failure is not None:
        return classification("state-inaccessible", failure["error"])
    data = _parse_frontmatter(text)
    state, failure = _state(data)
    if failure is not None:
        return failure
    if state is None:
        status = str(data.get("status") or "")
        if status in ("claimed", "suspended"):
            return classification(
                "legacy-live-claim", "pre-v1 live claim has no dispatch record"
            )
        return classification("dispatch-mismatch", "ticket has no dispatch-v1 attempt")
    attempt = next(
        (item for item in state["attempts"] if item.get("dispatch_id") == dispatch_id),
        None,
    )
    if attempt is None:
        return classification(
            "dispatch-mismatch",
            f"dispatch_id '{dispatch_id}' was never opened for this ticket",
        )

    # A valid closed state may legitimately have only a committed packet. Use
    # the protocol validator's same receipt gate so a missing or malformed
    # accepted receipt is never represented as success.
    failure = accepted_receipt_failure(attempt)
    if failure is not None:
        return failure
    receipt_record = next(
        (
            item for item in attempt.get("records", [])
            if item.get("record_id") == RECEIPT_RECORD_ID
        ),
        None,
    )
    try:
        content = parse_canonical_json(receipt_record["content"])
        receipt = content["receipt"]
    except (KeyError, TypeError, ValueError):
        return classification(
            "dispatch-record-invalid",
            "accepted receipt has no canonical persisted receipt",
        )
    return {"receipt": receipt}
