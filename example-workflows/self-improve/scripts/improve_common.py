"""Frozen selection and safe evidence primitives; no semantic diagnosis."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Source and installed layouts share the public trace/state facades.
for ancestor in Path(__file__).resolve().parents:
    for candidate in (ancestor / "scripts", ancestor / "bin"):
        if all((candidate / name).is_file() for name in ("state_root.py", "trace.py")):
            sys.path.insert(0, str(candidate))
            break
    else:
        continue
    break
import state_root


class EvidenceError(ValueError):
    """A named input, coverage or lifecycle refusal."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def instant(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            raise ValueError()
        return stamp.astimezone(timezone.utc)
    except (ValueError, AttributeError, TypeError):
        raise EvidenceError("timestamp requires an explicit UTC offset") from None


def utc(value):
    return instant(value).isoformat().replace("+00:00", "Z")


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def identity(path):
    return os.path.normcase(str(Path(path).expanduser().resolve()))


def project(path):
    root = state_root.find_repo_root(Path(path))
    return identity(root or path)


def inside(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


SECRET_KEY = re.compile(r"(?i)(?:password|passwd|secret|token|api.?key|authorization|cookie|credential|private.?key)")
SECRET_TEXT = re.compile(r'''(?ix)(["']?(?:password|passwd|secret|[\w-]*token|api[_-]?key|authorization|cookie)["']?\s*[:=]\s*)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;&]+)''')


def redact(value):
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if SECRET_KEY.search(str(k)) or k == "encrypted_content"
                or value.get("type") == "redacted_thinking" and k == "data" else redact(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if not isinstance(value, str):
        return value
    value = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|$)",
                   "[REDACTED PRIVATE KEY]", value, flags=re.S)
    value = re.sub(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9+/=_\-.]+", r"\1 [REDACTED]", value)
    value = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[REDACTED]@", value)
    value = SECRET_TEXT.sub(r"\1[REDACTED]", value)
    value = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|AKIA[A-Z0-9]{16})\b", "[REDACTED]", value)
    return value


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise EvidenceError("cannot read valid JSON input") from None


def selection(raw):
    if not isinstance(raw, dict):
        raise EvidenceError("selection must be an object")
    required = {"mode", "timezone", "timezone_provenance", "as_of", "start", "end",
                "sources", "projects", "sessions", "runs", "descendants", "repair_bound"}
    if set(raw) != required:
        raise EvidenceError("selection fields missing/unknown: " + ",".join(sorted(set(raw) ^ required)))
    value = dict(raw)
    if value["mode"] == "mine-only":
        value["mode"] = "review"
    if value["mode"] not in ("review", "repair") or value["repair_bound"] != 2:
        raise EvidenceError("mode review|repair and repair_bound 2 required")
    if any(not isinstance(value[key], str) or not value[key].strip()
           for key in ("timezone", "timezone_provenance")):
        raise EvidenceError("timezone and timezone_provenance are required")
    for key in ("start", "end", "as_of"):
        value[key] = utc(value[key])
    if not instant(value["start"]) < instant(value["end"]) <= instant(value["as_of"]):
        raise EvidenceError("require start < end <= as_of")
    if type(value["descendants"]) is not bool:
        raise EvidenceError("descendants must be boolean")
    for key in ("projects", "sessions", "runs"):
        if not isinstance(value[key], list) or any(not isinstance(x, str) or not x for x in value[key]):
            raise EvidenceError(key + " must be a list of exact identities")
        if key == "projects":
            if any(not Path(x).is_absolute() for x in value[key]):
                raise EvidenceError("projects require absolute repository identities, never basenames")
            value[key] = sorted(set(project(x) for x in value[key]))
        else:
            value[key] = sorted(set(value[key]))
    if not isinstance(value["sources"], list) or not value["sources"]:
        raise EvidenceError("explicit expected sources required")
    sources = []
    for source in value["sources"]:
        if not isinstance(source, dict) or set(source) != {"kind", "path"}:
            raise EvidenceError("source needs kind and absolute path")
        if source["kind"] not in ("codex", "claude", "friction", "events", "tickets", "runs", "other"):
            raise EvidenceError("unknown source kind")
        if not isinstance(source["path"], str) or not Path(source["path"]).is_absolute():
            raise EvidenceError("source path must be absolute")
        sources.append({"kind": source["kind"], "path": identity(source["path"])})
    value["sources"] = sorted(sources, key=lambda s: (s["kind"], s["path"]))
    return value


def safe_sink(sources=()):
    root = state_root.improvement_root().resolve()
    if state_root.find_repo_root(root) is not None:
        raise EvidenceError("improvement sink is inside a Git repository")
    for source in sources:
        # A sink tree is an input, but never let output sit within its log subtree.
        path = Path(source["path"])
        if inside(root, path) or inside(path, root):
            raise EvidenceError("improvement sink overlaps a source-log tree")
    return root
