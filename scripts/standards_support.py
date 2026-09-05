#!/usr/bin/env python3
"""Internal standard resolver implementation for the public ``standards.py`` facade."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from scripts import rings
    from scripts.tickets_adapters import (
        ADAPTER_REGISTRY, AdapterError, adapter_for_key, adapter_in_frontmatter,
    )
    from scripts.tickets_markdown import _parse_frontmatter, dequote
except ImportError:
    import rings
    from tickets_adapters import (
        ADAPTER_REGISTRY, AdapterError, adapter_for_key, adapter_in_frontmatter,
    )
    from tickets_markdown import _parse_frontmatter, dequote


# v3 reads the collapsed standard: one manifest and optional legacy `adapter`
# frontmatter.  The version describes the reader, but is deliberately absent
# from the standard identity: tickets and the public resolver pin the same
# directory tree, independently of which reader reported it.
RESOLVER_VERSION = "orchflows.standard-resolver.v3"
TREE_VERSION = b"orchflows.item-tree.v1\n"
DIGEST_PREFIX = "sha256:"
# Roots and narrowings are one ring kind under one `standards/` directory: a
# root is a standard with no `narrows:`, never a standard in a particular
# place.
STANDARD_KIND = "standard"
_STANDARD_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ADAPTER_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# The retired signature table's header row. A manifest still carrying it is
# half-migrated, and accepting it silently is how such an item survives.
_RETIRED_TABLE_RE = re.compile(r"(?mi)^\s*\|\s*cell\s*\|\s*binding\s*\|\s*$")
_FRONTMATTER_NAME_RE = re.compile(r"(?m)^name:\s*([^\r\n]+?)\s*$")
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class StandardError(ValueError):
    """A standard could not be resolved or does not satisfy the closed shape."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _canonicalize_bytes(value: bytes) -> bytes:
    """Return stable UTF-8 text bytes independent of checkout line endings."""

    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return value
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _read_bytes(path: Path, subject: str) -> bytes:
    """Read and canonicalize one file through the resolver's sole byte seam."""

    try:
        return _canonicalize_bytes(path.read_bytes())
    except (OSError, UnicodeError) as error:
        raise StandardError("standard-unreadable", f"unreadable {subject} {path}: {error}") from error


def _standard_name(value: object) -> str:
    name = dequote(value)
    if not name or not _STANDARD_NAME_RE.fullmatch(name) or name in (".", ".."):
        raise StandardError("standard-invalid", f"invalid standard name: {name or '<missing>'}")
    return name


def _roots(
    *,
    canonical_root: Optional[Path],
    project_root: Optional[Path],
    user_root: Optional[Path],
) -> List[Tuple[str, Path]]:
    """Return the ring roots for standards, nearest first."""

    return rings.item_roots(
        STANDARD_KIND,
        project=project_root,
        home=user_root,
        lib_dir=canonical_root,
    )


def _frontmatter_name(text: str, path: Path) -> Optional[str]:
    match = _FRONTMATTER_NAME_RE.search(text)
    return dequote(match.group(1)) if match else None


def _manifest_text(path: Path) -> str:
    """One standard's manifest as text -- the resolver's sole document."""

    raw = _read_bytes(path, "standard")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise StandardError("standard-unreadable", f"unreadable standard {path}: {error}") from error


def declared_adapter_of(text: str, path: Path) -> str:
    """The workspace mechanism this standard declares, or `''` for none.

    Frontmatter is the one place it is declared since the collapse, and
    `tickets_adapters.adapter_in_frontmatter` is the one reader of that
    field -- this passes the manifest bytes it already holds rather than
    resolving the name a second time. A standard carrying no `adapter:` is
    a fact the resolved-set check reads, not an error to swallow here.
    """

    declared = adapter_in_frontmatter(text).strip()
    if not declared:
        return ""
    if not _ADAPTER_RE.fullmatch(declared):
        raise StandardError(
            "standard-shape-invalid", f"adapter has invalid key {declared!r} in {path}",
        )
    # Whether the key is *registered* is `tickets_adapters`', at the one door
    # that turns a key into a mechanism. Counted here as declared either way,
    # so a set carrying one unregistered adapter is refused as unregistered
    # rather than as carrying none.
    return declared


