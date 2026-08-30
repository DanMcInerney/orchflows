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
    from .tickets_dispatch_launch import launch_spec, precheck, selected_host
    from .tickets_dispatch_packet import _cmd_dispatch_packet
    from .tickets_format import _extract_flag, canonical_json
    from .tickets_lifecycle import _cmd_ready
    from .tickets_store import _run_lock, _segment_error
else:
    from tickets_attempts import _cmd_dispatch_open, _cmd_dispatch_retire
    from tickets_commands import DISPATCH_USAGE
    from tickets_dispatch_launch import launch_spec, precheck, selected_host
    from tickets_dispatch_packet import _cmd_dispatch_packet
    from tickets_format import _extract_flag, canonical_json
    from tickets_lifecycle import _cmd_ready
    from tickets_store import _run_lock, _segment_error


def _workspace_establish(run: str, ticket_id: str, workspace: str | None):
    """Run the workspace owner and return its one JSON response.

    Workspace establishment is intentionally kept behind its public script:
    it owns adapter selection, the derived candidate worktree, and the host
    checkout observation. ``--workspace`` names the tree the candidate is cut
    from, never the candidate itself -- an isolation-required item's tree is
    derived from its identity by ``workspace.py``, which is what stops two
    siblings of one run from being dispatched into one directory. The facade
    feeds back only the structured response, so a refusal cannot be repaired
    or translated into a second protocol.

    ``--lock-held`` (``workspace_git.LOCK_HELD``, pinned by a test) says this
    process already holds the run lock across the whole composition: the child
    stamps inside the caller's critical section rather than waiting for a lock
    its own parent holds while waiting for the child.
    """

    script = Path(__file__).with_name("workspace.py").resolve()
    source = Path(workspace).expanduser().resolve() if workspace else Path.cwd()
    try:
        completed = subprocess.run(
            [sys.executable, str(script), "establish", run, ticket_id,
             "--repo", str(source), "--lock-held"],
            cwd=str(source), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except (OSError, ValueError) as error:
        return {"error": f"workspace establish failed: {error}"}
    try:
        response = json.loads(completed.stdout)
    except (TypeError, ValueError) as error:
        return {"error": f"workspace establish returned invalid JSON: {error}"}
    if not isinstance(response, dict):
        return {"error": "workspace establish returned a non-object response"}
    if "error" in response:
        return response
    if completed.returncode:
        return {
            "error": "workspace establish refused",
            "code": completed.returncode,
            "response": response,
        }
    established = response.get("establish")
    if not isinstance(established, dict) or not str(
        established.get("workspace_path") or ""
    ).strip():
        return {"error": "workspace establish did not record workspace_path"}
    return response


def _write_packet_file(destination: str, packet: dict):
    """Put the committed packet where the launched child can read it.

    UTF-8 with LF, written whole: the child is told a path rather than told
    to reconstruct a shell literal, which is how a packet came to be
    truncated by a console code page. The packet is already durable in the
    attempt when this runs, so a write that fails is reported with the one
    command that replays it rather than pretending the dispatch failed.
    """

    path = Path(destination).expanduser()
    try:
        if path.parent and not path.parent.is_dir():
            path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(packet) + "\n")
    except (OSError, ValueError) as error:
        return {
            "error": (
                f"dispatch packet is committed and the packet file could not be "
                f"written: {error}. Replay this exact `tickets.py dispatch` call "
                "to write it"
            ),
            "code": "packet-file-unwritable",
        }
    return None


