"""Standard-declared workspace adapters and their closed mechanism registry."""

from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess
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
    # The prefix of the one verbatim artifact line a child of this adapter's
    # standard prints, and every command that binds a fixed identity grades.
    artifact_kind: str
    establishes_isolation: bool
    deterministic_gate: bool
    workspace_strategy: str
    # Whether a child of this adapter must commit in the tree it stands in
    # for its bytes to survive: true for git and document-tree, false for
    # evidence-store, whose identity is a lane packet no commit stands
    # behind. Distinct from `establishes_isolation and workspace_strategy
    # == "git"` (whether the landing merges a candidate branch): a
    # document-tree child commits straight onto the coordinator's own
    # branch, so it must commit but has no isolated candidate to merge.
    commits_in_place: bool


ADAPTER_REGISTRY = {
    "document-tree": Adapter(
        key="document-tree",
        artifact_kind="doc",
        establishes_isolation=False,
        deterministic_gate=False,
        workspace_strategy="document-tree",
        commits_in_place=False,
    ),
    "evidence-store": Adapter(
        key="evidence-store",
        artifact_kind="evidence",
        establishes_isolation=True,
        deterministic_gate=False,
        workspace_strategy="evidence-store",
        commits_in_place=False,
    ),
    "git": Adapter(
        key="git",
        artifact_kind="git",
        establishes_isolation=True,
        deterministic_gate=True,
        workspace_strategy="git",
        commits_in_place=True,
    ),
}

WORKSPACE_ADAPTER_FIELD = "workspace_adapter"


