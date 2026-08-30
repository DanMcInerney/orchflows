#!/usr/bin/env python3
"""Internal pack resolver implementation for the public ``packs.py`` facade."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from scripts.tickets_adapters import ADAPTER_REGISTRY
    from scripts.tickets_markdown import dequote
except ImportError:
    from tickets_adapters import ADAPTER_REGISTRY
    from tickets_markdown import dequote


RESOLVER_VERSION = "orchflows.pack-resolver.v2"
PACK_CELLS = (
    "slicing",
    "workspace",
    "required_spec_fields",
    "craft",
    "lens",
    "evidence",
    "outline",
    "adapter",
    "stages",
    "assembly",
)
EXECUTE_CELLS = (
    "slicing",
    "workspace",
    "required_spec_fields",
    "craft",
    "adapter",
    "stages",
    "assembly",
)
CHECK_CELLS = ("lens", "evidence", "craft")
OUTLINE_CELLS = ("outline", "required_spec_fields", "craft")
CONSUMER_CELLS = {
    "execute": EXECUTE_CELLS,
    "check": CHECK_CELLS,
    "outline": OUTLINE_CELLS,
}
TYPED_CELLS = frozenset(("adapter", "stages", "assembly"))
_CELL_SET = frozenset(PACK_CELLS)
_PACK_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_ADAPTER_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_STAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CELL_ROW_RE = re.compile(r"^\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$")
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
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


def _root_is_packs(path: Path) -> bool:
    return path.name.lower() == "packs"


def _canonical_default() -> Path:
    here = Path(__file__).resolve()
    checkout = here.parent.parent
    source = checkout / "packs"
    if source.is_dir():
        return source
    installed = checkout / "lib" / "packs"
    return installed


def _project_default() -> Optional[Path]:
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".orchflows" / "packs"
        if candidate.is_dir():
            return candidate
    return None


def _scope_root(value: Optional[Path], *, project: bool) -> Optional[Path]:
    if value is None:
        return None
    resolved = Path(value).expanduser().resolve()
    if _root_is_packs(resolved):
        return resolved
    return resolved / ".orchflows" / "packs" if project else resolved / "packs"


def _roots(
    *,
    canonical_root: Optional[Path],
    project_root: Optional[Path],
    user_root: Optional[Path],
) -> List[Tuple[str, Path]]:
    """Return roots in shadowing order: project, user, canonical."""

    if project_root is None:
        project_root = _project_default()
    project = _scope_root(project_root, project=True)
    canonical = (
        Path(canonical_root).expanduser().resolve()
        if canonical_root is not None
        else _canonical_default()
    )
    user = _scope_root(user_root, project=False)
    if user is None:
        home = Path.home() / ".orchflows"
        user = home / "packs"
    candidates: List[Tuple[str, Path]] = []
    if project is not None:
        candidates.append(("project", project))
    candidates.append(("user", user))
    candidates.append(("canonical", canonical))
    # An installed user pack lives under lib/packs. Keep this as a second
    # user root only when the ordinary user root did not point there itself.
    if user.name.lower() != "packs" or user.parent.name.lower() != "lib":
        candidates.append(("user", user.parent / "lib" / "packs"))
    seen = set()
    result = []
    for scope, candidate in candidates:
        marker = str(candidate).casefold()
        if marker in seen:
            continue
        seen.add(marker)
        result.append((scope, candidate))
    return result


def _candidate_path(name: str, packs_root: Path) -> Path:
    # Name validation makes this join safe, while resolve catches unusual
    # filesystem aliases before a caller can escape the selected scope.
    candidate = (packs_root / name / "SKILL.md").resolve()
    try:
        candidate.relative_to(packs_root.resolve())
    except ValueError as error:
        raise PackError("pack-invalid", f"pack path escapes scope: {name}") from error
    return candidate


def _frontmatter_name(text: str, path: Path) -> Optional[str]:
    match = _FRONTMATTER_NAME_RE.search(text)
    return dequote(match.group(1)) if match else None


def _parse_rows(
    text: str,
    path: Path,
    *,
    require_all: bool = True,
) -> Dict[str, str]:
    """Parse the one cell table and reject unknown/repeated cell names.

    The complete resolver requires every declared cell.  A few boundary
    validators need to inspect one typed leaf before a complete pack is
    available (for example, a workspace adapter during admission), so they
    may request a partial row set while still using this one parser.  Partial
    parsing never weakens row, name, or duplicate checks.
    """

    rows: Dict[str, str] = {}
    saw_header = False
    saw_delimiter = False
    in_table = False
    for line in text.splitlines():
        match = _CELL_ROW_RE.match(line)
        if not match:
            if in_table:
                in_table = False
            continue
        key, value = match.groups()
        key = key.strip()
        if key.lower() == "cell" and value.lower() == "binding":
            if saw_header:
                raise PackError("pack-shape-invalid", f"pack signature table repeated in {path}")
            saw_header = True
            continue
        if not saw_header:
            continue
        if not saw_delimiter:
            if re.fullmatch(r"[-: ]+", key) and re.fullmatch(r"[-: ]+", value):
                saw_delimiter = True
                in_table = True
                continue
            raise PackError("pack-shape-invalid", f"pack signature table missing delimiter in {path}")
        if re.fullmatch(r"[-: ]+", key) and re.fullmatch(r"[-: ]+", value):
            in_table = True
            continue
        if not in_table:
            continue
        if key not in _CELL_SET:
            raise PackError("pack-shape-invalid", f"unknown pack cell {key!r} in {path}")
        if key in rows:
            raise PackError("pack-shape-invalid", f"pack cell repeated: {key}")
        if not value.strip():
            raise PackError("pack-shape-invalid", f"pack cell is empty: {key}")
        rows[key] = value.strip()
    if saw_header and not saw_delimiter:
        raise PackError("pack-shape-invalid", f"pack signature table missing delimiter in {path}")
    missing = [cell for cell in PACK_CELLS if cell not in rows]
    if require_all and missing:
        raise PackError("pack-shape-invalid", f"pack signature missing cell(s): {', '.join(missing)}")
    return rows


def _declared_cell(path: Path, cell: str) -> str:
    """Read one declared cell through the resolver's sole table parser.

    This is intentionally private: callers that need a content-addressed
    pack must use :func:`resolve_pack`; the leaf seam exists only for the
    adapter registry's early admission check, where synthetic or incomplete
    pack fixtures are still useful.  It shares byte normalization and table
    validation with the complete resolver, so no second pack parser can drift.
    """

    if cell not in _CELL_SET:
        raise PackError("pack-cell-invalid", f"unknown pack cell: {cell}")
    raw = _read_bytes(path, "pack")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PackError("pack-unreadable", f"unreadable pack {path}: {error}") from error
    rows = _parse_rows(text, path, require_all=False)
    value = rows.get(cell)
    if value is None:
        raise PackError("pack-shape-invalid", f"pack signature missing cell: {cell}")
    return value


def _atom(value: str, cell: str, path: Path) -> str:
    normalized = value.strip()
    if normalized.startswith("`") or normalized.endswith("`"):
        raise PackError("pack-shape-invalid", f"{cell} cell must not bind a skill-style name in {path}")
    if not normalized or "\n" in normalized:
        raise PackError("pack-shape-invalid", f"{cell} cell must be one value in {path}")
    return normalized


def _typed_cells(rows: Dict[str, str], path: Path) -> Dict[str, object]:
    cells: Dict[str, object] = dict(rows)
    adapter = _atom(rows["adapter"], "adapter", path)
    if not _ADAPTER_RE.fullmatch(adapter):
        raise PackError("pack-shape-invalid", f"adapter cell has invalid key: {adapter!r}")
    if adapter not in ADAPTER_REGISTRY:
        raise PackError("pack-shape-invalid", f"adapter cell names an unregistered key: {adapter!r}")
    cells["adapter"] = adapter

    stages_raw = rows["stages"].strip()
    if not (stages_raw.startswith("[") and stages_raw.endswith("]")):
        raise PackError("pack-shape-invalid", "stages cell must be a bracketed list")
    stages: List[str] = []
    inside = stages_raw[1:-1].strip()
    if inside:
        for item in inside.split(","):
            raw_stage = item.strip()
            if raw_stage.startswith("`") or raw_stage.endswith("`"):
                raise PackError("pack-shape-invalid", f"stages cell must use plain stage names: {raw_stage!r}")
            stage = raw_stage
            if not stage or not _STAGE_RE.fullmatch(stage):
                raise PackError("pack-shape-invalid", f"stages cell has invalid stage: {stage!r}")
            if stage in stages:
                raise PackError("pack-shape-invalid", f"stages cell repeats stage: {stage}")
            stages.append(stage)
    cells["stages"] = stages

    assembly = _atom(rows["assembly"], "assembly", path)
    if assembly != "none" and not _STAGE_RE.fullmatch(assembly):
        raise PackError("pack-shape-invalid", f"assembly cell has invalid value: {assembly!r}")
    # ``none`` may coexist with ordinary execution stages when no terminal
    # assembly item exists. A named assembly is a stage name, never a skill
    # binding.
    if assembly != "none" and assembly not in stages:
        raise PackError("pack-shape-invalid", f"assembly is not a declared stage: {assembly}")
    cells["assembly"] = assembly
    return cells


def _reference_paths(value: str) -> List[str]:
    references = []
    for target in _LINK_RE.findall(value):
        target = target.strip().split("#", 1)[0].split("?", 1)[0].strip()
        if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", target):
            continue
        if target.startswith("/"):
            raise PackError("pack-reference-invalid", f"pack reference is absolute: {target}")
        references.append(target)
    return references


def _read_references(rows: Dict[str, str], pack_dir: Path) -> List[Dict[str, object]]:
    result: List[Dict[str, object]] = []
    seen = set()
    for cell in PACK_CELLS:
        for target in _reference_paths(rows[cell]):
            resolved = (pack_dir / target).resolve()
            normalized_target = target.replace("\\", "/")
            marker = (normalized_target, str(resolved).casefold())
            if marker in seen:
                continue
            seen.add(marker)
            data = _read_bytes(resolved, "pack reference")
            result.append({
                "path": normalized_target,
                "sha256": _sha256(data),
                "bytes": base64.b64encode(data).decode("ascii"),
            })
    return sorted(result, key=lambda item: str(item["path"]))


def _signature_digest(pack_dir: Path) -> Optional[str]:
    """Hash the signature contract governing this pack's authored scope."""

    here = Path(__file__).resolve()
    candidates = (
        pack_dir.parent.parent / "contracts" / "pack-signature.md",
        here.parent.parent / "contracts" / "pack-signature.md",
        here.parent.parent / "lib" / "contracts" / "pack-signature.md",
    )
    for candidate in candidates:
        if candidate.is_file():
            return _sha256(_read_bytes(candidate, "pack signature"))
    return None