def _cmd_dispatch(rest):
    """Compose ready, workspace, attempt, packet, and launch for one caller.

    The established public operations remain the recovery seam. This
    caller convenience operation composes them in order, relays every
    structured refusal unchanged, and retires a newly opened attempt if
    packet projection refuses so no live attempt is left behind.

    The launch binding is resolved twice on purpose: once before anything is
    opened, so a host or role that cannot be launched refuses while the
    ticket is still untouched, and once from the committed packet, which is
    the authority on what was actually projected. Both ask the one resolver,
    under this one lock, so they cannot disagree.
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
    host = selected_host(_extract_flag(args, "--host"))
    packet_file = _extract_flag(args, "--packet-file")
    inline_limit = _extract_flag(args, "--inline-limit")
    if len(args) != 2 or not all((owner, dispatch_id, lease, reply_to)):
        return {"error": f"usage: {DISPATCH_USAGE}"}
    if form not in ("reference", "inline"):
        return {"error": f"--form takes reference or inline, not '{form}'"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid

    # Before the lock, and it has to be: promotion takes the run lock for
    # itself for each ticket it admits, and `_run_lock` is not reentrant, so
    # readying a sealed-but-pending item from inside our own lock is this
    # process waiting on itself -- which is what the ordinary first dispatch
    # of a sealed root did. Nothing is lost by promoting first: it is a
    # whole-run convenience, not part of this ticket's transaction, and
    # `dispatch-open` re-grades admission under the lock below and refuses a
    # ticket that is not ready however it got there.
    ready = _cmd_ready(["--run", run])
    if "error" in ready:
        return ready

    with _run_lock(run):
        # Before the first side effect: an attempt opened for a launch that
        # cannot resolve is an attempt nobody can start. Then open before
        # workspace establishment, because workspace.start stamps the ticket
        # and doing it first would mutate bytes on a pre-open refusal.
        record, failure = precheck(run, ticket_id, host)
        if failure is not None:
            return failure

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

        established = _workspace_establish(run, ticket_id, workspace)
        if "error" in established:
            projected = established
        else:
            # only establishment's own answer reaches the packet: the caller's
            # ``--workspace`` named the tree to cut from, and a packet built
            # from that instead has carried another item's workspace
            candidate = established.get("establish")
            workspace_path = (
                candidate.get("workspace_path") if isinstance(candidate, dict) else None
            )
            if not str(workspace_path or "").strip():
                projected = {"error": "workspace establish did not record workspace_path"}
            else:
                packet_args = [
                    run, ticket_id, "--dispatch-id", dispatch_id, "--reply-to", reply_to,
                    "--workspace", workspace_path, "--form", form,
                ]
                if review_kind is not None:
                    packet_args.extend(("--review-kind", review_kind))
                if artifact is not None:
                    packet_args.extend(("--artifact", artifact))
                if inline_limit is not None:
                    packet_args.extend(("--inline-limit", inline_limit))
                try:
                    projected = _cmd_dispatch_packet(packet_args, _lock_held=True)
                    if not isinstance(projected, dict):
                        projected = {
                            "error": "dispatch-packet returned a non-object response"
                        }
                    elif "error" not in projected and not isinstance(
                        projected.get("packet"), dict
                    ):
                        projected = {"error": "dispatch-packet returned no packet"}
                except Exception as error:
                    projected = {"error": str(error)}
        if "error" not in projected:
            return _launched(projected, record, packet_file)
        if newly_opened:
            retirement = _cmd_dispatch_retire([
                run, ticket_id, "--assignment-seal", dispatch["assignment_seal"],
                "--dispatch-id", dispatch_id,
                "--record-id", f"lifecycle:dispatch-facade-{dispatch_id}",
            ], _lock_held=True)
            if not isinstance(retirement, dict) or "error" in retirement:
                return {
                    "error": "dispatch attempt retirement failed after projection refusal",
                    "code": "dispatch-retirement-failed",
                    "projection": projected,
                    "retirement": retirement,
                }
        return projected


def _launched(projected: dict, record: dict, packet_file):
    """The committed packet plus the concrete invocation that carries it."""

    packet = projected["packet"]
    if packet_file is not None:
        failure = _write_packet_file(packet_file, packet)
        if failure is not None:
            return {**failure, "packet": packet}
    launch, failure = launch_spec(record, packet, packet_file=packet_file)
    if failure is not None:
        return {**failure, "packet": packet}
    return {**projected, "launch": launch}


__all__ = ("_cmd_dispatch", "_launched", "_workspace_establish")