class AdapterError(ValueError):
    """A standard cannot select one closed registered adapter."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


# One code per ring refusal. Only `<dir>/.orchflows/standards` is an ancestor
# root: a second one gave admission and execution different first hits for
# one name, which is the divergence ``scripts/rings.py`` exists to close.
_RING_CODES = {
    "unresolved": "standard-unresolved",
    "reserved-name": "standard-reserved",
    "bundle-untrusted": "standard-untrusted",
    "trust-unavailable": "standard-untrusted",
    "name-invalid": "standard-unresolved",
}


def standard_path(standard, *, root=None) -> Path:
    """Resolve the stamped standard through the one ring resolver."""

    name = dequote(standard)
    if not name:
        raise AdapterError("standard-unresolved", "ticket names no standard")
    try:
        record = rings.resolve("standard", name, start=root)
    except rings.RingError as error:
        raise AdapterError(_RING_CODES.get(error.code, "standard-unresolved"), error.detail) from error
    return Path(str(record["path"]))


def manifest_path(standard, *, root=None) -> Path:
    """The stamped standard's manifest -- the document a verb reads whole.

    One file since the collapse: the manifest carries the domain prose that
    used to sit behind a `standard` cell pointing at a second file, so the
    path the launch prompt hands a child is the manifest the ring resolved.
    """

    path = standard_path(standard, root=root)
    if not path.is_file():  # pragma: no cover - the ring resolver already refused
        raise AdapterError(
            "standard-declaration-invalid", f"standard does not resolve: {path}",
        )
    return path


ADAPTER_FIELD_RE = re.compile(r"(?m)^adapter:\s*([^\r\n]+?)\s*$")


def adapter_in_frontmatter(text: str) -> str:
    """The adapter key one standard's frontmatter names, or `''` for none.

    The one reader of that field. `scripts/standards_support.py` resolves a
    standard whose bytes it has already read and calls this rather than
    carrying a second regex for one spelling; whether the key is
    *registered* stays `adapter_for_key`'s, one door further on.
    """

    parts = text.split("---", 2)
    match = ADAPTER_FIELD_RE.search(parts[1]) if len(parts) > 2 else None
    return dequote(match.group(1)) if match else ""


def declared_adapter(standard, *, root=None) -> str:
    """The stable adapter key one standard declares in its frontmatter.

    Frontmatter rather than a table cell since the collapse: the adapter is
    the typed leaf downstream machinery branches on, and the manifest is
    where contracts/standard.md puts it.
    """

    path = standard_path(standard, root=root)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise AdapterError(
            "adapter-declaration-invalid", f"unreadable standard {path}: {error}",
        ) from error
    normalized = adapter_in_frontmatter(text)
    if not normalized:
        raise AdapterError(
            "adapter-declaration-invalid",
            f"standard must declare exactly one adapter: {path}",
        )
    return normalized


def adapter_for_key(key: str) -> Adapter:
    """Return one implemented adapter or fail closed on its declared key."""

    normalized = str(key or "").strip()
    adapter = ADAPTER_REGISTRY.get(normalized)
    if adapter is None:
        raise AdapterError(
            "adapter-unregistered", f"standard declares unregistered adapter: {normalized or '<missing>'}",
        )
    return adapter


def infer_adapter(target) -> Adapter:
    """Select the workspace mechanism established by one concrete directory."""

    path = Path(target).expanduser()
    if not path.is_dir():
        raise AdapterError(
            "workspace-target-invalid", f"workspace target is not a directory: {path}",
        )
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False,
        )
    except OSError as error:
        raise AdapterError(
            "workspace-adapter-unavailable",
            f"cannot inspect workspace target {path} with git: {error}",
        ) from error
    if result.returncode == 0 and result.stdout.strip() == "true":
        return ADAPTER_REGISTRY["git"]
    metadata = next(
        (candidate / ".git" for candidate in (path, *path.parents)
         if (candidate / ".git").exists()),
        None,
    )
    if metadata is not None and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise AdapterError(
            "workspace-git-invalid",
            f"git metadata at {metadata} could not establish the workspace: {detail}",
        )
    return ADAPTER_REGISTRY["document-tree"]


def legacy_adapter_hints(standards, **overrides) -> tuple:
    """Distinct adapter keys still declared by resolved legacy standards."""

    if not standards:
        return ()
    if __package__:
        from .standards_support import StandardError, resolve_chain
    else:  # pragma: no cover - direct/installed flat script path
        from standards_support import StandardError, resolve_chain
    try:
        links = resolve_chain(standards, **overrides)
    except StandardError as error:
        raise AdapterError(error.code, error.detail) from error
    return tuple(dict.fromkeys(
        str(link.get("adapter") or "").strip()
        for link in links if str(link.get("adapter") or "").strip()
    ))


def select_adapter(*, explicit=None, standards=(), target=None,
                   target_supplied: bool = False, **overrides) -> Adapter:
    """Select one execution workspace independently of standard composition.

    An explicit binding wins.  A caller-supplied location is concrete enough
    to choose Git versus an existing directory.  Without one, one distinct
    legacy standard hint preserves old calls; otherwise the current concrete
    directory decides.  Evidence-store therefore remains an explicit or
    legacy-hinted choice because a directory alone cannot identify it.
    """

    named = dequote(explicit)
    if named:
        return adapter_for_key(named)
    if target_supplied:
        return infer_adapter(target)
    hints = legacy_adapter_hints(standards, **overrides)
    if len(hints) == 1:
        return adapter_for_key(hints[0])
    if len(hints) > 1:
        raise AdapterError(
            "workspace-adapter-ambiguous",
            "resolved standards carry competing legacy workspace adapters "
            f"({', '.join(hints)}); name --workspace-adapter with one "
            f"of {', '.join(sorted(ADAPTER_REGISTRY))}",
        )
    if target is not None:
        return infer_adapter(target)
    raise AdapterError(
        "workspace-adapter-ambiguous",
        "workspace mechanism is ambiguous; name --workspace-adapter with one "
        f"of {', '.join(sorted(ADAPTER_REGISTRY))}",
    )


def adapter_for_ticket(data: dict, *, target=None, **overrides) -> Adapter:
    """Read a new ticket binding or derive the compatibility answer for an old one."""

    explicit = data.get(WORKSPACE_ADAPTER_FIELD)
    if WORKSPACE_ADAPTER_FIELD in data and not dequote(explicit):
        raise AdapterError(
            "workspace-adapter-invalid",
            f"{WORKSPACE_ADAPTER_FIELD} is present but empty; name one of "
            f"{', '.join(sorted(ADAPTER_REGISTRY))}",
        )
    try:
        if __package__:
            from .tickets_pins import STANDARDS_FIELD, standards_of
        else:  # pragma: no cover - direct/installed flat script path
            from tickets_pins import STANDARDS_FIELD, standards_of
        standards = [name for name, _digest in standards_of(data.get(STANDARDS_FIELD))]
    except ImportError:  # pragma: no cover - partial install
        standards = []
    return select_adapter(
        explicit=explicit, standards=standards, target=target,
        target_supplied=False, **overrides,
    )


def adapter_spec(standard, *, root=None) -> Adapter:
    return adapter_for_key(declared_adapter(standard, root=root))


def derived_isolation(declared, standard, *, root=None) -> str:
    """The ticket's effective isolation: the rare declared override, else
    what the stamped standard's adapter establishes (contracts/work-item.md)."""
    value = dequote(declared)
    if value:
        return "required" if value == "required" else "none"
    if not dequote(standard):
        return "none"
    try:
        named = dequote(standard)
        adapter = (
            adapter_for_key(named) if named in ADAPTER_REGISTRY
            else adapter_spec(named, root=root)
        )
        return "required" if adapter.establishes_isolation else "none"
    except AdapterError:
        return "required"


def adapter_id(standard, *, root=None) -> str:
    return adapter_spec(standard, root=root).key


__all__ = (
    "ADAPTER_REGISTRY", "WORKSPACE_ADAPTER_FIELD", "Adapter", "AdapterError",
    "adapter_for_key", "adapter_for_ticket", "adapter_id",
    "adapter_in_frontmatter", "adapter_spec", "declared_adapter",
    "derived_isolation", "infer_adapter", "legacy_adapter_hints",
    "manifest_path", "select_adapter", "standard_path",
)
