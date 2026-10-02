"""The delivered package as the meta-verifier reads it: tasks, their public workspaces and prompts, and which task a
captured prompt and workspace belong to. Reads the package's own files and nothing from the kit.
"""
from __future__ import annotations

import filecmp
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Task:
    id: str
    dir: Path
    instruction: str

    @property
    def environment(self) -> Path:
        return self.dir / "environment"


def files(root: Path):
    """Files under root (links skipped), skipping bytecode folders."""
    root = Path(root)
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
            yield path


def tasks(package: Path) -> dict[str, Task]:
    base = Path(package) / "tasks"
    found = {}
    for folder in sorted(base.iterdir()) if base.is_dir() else []:
        if (folder / "instruction.md").is_file():
            found[folder.name] = Task(folder.name, folder, (folder / "instruction.md").read_text(encoding="utf-8", errors="replace"))
    return found


def stage(task: Task, workspace: Path) -> str:
    """The task's public workspace (a plain copy of environment/) and its prompt, for the domain's recognizer."""
    workspace = Path(workspace)
    if task.environment.is_dir():
        shutil.copytree(task.environment, workspace, ignore=shutil.ignore_patterns("__pycache__"))
    else:
        workspace.mkdir(parents=True)
    return task.instruction


def _same_environment(task: Task, workspace: Path) -> bool:
    return all((Path(workspace) / path.relative_to(task.environment)).is_file()
               and filecmp.cmp(path, Path(workspace) / path.relative_to(task.environment), shallow=False)
               for path in files(task.environment) if path.stat().st_size)


def identify(delivered: dict[str, Task], prompt: str, workspace: Path | None = None) -> str | None:
    """The one task whose instruction the prompt holds, told apart by its unchanged environment files when several
    share the instruction; None when no task, or no single task, fits."""
    found = [t for t in delivered.values() if t.instruction.strip() and t.instruction.strip() in prompt]
    if len(found) > 1 and workspace is not None:
        found = [t for t in found if _same_environment(t, workspace)] or found
    return found[0].id if len(found) == 1 else None


def suite(package: Path) -> dict:
    try:
        return json.loads((Path(package) / "suite.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def copied_from(package: Path, reference: Path | None) -> list[str]:
    """Files of the package byte-identical to a file of the committed reference package sources, as package-relative
    paths; the kit's own files are not counted. Flagged for the report, never penalized."""
    if reference is None or not Path(reference).is_dir():
        return []
    known: dict[int, list[Path]] = {}
    for path in files(reference):
        if path.stat().st_size:
            known.setdefault(path.stat().st_size, []).append(path)
    filecmp.clear_cache()
    found = []
    for path in files(package):
        relative = path.relative_to(package).as_posix()
        if relative == "run.py" or relative.startswith("benchkit/"):
            continue
        if any(filecmp.cmp(path, other, shallow=False) for other in known.get(path.stat().st_size, [])):
            found.append(relative)
    return found
