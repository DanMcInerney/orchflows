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
    from . import rings
    from .tickets_adapters import (
        AdapterError, adapter_spec, craft_path, derived_isolation,
    )
    from .tickets_context import graded_admission, run_snapshot
    from .tickets_dispatch_launch import resolved_role_profile
    from .tickets_format import (
        ARTIFACT_CLAUSE, MAKES_FIELD, REPORT_SECTION, _executor_of, lease_of,
        _extract_flag, _read_utf8, _sections, dequote,
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
        AdapterError, adapter_spec, craft_path, derived_isolation,
    )
    from tickets_context import graded_admission, run_snapshot
    from tickets_dispatch_launch import resolved_role_profile
    from tickets_format import (
        ARTIFACT_CLAUSE, MAKES_FIELD, REPORT_SECTION, _executor_of, lease_of,
        _extract_flag, _read_utf8, _sections, dequote,
    )
    from tickets_registry import EXECUTOR_REGISTRY
    from tickets_transitions import CHECKABLE_STATUSES
    from tickets_store import (
        NO_SINK_ERROR, _executor_script, _load_ticket, _tickets_root,
    )
    from workspace_git import BASELINE_KEY, BRANCH_KEY

ASSIGNMENT_SECTIONS = (("goal", "Goal"), ("context", "Context"))
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
    # Without a dispatch record there is no live claim to defend: the
    # lease lives in dispatch_v1 alone (contracts/dispatch.md).
    return True, []


def _dependency_paths(loaded: dict, ticket_path: Path) -> list:
    return [
        str(ticket_path.with_name(f"{dependency}.md"))
        for dependency in (loaded.get("depends_on") or [])
    ]


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


def _workspace_line(path: Path):
    """The craft's own `## Workspace` sentence, collapsed to one line, or None.

    Read the one anchor `contracts/pack-signature.md` fixes for every craft:
    a launch whose adapter commits nothing still owes the child its
    workspace's own words for what an identity and a conflict are here,
    exactly as its craft states them, never paraphrased in this module.
    """

    text, failure = _read_utf8(path, "pack craft")
    if failure is not None:
        return None
    collapsed = re.sub(r"\s+", " ", _sections(text).get("Workspace", "")).strip()
    return collapsed or None


def _craft(pack):
    """`(craft_path, scope_sentence, workspace_line)` for the stamped pack,
    or `(None, None, None)`."""

    if not str(pack or "").strip():
        return None, None, None
    try:
        path = craft_path(pack)
    except AdapterError:
        return None, None, None
    return str(path), _craft_scope(path), _workspace_line(path)


def _skill_path(executor):
    """The applied skill's own manifest, resolved through the one ring
    resolver -- the same guarantee `craft_path` already gives the pack.

    A launch hands the child this path instead of telling it to find one:
    `scripts/rings.py` resolves a skill name to one absolute path
    deterministically (S7, 2026-09-01: a forked child fired an unscoped
    filesystem search to locate its own skill file, the installed layout
    the host block documents never reaching it). None when the executor
    names no resolvable skill -- a launch with no working prompt is refused
    long before this fact is read, so a caller here always holds a name
    that either resolves or the dispatch never opens.
    """

    name = dequote(executor)
    if not name:
        return None
    try:
        return str(rings.resolve("skill", name)["path"])
    except rings.RingError:
        return None


def git_candidate(pack) -> bool:
    """Whether the landing merges a candidate branch this pack's child
    committed into.

    The same fact `workspace_establishment_finding` already checks a
    recorded workspace's branch and baseline against
    (``workspace_strategy == "git"``): only there does an isolated branch
    exist for `land` to merge. This answers a narrower question than "did
    the child commit" -- a document-tree child commits too
    (`commits_in_place`), straight onto the coordinator's own branch, and
    nothing is merged for it because nothing was isolated to merge from.
    """

    if not str(pack or "").strip():
        return False
    try:
        return adapter_spec(pack).workspace_strategy == "git"
    except AdapterError:
        return False


