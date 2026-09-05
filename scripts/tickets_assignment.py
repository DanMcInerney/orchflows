"""The sealed ticket, read as one dispatchable assignment.

The ticket is the assignment: there is no wire object between it and the
child. This module grades one ticket against everything a dispatch requires
of it -- admitted claim, complete Goal and Context, a lawful review lane, an
established workspace -- and resolves the facts a launch prompt cannot
derive from the ticket alone.

It does not compose the prompt. `tickets_dispatch_launch.py` owns the one
child-facing surface, and this module hands it resolved facts.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

if __package__:
    from . import rings
    from .tickets_adapters import (
        ADAPTER_REGISTRY, Adapter, AdapterError, adapter_for_key,
        adapter_for_ticket, adapter_spec, derived_isolation,
    )
    from .tickets_context import graded_admission, run_snapshot
    from .tickets_dispatch_launch import resolved_role_profile
    from .tickets_format import (
        ARTIFACT_CLAUSE, MAKES_FIELD, REPORT_SECTION, _executor_of, lease_of,
        _extract_flag, _read_utf8, _sections, dequote,
    )
    from .tickets_pins import (
        STANDARDS_FIELD, adapter_standard, standards_of,
    )
    from .tickets_registry import EXECUTOR_REGISTRY
    from .tickets_transitions import CHECKABLE_STATUSES
    from .tickets_store import (
        NO_SINK_ERROR, _executor_script, _load_ticket, _tickets_root,
    )
    from .workspace_git import BASELINE_KEY, BRANCH_KEY
else:
    import rings
    from tickets_adapters import (
        ADAPTER_REGISTRY, Adapter, AdapterError, adapter_for_key,
        adapter_for_ticket, adapter_spec, derived_isolation,
    )
    from tickets_context import graded_admission, run_snapshot
    from tickets_dispatch_launch import resolved_role_profile
    from tickets_format import (
        ARTIFACT_CLAUSE, MAKES_FIELD, REPORT_SECTION, _executor_of, lease_of,
        _extract_flag, _read_utf8, _sections, dequote,
    )
    from tickets_pins import (
        STANDARDS_FIELD, adapter_standard, standards_of,
    )
    from tickets_registry import EXECUTOR_REGISTRY
    from tickets_transitions import CHECKABLE_STATUSES
    from tickets_store import (
        NO_SINK_ERROR, _executor_script, _load_ticket, _tickets_root,
    )
    from workspace_git import BASELINE_KEY, BRANCH_KEY

ASSIGNMENT_SECTIONS = (("goal", "Goal"), ("context", "Context"))
# The installer's flat name surface (`installer/planning.py`): one
# deterministic path per canonical name, which is what a launch hands a
# child for the kernel contract its applied skill is a method of.
BY_NAME_DIR = "by-name"


def _attempt_workspace(data: dict):
    """The tree the ticket's dispatch attempt recorded, through its one owner."""

    try:
        if __package__:
            from . import workspace_record
        else:  # pragma: no cover - the flat installed layout
            import workspace_record
    except ImportError:  # pragma: no cover - a partial install
        return None
    return workspace_record.attempt_workspace(data)


def workspace_establishment_finding(data: dict, workspace):
    """Return the refusal code/detail for a non-established workspace."""

    try:
        adapter = adapter_for_ticket(data, target=workspace)
    except AdapterError as error:
        return error.code, error.detail
    if adapter is None:
        return None
    required = derived_isolation(data.get("isolation"), adapter.key) == "required"
    if not required:
        return None
    recorded = _attempt_workspace(data)
    if not recorded:
        return (
            "workspace-unestablished",
            "required workspace has no pre-dispatch establishment on this attempt",
        )
    if workspace != recorded:
        return (
            "workspace-mismatch",
            "dispatch workspace does not equal the recorded candidate workspace",
        )
    if adapter.workspace_strategy == "git" and any(
        not str(data.get(key) or "").strip()
        for key in (BRANCH_KEY, BASELINE_KEY)
    ):
        return (
            "workspace-unestablished",
            "Git candidate lacks its pre-dispatch branch or baseline record",
        )
    if adapter.workspace_strategy == "evidence-store" and not Path(recorded).is_dir():
        return (
            "workspace-unestablished",
            "recorded evidence-store workspace is unavailable",
        )
    return None


def _claim_is_stale(ticket_path, text: str, data: dict, now: datetime):
    if data.get("dispatch_v1"):
        if __package__:
            from .tickets_dispatch_schema import attempt_window
        else:
            from tickets_dispatch_schema import attempt_window
        window, failure = attempt_window(data)
        if failure is not None:
            return True, [failure["error"]]
        attempt = window["attempt"]
        return (
            attempt.get("state") != "live" or now >= window["lease_expires_at"],
            [],
        )
    # Without a dispatch record there is no live claim to defend: the lease
    # lives in dispatch_v1 alone (contracts/dispatch.md).
    return True, []


def _dependency_paths(loaded: dict, ticket_path: Path) -> list:
    return [
        str(ticket_path.with_name(f"{dependency}.md"))
        for dependency in (loaded.get("depends_on") or [])
    ]


