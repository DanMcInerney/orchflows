"""Canonical Fixed-input parsing and portable pack identity resolution.

The admission layer supplies ticket bytes, sibling bytes, the stable adapter
id, and execution-only roots.  This module returns only portable findings and
fingerprints; host paths never enter a receipt.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

if __package__:
    from . import tickets_store as _store
    from .tickets_format import (
        DuplicateJsonKey, canonical_json, parse_canonical_json,
        _parse_frontmatter, _sections,
    )
else:  # installed flat beside tickets.py
    import tickets_store as _store
    from tickets_format import (
        DuplicateJsonKey, canonical_json, parse_canonical_json,
        _parse_frontmatter, _sections,
    )


NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ADMITTED_PREFIXES = ("v1:", "v2:")


def is_admitted(data: dict) -> bool:
    """Whether this ticket was written on either side of the boundary.

    Both graded versions are graded alike: the prefix names which admission
    grammar produced the ticket, never how much of it is worth grading.  Only
    the shape that predates the boundary -- no ``admission`` field at all --
    is read as legacy, and that shape no CLI write path can still produce.
    """

    return str(data.get("admission") or "").startswith(ADMITTED_PREFIXES)
OBJECT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
TERMINAL = frozenset({"complete", "blocked", "stalled", "limited", "failed"})
COMMON_KINDS = frozenset({"artifact", "ticket-section"})
ADAPTER_KINDS = {
    "plain-artifact": COMMON_KINDS,
    "git": COMMON_KINDS | {"git-tree", "git-path", "git-symbol"},
    "document-tree": COMMON_KINDS | {"document-revision"},
    "evidence-store": COMMON_KINDS | {"evidence-packet"},
    "git-plus-render": COMMON_KINDS | {"git-tree", "git-path", "git-symbol", "view-identity"},
}
SCHEMAS = {
    "artifact": frozenset({"kind", "locator", "sha256"}),
    "git-tree": frozenset({"kind", "repo", "revision"}),
    "git-path": frozenset({"kind", "path", "repo", "revision"}),
    "git-symbol": frozenset({"kind", "path", "repo", "revision", "symbol"}),
    "document-revision": frozenset({"kind", "locator", "sha256"}),
    "evidence-packet": frozenset({"kind", "locator", "sha256"}),
    "view-identity": frozenset({
        "breakpoint", "capture", "kind", "repo", "revision", "sha256", "state", "view",
    }),
}


def _canonical(value) -> str:
    return canonical_json(value)


def _finding(code: str, detail: str, field: str = "Fixed inputs") -> dict:
    return {"code": code, "field": field, "detail": detail}


def _ordered(findings) -> list:
    rows = {(str(x["code"]), str(x["field"]), str(x["detail"])) for x in findings}
    return [_finding(code, detail, field) for code, field, detail in sorted(rows)]


def section_body(text: str, section: str) -> str:
    """Return the exact normalized section body shared by ticket readers."""

    return _sections(text).get(section, "")


def parse_input_records(text: str) -> dict:
    """Parse one canonical JSON record per non-empty Fixed-input line."""

    findings, records, seen = [], [], set()
    for position, line in enumerate(section_body(text, "Fixed inputs").splitlines(), start=1):
        if not line.strip():
            continue
        if not line.startswith("- input: "):
            findings.append(_finding("non-identity", f"line {position}"))
            continue
        encoded = line[len("- input: "):]
        try:
            value = parse_canonical_json(encoded)
        except DuplicateJsonKey as error:
            findings.append(_finding("input-json-duplicate-key", f"line {position}:{error}"))
            continue
        except (TypeError, ValueError):
            findings.append(_finding("input-json-invalid", f"line {position}"))
            continue
        if _canonical(value) != encoded:
            findings.append(_finding("input-json-noncanonical", f"line {position}"))
            continue
        if not isinstance(value, dict):
            findings.append(_finding("input-record-shape", f"line {position}:not-object"))
            continue
        variant = value.get("type")
        expected = ({"name", "type", "value"} if variant == "literal" else
                    {"identity", "name", "type"} if variant == "identity" else set())
        if set(value) != expected:
            findings.append(_finding("input-record-shape", f"line {position}:{variant or '<missing>'}"))
            continue
        name = value.get("name")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            findings.append(_finding("input-name-invalid", f"line {position}"))
            continue
        if name in seen:
            findings.append(_finding("input-name-duplicate", name))
            continue
        seen.add(name)
        if variant == "identity" and not isinstance(value.get("identity"), dict):
            findings.append(_finding("identity-schema", f"{name}:not-object"))
            continue
        records.append(value)
    return {"records": records, "findings": _ordered(findings)}


def _relative(value, *, directory=False) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or value.startswith("/"):
        return False
    if directory != value.endswith("/"):
        return False
    parts = value.rstrip("/").split("/")
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


def _digest(value) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _context_path(context, key):
    value = context.get(key)
    if value:
        return Path(value).expanduser().resolve()
    run_project = context.get("run_project")
    if key == "project_root" and isinstance(run_project, dict) and run_project.get("root"):
        return Path(run_project["root"]).expanduser().resolve()
    if key == "sink_root" and context.get("tickets_root"):
        return Path(context["tickets_root"]).expanduser().resolve().parent
    if key == "project_root":
        process = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False, cwd=str(_store._cwd()),
        )
        if process.returncode == 0 and process.stdout.strip():
            return Path(process.stdout.strip()).resolve()
    if key in {"sink_root", "tickets_root"}:
        try:
            if __package__:
                from . import state_root
            else:
                import state_root
            root = state_root.state_root().resolve()
            return root / "tickets" if key == "tickets_root" else root
        except (ImportError, OSError):
            pass
    return None


def _git(project, *args):
    if project is None:
        return (1, b"", b"project root is unavailable")
    process = subprocess.run(
        ["git", "-C", str(project), *args], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    return (process.returncode, process.stdout, process.stderr)


def _git_blob(project, revision, path):
    code, content, _ = _git(project, "show", f"{revision}:{path}")
    return content if code == 0 else None


def _remote(value):
    text = str(value or "").strip().replace("\\", "/")
    if text.endswith(".git"):
        text = text[:-4]
    return text.rstrip("/").casefold()


def _revision(project, value):
    if not isinstance(value, str) or not OBJECT_RE.fullmatch(value):
        return (None, _finding("git-revision-invalid", str(value)))
    code, resolved, _ = _git(project, "rev-parse", "--verify", f"{value}^{{commit}}")
    if code != 0 or resolved.decode("ascii", "replace").strip() != value:
        return (None, _finding("git-revision-unresolved", value))
    code, tree, _ = _git(project, "rev-parse", f"{value}^{{tree}}")
    if code != 0:
        return (None, _finding("git-revision-unresolved", value))
    return (tree.decode("ascii").strip(), None)


def _portable_file(root, relative):
    if root is None:
        return (None, _finding("identity-root-unavailable", "execution root"))
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return (None, _finding("identity-path-escape", relative))
    try:
        return (candidate.read_bytes(), None)
    except OSError:
        return (None, _finding("identity-locator-absent", relative))


def _hash_bytes(content, expected):
    if not _digest(expected):
        return _finding("identity-digest-invalid", str(expected))
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        return _finding("identity-digest-mismatch", expected)
    return None


def _artifact(identity, context):
    locator = identity.get("locator")
    if not isinstance(locator, str):
        return (None, [_finding("identity-locator-invalid", "artifact")], "")
    if locator.startswith("sink:"):
        relative = locator[5:]
        root = _context_path(context, "sink_root")
        portable = locator
    elif locator.startswith("project:"):
        rest = locator[8:]
        revision, separator, relative = rest.partition(":")
        if not separator:
            return (None, [_finding("identity-locator-invalid", locator)], "")
        if not _relative(relative):
            return (None, [_finding("identity-path-invalid", str(relative))], "")
        root = _context_path(context, "project_root")
        tree, error = _revision(root, revision)
        if error:
            return (None, [error], "")
        content = _git_blob(root, revision, relative)
        findings = [] if content is not None else [_finding("identity-locator-absent", relative)]
        if content is not None:
            mismatch = _hash_bytes(content, identity.get("sha256"))
            if mismatch:
                findings.append(mismatch)
        return (content, findings, f"artifact:project:{tree}:{relative}:{identity.get('sha256')}")
    else:
        return (None, [_finding("identity-locator-invalid", str(locator))], "")
    if not _relative(relative):
        return (None, [_finding("identity-path-invalid", str(relative))], "")
    content, error = _portable_file(root, relative)
    findings = [error] if error else []
    if content is not None:
        mismatch = _hash_bytes(content, identity.get("sha256"))
        if mismatch:
            findings.append(mismatch)
    return (content, findings, f"artifact:{portable}:{identity.get('sha256')}")


def _dependencies(ticket_id, siblings):
    found, frontier = set(), [ticket_id]
    while frontier:
        current = frontier.pop()
        data = _parse_frontmatter(siblings.get(current, ""))
        for dependency in data.get("depends_on") or []:
            dependency = str(dependency)
            if dependency not in found:
                found.add(dependency)
                frontier.append(dependency)
    return found


def _ticket_section(identity, context):
    run, ticket_id, section = identity.get("run"), identity.get("ticket"), identity.get("section")
    segment = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    if not all(isinstance(value, str) and segment.fullmatch(value) for value in (run, ticket_id)):
        return (None, [_finding("ticket-coordinate-invalid", f"{run}/{ticket_id}")], "")
    current_run = str(context.get("run") or "")
    siblings = context.get("siblings") or {}
    owner = str(context.get("ticket_id") or "")
    same = run == current_run
    if same:
        text = siblings.get(ticket_id)
        if text is None:
            return (None, [_finding("ticket-section-absent", f"{run}/{ticket_id}")], "")
        if "sha256" in identity:
            return (None, [_finding("ticket-section-digest-forbidden", f"{run}/{ticket_id}")], "")
        if section == "Result":
            if ticket_id not in _dependencies(owner, siblings):
                return (None, [_finding("ticket-result-not-dependency", str(ticket_id))], "")
            if str(_parse_frontmatter(text).get("status") or "") not in TERMINAL:
                return (None, [_finding("ticket-result-not-terminal", str(ticket_id))], "")
        elif section == "Completion test":
            cohort = str(_parse_frontmatter(siblings.get(owner, "")).get("cohort") or "")
            root_id = cohort.removeprefix("v1:root:") if cohort.startswith("v1:root:") else ""
            named_acceptance = ".gate." in owner and context.get("input_name") == "acceptance"
            if ticket_id != root_id and not named_acceptance:
                return (None, [_finding("ticket-completion-owner-invalid", str(ticket_id))], "")
        else:
            return (None, [_finding("ticket-section-invalid", str(section))], "")
    else:
        tickets_root = _context_path(context, "tickets_root")
        if tickets_root is None:
            sink = _context_path(context, "sink_root")
            tickets_root = sink / "tickets" if sink else None
        if tickets_root is None:
            return (None, [_finding("identity-root-unavailable", "tickets root")], "")
        try:
            text = (tickets_root / str(run) / f"{ticket_id}.md").read_text(encoding="utf-8")
        except OSError:
            return (None, [_finding("ticket-section-absent", f"{run}/{ticket_id}")], "")
        if not _digest(identity.get("sha256")):
            return (None, [_finding("identity-digest-invalid", str(identity.get("sha256")))], "")
    content = section_body(text, str(section)).encode("utf-8")
    if str(section) not in _sections(text):
        return (None, [_finding("ticket-section-absent", f"{run}/{ticket_id}:{section}")], "")
    digest = hashlib.sha256(content).hexdigest()
    if not same and digest != identity.get("sha256"):
        return (content, [_finding("identity-digest-mismatch", str(identity.get("sha256")))], "")
    return (content, [], f"ticket-section:{run}:{ticket_id}:{section}:{digest}")


def _git_identity(identity, context):
    project = _context_path(context, "project_root")
    if identity.get("repo") != "run-project":
        return (None, [_finding("git-project-mismatch", str(identity.get("repo")))], "")
    expected_remote = context.get("project_remote")
    run_project = context.get("run_project")
    if expected_remote is None and isinstance(run_project, dict):
        expected_remote = run_project.get("origin")
    if expected_remote:
        code, actual, _ = _git(project, "config", "--get", "remote.origin.url")
        if code != 0 or _remote(actual.decode("utf-8", "replace")) != _remote(expected_remote):
            return (None, [_finding("git-remote-mismatch", "run-project")], "")
    tree, error = _revision(project, identity.get("revision"))
    if error:
        return (None, [error], "")
    kind = identity["kind"]
    if kind == "git-tree":
        return (None, [], f"git-tree:{tree}")
    path = identity.get("path")
    if not _relative(path):
        return (None, [_finding("identity-path-invalid", str(path))], "")
    content = _git_blob(project, identity["revision"], path)
    if content is None:
        return (None, [_finding("git-path-absent", path)], "")
    if kind == "git-symbol":
        symbol = identity.get("symbol")
        source = content.decode("utf-8", "replace")
        present = (
            isinstance(symbol, str) and bool(symbol)
            and re.search(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])", source) is not None
        )
        if not present:
            return (content, [_finding("git-symbol-absent", str(symbol))], "")
    blob = hashlib.sha256(content).hexdigest()
    suffix = f":{identity.get('symbol') or ''}" if kind == "git-symbol" else ""
    return (content, [], f"{kind}:{tree}:{path}:{blob}{suffix}")


def _rooted(identity, context, root_name, schemes):
    roots = context.get("input_literals") or {}
    declaration = roots.get(root_name)
    scheme = next(
        (item for item in schemes if isinstance(declaration, str) and declaration.startswith(f"{item}:")),
        None,
    )
    if scheme is None:
        return (None, [_finding("adapter-root-invalid", root_name)], "")
    prefix = f"{scheme}:"
    relative_root = declaration[len(prefix):]
    if not _relative(relative_root, directory=True):
        return (None, [_finding("adapter-root-invalid", root_name)], "")
    locator = identity.get("locator")
    if not _relative(locator):
        return (None, [_finding("identity-path-invalid", str(locator))], "")
    base = _context_path(context, "project_root" if scheme == "project" else "sink_root")
    root = (base / relative_root).resolve() if base else None
    content, error = _portable_file(root, locator)
    findings = [error] if error else []
    if content is not None:
        mismatch = _hash_bytes(content, identity.get("sha256"))
        if mismatch:
            findings.append(mismatch)
    return (content, findings, f"{identity['kind']}:{declaration}:{locator}:{identity.get('sha256')}")


def _view(identity, context):
    projected = {"kind": "git-path", "path": identity.get("capture"), "repo": identity.get("repo"), "revision": identity.get("revision")}
    content, findings, fingerprint = _git_identity(projected, context)
    if content is not None:
        mismatch = _hash_bytes(content, identity.get("sha256"))
        if mismatch:
            findings.append(mismatch)
    values = ":".join(str(identity.get(key)) for key in ("view", "breakpoint", "state"))
    return (content, findings, f"view-identity:{fingerprint}:{values}:{identity.get('sha256')}")


def resolve_identity_payload(*, identity, adapter_id, context=None, mode="input") -> dict:
    """Resolve one identity through the selected stable adapter."""

    context = dict(context or {})
    kind = identity.get("kind") if isinstance(identity, dict) else None
    if not isinstance(kind, str):
        return {"findings": [_finding("identity-schema", "missing kind")], "fingerprint": "identity:error", "bytes": None}
    expected = SCHEMAS.get(kind)
    if kind == "ticket-section":
        same = identity.get("run") == str(context.get("run") or "")
        expected = frozenset({"kind", "run", "section", "ticket"} | (set() if same else {"sha256"}))
    if expected is None:
        return {"findings": [_finding("identity-kind-unsupported", kind)], "fingerprint": f"identity:{kind}:error", "bytes": None}
    if set(identity) != set(expected):
        return {"findings": [_finding("identity-schema", f"{kind}:{sorted(identity)}")], "fingerprint": f"identity:{kind}:error", "bytes": None}
    if any(not isinstance(identity.get(key), str) for key in expected):
        return {"findings": [_finding("identity-schema", f"{kind}:non-string")], "fingerprint": f"identity:{kind}:error", "bytes": None}
    allowed = ADAPTER_KINDS.get(adapter_id)
    if allowed is None:
        return {"findings": [_finding("adapter-unknown", str(adapter_id))], "fingerprint": "identity:adapter-error", "bytes": None}
    if kind not in allowed:
        return {"findings": [_finding("adapter-kind-unsupported", f"{adapter_id}:{kind}")], "fingerprint": f"identity:{kind}:error", "bytes": None}
    if kind == "artifact":
        content, findings, fingerprint = _artifact(identity, context)
    elif kind == "ticket-section":
        content, findings, fingerprint = _ticket_section(identity, context)
    elif kind.startswith("git-"):
        content, findings, fingerprint = _git_identity(identity, context)
    elif kind == "document-revision":
        content, findings, fingerprint = _rooted(identity, context, "document-root", ("project", "sink"))
    elif kind == "evidence-packet":
        content, findings, fingerprint = _rooted(identity, context, "evidence-store-root", ("sink",))
    else:
        content, findings, fingerprint = _view(identity, context)
    return {"findings": _ordered(findings), "fingerprint": fingerprint or f"identity:{kind}:error", "bytes": content}


def grade_inputs(*, ticket_id, text, siblings, adapter_id, context=None) -> dict:
    """Grade all records and return ordered portable codes plus fingerprint."""

    data = _parse_frontmatter(text)
    if not is_admitted(data):
        return {"findings": [], "fingerprint": "inputs:legacy-unadmitted"}
    parsed = parse_input_records(text)
    findings = list(parsed["findings"])
    records = parsed["records"]
    literals = {item["name"]: item["value"] for item in records if item["type"] == "literal"}
    resolution_context = {
        **dict(context or {}), "siblings": siblings, "ticket_id": ticket_id,
        "run": str(data.get("run") or (context or {}).get("run") or ""),
        "input_literals": literals,
    }
    fingerprints = []
    baseline_count = 0
    for item in records:
        if item["type"] == "literal":
            fingerprints.append({"name": item["name"], "literal": item["value"]})
            continue
        identity = item["identity"]
        baseline_count += int(item["name"] == "baseline" and identity.get("kind") == "git-tree")
        resolved = resolve_identity_payload(
            identity=identity, adapter_id=adapter_id,
            context={**resolution_context, "input_name": item["name"]},
        )
        findings.extend(resolved["findings"])
        fingerprints.append({"fingerprint": resolved["fingerprint"], "name": item["name"]})
    if adapter_id in {"git", "git-plus-render"} and baseline_count != 1:
        findings.append(_finding("git-baseline-cardinality", str(baseline_count)))
    root_rules = {
        "document-tree": ("document-root", ("project:", "sink:")),
        "evidence-store": ("evidence-store-root", ("sink:",)),
    }
    if adapter_id in root_rules:
        root_name, prefixes = root_rules[adapter_id]
        declaration = literals.get(root_name)
        if list(literals).count(root_name) != 1:
            findings.append(_finding("adapter-root-cardinality", root_name))
        elif not isinstance(declaration, str) or not any(
            declaration.startswith(prefix) and _relative(declaration[len(prefix):], directory=True)
            for prefix in prefixes
        ):
            findings.append(_finding("adapter-root-invalid", root_name))
    encoded = _canonical(fingerprints).encode("utf-8")
    return {
        "findings": _ordered(findings),
        "fingerprint": f"inputs:sha256:{hashlib.sha256(encoded).hexdigest()}",
    }


__all__ = ("grade_inputs", "is_admitted", "parse_input_records", "resolve_identity_payload", "section_body")
