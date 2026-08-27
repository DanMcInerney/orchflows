"""Receiver identity checks and byte-safe packet input carriage."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__:
    from .tickets_dispatch_schema import classification
    from .tickets_format import _read_utf8
else:
    from tickets_dispatch_schema import classification
    from tickets_format import _read_utf8


def actual_mismatch(packet: dict, role, profile, owner, reply_to, workspace):
    for key, expected, actual, code in (
        ("assigned_name", packet["assigned_name"], owner, "identity-mismatch"),
        ("role", packet["role"], role, "role-mismatch"),
        ("profile", packet["profile"], profile, "profile-mismatch"),
        ("reply_to", packet["reply_to"], reply_to, "authority-mismatch"),
        ("workspace", packet.get("workspace"), workspace, "authority-mismatch"),
    ):
        if expected != actual:
            return classification(code, f"received {key} does not match packet")
    return None


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
