"""Deterministic routing grades and fixed-result gate probes.

This module owns the small amount of state-derived routing information that
is safe to compute without making a model decision.  In particular, it does
not decide whether a Goal is adequate or whether a review lens is sufficient;
it only reports graph shape, declared pack coverage, and adapter capability.
"""

from __future__ import annotations

import hashlib
import json
import re

if __package__:
    from .tickets_adapters import AdapterError, adapter_spec, pack_path
    from .tickets_format import GATE_ID_MARKER, ROOT_EXECUTOR, is_review_stage_id, parse_loop
    from .tickets_markdown import _parse_frontmatter, _sections, dequote
    from .tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root
    from .tickets_context import run_snapshot
else:
    from tickets_adapters import AdapterError, adapter_spec, pack_path
    from tickets_format import GATE_ID_MARKER, ROOT_EXECUTOR, is_review_stage_id, parse_loop
    from tickets_markdown import _parse_frontmatter, _sections, dequote
    from tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root
    from tickets_context import run_snapshot


GRADE_USAGE = "grade <run> <root>"
_UNRESOLVED_COVER = "<unresolved-cover>"


class GradeError(ValueError):
    """The durable ticket projection cannot receive a deterministic grade."""


def _revision_of(baseline) -> str:
    """``workspace_git.revision_of``, loaded after the flat ticket importer."""

    if __package__:
        from .workspace_git import revision_of
    else:
        from workspace_git import revision_of
    return revision_of(baseline)


def _ticket_data(value):
    if isinstance(value, dict):
        return value
    return _parse_frontmatter(str(value or ""))


def _ticket_text(value):
    return value if isinstance(value, str) else ""


def _executor(value):
    return dequote(_ticket_data(value).get("executor"))


def _member_ids(root_id: str, snapshot: dict) -> list[str]:
    """Return the root's executor-result members, excluding review plumbing.

    Gate and ordinary checker stages are descendants in the ticket directory,
    but they are assurance work rather than independent result members.  A
    nested member remains a member of the issued root: the graph's width is
    the number of independently observable result tickets in its cut.
    """

    members = []
    for ticket_id in sorted(snapshot):
        if not ticket_id.startswith(root_id + "."):
            continue
        if is_review_stage_id(ticket_id):
            continue
        executor = _executor(snapshot[ticket_id])
        members.append(ticket_id)
    return members


