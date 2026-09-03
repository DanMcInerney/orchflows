#!/usr/bin/env python3
"""Digest pins for the ring items a ticket stamps beside its pack.

Two kinds pin here: the sheets a ticket stamps as extra craft
(`contracts/sheet.md`) and the applied skill its executor enters as its
method. Both are ordinary ring items resolving through `scripts/rings.py`'s
one order, so both carry the hazard a pack does: a *name* resolves to
whatever bytes happen to be nearest.

The answer is the pack's, applied to two more kinds: take the digest at
issue, the last moment the assignment is still a draft, and re-derive it at
every later door. These items are directories of prose rather than a cell
table, so their identity is a tree hash rather than a resolved-cell
identity, which is why `pack_digest` is not migrated onto this module.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from scripts import rings
    from scripts.tickets_markdown import _parse_frontmatter, dequote
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings
    from tickets_markdown import _parse_frontmatter, dequote


# The kinds this module pins, and the directories inside one that its tree
# hash skips. A sheet carries prose and nothing else, so nothing is skipped
# there. A skill may carry its own tests and installed dependencies, and
# neither is what the ticket stamped.
PINNED_KINDS = ("sheet", "skill")
SKIPPED_DIRS = {
    "sheet": frozenset(),
    "skill": frozenset(("tests", "__pycache__", "node_modules")),
}
# The one hashed-tree format version. It prefixes the digest input so a
# change to how a tree is walked is a visibly different digest rather than a
# silent collision with the old one.
TREE_VERSION = b"orchflows.item-tree.v1\n"
DIGEST_PREFIX = "sha256:"


class PinError(ValueError):
    """A pinned item does not resolve, or is not readable as one."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _lf(data: bytes) -> bytes:
    """Text bytes with the checkout's line endings normalized away."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _files(kind: str, directory: Path) -> List[Tuple[str, Path]]:
    """Every hashed file under one item, as `(relative posix path, path)`."""

    skipped = SKIPPED_DIRS[kind]
    found = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(directory)
        if skipped.intersection(relative.parts[:-1]):
            continue
        found.append((relative.as_posix(), path))
    return sorted(found)


def tree_digest(kind: str, directory) -> str:
    """`sha256:<hex>` over one item directory: sorted paths, then bytes."""

    if kind not in PINNED_KINDS:
        raise PinError("kind-unpinned", f"kind '{kind}' carries no ticket pin")
    digest = hashlib.sha256()
    digest.update(TREE_VERSION)
    digest.update(f"{kind}\n".encode("utf-8"))
    for relative, path in _files(kind, Path(directory)):
        try:
            data = _lf(path.read_bytes())
        except OSError as error:
            raise PinError("item-unreadable", f"unreadable {kind} file {path}: {error}") from error
        digest.update(f"{relative}\n{len(data)}\n".encode("utf-8"))
        digest.update(data)
    return DIGEST_PREFIX + digest.hexdigest()


def resolved(kind: str, name: str, **overrides) -> Dict[str, object]:
    """One pinned item's ring record with its `digest`, or a `PinError`."""

    try:
        record = dict(rings.resolve(kind, name, **overrides))
    except rings.RingError as error:
        raise PinError(error.code, f"{kind} '{name}' cannot be pinned: {error.detail}") from error
    record["digest"] = tree_digest(kind, record["dir"])
    return record


def item_digest(kind: str, name: str, **overrides) -> str:
    return str(resolved(kind, name, **overrides)["digest"])


def drift_refusal(kind: str, name: str, ring: str, pinned: str, current: str) -> str:
    """The one sentence every door says when a pinned item moved under a seal."""

    return (
        f"{kind} '{name}' resolves from the {ring} ring at {current}, but this "
        f"sealed assignment pinned {pinned}: the {kind} changed under the seal, "
        f"or another ring now shadows it. Restore the pinned {kind}, or open a "
        f"fresh callable (tickets.py do | judge) against the {kind} you mean "
        "to stamp."
    )


def drift(kind: str, name: str, pinned: str, **overrides) -> Optional[str]:
    """`None` when the resolved item still hashes to `pinned`, else why not."""

    try:
        record = resolved(kind, name, **overrides)
    except PinError as error:
        return error.detail
    current = str(record["digest"])
    if current == str(pinned).strip():
        return None
    return drift_refusal(kind, name, str(record["ring"]), str(pinned).strip(), current)


def names_of(value) -> List[str]:
    """The stamped names one frontmatter value carries, in file order."""

    values = value if isinstance(value, (list, tuple)) else [value]
    return [name for name in (dequote(item) for item in values) if name]


