"""Reference packages: assemble one from its committed generator and the kit, and build the private slice.

`BB/reference-packages/<mt>/generate.py --instances offline|<dir> --out <pkg>` writes a package without the kit;
assembling copies `benchkit/` and `run.py` in, the way a builder's package gets them. `instances` is `offline`
(the committed synthetic instances), `public` (the store's public material) or a directory.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from . import execute, registry, store

store.use_kit()
from benchkit import launch  # noqa: E402

GENERATE_SECONDS = 900


class RefpkgError(Exception):
    pass


def instances_arg(meta_task: str, instances: str, store_root: Path | None) -> str:
    if instances == "offline":
        return instances
    if instances == "public":
        return str(store.Store(store_root or store.default_store()).material(meta_task) / "public")
    return str(Path(instances))


def assemble(meta_task: str, out: Path, *, instances: str = "offline", store_root: Path | None = None,
             seconds: float = GENERATE_SECONDS) -> Path:
    """Write the reference package for a meta-task into `out` (which must be new or empty), kit included."""
    task = registry.get(meta_task)
    generate = Path(task.reference) / "generate.py"
    out = Path(out)
    if not generate.is_file():
        raise RefpkgError(f"{meta_task}: no generator at {generate}")
    if out.exists() and any(out.iterdir()):
        raise RefpkgError(f"{out} is not empty")
    with tempfile.TemporaryDirectory(prefix="refpkg-") as scratch:
        command = [sys.executable, str(generate), "--instances", instances_arg(meta_task, instances, store_root),
                   "--out", str(out)]
        outcome = launch.run_capped(command, cwd=Path(task.reference), env=None, stdout=Path(scratch) / "out.txt",
                                    stderr=Path(scratch) / "err.txt", timeout=seconds)
        if outcome.status != "completed" or outcome.exit_code != 0:
            raise RefpkgError(f"generate.py failed ({outcome.reason}): {execute.tail(Path(scratch) / 'err.txt', 600)}")
    shutil.copytree(store.KIT / "benchkit", out / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(store.KIT / "run.py", out / "run.py")
    return out


def build_slice(meta_task: str, st: store.Store, slice_id: str | None = None) -> tuple[str, Path]:
    """The private slice: a reference package generated from the store's held-out material."""
    slice_id = slice_id or store.anon_id("s")
    package = st.slice(meta_task, slice_id) / "package"
    held_out = st.material(meta_task) / "held-out"
    if not held_out.is_dir():
        raise RefpkgError(f"no held-out material at {held_out}; run `material fetch --meta-task {meta_task}` first")
    assemble(meta_task, package, instances=str(held_out), store_root=st.root)
    return slice_id, package
