"""Dispatch packets for sealed tickets."""
from __future__ import annotations

import re
import shlex
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if __package__:
    from .tickets_adapters import AdapterError, adapter_spec
    from .tickets_context import graded_admission, run_snapshot
    from .tickets_format import (
        CHECKED_BY_KEY, DISPATCHING_EXECUTORS, EXECUTOR_SECTIONS,
        LOOP_EXECUTOR, ROOT_EXECUTOR, _executor_of,
        _extract_flag, _parse_bound_minutes, _parse_iso, _read_utf8, _sections,
        canonical_json,
    )
    from .tickets_registry import REVIEW_KINDS
    from .tickets_sequence import sequence_block
    from .tickets_store import (
        NO_SINK_ERROR, _executor_script, _load_ticket, _run_lock,
        _segment_error, _tickets_root, normalized_isolation,
    )
else:
    from tickets_adapters import AdapterError, adapter_spec
    from tickets_context import graded_admission, run_snapshot
    from tickets_format import (
        CHECKED_BY_KEY, DISPATCHING_EXECUTORS, EXECUTOR_SECTIONS,
        LOOP_EXECUTOR, ROOT_EXECUTOR, _executor_of,
        _extract_flag, _parse_bound_minutes, _parse_iso, _read_utf8, _sections,
        canonical_json,
    )
    from tickets_registry import REVIEW_KINDS
    from tickets_sequence import sequence_block
    from tickets_store import (
        NO_SINK_ERROR, _executor_script, _load_ticket, _run_lock,
        _segment_error, _tickets_root, normalized_isolation,
    )

PACKET_SECTIONS = (("goal", "Goal"), ("context", "Context"))
PACKET_USAGE = "packet <run> <id> --reply-to <name> [--by <name>] [--workspace <path>] [--review-kind critique|repair|verify]"
CHECKABLE_STATUSES = frozenset({"claimed", "suspended"})
CUT_LENS_PARTS = ("skills", "kernel", "orch-decompose", "references", "cut-lens.md")
GATE_CRITIQUE_ID = "{root}.gate.critique.{lens}"
GATE_REPAIR_ID = "{root}.gate.repair"
GATE_VERIFY_ID = "{root}.gate.verify"
GATE_EXECUTOR_SECTIONS = [("Result", ""), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]")]
_SHELL_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./:\\=-]+$")


def _command_text(*arguments) -> str:
    values = [str(argument) for argument in arguments]
    if all(_SHELL_SAFE_TOKEN.fullmatch(value) for value in values):
        return " ".join(values)
    if sys.platform == "win32":
        return "& " + " ".join("'" + value.replace("'", "''") + "'" for value in values)
    return shlex.join(values)


