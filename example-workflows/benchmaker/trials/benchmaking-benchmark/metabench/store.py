"""The private store, the output root and the work root: where they live and what keeps them apart.

The store holds held-out material, pools with their ORDER.json, private operators, slices and run records. It
must not sit inside the repository, the output root or the work root (nor contain them), so nothing a build or a
package run writes can land beside it by accident. `METABENCH_STORE` overrides the default; tests use temp stores.
"""
from __future__ import annotations

import json
import math
import os
import secrets
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
BB = Path(__file__).resolve().parents[1]
KIT = BB.parents[1] / "skills" / "benchmaker" / "scripts"


class StoreError(Exception):
    pass


def use_kit() -> None:
    """Put the kit's scripts directory on sys.path so `benchkit` imports."""
    if str(KIT) not in sys.path:
        sys.path.insert(0, str(KIT))


def default_store(env=None) -> Path:
    env = os.environ if env is None else env
    return Path(env.get("METABENCH_STORE") or Path.home() / ".bmk-eval" / "meta")


def default_out_root() -> Path:
    return Path.home() / "bmk-meta-out"


def default_work_root() -> Path:
    return Path.home() / "bmk-meta-work"


def inside(path, parent) -> bool:
    path, parent = Path(os.path.realpath(path)), Path(os.path.realpath(parent))
    return path == parent or parent in path.parents


def apart(store, *others, labels=None) -> None:
    """Raise StoreError unless every other root is neither inside the store nor holding it."""
    names = labels or ["the output root", "the work root", "the repository"]
    for other, name in zip(others, names):
        if other is not None and (inside(store, other) or inside(other, store)):
            raise StoreError(f"the store {store} and {name} {other} must not contain each other")


def resolve(path=None, *, out_root=None, work_root=None, env=None, create=True) -> Path:
    """The store directory, checked against the repository, the output root and the work root."""
    store = Path(path) if path else default_store(env)
    apart(store, out_root or default_out_root(), work_root or default_work_root(), REPO)
    if create:
        store.mkdir(parents=True, exist_ok=True)
    return store.resolve()


def anon_id(prefix: str = "m", taken=()) -> str:
    """A random id; prefix plus six hex digits, never derived from what it names."""
    while True:
        value = prefix + secrets.token_hex(3)
        if value not in taken:
            return value


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_safe(value):
    """The value with NaN and infinity replaced by None, so every file written is strict JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def write_json(path, doc) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(json_safe(doc), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(part, path)


class Store:
    """Paths inside the store (layout in BB/README.md)."""

    def __init__(self, root):
        self.root = Path(root)

    def material(self, meta_task) -> Path:
        return self.root / "material" / meta_task

    def pool(self, meta_task, pool_id) -> Path:
        return self.root / "pools" / meta_task / pool_id

    def pools(self, meta_task) -> list[str]:
        base = self.root / "pools" / meta_task
        return sorted(p.name for p in base.iterdir() if (p / "ORDER.json").is_file()) if base.is_dir() else []

    def runtime(self, pool_id) -> Path:
        return self.root / "runtime" / pool_id

    def private_members(self) -> Path:
        return self.root / "private_members"

    def slice(self, meta_task, slice_id) -> Path:
        return self.root / "slices" / meta_task / slice_id

    def slices(self, meta_task) -> list[str]:
        base = self.root / "slices" / meta_task
        return sorted(p.name for p in base.iterdir() if (p / "package").is_dir()) if base.is_dir() else []

    def run(self, run_id) -> Path:
        return self.root / "runs" / run_id

    def find_pool(self, meta_task, pool_id) -> tuple[str, Path]:
        """The pool directory for an id; the only pool of the meta-task when `pool_id` is None."""
        if pool_id is None:
            known = self.pools(meta_task)
            if len(known) != 1:
                raise StoreError(f"name a pool with --pool; {meta_task} has {known or 'none'}")
            pool_id = known[0]
        path = self.pool(meta_task, pool_id)
        if not (path / "ORDER.json").is_file():
            raise StoreError(f"no pool {pool_id} for {meta_task} in {self.root}")
        return pool_id, path
