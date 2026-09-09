"""Discover and identify a usable native Blender executable.

The probe records facts observed from the executable on this machine. The
package never embeds a machine-specific path; callers can pass ``--blender``
or use the generic environment/PATH and standard installation-root search.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


EXIT_OK = 0
EXIT_INVALID = 2
EXIT_CAPABILITY = 3


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _candidate_paths() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("BLENDER_EXECUTABLE")
    if configured:
        candidates.append(Path(configured))
    found = shutil.which("blender")
    if found:
        candidates.append(Path(found))
    roots: list[Path] = []
    for variable in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA"):
        raw = os.environ.get(variable)
        if raw:
            roots.append(Path(raw))
    for root in roots:
        foundation = root / "Blender Foundation"
        if foundation.is_dir():
            candidates.extend(sorted(foundation.glob("**/blender.exe")))
            candidates.extend(sorted(foundation.glob("**/blender")))
    # Preserve first-seen ordering while eliminating aliases.
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def locate_blender(explicit: Path | None = None) -> Path | None:
    if explicit is not None and not explicit.is_absolute():
        return None
    candidates = [explicit] if explicit else _candidate_paths()
    for candidate in candidates:
        if candidate is None:
            continue
        path = candidate.expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
    return None


def _version_probe(executable: Path, timeout: float) -> tuple[int, str, str]:
    expression = (
        "import bpy, json, platform; "
        "text=lambda value: value.decode('utf-8', 'replace') if isinstance(value, bytes) else str(value); "
        "print(json.dumps({'version': '.'.join(map(str, bpy.app.version)), "
        "'version_string': text(bpy.app.version_string), 'build': text(bpy.app.build_hash), "
        "'build_date': text(bpy.app.build_date), 'backend': platform.platform()}))"
    )
    argv = [str(executable), "--background", "--factory-startup", "--python-expr", expression]
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return 5, "", "Blender capability probe timed out"
    return completed.returncode, completed.stdout, completed.stderr


def _extract_identity(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "version" in value and "build" in value:
            return value
    return None


def probe(executable: Path | None = None, *, timeout: float = 30.0) -> dict[str, Any]:
    """Return a capability record without claiming render/export support."""

    found = locate_blender(executable)
    if found is None:
        return {"status": "unavailable", "kind": "blender-capability", "gaps": ["blender-executable"]}
    if not found.is_absolute():
        return {"status": "unverified", "kind": "blender-capability", "gaps": ["absolute-path"]}
    try:
        code, stdout, stderr = _version_probe(found, timeout)
    except OSError as exc:
        return {"status": "unverified", "kind": "blender-capability", "path": str(found), "error": str(exc), "gaps": ["probe-error"]}
    identity = _extract_identity(stdout)
    if code != 0 or identity is None:
        return {
            "status": "unverified",
            "kind": "blender-capability",
            "path": str(found),
            "exit_code": code,
            "stderr": stderr[-4000:],
            "gaps": ["bpy-version-probe"],
        }
    return {
        "status": "available",
        "kind": "blender-capability",
        "path": str(found),
        "executable_sha256": sha256_file(found),
        "version": identity.get("version"),
        "version_string": identity.get("version_string"),
        "build": identity.get("build"),
        "build_date": identity.get("build_date"),
        "backend": identity.get("backend"),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "exit_code": code,
        "gaps": ["render-export-probe-pending"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        print(json.dumps({"status": "invalid", "error": "timeout must be positive"}, sort_keys=True))
        return EXIT_INVALID
    record = probe(args.blender, timeout=args.timeout)
    print(json.dumps(record, sort_keys=True))
    return EXIT_OK if record["status"] == "available" else EXIT_CAPABILITY


if __name__ == "__main__":
    raise SystemExit(main())