def workspace_establishment_finding(data: dict, workspace):
    """Return the refusal code/detail for a non-established packet workspace."""

    pack = data.get("pack")
    if not str(pack or "").strip():
        return None
    try:
        adapter = adapter_spec(pack)
    except AdapterError as error:
        return error.code, error.detail
    required = (
        adapter.establishes_isolation
        and normalized_isolation(data.get("isolation")) == "required"
    )
    if not required:
        return None
    recorded = str(data.get("workspace_path") or "").strip()
    if not recorded:
        return (
            "workspace-unestablished",
            "required workspace has no pre-dispatch workspace_path record",
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


def _last_motion(ticket_path: Path, result_text: str = "", _unused=()):
    """The ticket file is the durable motion record; result writes update it."""
    del result_text, _unused
    try:
        return datetime.fromtimestamp(Path(ticket_path).stat().st_mtime, timezone.utc), []
    except OSError as error:
        return None, [f"could not stat {ticket_path}: {error}"]


def _is_stale(claimed_at, bound_minutes: int, now: datetime, last_motion=None) -> bool:
    parsed = _parse_iso(claimed_at)
    if parsed is None:
        return True
    if last_motion is not None and last_motion > parsed:
        parsed = last_motion
    return now - parsed > timedelta(minutes=bound_minutes)


def _claim_is_stale(ticket_path, text: str, data: dict, now: datetime):
    if data.get("dispatch_v1"):
        if __package__:
            from .tickets_attempts import attempt_window
        else:
            from tickets_attempts import attempt_window
        window, failure = attempt_window(data)
        if failure is not None:
            return True, [failure["error"]]
        attempt = window["attempt"]
        return (
            attempt.get("state") != "live" or now >= window["lease_expires_at"],
            [],
        )
    motion, unreadable = _last_motion(Path(ticket_path), _sections(text).get("Result", ""))
    return _is_stale(data.get("claimed_at"), _parse_bound_minutes(data.get("bound")), now, motion), unreadable


def _cut_subtree(run: str, root_id: str) -> list:
    root = _tickets_root()
    directory = root / run if root is not None else None
    if directory is None or not directory.is_dir():
        return []
    values = []
    for path in sorted(directory.glob(f"{root_id}.*.md")):
        loaded = _load_ticket(path)
        if "error" not in loaded:
            values.append((str(loaded.get("id") or path.stem), str(loaded.get("status") or "")))
    return values


def _cut_lens_path():
    here = Path(__file__).resolve()
    for root in (here.parent.parent, here.parent.parent / "lib"):
        candidate = root.joinpath(*CUT_LENS_PARTS)
        if candidate.is_file():
            return str(candidate)
    return "/".join(CUT_LENS_PARTS)


def _cmd_packet(rest):
    probe = list(rest)
    for flag in ("--reply-to", "--by", "--workspace", "--review-kind"):
        _extract_flag(probe, flag)
    if len(probe) != 2 or _segment_error("run id", probe[0]) is not None:
        return _packet_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _packet_under_run_lock(rest)
    except OSError as error:
        return {"error": f"unable to emit packet: {error}"}


def _dependency_prompt(loaded: dict, ticket_path: Path) -> list:
    dependencies = [str(value) for value in (loaded.get("depends_on") or [])]
    if not dependencies:
        return []
    lines = ["Dependency results are system-owned inputs. Read these completed tickets' Result and Verification sections:"]
    lines.extend(str(ticket_path.with_name(f"{dependency}.md")) for dependency in dependencies)
    return lines


def _packet_under_run_lock(rest, *, result_attempt=None, review_state=None):
    args = list(rest)
    reply_to = _extract_flag(args, "--reply-to")
    dispatched_name = _extract_flag(args, "--by")
    workspace = _extract_flag(args, "--workspace")
    requested_review_kind = _extract_flag(args, "--review-kind")
    if len(args) != 2:
        return {"error": f"usage: {PACKET_USAGE}"}
    if requested_review_kind is not None:
        requested_review_kind = requested_review_kind.strip().strip("`")
        if requested_review_kind not in REVIEW_KINDS:
            return {"error": f"--review-kind takes one of {list(REVIEW_KINDS)}, not '{requested_review_kind}'"}
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
    status = str(loaded.get("status") or "").strip().strip("`")
    if status not in CHECKABLE_STATUSES:
        return {"error": f"ticket is not claimed (status '{status}'): packet emission requires an admitted claim"}
    snapshot, failures = run_snapshot(ticket_path.parent)
    if failures:
        return failures[0][1]
    grade = graded_admission(ticket_id, text, snapshot, run)
    if grade["findings"]:
        return {"error": "packet admission grade failed", "findings": grade["findings"]}
    stored = str(loaded.get("admission") or "")
    if stored != grade["receipt"]:
        return {"error": f"ticket has no current admission receipt: stored {stored or '<missing>'}, current {grade['receipt']}"}
    sections = _sections(text)
    executor = _executor_of(loaded)
    missing = []
    if not reply_to:
        missing.append("reply_to (--reply-to)")
    if not executor:
        missing.append("executor (frontmatter)")
    if not loaded.get("bound"):
        missing.append("bound (frontmatter)")
    for part, heading in PACKET_SECTIONS:
        if not sections.get(heading):
            missing.append(f"{part} (## {heading})")
    if missing:
        return {"error": "packet incomplete: " + "; ".join(missing)}
    declared_review_kind = str(loaded.get("review_kind") or "").strip().strip("`")
    if declared_review_kind and declared_review_kind not in REVIEW_KINDS:
        return {"error": f"ticket {run}/{ticket_id} has an invalid review_kind '{declared_review_kind}'"}
    if requested_review_kind is not None and declared_review_kind and requested_review_kind != declared_review_kind:
        return {"error": f"ticket {run}/{ticket_id} review_kind differs from the sealed assignment"}
    review_kind = requested_review_kind or declared_review_kind or None
    if review_kind == "critique" and str(loaded.get(CHECKED_BY_KEY) or "").strip():
        return {"error": f"ticket {run}/{ticket_id} already has its one checker"}
    run_id = str(loaded.get("run") or run)
    script = Path(__file__).with_name("tickets.py").resolve()
    executor_script = _executor_script(executor)
    assigned_name = str(dispatched_name or loaded.get("claimed_by") or "").strip() or None
    if assigned_name is None:
        return {"error": "packet requires the dispatched child identity through --by when it differs from claimed_by"}
    if review_kind == "critique":
        prompt = [
            "Apply orch-check to the immutable review ledger and fixed artifact.",
            "Read the fixed artifact identity, Goal, Context, executor Result and Verification evidence, and pack lens.",
            "Remain read-only. Enumerate every evidence-backed material blocker, then synthesize and rank the smallest architectural repair set. File findings in Feedback, never rewrite Result or Verification.",
        ]
    elif review_kind == "verify":
        prompt = [
            "Apply orch-check to the immutable review ledger and repaired artifact.",
            "Independently challenge the fixed artifact and executor evidence against Goal, Context, and pack evidence. File the verdict and observations in Verification without editing the artifact.",
        ]
    elif review_kind == "repair":
        prompt = [
            "Apply orch-execute to the immutable review ledger and accepted blocker set.",
            "Resolve only the accepted blockers, preserving the fixed pack and workspace authority, then file fresh evidence for the repaired artifact.",
        ]
    elif executor_script is not None:
        prompt = [
            f"Run the script {executor_script} with ticket path {ticket_path} from the assigned workspace.",
            "File stdout as Result and the exit status as Verification.",
        ]
    else:
        prompt = [
            f"Apply skill {executor} to ticket {ticket_path}.",
            "The sealed semantic assignment is Goal, Context, and optional Suggested files. Suggested files are non-binding; inspect and change or create any repository files needed for Goal.",
            "Choose the implementation, tests, and verification yourself. Repository-global deterministic gates run on the integrated tip.",
        ]
        prompt.extend(sequence_block(loaded))
        prompt.extend(_dependency_prompt(loaded, ticket_path))
    if executor == LOOP_EXECUTOR:
        prompt.append(f"Each pass works toward Goal and stops when it is achieved or the operational bound {loaded.get('bound')} is exhausted.")
    if workspace:
        prompt.append(f"Workspace: {workspace}")
    if review_state is not None:
        prompt.extend((
            "Immutable review ledger; consume this exact predecessor chain:",
            canonical_json(review_state),
        ))
    isolation = normalized_isolation(loaded.get("isolation"))
    if review_kind == "critique":
        prompt.append("File Feedback and Risks as findings are produced; the join alone sets terminal status.")
    elif review_kind == "verify":
        prompt.append("File Verification, Feedback, and Risks as evidence is produced; the join alone sets terminal status.")
    else:
        prompt.append("File Result, Verification, Feedback, Risks, or Handoff as work is produced; the join alone sets terminal status.")
    if review_kind == "verify":
        prompt.append("Begin ordinary verdict evidence with exactly `PASS:`, `FAIL:`, or `UNVERIFIED:` so the join can bind the verdict to the verified artifact.")
    prompt.append(f"Filing channel, with SECTION one of {list(EXECUTOR_SECTIONS)} and PATH in the candidate workspace:")
    result_identity = []
    if result_attempt is not None:
        result_identity = [
            "--assignment-seal", result_attempt["assignment_seal"],
            "--dispatch-id", result_attempt["dispatch_id"],
            "--record-id", "RECORD_ID",
        ]
    prompt.append(_command_text(sys.executable, script, "result", run_id, loaded["id"], *result_identity, "--by", assigned_name, "--section", "SECTION", "--file", "PATH", "--append"))
    prompt.append(_command_text(sys.executable, script, "result", run_id, loaded["id"], *result_identity, "--by", assigned_name, "--section", "SECTION", "--text", "TEXT", "--append"))
    if assigned_name is not None:
        prompt.append(f"Your assigned name is `{assigned_name}`; use exactly it wherever a command takes --by.")
    if executor in DISPATCHING_EXECUTORS and assigned_name is not None:
        prompt.append(f"Every packet you dispatch carries `{assigned_name}` as reply_to.")
    prompt.append(f"reply_to: {reply_to} — address your closing message to `{reply_to}`.")
    return {"packet": {
        "run": run_id, "id": loaded["id"], "path": str(ticket_path),
        "executor": executor, "script": executor_script, "pack": loaded.get("pack"),
        "profile": loaded.get("profile"),
        "independence": loaded.get("independence") or "checker",
        "isolation": isolation, "admission": stored, "assigned_name": assigned_name,
        "reply_to": reply_to, "workspace": workspace, "prompt": "\n".join(prompt),
        "review_kind": review_kind,
    }}


__all__ = (
    "CUT_LENS_PARTS", "GATE_CRITIQUE_ID", "GATE_EXECUTOR_SECTIONS",
    "GATE_REPAIR_ID", "GATE_VERIFY_ID", "PACKET_SECTIONS", "PACKET_USAGE",
    "_claim_is_stale", "_cmd_packet", "_cut_lens_path", "_cut_subtree",
    "_is_stale", "_last_motion", "_packet_under_run_lock",
)
