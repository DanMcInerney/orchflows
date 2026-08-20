"""Deterministic Workflows identities and canonical contained file reads."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from pathlib import Path
from urllib.parse import quote


NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class WorkflowIdentityError(ValueError):
    """A canonical identity input is malformed."""


class ContainedFileError(OSError):
    """A canonical file cannot be opened inside its declared boundary."""


class ContainedFileUnavailable(ContainedFileError):
    """A contained canonical file exists but cannot be read."""


@dataclass(frozen=True)
class WorkflowRoots:
    """Canonical package, library, and executable roots for one layout."""

    package: Path
    library: Path
    executable: Path


def workflow_roots(root: Path) -> WorkflowRoots:
    """Derive checkout ``scripts/`` or installed sibling ``bin/`` roots."""

    library = Path(root).resolve()
    checkout_scripts = library / "scripts"
    if library.name == "lib" and not contained_directory(library, checkout_scripts):
        return WorkflowRoots(library.parent, library, library.parent / "bin")
    return WorkflowRoots(library, library, checkout_scripts)


def _contained_target(boundary: Path, candidate: Path) -> tuple[Path, Path]:
    try:
        resolved_boundary = Path(boundary).resolve(strict=True)
        resolved = Path(candidate).resolve(strict=True)
        resolved.relative_to(resolved_boundary)
    except (OSError, RuntimeError, ValueError) as error:
        raise ContainedFileError("canonical file escapes its boundary") from error
    return resolved_boundary, resolved


def contained_directory(boundary: Path, candidate: Path) -> bool:
    try:
        _, resolved = _contained_target(boundary, candidate)
    except ContainedFileError:
        return False
    return resolved.is_dir()


def contained_file(boundary: Path, candidate: Path) -> bool:
    try:
        _, resolved = _contained_target(boundary, candidate)
    except ContainedFileError:
        return False
    return resolved.is_file()


def installed_source(root: Path, installed_path: str) -> tuple[Path, Path] | None:
    """Map one allowlisted installed path to its independent boundary."""

    try:
        installed = normalize_installed_path(installed_path)
    except WorkflowIdentityError:
        return None
    roots = workflow_roots(root)
    if installed.startswith("lib/"):
        return roots.library, roots.library / installed.removeprefix("lib/")
    if installed.startswith("bin/") and installed.count("/") == 1:
        return roots.executable, roots.executable / installed.removeprefix("bin/")
    return None


def _windows_opened_path(file_descriptor: int) -> Path:
    import msvcrt
    from ctypes import wintypes

    get_final_path = ctypes.WinDLL("kernel32", use_last_error=True).GetFinalPathNameByHandleW
    get_final_path.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    get_final_path.restype = wintypes.DWORD
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(file_descriptor))
    length = get_final_path(handle, None, 0, 0)
    if length == 0:
        raise ContainedFileError("opened file identity is unavailable")
    buffer = ctypes.create_unicode_buffer(length + 1)
    if get_final_path(handle, buffer, len(buffer), 0) == 0:
        raise ContainedFileError("opened file identity is unavailable")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value).resolve(strict=True)


def _opened_path(file_descriptor: int) -> Path:
    if os.name == "nt":
        return _windows_opened_path(file_descriptor)
    if sys.platform == "darwin":
        import fcntl

        raw = fcntl.fcntl(file_descriptor, 50, b"\0" * 1024)
        value = raw.split(b"\0", 1)[0].decode(sys.getfilesystemencoding())
        return Path(value).resolve(strict=True)
    try:
        value = os.readlink(f"/proc/self/fd/{file_descriptor}")
        return Path(value).resolve(strict=True)
    except (OSError, UnicodeError) as error:
        raise ContainedFileError("opened file identity is unavailable") from error


def read_contained_bytes(boundary: Path, candidate: Path) -> bytes:
    """Open once, validate the held object, and read through that descriptor."""

    resolved_boundary, expected = _contained_target(boundary, candidate)
    try:
        expected_stat = expected.stat()
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        file_descriptor = os.open(candidate, flags)
    except OSError as error:
        raise ContainedFileUnavailable("canonical file is unreadable") from error
    try:
        opened_stat = os.fstat(file_descriptor)
        opened_path = _opened_path(file_descriptor)
        opened_path.relative_to(resolved_boundary)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ContainedFileError("canonical source is not a regular file")
        if opened_path != expected or not os.path.samestat(opened_stat, expected_stat):
            raise ContainedFileError("canonical file changed while it was opened")
        chunks = []
        while True:
            chunk = os.read(file_descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    except (OSError, RuntimeError, ValueError) as error:
        if isinstance(error, ContainedFileError):
            raise
        raise ContainedFileUnavailable("canonical file is unreadable") from error
    finally:
        os.close(file_descriptor)


def read_contained_text(boundary: Path, candidate: Path) -> str:
    try:
        return read_contained_bytes(boundary, candidate).decode("utf-8")
    except UnicodeError as error:
        raise ContainedFileError("canonical file is not UTF-8") from error


def _name(value: object, subject: str) -> str:
    if not isinstance(value, str) or NAME_RE.fullmatch(value) is None:
        raise WorkflowIdentityError(f"{subject} is not a canonical name")
    return value


def normalize_installed_path(path: object) -> str:
    """Return one stable installed-library-relative POSIX path."""

    if not isinstance(path, str) or not path or path != path.strip():
        raise WorkflowIdentityError("installed path must be a non-empty string")
    portable = path.replace("\\", "/")
    if portable.startswith("/") or re.match(r"[A-Za-z]:", portable):
        raise WorkflowIdentityError("installed path must be relative")
    if ".." in portable.split("/"):
        raise WorkflowIdentityError("installed path cannot traverse its root")
    normalized = PurePosixPath(portable).as_posix()
    if normalized in {"", "."}:
        raise WorkflowIdentityError("installed path must name a file")
    return normalized


def workflow_node_id(workflow: str) -> str:
    return f"workflow:{_name(workflow, 'workflow')}"


def work_node_id(workflow: str, stub: str) -> str:
    return f"work:{_name(workflow, 'workflow')}/{_name(stub, 'stub')}"


def skill_node_id(skill: str) -> str:
    return f"skill:{_name(skill, 'skill')}"


def script_node_id(installed_path: str) -> str:
    return f"script:{normalize_installed_path(installed_path)}"


def edge_id(kind: str, source: str, target: str) -> str:
    """Encode an edge tuple so repeated occurrences have one stable ID."""

    kind = _name(kind, "edge kind")
    if not isinstance(source, str) or not source:
        raise WorkflowIdentityError("edge source must be a non-empty string")
    if not isinstance(target, str) or not target:
        raise WorkflowIdentityError("edge target must be a non-empty string")
    return "edge:{0}:{1}:{2}".format(
        quote(kind, safe=""),
        quote(source, safe=""),
        quote(target, safe=""),
    )


def source_id(installed_path: str) -> str:
    """Hash a normalized installed path into an opaque URL-safe source ID."""

    normalized = normalize_installed_path(installed_path)
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return "src_" + encoded