def digests_of(value) -> Dict[str, str]:
    """The `{name: digest}` mapping one frontmatter value carries, or `{}`."""

    raw = str(value or "").strip()
    if not raw:
        return {}
    try:
        mapping = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(mapping, dict):
        return {}
    return {str(key): str(item) for key, item in mapping.items()}


def encode_digests(mapping: Dict[str, str]) -> str:
    """One frontmatter-safe line for a `{name: digest}` mapping."""

    return json.dumps(mapping, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def declared_packs(record: Dict[str, object]) -> List[str]:
    """The pack names one resolved sheet's `packs:` frontmatter carries."""

    try:
        text = Path(str(record["path"])).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise PinError("item-unreadable", f"unreadable sheet {record['path']}: {error}")
    return names_of(_parse_frontmatter(text).get("packs"))


def stamp_refusal(name: str, pack: str, packs: Sequence[str]) -> str:
    """The one sentence a sheet says when it is stamped beside a wrong pack."""

    remedy = (
        f"Stamp '{name}' beside a pack it names, or add '{pack}' to its "
        "`packs:` if the sheet really governs that domain."
    )
    if not packs:
        return (
            f"sheet '{name}' declares no `packs:`, and this callable stamps "
            f"'{pack}'. Every sheet names the packs it may be stamped beside "
            f"(contracts/sheet.md): add `packs: [{pack}]` to the sheet."
        )
    return (
        f"sheet '{name}' declares packs {list(packs)} and this callable stamps "
        f"'{pack}': a sheet tightens a craft it was written against and says "
        f"nothing about one it was not. {remedy}"
    )


def pin_fields(sheets: Sequence[str], skill, pack=None, **overrides):
    """`(fields, refusal)` -- the four pin fields for one issuing ticket."""

    fields = {
        "sheets": None, "sheet_digests": None, "skill": None, "skill_digest": None,
    }
    names = names_of(list(sheets or ()))
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        return None, {"error": (
            "--sheet names " + ", ".join(f"'{name}'" for name in duplicated)
            + " more than once; one stamp per sheet"
        )}
    stamped = dequote(pack) or ""
    if names:
        digests = {}
        for name in names:
            try:
                record = resolved("sheet", name, **overrides)
                declared = declared_packs(record)
            except PinError as error:
                return None, {"error": error.detail}
            if stamped and stamped not in declared:
                return None, {"error": stamp_refusal(name, stamped, declared)}
            digests[name] = str(record["digest"])
        fields["sheets"] = sorted(names)
        fields["sheet_digests"] = encode_digests(digests)
    applied = names_of(skill)
    if applied:
        try:
            fields["skill_digest"] = item_digest("skill", applied[0], **overrides)
        except PinError as error:
            return None, {"error": error.detail}
        fields["skill"] = applied[0]
    return fields, None


def pinned_findings(data: dict, finding, **overrides) -> List[dict]:
    """Every pin defect one ticket's frontmatter carries, as gradeable findings."""

    findings = []
    sheets = names_of(data.get("sheets"))
    digests = digests_of(data.get("sheet_digests"))
    raw_digests = str(data.get("sheet_digests") or "").strip()
    if raw_digests and not digests:
        findings.append(finding(
            "sheet-digests-invalid", "sheet_digests",
            "sheet_digests is not a canonical JSON object of name to digest",
        ))
    elif sorted(digests) != sorted(sheets):
        findings.append(finding(
            "sheet-digest-unbound", "sheet_digests",
            f"stamped sheets {sorted(sheets)} and pinned digests "
            f"{sorted(digests)} name different sets",
        ))
    else:
        for name in sheets:
            detail = drift("sheet", name, digests[name], **overrides)
            if detail is not None:
                findings.append(finding("sheet-digest-mismatch", "sheet_digests", detail))
    applied = names_of(data.get("skill"))
    pinned = str(data.get("skill_digest") or "").strip()
    if bool(applied) != bool(pinned):
        findings.append(finding(
            "skill-digest-unbound", "skill_digest",
            "an applied skill and its pinned digest are stamped together or "
            "not at all",
        ))
    elif applied:
        detail = drift("skill", applied[0], pinned, **overrides)
        if detail is not None:
            findings.append(finding("skill-digest-mismatch", "skill_digest", detail))
    return findings


__all__ = (
    "DIGEST_PREFIX", "PINNED_KINDS", "PinError", "SKIPPED_DIRS", "TREE_VERSION",
    "declared_packs", "digests_of", "drift", "drift_refusal", "encode_digests",
    "item_digest", "names_of", "pin_fields", "pinned_findings", "resolved",
    "stamp_refusal", "tree_digest",
)
