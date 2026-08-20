"""Deterministic node, edge, and source identities for Workflows."""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import PurePosixPath
from urllib.parse import quote


NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class WorkflowIdentityError(ValueError):
    """A canonical identity input is malformed."""


def _name(value: object, subject: str) -> str:
    if not isinstance(value, str) or NAME_RE.fullmatch(value) is None:
        raise WorkflowIdentityError(f"{subject} is not a canonical name")
    return value


def normalize_installed_path(path: object) -> str:
    """Return one stable installed-library-relative POSIX path."""

    if not isinstance(path, str) or not path or path != path.strip():
        raise WorkflowIdentityError("installed path must be a non-empty string")
    portable = path.replace("\\", "/")
    if portable.startswith("/") or re.match(r"[A-Za-z]:", portable):
        raise WorkflowIdentityError("installed path must be relative")
    if ".." in portable.split("/"):
        raise WorkflowIdentityError("installed path cannot traverse its root")
    normalized = PurePosixPath(portable).as_posix()
    if normalized in {"", "."}:
        raise WorkflowIdentityError("installed path must name a file")
    return normalized


def workflow_node_id(workflow: str) -> str:
    return f"workflow:{_name(workflow, 'workflow')}"


def work_node_id(workflow: str, stub: str) -> str:
    return f"work:{_name(workflow, 'workflow')}/{_name(stub, 'stub')}"


def skill_node_id(skill: str) -> str:
    return f"skill:{_name(skill, 'skill')}"


def script_node_id(installed_path: str) -> str:
    return f"script:{normalize_installed_path(installed_path)}"


def edge_id(kind: str, source: str, target: str) -> str:
    """Encode an edge tuple so repeated occurrences have one stable ID."""

    kind = _name(kind, "edge kind")
    if not isinstance(source, str) or not source:
        raise WorkflowIdentityError("edge source must be a non-empty string")
    if not isinstance(target, str) or not target:
        raise WorkflowIdentityError("edge target must be a non-empty string")
    return "edge:{0}:{1}:{2}".format(
        quote(kind, safe=""),
        quote(source, safe=""),
        quote(target, safe=""),
    )


def source_id(installed_path: str) -> str:
    """Hash a normalized installed path into an opaque URL-safe source ID."""

    normalized = normalize_installed_path(installed_path)
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return "src_" + encoded
