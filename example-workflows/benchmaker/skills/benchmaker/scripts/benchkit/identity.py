"""Retain the bytes a run used, prove they are unchanged, and record the tool versions observed."""
from __future__ import annotations

import filecmp
import os
import shutil
import stat
import tempfile
from pathlib import Path

from .launch import run_capped
from .stage import walk

SKIPPED = frozenset({"runs", "__pycache__", ".git"})
OBSERVE_SECONDS = 30


class IdentityError(Exception):
    pass


def _layout(roots: dict[str, Path]) -> dict[str, Path]:
    """Every regular file under each root, keyed by `name` for a file root and `name/relative` for a folder.

    Folders named in SKIPPED are left out; a link raises.
    """
    layout = {}
    for name, root in roots.items():
        root = Path(root)
        if root.is_file():
            layout[name] = root
            continue
        for path, kind in walk(root, SKIPPED):
            if kind == "link":
                raise IdentityError(f"link in retained material: {path}")
            if kind == "file":
                layout[f"{name}/{path.relative_to(root).as_posix()}"] = path
    return layout


def retain(sources: dict[str, Path], dest: Path) -> None:
    """Copy each source (a file or folder) to `dest/<name>` as real files, then mark them read-only."""
    dest = Path(dest)
    for name, source in sources.items():
        if not Path(source).exists():
            raise FileNotFoundError(source)
        if (dest / name).exists():
            raise FileExistsError(f"{dest / name} is already retained")
    for name, source in sources.items():
        if Path(source).is_dir():
            (dest / name).mkdir(parents=True)
    for relative, path in _layout(sources).items():
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(stat.S_IREAD)


def compare(sources: dict[str, Path], retained: Path) -> list[str]:
    """'changed: x', 'missing: x' (retained, gone from the source) or 'extra: x' (in the source, not retained)."""
    retained = Path(retained)
    filecmp.clear_cache()  # filecmp caches by size and mtime; the bytes must always be read
    now = _layout(sources)
    kept = _layout({name: retained / name for name in sources})
    found = [f"missing: {name}" for name in sorted(kept.keys() - now.keys())]
    found += [f"extra: {name}" for name in sorted(now.keys() - kept.keys())]
    found += [f"changed: {name}" for name in sorted(kept.keys() & now.keys())
              if not filecmp.cmp(now[name], kept[name], shallow=False)]
    return found


def observe(commands: list[list[str]], cwd: Path) -> dict[str, str]:
    """Run each command, capped at 30 s, and record its output text keyed by the command line."""
    seen = {}
    with tempfile.TemporaryDirectory() as folder:
        out, err = Path(folder) / "out", Path(folder) / "err"
        for command in commands:
            outcome = run_capped(command, cwd=cwd, stdout=out, stderr=err, timeout=OBSERVE_SECONDS)
            text = (out.read_text(encoding="utf-8", errors="replace") + err.read_text(encoding="utf-8", errors="replace")).strip()
            if outcome.status != "completed":
                text = f"{text}\n[{outcome.status}: {outcome.reason}]".strip()
            seen[" ".join(map(str, command))] = text
    return seen


def discard(path: Path) -> None:
    """Delete a retained tree whose files are read-only."""
    path = Path(path)
    for root, folders, files in os.walk(path):
        for name in folders + files:
            try:
                os.chmod(Path(root) / name, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=True)
