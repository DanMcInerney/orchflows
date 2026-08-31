#!/usr/bin/env python3
"""The one resolver for custom skills, packs, and workflows across the rings.

Search order -- one fixed root-relative path per ring and per kind, never a
configurable search path:

    project   <repo>/.orchflows/{skills,packs,workflows}/<name>
    home      ~/.orchflows/{skills,packs,workflows}/<name>
    imports   ~/.orchflows/imports/<bundle>/.orchflows/{skills,packs,workflows}/<name>,
              bundle by bundle in the order ~/.orchflows/imports.lock records
    lib       the installed library: skills/<sublayer>/<name>, packs/<name>,
              example-workflows/<name>

Nearest ring wins.  A non-reserved name found in more than one ring resolves
to the nearest hit and carries a one-line shadow notice naming both paths --
never a silent first-hit.  `orch-` is a mechanically reserved floor: a
project, home, or imports item bearing that prefix is refused loudly here
rather than shadowing a library name or, worse, never running.

A skill lives at `<name>/SKILL.md`, a pack at `<name>/SKILL.md`, and a
workflow — a skill whose prose calls bricks — at `<name>/SKILL.md` too.
Home roots are honoured when they exist and never required to;
`orchflows sync` creates them.

This module is the sole owner of that order.  `scripts/packs_support.py` and
`scripts/tickets_adapters.py` both route through it, which is what keeps
admission and execution from reading two different files as "the pack".
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from scripts import state_root
except ImportError:  # pragma: no cover - direct/installed flat script path
    import state_root


KINDS = ("skill", "pack", "workflow")
RINGS = ("project", "home", "imports", "lib")
RING_DIRS = {"skill": "skills", "pack": "packs", "workflow": "workflows"}
LIB_DIRS = {"skill": "skills", "pack": "packs", "workflow": "example-workflows"}
MANIFESTS = {"skill": "SKILL.md", "pack": "SKILL.md", "workflow": "SKILL.md"}
RESERVED_PREFIX = "orch-"
BUNDLE_DIR = ".orchflows"
IMPORTS_DIR = "imports"
IMPORTS_LOCK = "imports.lock"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RingError(ValueError):
    """A ring item does not resolve, or resolves to a refused name."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def kind_of(value: str) -> str:
    kind = str(value or "").strip()
    if kind not in KINDS:
        raise RingError("kind-invalid", f"unknown ring kind: {kind or '<missing>'}")
    return kind


def item_name(value: str) -> str:
    name = str(value or "").strip()
    if not name or not NAME_RE.fullmatch(name) or name in (".", ".."):
        raise RingError("name-invalid", f"invalid item name: {name or '<missing>'}")
    return name


def reserved_refusal(kind: str, name: str, ring: str, path: Path) -> str:
    """The one reserved-floor sentence, so every door says it the same way."""

    return (
        f"{kind} '{name}' in the {ring} ring at {path} takes the reserved "
        f"'{RESERVED_PREFIX}' prefix. That prefix is the library's mechanical "
        "floor: no ring item may carry it, because a name that shadows a "
        "library verb -- or silently never runs -- is how a ring becomes an "
        f"injection surface. Rename the item to something outside "
        f"'{RESERVED_PREFIX}*'."
    )


# --- roots -------------------------------------------------------------


def home_ring() -> Path:
    """``~/.orchflows`` -- through the one resolver that also moves for a test."""

    return state_root.orchflows_home()


def lib_root() -> Path:
    """The library this checkout or install reads: a source tree, else ``lib/``."""

    checkout = Path(__file__).resolve().parent.parent
    if (checkout / "packs").is_dir() and (checkout / "contracts").is_dir():
        return checkout
    return checkout / "lib"


def project_ring(start=None, home: Optional[Path] = None) -> Optional[Path]:
    """The nearest ancestor's ``.orchflows`` bundle, or ``None``.

    The home ring is never a project ring, however far a caller has cd'd
    into their own home directory: the two have different trust rules and
    reading one as the other would grant the project ring the home's.  Both
    spellings are excluded -- the configured home ring, and the default
    ``~/.orchflows`` -- because a test that moves the first still walks up
    through the second.
    """

    try:
        current = Path(start or Path.cwd()).resolve()
    except OSError:  # pragma: no cover - an unreadable cwd
        return None
    excluded = {_folded(home if home is not None else home_ring())}
    try:
        excluded.add(_folded(Path.home() / BUNDLE_DIR))
    except (OSError, RuntimeError):  # pragma: no cover - a home-less platform
        pass
    for directory in (current, *current.parents):
        candidate = directory / BUNDLE_DIR
        if candidate.is_dir() and _folded(candidate) not in excluded:
            return candidate
    return None