def commits_in_place(pack) -> bool:
    """Whether this pack's child must commit in the tree it stands in for
    its bytes to survive.

    True for every adapter whose identity is a commit or a document
    revision one records (git, git-plus-render, document-tree); false only
    for evidence-store, whose identity is a lane packet with no commit
    behind it. Kept separate from `git_candidate`: a document-tree child
    commits but the landing merges no branch for it, so the launch's
    return line reads both facts to decide what it renders (finding F4).
    """

    if not str(pack or "").strip():
        return False
    try:
        return adapter_spec(pack).commits_in_place
    except AdapterError:
        return False


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


def lens_key(loaded: dict, sections: dict):
    """The `## Lens` entry this child's work is measured against, or None.

    One key, read in whichever direction the ticket runs. A judge is handed
    finished artifacts, so the typed identities on its Context name the kind
    it checks -- one kind per judge, which the mint enforces, so two kinds
    here is a ticket no mint could have written and gets no key rather than
    a guessed one. A `do` makes the stamped pack's own deliverable, whose
    kind its adapter fixes, unless it was minted to make a planning artifact
    no adapter names and says so on `makes`.
    """

    # Only the verb whose product is a findings file is keyed by the
    # identities on its Context; for every other executor an artifact line
    # is evidence it read, not the product it owes, and a planning `do`
    # citing a predecessor would otherwise be sent to that predecessor's
    # kind. The registry is the same one the launch prompt reads.
    if EXECUTOR_REGISTRY.get(_executor_of(loaded), {}).get("files_findings"):
        kinds = sorted({
            line.strip()[len(ARTIFACT_CLAUSE):].split(":", 1)[0].strip()
            for line in sections.get("Context", "").splitlines()
            if line.strip().startswith(ARTIFACT_CLAUSE)
        })
        if kinds:
            return kinds[0] if len(kinds) == 1 else None
    return dequote(loaded.get(MAKES_FIELD)) or artifact_kind(loaded.get("pack"))


def dispatch_assignment(rest, *, attempt=None):
    """Grade one ticket for dispatch and resolve every fact its launch names.

    Read under the caller's run lock, because each of these decides what the
    launch commits: the admission receipt, the established tree, and the
    identity every record will be filed under.
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
    assigned_name = str(dispatched_name or lease_of(loaded)[0] or "").strip() or None
    if assigned_name is None:
        return {"error": "dispatch requires the child identity through --by when it differs from the dispatch attempt owner"}
    role, _profile = resolved_role_profile(executor, loaded.get("profile"))
    pack = loaded.get("pack")
    craft, scope, workspace_line = _craft(pack)
    return {"assignment": {
        "artifact_kind": artifact_kind(pack),
        "assigned_name": assigned_name,
        "assignment_seal": None if attempt is None else attempt["assignment_seal"],
        "commits_in_place": commits_in_place(pack),
        "craft": craft,
        "craft_scope": scope,
        "dependencies": _dependency_paths(loaded, ticket_path),
        "dispatch_id": None if attempt is None else attempt["dispatch_id"],
        "executor": executor,
        "executor_script": _executor_script(executor),
        "git_candidate": git_candidate(pack),
        "id": loaded["id"],
        "lease_expires_at": None if attempt is None else attempt["lease_expires_at"],
        "lens_key": lens_key(loaded, sections),
        "pack": pack,
        "role": role,
        "run": str(loaded.get("run") or run),
        "skill_path": _skill_path(executor),
        "ticket_path": str(ticket_path),
        "workspace": workspace,
        "workspace_line": workspace_line,
    }}


__all__ = (
    "ASSIGNMENT_SECTIONS",
    "_claim_is_stale", "artifact_kind", "commits_in_place", "dispatch_assignment",
    "git_candidate", "lens_key", "workspace_establishment_finding",
)
