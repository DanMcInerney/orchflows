"""One caller-side dispatch operation over the public dispatch steps."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if __package__:
    from .tickets_attempts import (
        _cmd_dispatch_open, _cmd_dispatch_retire,
    )
    from .tickets_commands import DISPATCH_USAGE
    from .tickets_dispatch_packet import _cmd_dispatch_packet
    from .tickets_format import _extract_flag
    from .tickets_lifecycle import _cmd_ready
    from .tickets_store import _run_lock, _segment_error
else:
    from tickets_attempts import _cmd_dispatch_open, _cmd_dispatch_retire
    from tickets_commands import DISPATCH_USAGE
    from tickets_dispatch_packet import _cmd_dispatch_packet
    from tickets_format import _extract_flag
    from tickets_lifecycle import _cmd_ready
    from tickets_store import _run_lock, _segment_error


def _workspace_start(run: str, ticket_id: str, workspace: str | None):
    """Run the workspace owner and return its one JSON response.

    Workspace establishment is intentionally kept behind its public script:
    it owns adapter selection and the host checkout observation. The facade
    supplies the candidate as the child process' working directory and feeds
    back only the structured response, so a refusal cannot be repaired or
    translated into a second protocol.
    """

    script = Path(__file__).with_name("workspace.py").resolve()
    candidate = Path(workspace).expanduser().resolve() if workspace else Path.cwd()
    try:
        completed = subprocess.run(
            [sys.executable, str(script), "start", run, ticket_id],
            cwd=str(candidate), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except (OSError, ValueError) as error:
        return {"error": f"workspace start failed: {error}"}
    try:
        response = json.loads(completed.stdout)
    except (TypeError, ValueError) as error:
        return {"error": f"workspace start returned invalid JSON: {error}"}
    if not isinstance(response, dict):
        return {"error": "workspace start returned a non-object response"}
    if "error" in response:
        return response
    if completed.returncode:
        return {
            "error": "workspace start refused",
            "code": completed.returncode,
            "response": response,
        }
    started = response.get("start")
    if not isinstance(started, dict) or not str(started.get("workspace_path") or "").strip():
        return {"error": "workspace start did not record workspace_path"}
    return response


def _cmd_dispatch(rest):
    """Compose ready, workspace, attempt, and packet for one caller.

    The established public operations remain the recovery seam. This
    caller convenience operation composes them in order, relays every
    structured refusal unchanged, and retires a newly opened attempt if
    packet projection refuses so no live attempt is left behind.
    """

    args = list(rest)
    owner = _extract_flag(args, "--by")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    lease = _extract_flag(args, "--lease-expires-at")
    reply_to = _extract_flag(args, "--reply-to")
    workspace = _extract_flag(args, "--workspace")
    artifact = _extract_flag(args, "--artifact")
    form = (_extract_flag(args, "--form") or "reference").strip()
    review_kind = _extract_flag(args, "--review-kind")
    if len(args) != 2 or not all((owner, dispatch_id, lease, reply_to)):
        return {"error": f"usage: {DISPATCH_USAGE}"}
    if form not in ("reference", "inline"):
        return {"error": f"--form takes reference or inline, not '{form}'"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid

    ready = _cmd_ready(["--run", run])
    if "error" in ready:
        return ready

    established = _workspace_start(run, ticket_id, workspace)
    if "error" in established:
        return established
    workspace_path = established["start"]["workspace_path"]

    with _run_lock(run):
        opening = _cmd_dispatch_open([
            run, ticket_id, "--by", owner, "--dispatch-id", dispatch_id,
            "--lease-expires-at", lease,
        ], _lock_held=True)
        if "error" in opening:
            return opening
        dispatch = opening.get("dispatch")
        if not isinstance(dispatch, dict):
            return {"error": "dispatch-open returned no dispatch response"}
        newly_opened = dispatch.get("outcome") == "opened"

        packet_args = [
            run, ticket_id, "--dispatch-id", dispatch_id, "--reply-to", reply_to,
            "--workspace", workspace_path, "--form", form,
        ]
        if review_kind is not None:
            packet_args.extend(("--review-kind", review_kind))
        if artifact is not None:
            packet_args.extend(("--artifact", artifact))
        try:
            projected = _cmd_dispatch_packet(packet_args, _lock_held=True)
        except Exception as error:
            projected = {"error": str(error)}
        if "error" not in projected:
            return projected
        if newly_opened:
            _cmd_dispatch_retire([
                run, ticket_id, "--assignment-seal", dispatch["assignment_seal"],
                "--dispatch-id", dispatch_id,
                "--record-id", f"lifecycle:dispatch-facade-{dispatch_id}",
            ], _lock_held=True)
        return projected


__all__ = ("_cmd_dispatch", "_workspace_start")
