"""Observed current Codex envelopes: diagnostic items versus provenance context."""
from __future__ import annotations


def text_blocks(value, kinds):
    return isinstance(value, list) and all(
        isinstance(block, dict) and block.get("type") in kinds
        and isinstance(block.get("text"), str) for block in value)


def opaque(value):
    if isinstance(value, dict):
        return any(key == "encrypted_content" and bool(item) or opaque(item)
                   for key, item in value.items())
    return isinstance(value, list) and any(opaque(item) for item in value)


def metadata_kind(row):
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return None
    kind = row.get("type")
    if kind == "world_state" and isinstance(payload.get("full"), bool) and isinstance(payload.get("state"), dict):
        return kind
    if kind == "inter_agent_communication_metadata" and isinstance(payload.get("trigger_turn"), bool):
        return kind
    if kind == "token_usage_record" and isinstance(payload.get("usage"), dict):
        usage = payload["usage"]
        if usage and all(type(value) is int and value >= 0 for value in usage.values()):
            return kind
    return None


def completed_item(row):
    payload = row.get("payload")
    if row.get("type") != "event_msg" or not isinstance(payload, dict) or payload.get("type") != "item_completed":
        return None
    item = payload.get("item")
    if not isinstance(item, dict) or not isinstance(item.get("id"), str):
        return None
    kind = item.get("type")
    if kind == "CommandExecution":
        command = item.get("command")
        if (isinstance(command, str) or isinstance(command, list) and all(isinstance(x, str) for x in command)) and (item.get("exit_code") is None or type(item["exit_code"]) is int):
            return item
    elif kind == "AgentMessage" and isinstance(item.get("content"), (str, list)):
        return item
    elif kind == "Reasoning" and isinstance(item.get("summary_text"), (str, list)) and isinstance(item.get("raw_content"), (str, list)):
        return item
    elif kind == "SubAgentActivity" and isinstance(item.get("agent_thread_id"), str) and isinstance(item.get("kind"), str):
        return item
    elif kind == "FileChange" and isinstance(item.get("changes"), (dict, list)) and isinstance(item.get("status"), str):
        return item
    return None


def agent_message(row):
    payload = row.get("payload")
    if row.get("type") != "response_item" or not isinstance(payload, dict) or payload.get("type") != "agent_message":
        return None
    content = payload.get("content")
    if isinstance(content, list) and all(isinstance(x, dict) and (x.get("type") in {"input_text", "output_text"} and isinstance(x.get("text"), str) or x.get("type") == "encrypted_content" and isinstance(x.get("encrypted_content"), str)) for x in content):
        return payload
    return None


def shape(row):
    """None delegates legacy kinds; False keeps novel/malformed forms partial."""
    payload = row.get("payload")
    if row.get("type") == "response_item" and isinstance(payload, dict):
        if payload.get("type") == "message":
            return text_blocks(payload.get("content"), {"input_text", "output_text"})
        if payload.get("type") == "reasoning":
            return text_blocks(payload.get("summary", []), {"summary_text"}) and (
                payload.get("content") is None or text_blocks(payload["content"], {"reasoning_text"}))
    if row.get("type") in {"world_state", "token_usage_record", "inter_agent_communication_metadata"}:
        return metadata_kind(row) is not None
    if isinstance(payload, dict) and payload.get("type") == "item_completed":
        return completed_item(row) is not None
    if isinstance(payload, dict) and payload.get("type") == "agent_message" and row.get("type") == "response_item":
        return agent_message(row) is not None
    return None


def events(row):
    message = agent_message(row)
    if message:
        return [{"type": "agent_message", "ts": row.get("timestamp"),
                 "author": message.get("author"), "recipient": message.get("recipient"),
                 "text": "\n".join(x["text"] for x in message["content"] if "text" in x)}]
    item = completed_item(row)
    if item is None:
        return []
    event = {"type": "completed_item", "item_type": item["type"],
             "item_id": item["id"], "ts": row.get("timestamp")}
    if item["type"] == "CommandExecution":
        command = item["command"]
        event.update(type="tool_call", command=" ".join(command) if isinstance(command, list) else command,
                     exit=item.get("exit_code") if item.get("exit_code") is not None else "unknown")
    elif item["type"] == "AgentMessage":
        event.update(type="narration", text=item["content"])
    elif item["type"] == "FileChange":
        event.update(type="file_change", changes=item["changes"], status=item["status"])
    elif item["type"] == "SubAgentActivity":
        event.update(type="subagent_activity", agent_thread_id=item["agent_thread_id"], kind=item["kind"])
    return [event]