def _workspace_line(path: Path):
    """The standard's own `## Workspace` sentence, collapsed to one line, or None."""

    text, failure = _read_utf8(path, "standard")
    if failure is not None:
        return None
    collapsed = re.sub(r"\s+", " ", _sections(text).get("Workspace", "")).strip()
    return collapsed or None


def _manifest(standard):
    """`(manifest path, workspace line)` for one resolved pinned standard."""

    if not standard:
        return None, None
    path = Path(str(standard["path"]))
    return str(path), _workspace_line(path)


def _skill_path(executor, *, owner=None):
    """The applied skill's own manifest, resolved through the one ring
    resolver -- the same guarantee `manifest_path` already gives the standard."""

    name = dequote(executor)
    if not name:
        return None
    try:
        return str(rings.resolve("skill", name, owner=owner)["path"])
    except rings.RingError:
        return None


def _kernel_contract(executor):
    """Where the child reads the verb its applied skill is the method of."""

    name = dequote(executor)
    if not name:
        return None
    try:
        minted = rings.lib_root() / BY_NAME_DIR / name / rings.MANIFESTS["skill"]
    except (OSError, RuntimeError):  # pragma: no cover - no resolvable library
        return _skill_path(name)
    return str(minted) if minted.is_file() else _skill_path(name)


def _applied_skill(loaded: dict):
    """The `{name, path, environment}` of the ticket's applied skill, or None."""

    name = dequote(loaded.get("skill"))
    if not name:
        return None
    try:
        record = rings.resolve(
            "skill", name, trust=False,
            owner=dequote(loaded.get("workflow")) or None,
        )
    except rings.RingError:
        return {"name": name, "path": None, "environment": False}
    return {
        "name": name,
        "path": str(record["path"]),
        "environment": _declares_environment(record["dir"]),
    }


def _declares_environment(item_dir) -> bool:
    """Whether this item carries its own `requirements.txt`."""

    try:
        if __package__:
            from . import orchflows_envs
        else:  # pragma: no cover - the flat installed layout
            import orchflows_envs
    except ImportError:  # pragma: no cover - a partial install
        return False
    return orchflows_envs.requirements_of(item_dir) is not None


def _standards(loaded: dict):
    """`[{"name", "path", "digest"}]` for every level this ticket stamped.

    Broad to narrow, at the pinned digests rather than at whatever resolves
    now: a launch that handed the child a fresher file than the one its seal
    covers would be the substitution the pin exists to prevent. A level that
    no longer resolves returns a classified refusal as a second value. This
    keeps direct assignment readers fail closed even if admission changes.
    """

    if __package__:
        from .standards_support import StandardError, resolve_chain
    else:  # pragma: no cover - direct/installed flat script path
        from standards_support import StandardError, resolve_chain
    levels = standards_of(loaded.get(STANDARDS_FIELD))
    if not levels:
        return [], None
    try:
        chain = {
            str(link["name"]): link
            for link in resolve_chain(
                [name for name, _digest in levels],
                owner=dequote(loaded.get("workflow")) or None,
            )
        }
    except StandardError as error:
        return [], {"error": error.detail, "code": error.code}
    stamped = []
    for name, digest in levels:
        link = chain.get(name)
        if link is None:
            return [], {
                "error": f"pinned standard '{name}' no longer resolves in its stamped chain",
                "code": "standard-chain-changed",
            }
        stamped.append({
            "name": name, "path": str(link["path"]), "digest": digest,
            "adapter": str(link.get("adapter") or ""),
        })
    return stamped, None


def _adapter(value):
    if isinstance(value, Adapter):
        return value
    named = dequote(value)
    if named in ADAPTER_REGISTRY:
        return adapter_for_key(named)
    return adapter_spec(named)


def git_candidate(standard) -> bool:
    """Whether the landing merges a candidate branch this standard's child
    committed into."""

    if not str(standard or "").strip():
        return False
    try:
        return _adapter(standard).workspace_strategy == "git"
    except AdapterError:
        return False


def commits_in_place(standard) -> bool:
    """Whether this standard's child must commit in the tree it stands in for
    its bytes to survive."""

    if not str(standard or "").strip():
        return False
    try:
        return _adapter(standard).commits_in_place
    except AdapterError:
        return False


def artifact_kind(standard):
    """The typed artifact prefix the standard's adapter fixes, or None."""

    if not str(standard or "").strip():
        return None
    try:
        return _adapter(standard).artifact_kind
    except AdapterError:
        return None


def lens_keys(loaded: dict, sections: dict, adapter=None) -> list:
    """The artifact kinds this child makes or reviews, in stable order."""

    # Only the verb whose product is a findings file is keyed by the
    # identities on its Context; for every other executor an artifact line
    # is evidence it read, not the product it owes.
    if EXECUTOR_REGISTRY.get(_executor_of(loaded), {}).get("files_findings"):
        kinds = sorted({
            line.strip()[len(ARTIFACT_CLAUSE):].split(":", 1)[0].strip()
            for line in sections.get("Context", "").splitlines()
            if line.strip().startswith(ARTIFACT_CLAUSE)
        })
        if kinds:
            return kinds
    made = dequote(loaded.get(MAKES_FIELD))
    if made:
        return [made]
    if adapter is None:
        adapter = adapter_standard(loaded)
    kind = artifact_kind(adapter)
    return [kind] if kind else []


