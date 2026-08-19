"""Installer-owned private Python runtime lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

from .foundation import MIN_PYTHON, REPO_ROOT, _scope_home

RUNTIME_REQUIREMENTS = REPO_ROOT / "requirements-runtime.txt"
RUNTIME_METADATA_FILENAME = ".orchflows-runtime.json"


def private_runtime_home() -> Path:
    """The user-owned runtime shared by every orchflows checkout."""

    return _scope_home("user", None) / "runtime"


def private_runtime_python(runtime_home: Path | None = None) -> Path:
    home = private_runtime_home() if runtime_home is None else runtime_home
    return home / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _runtime_requirement_lines() -> list[str]:
    return [
        line.strip()
        for line in RUNTIME_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _runtime_metadata() -> dict:
    return {
        "schema": 1,
        "requirements_sha256": hashlib.sha256(
            RUNTIME_REQUIREMENTS.read_bytes()
        ).hexdigest(),
    }


def _read_runtime_metadata(runtime_home: Path) -> dict | None:
    try:
        reading = json.loads(
            (runtime_home / RUNTIME_METADATA_FILENAME).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None
    return reading if isinstance(reading, dict) else None


def private_runtime_is_owned(runtime_home: Path | None = None) -> bool:
    """Whether ``home`` carries metadata written by this installer.

    Requirement drift makes a runtime unhealthy but does not make it
    unowned. A directory with missing or foreign metadata is never safe for
    the installer to recursively replace.
    """

    home = private_runtime_home() if runtime_home is None else runtime_home
    metadata = _read_runtime_metadata(home)
    return bool(
        metadata is not None
        and set(metadata) == {"schema", "requirements_sha256"}
        and metadata.get("schema") == 1
        and isinstance(metadata.get("requirements_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", metadata["requirements_sha256"])
    )


def private_runtime_is_healthy(runtime_home: Path | None = None) -> bool:
    home = private_runtime_home() if runtime_home is None else runtime_home
    runtime_python = private_runtime_python(home)
    if not runtime_python.is_file():
        return False
    metadata = _read_runtime_metadata(home)
    if metadata is None:
        return False
    try:
        expected_metadata = _runtime_metadata()
    except OSError:
        return False
    if metadata != expected_metadata:
        return False
    try:
        probe = subprocess.run(
            [
                str(runtime_python),
                "-I",
                "-c",
                "import json, sys; print(json.dumps({"
                "'prefix': sys.prefix, 'version': list(sys.version_info[:3])}))",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if probe.returncode != 0:
        return False
    try:
        reading = json.loads(probe.stdout)
        version = tuple(reading["version"])
        return (
            Path(reading["prefix"]).resolve() == home.resolve()
            and version >= MIN_PYTHON
        )
    except (KeyError, OSError, TypeError, ValueError):
        return False


def private_runtime_action(runtime_home: Path | None = None) -> str:
    """Return the action apply would take: create, reuse, repair or refuse."""

    home = private_runtime_home() if runtime_home is None else runtime_home
    if private_runtime_is_healthy(home):
        return "reuse"
    if not home.exists():
        return "create"
    return "repair" if private_runtime_is_owned(home) else "refuse"


def _dependency_environment() -> dict[str, str]:
    """Keep ambient project/Python configuration out of runtime installs."""

    environment = os.environ.copy()
    for name in (
        "PIP_CONFIG_FILE",
        "PIP_PREFIX",
        "PIP_TARGET",
        "PIP_USER",
        "PYTHONHOME",
        "PYTHONPATH",
    ):
        environment.pop(name, None)
    environment["PIP_CONFIG_FILE"] = os.devnull
    return environment


def _build_private_runtime(runtime_home: Path) -> Path:
    requirement_lines = _runtime_requirement_lines()
    venv.EnvBuilder(with_pip=bool(requirement_lines)).create(runtime_home)
    runtime_python = private_runtime_python(runtime_home)
    if requirement_lines:
        installed = subprocess.run(
            [
                str(runtime_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--requirement",
                str(RUNTIME_REQUIREMENTS),
            ],
            check=False,
            env=_dependency_environment(),
        )
        if installed.returncode != 0:
            raise RuntimeError("private runtime dependency installation failed")
    (runtime_home / RUNTIME_METADATA_FILENAME).write_text(
        json.dumps(_runtime_metadata(), sort_keys=True) + "\n", encoding="utf-8"
    )
    if not private_runtime_is_healthy(runtime_home):
        raise RuntimeError(f"private runtime is not healthy at {runtime_python}")
    return runtime_python


def _create_private_runtime() -> Path:
    """Create or replace the managed runtime without risking the old one.

    A replacement is built and probed in a sibling staging directory first.
    Only an installer-owned target is moved aside, and a failed swap restores
    it before the error reaches the caller.
    """

    runtime_home = private_runtime_home()
    action = private_runtime_action(runtime_home)
    if action == "reuse":
        return private_runtime_python(runtime_home)
    if action == "refuse":
        raise RuntimeError(
            f"refusing to replace unowned private runtime at {runtime_home}; "
            "move it aside or remove it manually, then reinstall"
        )

    runtime_home.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{runtime_home.name}-build-", dir=runtime_home.parent)
    )
    backup = None
    try:
        _build_private_runtime(staging)
        if runtime_home.exists():
            backup = Path(
                tempfile.mkdtemp(
                    prefix=f".{runtime_home.name}-backup-", dir=runtime_home.parent
                )
            )
            backup.rmdir()
            runtime_home.replace(backup)
        try:
            staging.replace(runtime_home)
        except Exception:
            if backup is not None and backup.exists() and not runtime_home.exists():
                backup.replace(runtime_home)
            raise
        if not private_runtime_is_healthy(runtime_home):
            shutil.rmtree(runtime_home)
            if backup is not None and backup.exists():
                backup.replace(runtime_home)
            raise RuntimeError(
                "private runtime replacement is not healthy at "
                f"{private_runtime_python(runtime_home)}"
            )
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
        return private_runtime_python(runtime_home)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
