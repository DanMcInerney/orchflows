"""Durable command receipts, written before a caller can advance its transaction.

Streams go directly to the state sink while the child runs. A killed supervisor
therefore leaves a running receipt and diagnostic bytes, never a success. The
completed receipt binds the raw streams and both observations of the source.
Ignored Git files are outside that source identity; this is no host-state probe.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts import state_root
except ImportError:  # pragma: no cover - installed flat scripts
    import state_root


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git(tree: Path, *args: str):
    return subprocess.run(["git", *args], cwd=str(tree), capture_output=True,
                          timeout=30)


def artifact_identity(tree) -> dict:
    """Observe Git source bytes or an explicitly identified non-Git directory."""
    root = Path(tree or Path.cwd()).resolve()
    try:
        if not root.is_dir():
            raise OSError(f"no source directory: {root}")
        status = (_git(root, "status", "--porcelain=v2", "--branch",
                       "--untracked-files=all", "-z")
                  if state_root.find_repo_root(root) is not None else None)
        if status is not None and status.returncode:
            raise OSError("Git source observation failed")
        if status is not None:
            # One observation supplies HEAD and all changed paths. Hash their
            # bytes too: two different edits can have identical status flags.
            commit, hashed = None, hashlib.sha256()
            entries = iter(status.stdout.split(b"\0"))
            for entry in entries:
                if entry.startswith(b"# branch.oid "):
                    commit = entry[13:].decode("ascii")
                if not entry or entry.startswith(b"# "):
                    continue
                kind = entry[:1]
                if kind == b"?":
                    raw = entry[2:]
                elif kind in (b"1", b"2", b"u"):
                    raw = entry.split(b" ", {b"1": 8, b"2": 9, b"u": 10}[kind])[-1]
                    if kind == b"2":
                        hashed.update(next(entries) + b"\0")
                else:
                    raise OSError("unrecognized Git source observation")
                name = os.fsdecode(raw)
                if name.startswith((".orch/", ".orch-notes/")):
                    continue
                hashed.update(entry + b"\0")
                path = root / name
                if path.is_dir():  # a changed submodule owns its own source
                    hashed.update(json.dumps(artifact_identity(path), sort_keys=True).encode())
                elif path.exists():
                    hashed.update(hashlib.sha256(path.read_bytes()).digest())
                else:
                    hashed.update(b"deleted")
            return {"kind": "git-source", "commit": commit,
                    "working_sha256": hashed.hexdigest()}
        hashed = hashlib.sha256()
        for path in sorted(root.rglob("*")):
            if any(part in ("__pycache__", ".orch", ".orch-notes")
                   for part in path.relative_to(root).parts):
                continue
            if path.is_file():
                hashed.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
                hashed.update(hashlib.sha256(path.read_bytes()).digest())
        return {"kind": "directory", "sha256": hashed.hexdigest()}
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {"kind": "unavailable", "error": str(error)}


def _write(path: Path, record: dict) -> dict:
    raw = (json.dumps(record, sort_keys=True, indent=1) + "\n").encode("utf-8")
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return {"path": str(path), "sha256": digest(raw)}


def _terminate(child) -> None:
    """Stop the owned process tree, then reap its immediate child."""
    if os.name == "nt":
        stopped = subprocess.run(
            ["taskkill", "/PID", str(child.pid), "/T", "/F"],
            capture_output=True, timeout=30,
        )
        if stopped.returncode and child.poll() is None:
            raise OSError("taskkill could not terminate the check process tree")
    else:
        # Nested runners may own separate process groups. Include descendants
        # instead of assuming the immediate child's group is the whole tree.
        listing = subprocess.run(["ps", "-eo", "pid=,ppid="],
                                 capture_output=True, timeout=30, check=True)
        parents = [tuple(map(int, row.split()))
                   for row in listing.stdout.decode("ascii").splitlines()]
        owned = {child.pid}
        while True:
            expanded = owned | {pid for pid, parent in parents if parent in owned}
            if expanded == owned:
                break
            owned = expanded
        for pid in sorted(owned - {child.pid}, reverse=True):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    child.wait(timeout=30)


def run_command(argv, tree, timeout: float, *, command=None, refusal=None,
                env=None):
    """Return (receipt, raw stdout, raw stderr), including failed supervision.

    Failure to persist raises OSError: callers must refuse rather than advance
    without evidence. An initial refusal is persisted without spawning a child.
    """
    root = Path(tree or Path.cwd()).resolve()
    directory = state_root.state_root() / "verification" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    path = directory / "receipt.json"
    out_path, err_path = directory / "stdout.bin", directory / "stderr.bin"
    project = state_root.find_repo_root(root)
    record = {
        "kind": "command-verification/v1", "command": command,
        "argv": list(argv), "cwd": str(root),
        "project": None if project is None else str(project),
        "started_at": stamp(), "ended_at": None, "exit_status": None,
        "outcome": "running", "timeout_seconds": timeout,
        "artifact_before": artifact_identity(root), "artifact_after": None,
        "changed_tree": None, "stdout_path": str(out_path),
        "stderr_path": str(err_path),
    }
    _write(path, record)
    child = None
    with out_path.open("wb") as out, err_path.open("wb") as err:
        try:
            if refusal is not None:
                record.update(outcome="spawn-failed", error=refusal)
            else:
                child = subprocess.Popen(
                    list(argv), cwd=str(root), stdout=out, stderr=err, env=env,
                    start_new_session=os.name != "nt",
                )
                record["pid"] = child.pid
                _write(path, record)
                record["exit_status"] = child.wait(timeout=timeout)
                record["outcome"] = "completed"
        except subprocess.TimeoutExpired as error:
            record.update(outcome="timeout", error=str(error))
        except (KeyboardInterrupt, SystemExit) as error:
            record.update(outcome="interrupted", error=type(error).__name__)
        except (OSError, ValueError) as error:
            record.update(outcome="spawn-failed", error=str(error))
        finally:
            if child is not None and record["outcome"] != "completed":
                try:
                    _terminate(child)
                    record["exit_status"] = child.returncode
                except (OSError, subprocess.SubprocessError) as error:
                    record["cleanup_error"] = str(error)
            out.flush()
            err.flush()
            os.fsync(out.fileno())
            os.fsync(err.fileno())
    raw_out, raw_err = out_path.read_bytes(), err_path.read_bytes()
    record.update(ended_at=stamp(), artifact_after=artifact_identity(root),
                  stdout_sha256=digest(raw_out), stderr_sha256=digest(raw_err))
    record["changed_tree"] = record["artifact_before"] != record["artifact_after"]
    record["evidence"] = _write(path, record)
    return record, raw_out, raw_err
