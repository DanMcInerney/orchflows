"""Stage a task's public material for a solver and capture its final workspace for grading.

A solver is handed `environment/` and the prompt, at paths in a temporary root, and nothing else. Staging
refuses anything that could carry evaluator material into the workspace; it never repairs a task silently.
The kit does not sandbox the solver process: it can read whatever its user can.
"""
from __future__ import annotations

import errno
import filecmp
import os
import shutil
import stat
import sys
from pathlib import Path

EVALUATOR_NAMES = {"solution", "tests", "labeled", "admission", "evaluation", "identity"}
EXTENDED = "\\\\?\\"   # the Windows extended-length path prefix, \\?\
SKIP_LIMIT = 50   # skipped entries listed by name; the rest are counted
# Capture errors that belong to the host rather than to the solver's files.
HARNESS_ERRNOS = {getattr(errno, name) for name in ("ENOSPC", "EDQUOT", "EMFILE", "ENFILE", "ENOMEM", "EIO", "EROFS")
                  if hasattr(errno, name)}


class StagingError(Exception):
    pass


def is_link(path: Path) -> bool:
    """A symbolic link, or on Windows a junction."""
    return path.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(path)


def walk(root: Path, skip: frozenset = frozenset()):
    """Every path under `root` as (path, kind), kind 'dir', 'file' or 'link'. Links are listed, never entered;
    folders named in `skip` are left out."""
    if not root.is_dir():
        return
    for entry in sorted(os.scandir(root), key=lambda item: item.name):
        path = Path(entry.path)
        if is_link(path):
            yield path, "link"
        elif entry.is_dir():
            if entry.name not in skip:
                yield path, "dir"
                yield from walk(path, skip)
        else:
            yield path, "file"


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _leaks(environment: Path, task_dir: Path):
    """Raise on links, evaluator names and files byte-identical to a solution or test file."""
    files = []
    for path, kind in walk(environment):
        relative = path.relative_to(environment)
        if kind == "link":
            raise StagingError(f"link in environment: {relative.as_posix()}")
        named = next((part for part in relative.parts if part.lower() in EVALUATOR_NAMES), None)
        if named:
            raise StagingError(f"evaluator name {named!r} in environment: {relative.as_posix()}")
        if kind == "file" and path.stat().st_size:
            files.append(path)
    filecmp.clear_cache()
    evaluator = [path for folder in ("solution", "tests") for path, kind in walk(task_dir / folder)
                 if kind == "file" and path.stat().st_size]
    for path in files:
        for other in evaluator:
            if other.stat().st_size == path.stat().st_size and filecmp.cmp(path, other, shallow=False):
                raise StagingError(f"environment file {path.relative_to(environment).as_posix()} "
                                   f"is byte-identical to {other.relative_to(task_dir).as_posix()}")


def stage_public(task_dir: Path, workspace: Path, prompt_path: Path) -> None:
    """Copy `environment/**` into `workspace` and write `instruction.md` to `prompt_path`.

    Raises StagingError when a path component is an evaluator name, a link is present, a staged file is
    byte-identical to a file under solution/ or tests/, the workspace is not empty or lies inside the task or
    its package, or the prompt would land inside the workspace. Nothing is written when it raises.
    """
    task_dir, workspace, prompt_path = Path(task_dir).resolve(), Path(workspace).resolve(), Path(prompt_path).resolve()
    package = task_dir.parent.parent if task_dir.parent.name == "tasks" else task_dir
    if _inside(workspace, package) or _inside(workspace, task_dir):
        raise StagingError(f"workspace {workspace} lies inside the task or its package")
    if _inside(prompt_path, workspace):
        raise StagingError("the prompt must live outside the workspace")
    if workspace.exists() and any(workspace.iterdir()):
        raise StagingError(f"workspace {workspace} is not empty")
    instruction, environment = task_dir / "instruction.md", task_dir / "environment"
    if not instruction.is_file():
        raise StagingError(f"{task_dir.name} has no instruction.md")
    if is_link(environment):
        raise StagingError("link in task: environment")
    _leaks(environment, task_dir)
    workspace.mkdir(parents=True, exist_ok=True)
    for path, kind in walk(environment):
        target = workspace / path.relative_to(environment)
        if kind == "dir":
            target.mkdir(parents=True, exist_ok=True)
        else:
            shutil.copy2(path, target)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(instruction, prompt_path)


def long_path(path) -> str:
    """The absolute path as a string that Windows opens past MAX_PATH (an extended-length path); unchanged elsewhere."""
    text = os.path.abspath(path)
    if os.name != "nt" or text.startswith(EXTENDED):
        return text
    return EXTENDED + "UNC" + text[1:] if text.startswith("\\\\") else EXTENDED + text


def _clear_and_retry(function, path, _error) -> None:
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
        function(path)
    except OSError:
        pass


def discard(path) -> None:
    """Delete a tree whatever it holds: long paths, read-only files; whatever cannot be removed is left."""
    handler = {"onexc" if sys.version_info >= (3, 12) else "onerror": _clear_and_retry}
    shutil.rmtree(long_path(path), **handler)


class _Skipped:
    def __init__(self):
        self.lines, self.extra = [], 0

    def add(self, relative: str, reason: str) -> None:
        if len(self.lines) < SKIP_LIMIT:
            self.lines.append(f"{relative}: {reason}")
        else:
            self.extra += 1

    def report(self) -> list[str]:
        return self.lines + ([f"and {self.extra} more not listed"] if self.extra else [])


def _copy_dir(source: str, target: str, prefix: str, skipped: _Skipped) -> None:
    try:
        entries = sorted(os.scandir(source), key=lambda item: item.name)
    except OSError as error:
        if error.errno in HARNESS_ERRNOS:
            raise
        skipped.add(prefix.rstrip("/") or ".", f"unreadable directory: {error.strerror or type(error).__name__}")
        return
    for entry in entries:
        relative, copy = prefix + entry.name, os.path.join(target, entry.name)
        try:
            if is_link(Path(entry.path)):
                continue
            if entry.is_dir(follow_symlinks=False):
                os.mkdir(copy)
                _copy_dir(entry.path, copy, relative + "/", skipped)
            elif stat.S_ISREG(entry.stat(follow_symlinks=False).st_mode):
                shutil.copy2(entry.path, copy)
            else:
                skipped.add(relative, "not a regular file (pipe, socket or device)")
        except OSError as error:
            if error.errno in HARNESS_ERRNOS:
                raise
            skipped.add(relative, error.strerror or type(error).__name__)
            try:
                os.unlink(copy)
            except OSError:
                pass


def capture(workspace: Path, dest: Path) -> list[str]:
    """Copy the final workspace to `dest` for grading; links are neither followed nor copied.

    An entry the solver left that cannot be copied (a pipe or socket, an unreadable file or folder, a name the host
    refuses) is skipped, not fatal: the workspace is graded as captured. Returns the skipped entries as
    'path: reason' lines, at most SKIP_LIMIT of them and then a count. Only a fault of the host (no destination, a
    full disk, exhausted handles) raises. Windows long paths are handled.
    """
    workspace, dest = Path(workspace), Path(dest)
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")
    os.makedirs(long_path(dest))
    skipped = _Skipped()
    _copy_dir(long_path(workspace), long_path(dest), "", skipped)
    return skipped.report()