def _folded(path) -> str:
    return os.path.normcase(str(Path(path)))


def _bundle_root(value, kind: str) -> Path:
    """Normalize one override to the item directory it names.

    A caller may hand the bundle (``<repo>/.orchflows``), the repository or
    home above it, or the item directory itself; all three name one place.
    """

    resolved = Path(value).expanduser().resolve()
    if resolved.name == RING_DIRS[kind]:
        return resolved
    if resolved.name == BUNDLE_DIR:
        return resolved / RING_DIRS[kind]
    if (resolved / BUNDLE_DIR).is_dir():
        return resolved / BUNDLE_DIR / RING_DIRS[kind]
    return resolved / RING_DIRS[kind]


def _home_root(value, kind: str) -> Path:
    """Normalize a home override, which may name the ring directory itself."""

    resolved = Path(value).expanduser().resolve()
    return resolved.parent if resolved.name == RING_DIRS[kind] else resolved


def _lib_roots(kind: str, root: Path) -> List[Path]:
    base = root if root.name == LIB_DIRS[kind] else root / LIB_DIRS[kind]
    if kind != "skill":
        return [base]
    try:
        sublayers = sorted(path for path in base.iterdir() if path.is_dir())
    except OSError:
        return [base]
    return sublayers or [base]


def imports_lock_path(home: Optional[Path] = None) -> Path:
    return (home if home is not None else home_ring()) / IMPORTS_LOCK


def read_imports(home: Optional[Path] = None) -> List[Dict[str, str]]:
    """The pinned bundles ``imports.lock`` records, in file order.

    An unreadable or malformed lock resolves to no imports rather than to a
    guess: the lock is the pin (P12), and a half-read pin is not one.
    """

    path = imports_lock_path(home)
    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    entries = document.get("imports") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        return []
    records = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name or not NAME_RE.fullmatch(name):
            continue
        records.append({
            "name": name,
            "url": str(entry.get("url") or ""),
            "pin": str(entry.get("pin") or ""),
        })
    return records


def item_roots(
    kind: str,
    *,
    project=None,
    home=None,
    lib=None,
    lib_dir=None,
    start=None,
) -> List[Tuple[str, Path]]:
    """Every ``(ring, directory)`` this kind resolves through, nearest first.

    ``lib`` names the library root; ``lib_dir`` names one item directory
    inside it verbatim, which is what a caller holding a bare packs
    directory (``packs.py --canonical-root``) has to hand.
    """

    kind = kind_of(kind)
    home_root = _home_root(home, kind) if home is not None else home_ring()
    roots: List[Tuple[str, Path]] = []
    project_root = (
        _bundle_root(project, kind)
        if project is not None
        else _project_default(kind, home_root, start)
    )
    if project_root is not None:
        roots.append(("project", project_root))
    roots.append(("home", home_root / RING_DIRS[kind]))
    for record in read_imports(home_root):
        roots.append((
            "imports",
            home_root / IMPORTS_DIR / record["name"] / BUNDLE_DIR / RING_DIRS[kind],
        ))
    if lib_dir is not None:
        roots.append(("lib", Path(lib_dir).expanduser().resolve()))
    else:
        library = Path(lib).expanduser().resolve() if lib is not None else lib_root()
        for candidate in _lib_roots(kind, library):
            roots.append(("lib", candidate))
    seen = set()
    ordered = []
    for ring, root in roots:
        marker = _folded(root)
        if marker in seen:
            continue
        seen.add(marker)
        ordered.append((ring, root))
    return ordered


def _project_default(kind: str, home_root: Path, start) -> Optional[Path]:
    bundle = project_ring(start, home_root)
    return None if bundle is None else bundle / RING_DIRS[kind]


# --- resolution --------------------------------------------------------


def _manifest(kind: str, root: Path, name: str) -> Optional[Path]:
    """The item's manifest under ``root``, or ``None`` when it is not there.

    The join is safe because the name is validated, and it is re-checked
    after resolution so no filesystem alias can carry a lookup out of the
    ring it was asked about.
    """

    candidate = root / name / MANIFESTS[kind]
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def locate(kind: str, name: str, **overrides) -> List[Dict[str, object]]:
    """Every ring hit for one name, nearest first. No reservation, no trust."""

    kind = kind_of(kind)
    name = item_name(name)
    hits = []
    for ring, root in item_roots(kind, **overrides):
        manifest = _manifest(kind, root, name)
        if manifest is None:
            continue
        hits.append({
            "kind": kind,
            "name": name,
            "ring": ring,
            "root": str(root),
            "dir": str(manifest.parent),
            "path": str(manifest),
        })
    return hits