_SPEC_FIELDS_HEADING = re.compile(r"(?m)^##\s+Spec fields\s*$")
_NEXT_CRAFT_SECTION = re.compile(r"(?m)^##\s+")
_FIELD_SEPARATOR = re.compile(r"\s*;\s*")
_EM_DASH = re.compile(r"\s+[—–-]\s+")
_WORDS = re.compile(r"[a-z0-9_]+")
_COVERS_LINE = re.compile(
    r"(?:^|\n)[^\n]*?\b(?:covers|covered(?:\s+identities)?)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def _required_spec_fields(pack: str) -> list[str]:
    try:
        craft = pack_path(pack).parent / "references" / "craft.md"
        text = craft.read_text(encoding="utf-8")
    except (AdapterError, OSError, UnicodeDecodeError) as error:
        raise GradeError(str(error)) from error
    match = _SPEC_FIELDS_HEADING.search(text)
    if not match:
        return []
    rest = text[match.end():]
    boundary = _NEXT_CRAFT_SECTION.search(rest)
    declared = " ".join(
        line.strip()
        for line in (rest[: boundary.start()] if boundary else rest).splitlines()
        if line.strip()
    )
    if not declared:
        return []
    fields = []
    for value in _FIELD_SEPARATOR.split(declared):
        value = dequote(value)
        if not value:
            continue
        # A pack may explain a field after an em dash.  The stable field name
        # is the portion before that explanation.
        value = dequote(_EM_DASH.split(value, maxsplit=1)[0])
        if value and value not in fields:
            fields.append(value)
    return fields


def _mentioned(field: str, text: str) -> bool:
    """Match a declared field by its meaningful words, not punctuation."""

    field_words = _WORDS.findall(field.casefold().replace("-", "_"))
    body_words = set(_WORDS.findall(text.casefold().replace("-", "_")))
    return bool(field_words) and all(word in body_words for word in field_words)


def grade_snapshot(root_id: str, snapshot: dict) -> dict:
    """Grade one exact ticket snapshot into the closed routing answer."""

    if not isinstance(snapshot, dict) or root_id not in snapshot:
        raise GradeError(f"root ticket not found in exact snapshot: {root_id}")
    root_value = snapshot[root_id]
    root_data = _ticket_data(root_value)
    if not root_data:
        raise GradeError(f"root ticket has no readable frontmatter: {root_id}")
    if str(root_data.get("id") or root_id).strip() != root_id:
        raise GradeError(f"root ticket id differs from requested id: {root_id}")
    root_executor = _executor(root_value)
    members = _member_ids(root_id, snapshot)
    if root_executor == ROOT_EXECUTOR:
        if dequote(root_data.get("independence")) == "checker":
            raise GradeError(f"decomposed root {root_id} must declare independence=gate")
        if len(members) == 1:
            raise GradeError(f"root {root_id} is over-decomposition: one executor result member")
        if not members:
            raise GradeError(f"root {root_id} has no executor result members")
        shape, width = "graph", len(members)
    elif parse_loop(root_data) is not None:
        shape, width = "loop", 1
    else:
        if members:
            raise GradeError(f"root {root_id} is a direct root with executor-result members")
        shape, width = "single", 1
    pack = dequote(root_data.get("pack"))
    if not pack:
        raise GradeError(f"root {root_id} names no pack")
    try:
        deterministic_gate = bool(adapter_spec(pack).deterministic_gate)
    except AdapterError as error:
        raise GradeError(error.detail) from error
    sections = _sections(_ticket_text(root_value)) if _ticket_text(root_value) else {}
    semantic_text = "\n".join(
        sections.get(name, "") for name in ("Goal", "Context", "Suggested files")
    )
    unmentioned = [
        field for field in _required_spec_fields(pack)
        if not _mentioned(field, semantic_text)
    ]
    return {
        "width": width,
        "shape": shape,
        "unmentioned_spec_fields": unmentioned,
        "deterministic_gate": deterministic_gate,
        "over_decomposed": False,
    }


def _section_identity(body: str) -> str:
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _result_identity(value):
    data = _ticket_data(value)
    explicit = data.get("result_identity")
    if explicit:
        return str(explicit).strip()
    text = _ticket_text(value)
    if text:
        result_text = _sections(text).get("Result", "")
        match = re.search(
            r"\b(?:fixed\s+)?result(?:\s+identity)?\s*(?:is|:)?\s*`?([0-9a-f]{7,64})`?",
            result_text, re.IGNORECASE,
        )
        if match:
            return match.group(1)
        match = re.search(
            r"\b(?:tip|revision|as\s+of)\b[^\n:]*[: ]\s*`?([0-9a-f]{7,64})`?",
            result_text, re.IGNORECASE,
        )
        if match:
            return match.group(1)
        return _section_identity(result_text)
    return None


def _identity_for(ticket_id: str, value) -> str:
    data = _ticket_data(value)
    seal = str(data.get("assignment_seal") or "").strip()
    if seal:
        return seal
    return _section_identity(_ticket_text(value))


def _fixed_payload(value):
    """Find a closed verdict payload in review_v1 or Verification prose.

    Older tickets carry only prose.  A fixed-result gate is opt-in: it is
    recognized only when a Verification payload names both a verdict and
    covered identities, so existing composite-gate lifecycle tickets retain
    their materialization behavior.
    """

    data = _ticket_data(value)
    raw = data.get("review_v1")
    candidates = []
    if raw:
        try:
            candidates.append(json.loads(raw) if isinstance(raw, str) else raw)
        except (TypeError, ValueError):
            return None
    text = _ticket_text(value)
    if text:
        sections = _sections(text)
        body = sections.get("Verification", "").strip()
        if body:
            try:
                candidates.append(json.loads(body))
            except (TypeError, ValueError):
                match = _COVERS_LINE.search(body)
                if match:
                    covers = _parse_covers_prose(match.group(1))
                    verdict_match = re.search(
                        r"\b(PASS|FAIL|UNVERIFIED)\b", body,
                    )
                    verdict = verdict_match.group(1) if verdict_match else ""
                    if verdict in {"PASS", "FAIL", "UNVERIFIED"} and covers is not None:
                        candidates.append({"verdict": verdict, "covers": covers})
    for candidate in candidates:
        records = candidate.get("records") if isinstance(candidate, dict) else None
        records = records if isinstance(records, list) else [candidate]
        for record in reversed(records):
            if not isinstance(record, dict) or record.get("kind") not in (None, "Verification"):
                continue
            if record.get("verdict") in {"PASS", "FAIL", "UNVERIFIED"} and "covers" in record:
                return record
    return None


def _parse_covers_prose(value: str):
    """Read the compact ``base ...; result ...; dependencies ...`` form."""

    covers = {}
    for part in re.split(r"\s*;\s*", value.strip()):
        name, separator, identity = part.partition(" ")
        name = name.strip().rstrip(":").casefold()
        identity = identity.strip()
        if not separator or name not in {"base", "result", "dependencies"}:
            continue
        if identity.casefold().startswith("none"):
            covers[name] = []
        else:
            quoted = re.match(r"`([^`]+)`", identity)
            covers[name] = quoted.group(1) if quoted else identity.split()[0]
    return covers if covers else None


def _cover_current(cover, target_id: str, snapshot: dict):
    """Resolve common cover spellings to current durable identities."""

    if isinstance(cover, dict):
        target = snapshot.get(target_id)
        target_data = _ticket_data(target)
        dependencies = target_data.get("depends_on") or []
        if "id" in cover and "identity" in cover:
            covered_id = str(cover.get("id") or "")
            current_identity = (
                _identity_for(covered_id, snapshot[covered_id])
                if covered_id in snapshot else _UNRESOLVED_COVER
            )
            return {"id": covered_id, "identity": current_identity}
        resolved = {}
        for key, value in sorted(cover.items()):
            name = str(key)
            if name in snapshot:
                resolved[name] = _identity_for(name, snapshot[name])
            elif name in {"base", "base_identity"}:
                current = (
                    target_data.get("base_identity")
                    or target_data.get("workspace_baseline")
                    or target_data.get("assignment_seal")
                )
                # A `workspace_baseline` stamp is a revision and then what was
                # uncommitted at the time; reading the revision out of it is
                # `workspace_git.revision_of`'s, beside the `_baseline` that
                # writes it. Loaded here rather than at module scope, so the
                # flat ticket importer is initialized first.
                resolved[name] = _revision_of(current or _UNRESOLVED_COVER)
            elif name in {"result", "result_identity"}:
                current = _result_identity(target)
                resolved[name] = str(current or _UNRESOLVED_COVER)
            elif name in {"dependencies", "dependency_identities"}:
                current = target_data.get("dependency_identities")
                if not current:
                    current = [
                        _identity_for(str(item), snapshot[str(item)])
                        if str(item) in snapshot else _UNRESOLVED_COVER
                        for item in dependencies
                    ]
                resolved[name] = current
            else:
                resolved[name] = _cover_current(value, target_id, snapshot)
        return resolved
    if isinstance(cover, list):
        return [_cover_current(item, target_id, snapshot) for item in cover]
    value = str(cover or "").strip()
    if value in snapshot:
        return _identity_for(value, snapshot[value])
    if value.startswith("ticket:") and value[7:] in snapshot:
        ticket_id = value[7:]
        return _identity_for(ticket_id, snapshot[ticket_id])
    return value


def _cover_equal(current, expected) -> bool:
    if isinstance(current, dict) and isinstance(expected, dict):
        return set(current) == set(expected) and all(
            _cover_equal(current[key], expected[key]) for key in current
        )
    if isinstance(current, list) and isinstance(expected, list):
        return len(current) == len(expected) and all(
            _cover_equal(actual, wanted)
            for actual, wanted in zip(current, expected)
        )
    if isinstance(current, str) and isinstance(expected, str):
        actual, wanted = current.strip().lower(), expected.strip().lower()
        if actual.startswith("sha256:"):
            actual = actual[7:]
        if wanted.startswith("sha256:"):
            wanted = wanted[7:]
        return actual == wanted
    return current == expected


def fixed_gate_snapshot(target_id: str, snapshot: dict) -> dict | None:
    """Return a deterministic fixed-result gate answer, or ``None``.

    ``reusable`` is true only when every declared cover resolves to the same
    current identity.  The caller can then avoid issuing a checker packet.
    No verdict adequacy is inferred here; the stored verdict is returned as
    evidence for the caller's route.
    """

    value = snapshot.get(target_id)
    if value is None:
        return None
    payload = _fixed_payload(value)
    if payload is None:
        return None
    covers = payload.get("covers")
    if not isinstance(covers, (dict, list)) or not covers:
        return None
    # A mapping may carry the expected identity as its value.  For a named
    # ticket/path key we resolve the current identity; opaque identities stay
    # opaque and therefore compare exactly.
    current = _cover_current(covers, target_id, snapshot)
    reusable = _cover_equal(current, covers)
    return {
        "target": target_id,
        "verdict": payload["verdict"],
        "covers": covers,
        "reusable": reusable,
        "outcome": "reused" if reusable else "stale",
    }


def _cmd_grade(rest):
    args = list(rest)
    if len(args) != 2:
        return {"error": f"usage: {GRADE_USAGE}"}
    run, root_id = args
    for kind, value in (("run id", run), ("ticket id", root_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    run_dir = tickets_root / run
    try:
        with _run_lock(run):
            snapshot, failures = run_snapshot(run_dir) if run_dir.is_dir() else ({}, [])
            if failures:
                return {"error": f"unreadable ticket: {failures[0][0]}"}
            try:
                grade = grade_snapshot(root_id, snapshot)
            except GradeError as error:
                return {"error": str(error)}
    except OSError as error:
        return {"error": f"unable to grade: {error}"}
    return {"grade": {"run": run, "root": root_id, **grade}}


def _cmd_fixed_gate(rest):
    """Probe a fixed result without issuing a checker packet.

    ``None`` means the target is an ordinary lifecycle ticket and the
    existing gate materializer should handle it.  An explicit fixed result
    returns a closed route answer; stale covers ask the caller to issue one
    fresh checker stage.
    """

    args = list(rest)
    if len(args) != 2:
        return None
    run, target_id = args
    if any(_segment_error(kind, value) is not None for kind, value in (("run id", run), ("ticket id", target_id))):
        return None
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    run_dir = tickets_root / run
    try:
        with _run_lock(run):
            snapshot, failures = run_snapshot(run_dir) if run_dir.is_dir() else ({}, [])
            if failures:
                return {"error": f"unreadable ticket: {failures[0][0]}"}
            probe = fixed_gate_snapshot(target_id, snapshot)
    except OSError as error:
        return {"error": f"unable to gate: {error}"}
    if probe is None:
        return None
    return {"gate": {"run": run, "root": target_id, "mode": "fixed", **probe}}


def _cmd_gate(rest):
    """Route fixed-result probes before the established gate materializer."""

    fixed = _cmd_fixed_gate(rest)
    if fixed is not None:
        if "error" not in fixed and fixed.get("gate", {}).get("outcome") == "stale":
            if __package__:
                from .tickets_dispatch_gate import _cmd_checker_stage
            else:
                from tickets_dispatch_gate import _cmd_checker_stage
            checker = _cmd_checker_stage(rest)
            if "error" not in checker:
                fixed["gate"]["checker_stage"] = checker.get("checker_stage")
                fixed["gate"]["outcome"] = "checker-emitted"
        return fixed
    if __package__:
        from .tickets_dispatch_gate import _cmd_gate as materialize_gate
    else:
        from tickets_dispatch_gate import _cmd_gate as materialize_gate
    return materialize_gate(rest)


__all__ = (
    "GRADE_USAGE", "GradeError", "_cmd_fixed_gate", "_cmd_gate", "_cmd_grade", "fixed_gate_snapshot",
    "grade_snapshot",
)
