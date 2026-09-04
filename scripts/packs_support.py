#!/usr/bin/env python3
"""Internal pack resolver implementation for the public ``packs.py`` facade."""

from __future__ import annotations

import hashlib
import json
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


# v3 reads the collapsed standard: one manifest, `adapter` in frontmatter,
# identity over the directory tree. v2 read a two-row cells table and the
# second file its `craft` cell named, and neither exists. The version rides
# in the identity so a resolver that reads differently cannot agree with
# itself across the change.
RESOLVER_VERSION = "orchflows.pack-resolver.v3"
_PACK_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ADAPTER_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# The retired signature table's header row. A manifest still carrying it is
# half-migrated, and accepting it silently is how such an item survives.
_RETIRED_TABLE_RE = re.compile(r"(?mi)^\s*\|\s*cell\s*\|\s*binding\s*\|\s*$")
_FRONTMATTER_NAME_RE = re.compile(r"(?m)^name:\s*([^\r\n]+?)\s*$")
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class PackError(ValueError):
    """A pack could not be resolved or does not satisfy the closed shape."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
        raise PackError("pack-unreadable", f"unreadable {subject} {path}: {error}") from error


def _pack_name(value: object) -> str:
    name = dequote(value)
    if not name or not _PACK_NAME_RE.fullmatch(name) or name in (".", ".."):
        raise PackError("pack-invalid", f"invalid pack name: {name or '<missing>'}")
    return name


def _roots(
    *,
    canonical_root: Optional[Path],
    project_root: Optional[Path],
    user_root: Optional[Path],
) -> List[Tuple[str, Path]]:
    """Return the ring roots for packs, nearest first."""

    return rings.item_roots(
        "pack",
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
        raise PackError("pack-unreadable", f"unreadable standard {path}: {error}") from error


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
        raise PackError(
            "pack-shape-invalid", f"adapter has invalid key {declared!r} in {path}",
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
        raise PackError(
            "pack-shape-invalid",
            f"standard still carries the retired '| Cell | Binding |' table: "
            f"{path}. The adapter is frontmatter now (contracts/standard.md).",
        )


def _tree(directory: Path) -> List[Dict[str, object]]:
    """Every file under one standard's directory, sorted, path and bytes.

    The path is relative to the standard's directory rather than to the
    repository, so identical bytes in two rings are one identity -- the
    scope a standard resolved from is an observation, never part of it.
    Bytes enter as their own SHA-256; adding a file, deleting one, renaming
    one and changing a byte each move the list, and so the digest over it.
    """

    entries: List[Dict[str, object]] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        entries.append({
            "path": path.relative_to(directory).as_posix(),
            "sha256": _sha256(_read_bytes(path, "standard file")),
        })
    return sorted(entries, key=lambda entry: str(entry["path"]))


def _signature_digest() -> Optional[str]:
    """Hash the library's own well-formedness contract for a standard.

    `contracts/standard.md` is that document since the collapse retired
    `contracts/pack-signature.md`. It is read from the library root and
    never from the standard's own ring: a ring supplying the document its
    items are judged against would be grading itself.
    """

    candidate = rings.lib_root() / "contracts" / "standard.md"
    if candidate.is_file():
        return _sha256(_read_bytes(candidate, "standard contract"))
    return None


def _resolved(path: Path, scope: str, name: str) -> Dict[str, object]:
    """One standard's observations and its content-addressed identity."""

    text = _manifest_text(path)
    _refuse_retired_table(text, path)
    declared = _frontmatter_name(text, path)
    if not declared:
        raise PackError("pack-shape-invalid", f"pack has no declared name: {path}")
    if declared != name:
        raise PackError("pack-shape-invalid", f"pack name {declared!r} does not match path {name!r}")
    adapter = declared_adapter_of(text, path)
    if adapter:
        # Registration is `tickets_adapters`', at the one door that turns a
        # key into a mechanism; called here rather than re-tested.
        try:
            adapter_for_key(adapter)
        except AdapterError as error:
            raise PackError("pack-shape-invalid", error.detail) from error
    identity = {
        "resolver": RESOLVER_VERSION,
        "pack": name,
        "adapter": adapter,
        "tree": _tree(path.parent),
        "signature_sha256": _signature_digest(),
    }
    digest = "sha256:" + _sha256(_canonical_json(identity))
    return {
        "pack": name,
        "scope": scope,
        "path": str(path),
        "adapter": adapter,
        "digest": digest,
    }


# One code per ring refusal, so a caller reading `PackError.code` learns the
# same distinction the resolver drew: unresolved, reserved-floor, untrusted.
_RING_CODES = {
    "unresolved": "pack-unresolved",
    "reserved-name": "pack-reserved",
    "bundle-untrusted": "pack-untrusted",
    "trust-unavailable": "pack-untrusted",
    "name-invalid": "pack-invalid",
    "kind-invalid": "pack-invalid",
}


def resolve_pack(
    pack: str,
    *,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
    start: Optional[Path] = None,
) -> Dict[str, object]:
    """Resolve one pack through the one ring resolver: project, home,
    imports, then lib. Scope and filesystem paths are observations; the
    digest is not derived from them, so identical bytes in two rings
    resolve to one identity. ``start`` is where to stand while looking."""

    name = _pack_name(pack)
    try:
        record = rings.resolve(
            "pack",
            name,
            project=project_root,
            home=user_root,
            lib_dir=canonical_root,
            start=start,
        )
    except rings.RingError as error:
        raise PackError(_RING_CODES.get(error.code, "pack-unresolved"), error.detail) from error
    resolved = _resolved(Path(str(record["path"])), str(record["ring"]), name)
    resolved["notices"] = list(record.get("notices") or [])
    return resolved