def _refuse_retired_table(text: str, path: Path) -> None:
    """Refuse a manifest still carrying the retired signature table.

    The collapse moved `adapter` into frontmatter and deleted the table
    outright. Reading such a manifest and ignoring the rows would let a
    half-migrated standard resolve as if it were whole, which is exactly
    the state this refusal exists to make loud.
    """

    if _RETIRED_TABLE_RE.search(text):
        raise StandardError(
            "standard-shape-invalid",
            f"standard still carries the retired '| Cell | Binding |' table: "
            f"{path}. The adapter is frontmatter now (contracts/standard.md).",
        )


def tree_digest(directory: Path) -> str:
    """The canonical identity of one standard directory.

    This is the same framed path-and-bytes format used by ticket item pins.
    Keeping the implementation here lets the public resolver and ticket
    pinning share one primitive without an import cycle.
    """

    root = Path(directory)
    digest = hashlib.sha256()
    digest.update(TREE_VERSION)
    digest.update(b"standard\n")
    files = sorted(
        (path.relative_to(root).as_posix(), path)
        for path in root.rglob("*") if path.is_file()
    )
    for relative, path in files:
        data = _read_bytes(path, "standard file")
        digest.update(f"{relative}\n{len(data)}\n".encode("utf-8"))
        digest.update(data)
    return DIGEST_PREFIX + digest.hexdigest()


def _resolved(path: Path, scope: str, name: str) -> Dict[str, object]:
    """One standard's observations and its content-addressed identity."""

    text = _manifest_text(path)
    _refuse_retired_table(text, path)
    declared = _frontmatter_name(text, path)
    if not declared:
        raise StandardError("standard-shape-invalid", f"standard has no declared name: {path}")
    if declared != name:
        raise StandardError("standard-shape-invalid", f"standard name {declared!r} does not match path {name!r}")
    adapter = declared_adapter_of(text, path)
    if adapter:
        # Registration is `tickets_adapters`', at the one door that turns a
        # key into a mechanism; called here rather than re-tested.
        try:
            adapter_for_key(adapter)
        except AdapterError as error:
            raise StandardError("standard-shape-invalid", error.detail) from error
    return {
        "standard": name,
        "scope": scope,
        "path": str(path),
        "adapter": adapter,
        "digest": tree_digest(path.parent),
    }


# One code per ring refusal, so a caller reading `StandardError.code` learns the
# same distinction the resolver drew: unresolved, reserved-floor, untrusted.
_RING_CODES = {
    "unresolved": "standard-unresolved",
    "reserved-name": "standard-reserved",
    "bundle-untrusted": "standard-untrusted",
    "trust-unavailable": "standard-untrusted",
    "name-invalid": "standard-invalid",
    "kind-invalid": "standard-invalid",
}


def resolve_standard(
    standard: str,
    *,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
    start: Optional[Path] = None,
) -> Dict[str, object]:
    """Resolve one standard through the one ring resolver: project, home,
    imports, then lib. Scope and filesystem paths are observations; the
    digest is not derived from them, so identical bytes in two rings
    resolve to one identity. ``start`` is where to stand while looking."""

    name = _standard_name(standard)
    try:
        record = rings.resolve(
            "standard",
            name,
            project=project_root,
            home=user_root,
            lib_dir=canonical_root,
            start=start,
        )
    except rings.RingError as error:
        raise StandardError(_RING_CODES.get(error.code, "standard-unresolved"), error.detail) from error
    resolved = _resolved(Path(str(record["path"])), str(record["ring"]), name)
    resolved["notices"] = list(record.get("notices") or [])
    return resolved


def _available_names(roots: Sequence[Tuple[str, Path]]) -> Iterable[str]:
    names = set()
    for _, standards_root in roots:
        try:
            entries = list(standards_root.iterdir())
        except OSError:
            continue
        for entry in entries:
            manifest = entry / rings.MANIFESTS[STANDARD_KIND]
            if entry.is_dir() and manifest.is_file() and _STANDARD_NAME_RE.fullmatch(entry.name):
                names.add(entry.name)
    return sorted(names)


def cells_for(
    digest: str,
    *,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
) -> Dict[str, object]:
    """Find a resolved digest and return the standard it identifies.

    The name survives the collapse; the cells table it was named for does
    not, so what a digest projects to is the standard's observations and
    its one declared adapter. `scripts/standards.py` renames both under U3.
    """

    requested = str(digest or "").strip()
    if not _SHA_RE.fullmatch(requested):
        raise StandardError("digest-invalid", f"invalid standard digest: {requested or '<missing>'}")
    roots = _roots(
        canonical_root=canonical_root,
        project_root=project_root,
        user_root=user_root,
    )
    for name in _available_names(roots):
        try:
            resolved = resolve_standard(
                name,
                canonical_root=canonical_root,
                project_root=project_root,
                user_root=user_root,
            )
        except StandardError:
            continue
        if resolved["digest"] != requested:
            continue
        return {
            "standard": resolved["standard"],
            "scope": resolved["scope"],
            "digest": requested,
            "adapter": resolved["adapter"],
        }
    raise StandardError("digest-unresolved", f"standard digest does not resolve: {requested}")


