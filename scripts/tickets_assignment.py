"""The sealed ticket, read as one dispatchable assignment.

The ticket is the assignment: there is no wire object between it and the
child. This module grades one ticket against everything a dispatch requires
of it -- admitted claim, complete Goal and Context, a lawful review lane, an
established workspace -- and resolves the facts a launch prompt cannot derive
from the ticket alone: the pack's own craft file, its verification-scope
sentence, the review lane's root ticket, and the dependency results.

What it does not do is compose the prompt. `tickets_dispatch_launch.py` owns
the one child-facing surface, and this module hands it resolved facts so the
prompt is filled rather than reasoned about.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

if __package__:
    from .tickets_adapters import (
        AdapterError, adapter_spec, craft_path, derived_isolation,
    )
    from .tickets_context import graded_admission, run_snapshot
    from .tickets_dispatch_launch import resolved_role_profile
    from .tickets_format import (
        CHECKED_BY_KEY, REPORT_SECTION, _executor_of, lease_of,
        _extract_flag, _read_utf8, _sections, dequote,
    )
    from .tickets_registry import REVIEW_KINDS
    from .tickets_transitions import CHECKABLE_STATUSES
    from .tickets_store import (
        NO_SINK_ERROR, _executor_script, _load_ticket, _tickets_root,
    )
else:
    from tickets_adapters import (
        AdapterError, adapter_spec, craft_path, derived_isolation,
    )
    from tickets_context import graded_admission, run_snapshot
    from tickets_dispatch_launch import resolved_role_profile
    from tickets_format import (
        CHECKED_BY_KEY, REPORT_SECTION, _executor_of, lease_of,
        _extract_flag, _read_utf8, _sections, dequote,
    )
    from tickets_registry import REVIEW_KINDS
    from tickets_transitions import CHECKABLE_STATUSES
    from tickets_store import (
        NO_SINK_ERROR, _executor_script, _load_ticket, _tickets_root,
    )

ASSIGNMENT_SECTIONS = (("goal", "Goal"), ("context", "Context"))
GATE_MARKER = ".gate."
CHECK_SUFFIX = ".check"
# The craft owns its verification scope; this finds the sentence rather than
# restating it. `## Stages` (or `## Lens`) is where a craft declares how far a
# unit's checks reach, and the gate's row is the anchor that says so.
CRAFT_SCOPE_SECTIONS = ("Stages", "Lens")
CRAFT_SCOPE_ANCHOR = "gate's row"


def _attempt_workspace(data: dict):
    """The tree the ticket's dispatch attempt recorded, through its one owner.

    Loaded at call time rather than at module scope: the flat installed
    layout initializes these siblings in an order neither may depend on.
    """

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

    pack = data.get("pack")
    if not str(pack or "").strip():
        return None
    try:
        adapter = adapter_spec(pack)
    except AdapterError as error:
        return error.code, error.detail
    required = derived_isolation(data.get("isolation"), pack) == "required"
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
        for key in ("workspace_branch", "workspace_baseline")
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
    # Without a dispatch record there is no live claim to defend: the
    # lease lives in dispatch_v1 alone (contracts/dispatch.md).
    return True, []


def _dependency_paths(loaded: dict, ticket_path: Path) -> list:
    return [
        str(ticket_path.with_name(f"{dependency}.md"))
        for dependency in (loaded.get("depends_on") or [])
    ]


def review_root_id(ticket_id: str):
    """The root a review stage was cut from, read off its own identity.

    A gate stub's id is generated from its root (`{root}.gate.critique.{lens}`)
    and an ordinary checker's from its target, so the id is where that fact
    already lives. Naming it again in the stub body would be a second home for
    the one context three proven verdicts turned on.
    """

    if GATE_MARKER in ticket_id:
        return ticket_id.split(GATE_MARKER, 1)[0] or None
    if ticket_id.endswith(CHECK_SUFFIX):
        return ticket_id[: -len(CHECK_SUFFIX)] or None
    return None


def _craft_scope(path: Path):
    """The craft's own verification-scope sentence, or None.

    A mechanical quote: the bullet in the craft's `## Stages` (or `## Lens`)
    that names the gate's row. A craft that declares no scope gets no quote,
    and the prompt's standing line answers alone.
    """

    text, failure = _read_utf8(path, "pack craft")
    if failure is not None:
        return None
    section = None
    bullet = []
    for line in [*text.splitlines(), "## "]:
        starts = line.startswith("## ") or line.lstrip().startswith("- ") or not line.strip()
        if starts and bullet:
            sentence = re.sub(r"\s+", " ", " ".join(bullet)).strip()
            if CRAFT_SCOPE_ANCHOR in sentence:
                return sentence
            bullet = []
        if line.startswith("## "):
            section = line[3:].strip()
        elif section in CRAFT_SCOPE_SECTIONS and line.strip():
            if line.lstrip().startswith("- "):
                bullet = [line.strip()[2:]]
            elif bullet:
                bullet.append(line.strip())
    return None


def _craft(pack):
    """`(craft_path, scope_sentence)` for the stamped pack, or `(None, None)`."""

    if not str(pack or "").strip():
        return None, None
    try:
        path = craft_path(pack)
    except AdapterError:
        return None, None
    return str(path), _craft_scope(path)


def artifact_kind(pack):
    """The typed artifact prefix the pack's adapter fixes, or None.

    Resolved here with the rest of what the prompt cannot derive from the
    ticket, and left None for a ticket that stamps no resolvable pack: a
    child asked for a line in no grammar would print one nothing grades.
    """

    if not str(pack or "").strip():
        return None
    try:
        return adapter_spec(pack).artifact_kind
    except AdapterError:
        return None


def dispatch_assignment(rest, *, attempt=None, review_state=None):
    """Grade one ticket for dispatch and resolve every fact its launch names.

    Read under the caller's run lock, because each of these decides what the
    launch commits: the admission receipt, the sealed review lane, the
    established tree, and the identity every record will be filed under.
    """

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
    declared_review_kind = dequote(loaded.get("review_kind"))
    if declared_review_kind and declared_review_kind not in REVIEW_KINDS:
        return {"error": f"ticket {run}/{ticket_id} has an invalid review_kind '{declared_review_kind}'"}
    review_kind = declared_review_kind or None
    if review_kind == "critique" and str(loaded.get(CHECKED_BY_KEY) or "").strip():
        return {"error": f"ticket {run}/{ticket_id} already has its one checker"}
    assigned_name = str(dispatched_name or lease_of(loaded)[0] or "").strip() or None
    if assigned_name is None:
        return {"error": "dispatch requires the child identity through --by when it differs from the dispatch attempt owner"}
    role, _profile = resolved_role_profile(executor, loaded.get("profile"))
    pack = loaded.get("pack")
    craft, scope = _craft(pack)
    tip = None
    if review_state is not None:
        tip = (review_state.get("records") or [{}])[-1]
    root_id = review_root_id(loaded["id"]) if review_kind else None
    root_path = None
    if root_id is not None:
        candidate = ticket_path.with_name(f"{root_id}.md")
        root_path = str(candidate) if candidate.is_file() else None
    return {"assignment": {
        "artifact_kind": artifact_kind(pack),
        "assigned_name": assigned_name,
        "assignment_seal": None if attempt is None else attempt["assignment_seal"],
        "craft": craft,
        "craft_scope": scope,
        "dependencies": _dependency_paths(loaded, ticket_path),
        "dispatch_id": None if attempt is None else attempt["dispatch_id"],
        "executor": executor,
        "executor_script": _executor_script(executor),
        "id": loaded["id"],
        "lease_expires_at": None if attempt is None else attempt["lease_expires_at"],
        "pack": pack,
        "review_kind": review_kind,
        "review_tip": tip,
        "role": role,
        "root_path": root_path,
        "run": str(loaded.get("run") or run),
        "ticket_path": str(ticket_path),
        "workspace": workspace,
    }}


__all__ = (
    "ASSIGNMENT_SECTIONS", "CHECK_SUFFIX", "GATE_MARKER",
    "_claim_is_stale", "artifact_kind", "dispatch_assignment",
    "review_root_id", "workspace_establishment_finding",
)
