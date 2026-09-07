"""Claude diagnostic content validation; trace remains the normalization owner."""
from __future__ import annotations


def content(value):
    if isinstance(value, str):
        return True
    return isinstance(value, list) and all(block(item) for item in value)


def block(value):
    if not isinstance(value, dict):
        return False
    kind = value.get("type")
    if kind == "text":
        return isinstance(value.get("text"), str)
    if kind == "thinking":
        return isinstance(value.get("thinking"), str)
    if kind == "redacted_thinking":
        return isinstance(value.get("data"), str)
    if kind == "tool_use":
        return all(isinstance(value.get(key), str) and value[key] for key in ("id", "name")) and isinstance(value.get("input"), dict)
    if kind == "tool_result":
        return (isinstance(value.get("tool_use_id"), str) and bool(value["tool_use_id"])
                and content(value.get("content", ""))
                and ("is_error" not in value or type(value["is_error"]) is bool))
    return False


def shape(row):
    if row.get("type") not in {"user", "assistant"}:
        return row.get("type") in {"summary", "system", "progress", "file-history-snapshot", "queue-operation"}
    message = row.get("message")
    if not isinstance(message, dict):
        return False
    value = message.get("content")
    return content(value) and (row["type"] == "user" or isinstance(value, list))


def opaque(value):
    if isinstance(value, dict):
        return value.get("type") == "redacted_thinking" or any(opaque(item) for item in value.values())
    return isinstance(value, list) and any(opaque(item) for item in value)
