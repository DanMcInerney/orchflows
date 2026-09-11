"""Small, portable workflow history. Python 3.11+; no host transcript capture.

Finalization is immutable: repeating the same status and exact summary bytes is
idempotent and preserves the original finish time. A concurrent writer gets an
OSError and can retry after the writer finishes. A crash may leave .finish.lock;
inspect the run before removing that lock. Interrupted summary publication can
be resumed only with the same bytes; existing results are never replaced.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid


_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
_PROJECT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_RUN_ID = re.compile(r"\d{8}T\d{12}Z-[0-9a-f]{32}\Z")
_FINAL_STATUSES = {"complete", "partial", "blocked"}


def _workflow_parts(workflow: str) -> tuple[str, str]:
    parts = workflow.split(":")
    if len(parts) != 2 or any(not _NAME.fullmatch(part) for part in parts):
        raise ValueError("workflow must be LIBRARY:SKILL using simple package and skill names")
    return parts[0], parts[1]


def _logs_root(home: Path, *, create: bool = False) -> tuple[Path, Path]:
    home = Path(home).expanduser().resolve(strict=True)
    if not home.is_dir():
        raise ValueError("orchflows home must be an existing directory; run setup first")
    logs = home / "logs"
    if logs.resolve() != logs:
        raise ValueError("home/logs must not redirect through a symlink or junction")
    if create:
        logs.mkdir(exist_ok=True)
    if not logs.is_dir():
        raise ValueError("home/logs is not a directory")
    return home, logs


def _atomic_write(path: Path, content: bytes) -> None:
    """Publish a complete file on the same filesystem; caller owns its lock."""
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _write_json(path: Path, data: dict) -> None:
    _atomic_write(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _read_package_file(root: Path, relative: str) -> bytes | None:
    path = root / relative
    try:
        if not path.resolve().is_relative_to(root):
            return None
        return path.read_bytes()
    except OSError:
        return None


def _package_identity(home: Path, library: str, skill: str | None = None) -> dict:
    relative_root = (".local/packages" if library == "orchflows-light" else "libraries") + "/" + library
    root = home / relative_root
    if not root.resolve().is_relative_to(home):
        return {}
    root = root.resolve()
    identity = {}
    for relative in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        content = _read_package_file(root, relative)
        if content is None:
            continue
        try:
            manifest = json.loads(content)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(manifest, dict) or manifest.get("name") != library:
            continue
        identity = {"manifest": relative, "name": manifest["name"],
                    "manifest_sha256": hashlib.sha256(content).hexdigest()}
        if isinstance(manifest.get("version"), str):
            identity["version"] = manifest["version"]
        break
    if skill:
        relative = f"skills/{skill}/SKILL.md"
        content = _read_package_file(root, relative)
        if content is not None:
            identity["skill"] = {"path": relative, "sha256": hashlib.sha256(content).hexdigest()}
    if identity:
        identity["home_path"] = relative_root
    return identity


def _result(run_dir: Path, metadata: dict) -> dict:
    result = {**metadata, "run_dir": str(run_dir), "run_json": str(run_dir / "run.json")}
    if metadata.get("summary"):
        result["summary_file"] = str(run_dir / metadata["summary"]["path"])
    return result


def start_run(home: Path, workflow: str, project: str | None = None) -> dict:
    """Create a unique run; project is an optional portable alias, not a path."""
    library, skill = _workflow_parts(workflow)
    if project is not None and not _PROJECT.fullmatch(project):
        raise ValueError("project must be a simple alias, not a path")
    home, logs = _logs_root(home, create=True)
    now = datetime.now(timezone.utc)
    month = logs / now.strftime("%Y-%m")
    if month.resolve() != month:
        raise ValueError("run month must not redirect through a symlink or junction")
    month.mkdir(exist_ok=True)
    for _ in range(10):
        run_id = f"{now:%Y%m%dT%H%M%S%fZ}-{uuid.uuid4().hex}"
        run_dir = month / run_id
        try:
            run_dir.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise OSError("could not allocate a unique run directory after 10 attempts")

    metadata = {"schema_version": 1, "run_id": run_id, "workflow": workflow,
                "status": "running", "started_at": now.isoformat().replace("+00:00", "Z")}
    if project is not None:
        metadata["project"] = project
    provenance = {}
    for label, package, component in (("core", "orchflows-light", None), ("workflow", library, skill)):
        identity = _package_identity(home, package, component)
        if identity:
            provenance[label] = identity
    if provenance:
        metadata["provenance"] = provenance
    _write_json(run_dir / "run.json", metadata)
    return _result(run_dir, metadata)


def _checked_run(logs: Path, run_dir: Path) -> Path:
    run_dir = Path(run_dir).expanduser().absolute()
    resolved = run_dir.resolve(strict=True)
    if resolved != run_dir or resolved.parent.parent != logs:
        raise ValueError("run directory must be directly under home/logs/YYYY-MM without redirects")
    if not re.fullmatch(r"\d{4}-\d{2}", run_dir.parent.name) or not _RUN_ID.fullmatch(run_dir.name):
        raise ValueError("run directory is not an orchflows run path")
    if not run_dir.is_dir():
        raise ValueError("run directory is not a directory")
    return run_dir


def _read_metadata(run_dir: Path) -> dict:
    path = run_dir / "run.json"
    if path.resolve() != path:
        raise ValueError("run.json must not redirect through a symlink or junction")
    try:
        metadata = json.loads(path.read_bytes())
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("run.json is not valid UTF-8 JSON") from error
    if (not isinstance(metadata, dict) or type(metadata.get("schema_version")) is not int
            or metadata["schema_version"] != 1
            or metadata.get("run_id") != run_dir.name
            or not isinstance(metadata.get("status"), str)
            or metadata.get("status") not in {"running", *_FINAL_STATUSES}
            or not isinstance(metadata.get("started_at"), str)
            or not isinstance(metadata.get("workflow"), str)):
        raise ValueError("run.json is not valid orchflows run metadata")
    _workflow_parts(metadata["workflow"])
    try:
        started = datetime.fromisoformat(metadata["started_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("run.json has an invalid start time") from error
    if (started.tzinfo is None or started.utcoffset().total_seconds() != 0
            or started.strftime("%Y-%m") != run_dir.parent.name
            or not run_dir.name.startswith(started.strftime("%Y%m%dT%H%M%S%fZ-"))):
        raise ValueError("run.json start time does not match its UTC run path")
    return metadata


def finish_run(home: Path, run_dir: Path, status: str, summary_file: Path) -> dict:
    """Finalize with an actual UTF-8 summary; preserve completed or conflicting data."""
    if status not in _FINAL_STATUSES:
        raise ValueError("status must be complete, partial, or blocked")
    _, logs = _logs_root(home)
    run_dir = _checked_run(logs, run_dir)
    summary = Path(summary_file).expanduser().read_bytes()
    try:
        if not summary.decode("utf-8-sig").strip():
            raise ValueError("summary must contain actual text")
    except UnicodeDecodeError as error:
        raise ValueError("summary must be UTF-8 text") from error
    receipt = {"path": "summary.md", "sha256": hashlib.sha256(summary).hexdigest()}
    lock = run_dir / ".finish.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise OSError("run finalization is locked; retry when the writer finishes or inspect a stale .finish.lock") from error
    try:
        os.close(descriptor)
        metadata = _read_metadata(run_dir)
        destination = run_dir / "summary.md"
        if destination.resolve() != destination:
            raise ValueError("summary.md must not redirect through a symlink or junction")
        existing_summary = destination.read_bytes() if destination.exists() else None
        if metadata["status"] in _FINAL_STATUSES:
            if (metadata["status"] == status and metadata.get("summary") == receipt
                    and existing_summary == summary and isinstance(metadata.get("finished_at"), str)):
                return _result(run_dir, metadata)
            raise ValueError("run is already finalized; only identical status and summary may be repeated")
        if existing_summary is not None and existing_summary != summary:
            raise ValueError("summary.md already contains different data; preserving it")
        if existing_summary is None:
            _atomic_write(destination, summary)
        metadata.update(status=status, summary=receipt,
                        finished_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        _write_json(run_dir / "run.json", metadata)
        return _result(run_dir, metadata)
    finally:
        lock.unlink()
