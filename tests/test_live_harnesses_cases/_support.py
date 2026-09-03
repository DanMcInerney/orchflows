"""Shared fixtures for the live-harness regression case modules."""


import collections
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import state_root
from tools import live_claude_profiles as claude_live
from tools import live_codex_profiles as codex_live
from tools import live_sweep_e2e as sweep_live

SWEEP_AGENT = "orch-sweep-e2e-42"
SWEEP_PY = Path(sweep_live.__file__).resolve()


def _launch(tool_id: str, agent_type: str, prompt: str = None) -> dict:
    """A parent-level Agent dispatch. The sweep's probe carries no packet,
    so `prompt` is absent from its input rather than empty -- the harness
    reads the key, and a present-but-empty one is a different transcript."""
    launch_input = {"subagent_type": agent_type}
    if prompt is not None:
        launch_input["prompt"] = prompt
    return {
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": "Agent",
                    "input": launch_input,
                }
            ]
        },
    }


def _reply(tool_id: str, text: str) -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": tool_id,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _parent_text(text: str) -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _stream(events: list) -> str:
    return "\n".join(json.dumps(event) for event in events)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tool_use(name: str, tool_input: dict, tool_id: str = "t1") -> dict:
    """A parent-level tool call, the only kind the router's first move can be."""

    return {
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {
            "content": [
                {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}
            ]
        },
    }


def _skill_use(skill: str, tool_id: str = "t1") -> dict:
    return _tool_use("Skill", {"skill": skill}, tool_id)


__all__ = [
    "collections",
    "contextlib",
    "hashlib",
    "io",
    "json",
    "os",
    "re",
    "subprocess",
    "tempfile",
    "unittest",
    "Path",
    "mock",
    "state_root",
    "claude_live",
    "codex_live",
    "sweep_live",
    "SWEEP_AGENT",
    "SWEEP_PY",
    "_launch",
    "_reply",
    "_parent_text",
    "_stream",
    "_sha256",
    "_tool_use",
    "_skill_use",
]