def _resolved(path: Path, scope: str, name: str) -> Dict[str, object]:
    raw = _read_bytes(path, "pack")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PackError("pack-unreadable", f"unreadable pack {path}: {error}") from error
    declared = _frontmatter_name(text, path)
    if not declared:
        raise PackError("pack-shape-invalid", f"pack has no declared name: {path}")
    if declared != name:
        raise PackError("pack-shape-invalid", f"pack name {declared!r} does not match path {name!r}")
    rows = _parse_rows(text, path)
    cells = _typed_cells(rows, path)
    references = _read_references(rows, path.parent)
    identity = {
        "resolver": RESOLVER_VERSION,
        "pack": name,
        "cells": cells,
        "references": references,
        "signature_sha256": _signature_digest(path.parent),
    }
    digest = "sha256:" + _sha256(_canonical_json(identity))
    return {
        "pack": name,
        "scope": scope,
        "path": str(path),
        "cells": cells,
        "references": references,
        "digest": digest,
    }


def resolve_pack(
    pack: str,
    *,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
) -> Dict[str, object]:
    """Resolve one pack using the project, user, then canonical scope."""

    name = _pack_name(pack)
    roots = _roots(
        canonical_root=canonical_root,
        project_root=project_root,
        user_root=user_root,
    )
    seen = set()
    for scope, packs_root in roots:
        candidate = _candidate_path(name, packs_root)
        marker = str(candidate).casefold()
        if marker in seen:
            continue
        seen.add(marker)
        if candidate.is_file():
            return _resolved(candidate, scope, name)
    raise PackError("pack-unresolved", f"pack does not resolve: {name}")


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
    consumer: str,
    canonical_root: Optional[Path] = None,
    project_root: Optional[Path] = None,
    user_root: Optional[Path] = None,
) -> Dict[str, object]:
    """Find a resolved digest and return only its execute/check cells."""

    requested = str(digest or "").strip()
    if not _SHA_RE.fullmatch(requested):
        raise PackError("digest-invalid", f"invalid pack digest: {requested or '<missing>'}")
    selected = CONSUMER_CELLS.get(consumer)
    if selected is None:
        raise PackError(
            "consumer-invalid",
            "consumer must be one of: " + ", ".join(sorted(CONSUMER_CELLS)),
        )
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
        cells = {cell: resolved["cells"][cell] for cell in selected}
        return {
            "pack": resolved["pack"],
            "scope": resolved["scope"],
            "digest": requested,
            "for": consumer,
            "cells": cells,
        }
    raise PackError("digest-unresolved", f"pack digest does not resolve: {requested}")
