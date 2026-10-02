"""`material fetch`: download a meta-task's real material into the store (network, no model calls).

The domain module owns the source, its licence record and the public/held-out split; this only dispatches to it.
The store then holds `material/<mt>/{source/, public/, held-out/, split.json}`; builder workspaces receive only
`public/`.
"""
from __future__ import annotations

from pathlib import Path

from . import registry


def fetch(meta_task: str, store_root: Path) -> dict:
    task = registry.get(meta_task)
    domain = registry.load_domain(task)
    hook = getattr(domain, "fetch_material", None)
    if hook is None:
        raise ValueError(f"{meta_task}: the {task.domain} domain has no material to fetch")
    return hook(Path(store_root))
