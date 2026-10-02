"""Stage a task's public material for a solver and capture its final workspace for grading.

A solver sees `environment/` and the prompt, nothing else. Staging refuses anything that could carry
evaluator material into the workspace; it never repairs a task silently.
"""
from __future__ import annotations

import filecmp
import os
import shutil
from pathlib import Path

EVALUATOR_NAMES = {"solution", "tests", "labeled", "admission", "evaluation", "identity"}


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


def capture(workspace: Path, dest: Path) -> None:
    """Copy the final workspace to `dest` for grading. Links are neither followed nor copied."""
    workspace, dest = Path(workspace), Path(dest)
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")
    dest.mkdir(parents=True)
    for path, kind in walk(workspace):
        target = dest / path.relative_to(workspace)
        if kind == "dir":
            target.mkdir(parents=True, exist_ok=True)
        elif kind == "file":
            shutil.copy2(path, target)