def _available_names(roots: Sequence[Tuple[str, Path]]) -> Iterable[str]:
    names = set()
    for _, packs_root in roots:
        try:
            entries = list(packs_root.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir() and (entry / "SKILL.md").is_file() and _PACK_NAME_RE.fullmatch(entry.name):
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
        raise PackError("digest-invalid", f"invalid pack digest: {requested or '<missing>'}")
    roots = _roots(
        canonical_root=canonical_root,
        project_root=project_root,
        user_root=user_root,
    )
    for name in _available_names(roots):
        try:
            resolved = resolve_pack(
                name,
                canonical_root=canonical_root,
                project_root=project_root,
                user_root=user_root,
            )
        except PackError:
            continue
        if resolved["digest"] != requested:
            continue
        return {
            "pack": resolved["pack"],
            "scope": resolved["scope"],
            "digest": requested,
            "adapter": resolved["adapter"],
        }
    raise PackError("digest-unresolved", f"pack digest does not resolve: {requested}")


# --- The `narrows:` cascade ------------------------------------------------
#
# A standard states what a good artifact carries in some domain, and may
# narrow exactly one other standard. Resolution walks that single parent to a
# standard carrying none, so `three-js` narrows `javascript` narrows `code`
# and the reader gets all three, broad to narrow.
#
# Two ring kinds are searched because a standard still lives in one of two
# directories: `packs/` holds the roots and `sheets/` the narrowings. Nothing
# here depends on which -- a root is a standard with no `narrows:`, not a
# standard in a particular directory -- so the collapse into one `standards/`
# ring changes this tuple and nothing else.
STANDARD_KINDS = ("pack", "sheet")
# The most `narrows:` edges one chain may follow. The ninth refuses: past
# eight, a chain is no longer specificity, and the walk needs a bound that
# does not depend on the cycle check catching a malformed ring first.
STANDARD_DEPTH_LIMIT = 8


def _standard_record(name: str, requested: str, depth: int, **overrides):
    """One standard's ring record and the old kind that still carries it.

    A name is looked for as every kind a standard can still live in, so the
    refusal reports the most specific failure rather than the last one: a
    reserved name or an untrusted bundle is a different answer from a name
    nothing anywhere carries, and only the latter is worth restating as
    "resolves in no reachable ring".
    """

    failures = []
    for kind in STANDARD_KINDS:
        try:
            return dict(rings.resolve(kind, name, **overrides)), kind
        except rings.RingError as error:
            failures.append(error)
    specific = next((error for error in failures if error.code != "unresolved"), None)
    if specific is not None:
        raise PackError(_RING_CODES.get(specific.code, "pack-unresolved"), specific.detail)
    if depth:
        raise PackError(
            "standard-parent-unresolved",
            f"standard '{requested}' narrows '{name}', which resolves in no "
            f"reachable ring",
        )
    raise PackError(
        "pack-unresolved",
        f"standard '{name}' cannot be pinned: it resolves in no reachable ring",
    )


def declared_narrows(text: str) -> str:
    """The one parent a standard's frontmatter names, or `''` for a root."""

    return dequote(_parse_frontmatter(text).get("narrows"))


def _chain(name: str, **overrides) -> List[Dict[str, object]]:
    """One stamped name's ancestry, broad to narrow, or a `PackError`."""

    requested = _pack_name(name)
    walked: List[str] = []
    links: List[Dict[str, object]] = []
    current, depth = requested, 0
    while True:
        if current in walked:
            raise PackError(
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
            raise PackError(
                "standard-depth",
                f"standard '{requested}' has not terminated in "
                f"{STANDARD_DEPTH_LIMIT} hops: " + " -> ".join(walked + [parent]),
            )
        current = _pack_name(parent)


def resolve_chain(names: Sequence[str], **overrides) -> List[Dict[str, object]]:
    """Every stamped name's chain, concatenated broad to narrow.

    Chains join in the order written and a standard reached twice is read
    once, at its first position, so a shared ancestor is not read -- or
    charged for -- twice. The joined set carries exactly one adapter: with
    none the ticket has no workspace mechanism, and with two it has a
    contradiction no later door can resolve.
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
        raise PackError("standard-unstamped", "no standard is stamped")
    declaring = [link for link in resolved_links if link["adapter"]]
    if not declaring:
        raise PackError(
            "standard-adapter-missing",
            "the resolved standards "
            + ", ".join(f"'{link['name']}'" for link in resolved_links)
            + " declare no adapter, so the ticket has no workspace mechanism",
        )
    if len(declaring) > 1:
        raise PackError(
            "standard-adapter-conflict",
            "the resolved standards declare "
            + " and ".join(
                f"'{link['name']}' -> {link['adapter']}" for link in declaring
            )
            + ": one ticket carries one adapter, so these do not compose",
        )
    return resolved_links


def adapter_standard(names: Sequence[str], **overrides) -> str:
    """The name of the one resolved standard that declares the adapter."""

    return next(
        str(link["name"]) for link in resolve_chain(names, **overrides) if link["adapter"]
    )
