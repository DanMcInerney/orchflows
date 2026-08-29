"""Pack-declared workspace adapters and their closed mechanism registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts import state_root
except ImportError:
    import state_root


@dataclass(frozen=True)
class Adapter:
    """Properties machinery may branch on for one implemented mechanism."""

    key: str
    identity_form: str
    establishes_isolation: bool
    deterministic_gate: bool
    conflict_semantics: str
    workspace_strategy: str


ADAPTER_REGISTRY = {
    "document-tree": Adapter(
        key="document-tree",
        identity_form="document-revision",
        establishes_isolation=False,
        deterministic_gate=False,
        conflict_semantics="section-overlap",
        workspace_strategy="document-tree",
    ),
    "evidence-store": Adapter(
        key="evidence-store",
        identity_form="evidence-packet",
        establishes_isolation=True,
        deterministic_gate=False,
        conflict_semantics="append-only-lanes",
        workspace_strategy="evidence-store",
    ),
    "git": Adapter(
        key="git",
        identity_form="git-commit",
        establishes_isolation=True,
        deterministic_gate=True,
        conflict_semantics="git-overlap",
        workspace_strategy="git",
    ),
    "git-plus-render": Adapter(
        key="git-plus-render",
        identity_form="view-identity",
        establishes_isolation=True,
        deterministic_gate=True,
        conflict_semantics="view-overlap",
        workspace_strategy="git",
    ),
}

_ADAPTER_DECLARATION = re.compile(r"ticket adapter:\s*`([^`]+)`")


class AdapterError(ValueError):
    """A pack cannot select one closed registered adapter."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _candidate_roots(root=None):
    start = Path(root or Path.cwd()).resolve()
    for directory in (start, *start.parents):
        yield directory / "packs"
        yield directory / ".orchflows" / "packs"
    try:
        yield state_root.state_root().parent / "lib" / "packs"
    except OSError:
        pass
    source = Path(__file__).resolve().parent.parent / "packs"
    yield source


def pack_path(pack, *, root=None) -> Path:
    """Resolve the stamped pack in project, installed, then source scope."""

    name = str(pack or "").strip().strip("`").strip()
    if not name:
        raise AdapterError("pack-unresolved", "ticket names no pack")
    seen = set()
    for packs_root in _candidate_roots(root):
        candidate = (packs_root / name / "SKILL.md").resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    raise AdapterError("pack-unresolved", f"pack does not resolve: {name}")


def declared_adapter(pack, *, root=None) -> str:
    """Read the stable adapter key from the pack's workspace cell."""

    path = pack_path(pack, root=root)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise AdapterError("pack-unreadable", f"unreadable pack {path}: {error}") from error
    matches = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == "workspace":
            matches.extend(_ADAPTER_DECLARATION.findall(cells[1]))
    if len(matches) != 1 or not matches[0].strip():
        raise AdapterError(
            "adapter-declaration-invalid",
            f"pack workspace cell must declare exactly one ticket adapter: {path}",
        )
    return matches[0].strip()


def adapter_for_key(key: str) -> Adapter:
    """Return one implemented adapter or fail closed on its declared key."""

    normalized = str(key or "").strip()
    adapter = ADAPTER_REGISTRY.get(normalized)
    if adapter is None:
        raise AdapterError(
            "adapter-unregistered", f"pack declares unregistered adapter: {normalized or '<missing>'}",
        )
    return adapter


def adapter_spec(pack, *, root=None) -> Adapter:
    return adapter_for_key(declared_adapter(pack, root=root))


def adapter_id(pack, *, root=None) -> str:
    return adapter_spec(pack, root=root).key


__all__ = (
    "ADAPTER_REGISTRY", "Adapter", "AdapterError", "adapter_for_key",
    "adapter_id", "adapter_spec", "declared_adapter", "pack_path",
)
