"""Pack-declared workspace adapters and their closed mechanism registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    from scripts import rings
    from scripts.tickets_markdown import dequote
except ImportError:
    import rings
    from tickets_markdown import dequote


@dataclass(frozen=True)
class Adapter:
    """Properties machinery may branch on for one implemented mechanism."""

    key: str
    identity_form: str
    # The prefix of the one verbatim artifact line a child of this adapter's
    # pack prints, and the prefix every command that binds a fixed identity
    # grades: `git:<full-commit-id>`, `doc:<path>@sha256:<digest>`,
    # `evidence:<store-id>`. `identity_form` names the *thing*; this names
    # how the line spells it, and the two are not the same string because a
    # prefix is typed for a reader and a form is named for a human.
    artifact_kind: str
    establishes_isolation: bool
    deterministic_gate: bool
    conflict_semantics: str
    workspace_strategy: str


ADAPTER_REGISTRY = {
    "document-tree": Adapter(
        key="document-tree",
        identity_form="document-revision",
        artifact_kind="doc",
        establishes_isolation=False,
        deterministic_gate=False,
        conflict_semantics="section-overlap",
        workspace_strategy="document-tree",
    ),
    "evidence-store": Adapter(
        key="evidence-store",
        identity_form="evidence-packet",
        artifact_kind="evidence",
        establishes_isolation=True,
        deterministic_gate=False,
        conflict_semantics="append-only-lanes",
        workspace_strategy="evidence-store",
    ),
    "git": Adapter(
        key="git",
        identity_form="git-commit",
        artifact_kind="git",
        establishes_isolation=True,
        deterministic_gate=True,
        conflict_semantics="git-overlap",
        workspace_strategy="git",
    ),
    "git-plus-render": Adapter(
        key="git-plus-render",
        identity_form="view-identity",
        artifact_kind="git",
        establishes_isolation=True,
        deterministic_gate=True,
        conflict_semantics="view-overlap",
        workspace_strategy="git",
    ),
}


class AdapterError(ValueError):
    """A pack cannot select one closed registered adapter."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


# One code per ring refusal. The bare ``<dir>/packs`` ancestor root this
# module used to check before ``<dir>/.orchflows/packs`` is gone: it gave
# admission and execution two different first hits for one name, which is
# the divergence ``scripts/rings.py`` exists to close.
_RING_CODES = {
    "unresolved": "pack-unresolved",
    "reserved-name": "pack-reserved",
    "bundle-untrusted": "pack-untrusted",
    "trust-unavailable": "pack-untrusted",
    "name-invalid": "pack-unresolved",
}


def pack_path(pack, *, root=None) -> Path:
    """Resolve the stamped pack through the one ring resolver.

    ``root`` is where to stand while looking, never a root to search: the
    order is project ring, home ring, pinned imports, then lib, and
    ``scripts/rings.py`` owns it for every caller.
    """

    name = dequote(pack)
    if not name:
        raise AdapterError("pack-unresolved", "ticket names no pack")
    try:
        record = rings.resolve("pack", name, start=root)
    except rings.RingError as error:
        raise AdapterError(_RING_CODES.get(error.code, "pack-unresolved"), error.detail) from error
    return Path(str(record["path"]))


def craft_path(pack, *, root=None) -> Path:
    """The stamped pack's own craft file, where the pack's signature names it.

    Read through the same declared-cell seam as the adapter key, and resolved
    against the pack directory, so a pack that moves or renames its craft is
    still the one place that says where the craft is. A launch prompt hands
    this path to the child instead of telling it to resolve the pack, which is
    the one instruction a fork arriving without a prompt could not obey.
    """

    path = pack_path(pack, root=root)
    try:
        if __package__:
            from . import packs_support
        else:  # pragma: no cover - direct/installed script path
            import packs_support
        value = packs_support._declared_cell(path, "craft")
        targets = packs_support._reference_paths(value)
    except ImportError as error:  # pragma: no cover - broken installation
        raise AdapterError("pack-resolver-unavailable", str(error)) from error
    except packs_support.PackError as error:
        raise AdapterError("craft-declaration-invalid", error.detail) from error
    if not targets:
        raise AdapterError(
            "craft-declaration-invalid",
            f"pack declares no craft reference: {path}",
        )
    resolved = (path.parent / targets[0]).resolve()
    if not resolved.is_file():
        raise AdapterError(
            "craft-declaration-invalid", f"pack craft does not resolve: {resolved}",
        )
    return resolved


def pack_digest(pack, *, root=None) -> str:
    """The resolved pack's content digest, through the one pack resolver.

    A ticket pins this at issue time and every later command compares against
    it, which is what makes "the stamped pack digest" a verification rather
    than a lookup: `cells_for` re-derives digests to *find* a pack, and a
    search can never notice that the pack changed under a sealed
    assignment.
    """

    name = dequote(pack)
    if not name:
        raise AdapterError("pack-unresolved", "ticket names no pack")
    try:
        if __package__:
            from . import packs_support
        else:  # pragma: no cover - direct/installed script path
            import packs_support
        resolved = packs_support.resolve_pack(name, start=root)
    except ImportError as error:  # pragma: no cover - broken installation
        raise AdapterError("pack-resolver-unavailable", str(error)) from error
    except packs_support.PackError as error:
        raise AdapterError(error.code, error.detail) from error
    return str(resolved["digest"])


def declared_adapter(pack, *, root=None) -> str:
    """Read the stable adapter key from the pack's typed `adapter` leaf.

    The key is a closed field because machinery branches on it, which is
    the whole reason `contracts/pack-signature.md` types it. It was read
    out of the `workspace` cell's prose by regex until that left two
    declarations of one fact with the prose winning -- a pack could type
    one adapter and describe another, and the description decided.
    """

    path = pack_path(pack, root=root)
    try:
        if __package__:
            from . import packs_support
        else:  # pragma: no cover - direct/installed script path
            import packs_support
        value = packs_support._declared_cell(path, "adapter")
    except ImportError as error:  # pragma: no cover - broken installation
        raise AdapterError("pack-resolver-unavailable", str(error)) from error
    except packs_support.PackError as error:
        raise AdapterError("adapter-declaration-invalid", error.detail) from error
    normalized = dequote(value)
    if not normalized:
        raise AdapterError(
            "adapter-declaration-invalid",
            f"pack must declare exactly one typed adapter leaf: {path}",
        )
    return normalized


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


def derived_isolation(declared, pack, *, root=None) -> str:
    """The ticket's effective isolation: the rare declared override, else
    what the stamped pack's adapter establishes (contracts/work-item.md).

    Fail-closed: a pack that cannot resolve derives 'required', because
    assuming isolation never lets two candidates share a tree by accident.
    """
    value = dequote(declared)
    if value:
        return "required" if value == "required" else "none"
    if not dequote(pack):
        return "none"
    try:
        return "required" if adapter_spec(pack, root=root).establishes_isolation else "none"
    except AdapterError:
        return "required"


def adapter_id(pack, *, root=None) -> str:
    return adapter_spec(pack, root=root).key


__all__ = (
    "ADAPTER_REGISTRY", "Adapter", "AdapterError", "adapter_for_key",
    "adapter_id", "adapter_spec", "craft_path", "declared_adapter",
    "derived_isolation", "pack_digest", "pack_path",
)