def lens_key(loaded: dict, sections: dict, adapter=None):
    """Compatibility projection for callers that still expect one kind."""

    keys = lens_keys(loaded, sections, adapter)
    return keys[0] if len(keys) == 1 else None


def dispatch_assignment(rest, *, attempt=None):
    """Grade one ticket for dispatch and resolve every fact its launch names."""

    args = list(rest)
    dispatched_name = _extract_flag(args, "--by")
    workspace = _extract_flag(args, "--workspace")
    if len(args) != 2:
        return {"error": "assignment reading takes one <run> and one <id>"}
    run, ticket_id = args
    root = _tickets_root()
    if root is None:
        return {"error": NO_SINK_ERROR}
    ticket_path = root / run / f"{ticket_id}.md"
    if not ticket_path.is_file():
        return {"error": f"ticket not found: {run}/{ticket_id}"}
    loaded = _load_ticket(ticket_path)
    if "error" in loaded:
        return {"error": loaded["error"]}
    text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    status = dequote(loaded.get("status"))
    if status not in CHECKABLE_STATUSES:
        return {"error": f"ticket is not claimed (status '{status}'): dispatch requires an admitted claim"}
    snapshot, failures = run_snapshot(ticket_path.parent)
    if failures:
        return failures[0][1]
    grade = graded_admission(ticket_id, text, snapshot, run)
    if grade["findings"]:
        return {"error": "dispatch admission grade failed", "findings": grade["findings"]}
    stored = str(loaded.get("admission") or "")
    if stored != grade["receipt"]:
        return {"error": f"ticket has no current admission receipt: stored {stored or '<missing>'}, current {grade['receipt']}"}
    sections = _sections(text)
    executor = _executor_of(loaded)
    missing = []
    if not executor:
        missing.append("executor (frontmatter)")
    if not loaded.get("bound"):
        missing.append("bound (frontmatter)")
    for part, heading in ASSIGNMENT_SECTIONS:
        if not sections.get(heading):
            missing.append(f"{part} (## {heading})")
    if missing:
        return {"error": "assignment incomplete: " + "; ".join(missing)}
    assigned_name = str(dispatched_name or lease_of(loaded)[0] or "").strip() or None
    if assigned_name is None:
        return {"error": "dispatch requires the child identity through --by when it differs from the dispatch attempt owner"}
    role, profile = resolved_role_profile(executor, loaded.get("profile"))
    stamped, standard_refusal = _standards(loaded)
    if standard_refusal is not None:
        return standard_refusal
    try:
        adapter = adapter_for_ticket(loaded, target=workspace)
    except AdapterError as error:
        return {"error": error.detail, "code": error.code}
    primary = stamped[0] if stamped else None
    manifest, workspace_line = _manifest(primary)
    legacy_workspace = next((
        level for level in stamped
        if str(level.get("adapter") or "") == adapter.key
    ), None)
    if legacy_workspace is not None:
        _legacy_manifest, workspace_line = _manifest(legacy_workspace)
    applied = _applied_skill(loaded)
    return {"assignment": {
        "applied_skill": None if applied is None else applied["name"],
        "applied_skill_environment": bool(applied and applied["environment"]),
        "artifact_kind": adapter.artifact_kind,
        "assigned_name": assigned_name,
        "assignment_seal": None if attempt is None else attempt["assignment_seal"],
        "commits_in_place": adapter.commits_in_place,
        "dependencies": _dependency_paths(loaded, ticket_path),
        "dispatch_id": None if attempt is None else attempt["dispatch_id"],
        "executor": executor,
        "executor_script": _executor_script(executor),
        "git_candidate": adapter.workspace_strategy == "git",
        "id": loaded["id"],
        "kernel_contract": None if applied is None else _kernel_contract(executor),
        "lease_expires_at": None if attempt is None else attempt["lease_expires_at"],
        "lens_key": lens_key(loaded, sections, adapter),
        "lens_keys": lens_keys(loaded, sections, adapter),
        "manifest": manifest,
        "other_standards": [
            level for level in stamped if primary is None or level["name"] != primary["name"]
        ],
        "profile": profile,
        "role": role,
        "run": str(loaded.get("run") or run),
        "standard": None if primary is None else primary["name"],
        "standards": stamped,
        "skill_path": (
            applied["path"] if applied is not None else _skill_path(executor)
        ),
        "ticket_path": str(ticket_path),
        "workspace": workspace,
        "workspace_line": workspace_line,
    }}


__all__ = (
    "ASSIGNMENT_SECTIONS", "BY_NAME_DIR",
    "_claim_is_stale", "artifact_kind", "commits_in_place", "dispatch_assignment",
    "git_candidate", "lens_key", "lens_keys", "workspace_establishment_finding",
)