def shadow_notice(record: Dict[str, object]) -> Optional[str]:
    """One line naming the winner and what it shadows, or ``None``."""

    shadowed = list(record.get("shadows") or [])
    if not shadowed:
        return None
    others = "; ".join(f"{item['ring']} {item['path']}" for item in shadowed)
    return (
        f"shadow: {record['kind']} '{record['name']}' resolves from the "
        f"{record['ring']} ring at {record['path']} and shadows {others}"
    )


def resolve(kind: str, name: str, *, trust: bool = True, **overrides) -> Dict[str, object]:
    """Resolve one item to its nearest ring, refusing a reserved ring name.

    ``trust`` gates a project-ring win on the user's own ledger; pass
    ``False`` from an inventory that reports trust state rather than acting
    on it.  Home, imports and lib never gate: you installed one, authored
    another, and pinned the third.
    """

    hits = locate(kind, name, **overrides)
    for hit in hits:
        if hit["ring"] != "lib" and name.startswith(RESERVED_PREFIX):
            raise RingError(
                "reserved-name",
                reserved_refusal(kind, name, str(hit["ring"]), Path(str(hit["path"]))),
            )
    if not hits:
        raise RingError("unresolved", f"{kind_of(kind)} does not resolve: {item_name(name)}")
    record = dict(hits[0])
    record["shadows"] = [
        {"ring": item["ring"], "path": item["path"]} for item in hits[1:]
    ]
    notice = shadow_notice(record)
    record["notices"] = [notice] if notice else []
    if trust and record["ring"] == "project":
        _require_trust(Path(str(record["dir"])).parent.parent)
    return record


def _require_trust(bundle: Path) -> None:
    """Refuse an untrusted project bundle through the ledger's own refusal."""

    try:
        if __package__:
            from . import rings_trust
        else:  # pragma: no cover - direct/installed flat script path
            import rings_trust
    except ImportError as error:  # pragma: no cover - a partial install
        raise RingError("trust-unavailable", str(error)) from error
    verdict = rings_trust.consume(bundle)
    if not verdict["trusted"]:
        raise RingError("bundle-untrusted", verdict["refusal"])


def inventory(kinds: Sequence[str] = KINDS, **overrides) -> List[Dict[str, object]]:
    """Every resolvable item from here, with ring, shadows and trust state.

    The same roots and the same order runtime resolution uses -- an
    inventory that walked its own tree would report a catalogue nothing
    runs (krew's inventory-versus-runtime split).
    """

    try:
        if __package__:
            from . import rings_trust
        else:  # pragma: no cover - direct/installed flat script path
            import rings_trust
    except ImportError:  # pragma: no cover - a partial install
        rings_trust = None
    records = []
    for kind in kinds:
        kind = kind_of(kind)
        names = set()
        for _ring, root in item_roots(kind, **overrides):
            try:
                entries = sorted(path for path in root.iterdir() if path.is_dir())
            except OSError:
                continue
            for entry in entries:
                if NAME_RE.fullmatch(entry.name) and (entry / MANIFESTS[kind]).is_file():
                    names.add(entry.name)
        for name in sorted(names):
            hits = locate(kind, name, **overrides)
            if not hits:
                continue
            record = dict(hits[0])
            record["shadows"] = [
                {"ring": item["ring"], "path": item["path"]} for item in hits[1:]
            ]
            notice = shadow_notice(record)
            record["notices"] = [notice] if notice else []
            reserved = [item for item in hits if item["ring"] != "lib"] if name.startswith(RESERVED_PREFIX) else []
            record["reserved"] = bool(reserved)
            if reserved:
                record["refusal"] = reserved_refusal(
                    kind, name, str(reserved[0]["ring"]), Path(str(reserved[0]["path"])),
                )
            record["trust"] = _trust_state(record, rings_trust)
            records.append(record)
    return records


def _trust_state(record: Dict[str, object], ledger) -> str:
    if record["ring"] != "project":
        return "inherent"
    if ledger is None:  # pragma: no cover - a partial install
        return "unknown"
    bundle = Path(str(record["dir"])).parent.parent
    return "trusted" if ledger.state(bundle)["trusted"] else "untrusted"


__all__ = (
    "IMPORTS_LOCK", "KINDS", "LIB_DIRS", "MANIFESTS", "NAME_RE", "RESERVED_PREFIX",
    "RINGS", "RING_DIRS", "RingError", "home_ring", "imports_lock_path",
    "inventory", "item_name", "item_roots", "kind_of", "lib_root", "locate",
    "project_ring", "read_imports", "reserved_refusal", "resolve",
    "shadow_notice",
)