# --- The `narrows:` cascade ------------------------------------------------
#
# A standard states what a good artifact carries in some domain, and may
# narrow exactly one other standard. Resolution walks that single parent to a
# standard carrying none, so `three-js` narrows `javascript` narrows `code`
# and the reader gets all three, broad to narrow.
#
# The most `narrows:` edges one chain may follow. The ninth refuses: past
# eight, a chain is no longer specificity, and the walk needs a bound that
# does not depend on the cycle check catching a malformed ring first.
STANDARD_DEPTH_LIMIT = 8


def _standard_record(name: str, requested: str, depth: int, **overrides):
    """One standard's ring record, or the most specific refusal for it.

    A refusal that is not "nothing carries this name" is reported as
    itself -- a reserved name or an untrusted bundle is a different answer
    from a name nothing anywhere carries, and only the latter is worth
    restating as "resolves in no reachable ring".
    """

    try:
        return dict(rings.resolve(STANDARD_KIND, name, **overrides)), STANDARD_KIND
    except rings.RingError as error:
        if error.code != "unresolved":
            raise StandardError(
                _RING_CODES.get(error.code, "standard-unresolved"), error.detail,
            ) from error
    if depth:
        raise StandardError(
            "standard-parent-unresolved",
            f"standard '{requested}' narrows '{name}', which resolves in no "
            f"reachable ring",
        )
    raise StandardError(
        "standard-unresolved",
        f"standard '{name}' cannot be pinned: it resolves in no reachable ring",
    )


def declared_narrows(text: str) -> str:
    """The one parent a standard's frontmatter names, or `''` for a root."""

    return dequote(_parse_frontmatter(text).get("narrows"))


def _chain(name: str, **overrides) -> List[Dict[str, object]]:
    """One stamped name's ancestry, broad to narrow, or a `StandardError`."""

    requested = _standard_name(name)
    walked: List[str] = []
    links: List[Dict[str, object]] = []
    current, depth = requested, 0
    while True:
        if current in walked:
            raise StandardError(
                "standard-cycle",
                f"standard '{requested}' narrows a cycle: "
                + " -> ".join(walked + [current]),
            )
        walked.append(current)
        record, kind = _standard_record(current, requested, depth, **overrides)
        path = Path(str(record["path"]))
        text = _manifest_text(path)
        _refuse_retired_table(text, path)
        links.append({
            "name": current,
            "kind": kind,
            "ring": str(record["ring"]),
            "path": str(path),
            "dir": str(record["dir"]),
            "adapter": declared_adapter_of(text, path),
        })
        parent = declared_narrows(text)
        if not parent:
            return list(reversed(links))
        depth += 1
        if depth > STANDARD_DEPTH_LIMIT:
            raise StandardError(
                "standard-depth",
                f"standard '{requested}' has not terminated in "
                f"{STANDARD_DEPTH_LIMIT} hops: " + " -> ".join(walked + [parent]),
            )
        current = _standard_name(parent)


def resolve_chain(names: Sequence[str], **overrides) -> List[Dict[str, object]]:
    """Every stamped name's chain, concatenated broad to narrow.

    Chains join in the order written and a standard reached twice is read
    once, at its first position, so a shared ancestor is not read -- or
    charged for -- twice. Legacy adapter declarations remain observations on
    each link; workspace selection consumes them only as a compatibility hint
    after the standards have composed.
    """

    resolved_links: List[Dict[str, object]] = []
    seen = set()
    for name in names:
        for link in _chain(name, **overrides):
            if link["name"] in seen:
                continue
            seen.add(link["name"])
            resolved_links.append(link)
    if not resolved_links:
        raise StandardError("standard-unstamped", "no standard is stamped")
    return resolved_links


def adapter_standard(names: Sequence[str], **overrides) -> str:
    """The standard declaring one distinct legacy adapter hint, or ``''``."""

    declaring = [link for link in resolve_chain(names, **overrides) if link["adapter"]]
    keys = {str(link["adapter"]) for link in declaring}
    if len(keys) != 1:
        return ""
    return str(declaring[0]["name"])
