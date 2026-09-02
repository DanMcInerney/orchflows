#!/usr/bin/env python3
"""Digest pins for the ring items a ticket stamps beside its pack.

Two kinds pin here: the sheets a ticket stamps as extra craft
(`contracts/sheet.md`) and the applied skill its executor enters as its
method. Both are ordinary ring items, so both resolve through
`scripts/rings.py`'s one order -- and both therefore carry the same hazard a
pack does: a *name* resolves to whatever bytes happen to be nearest, so a
sealed assignment that carried only the name would silently run whatever the
nearest ring came to hold.

The answer is the pack's, applied to two more kinds: take the digest at
issue, which is the last moment the assignment is still a draft, and
re-derive it at every later door. What is new here is that these items are
directories of prose rather than a cell table, so their identity is a tree
hash rather than a resolved-cell identity -- which is why `pack_digest` is
not migrated onto this module and this module does not reach for it. One
resolver, one hasher, one refusal sentence, for both new kinds.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from scripts import rings
    from scripts.tickets_markdown import dequote
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings
    from tickets_markdown import dequote


# The kinds this module pins, and the directories inside one that its tree
# hash skips. A sheet carries prose and nothing else -- `contracts/sheet.md`
# refuses a `scripts/` inside one -- so nothing is skipped there. A skill may
# carry its own tests and installed dependencies, and neither is what the
# ticket stamped: a test edit or an `npm install` under the seal would read
# as the skill changing.
PINNED_KINDS = ("sheet", "skill")
SKIPPED_DIRS = {
    "sheet": frozenset(),
    "skill": frozenset(("tests", "__pycache__", "node_modules")),
}
# The one hashed-tree format version. It prefixes the digest input so a
# change to how a tree is walked is a visibly different digest rather than
# a silent collision with the old one.
TREE_VERSION = b"orchflows.item-tree.v1\n"
DIGEST_PREFIX = "sha256:"


class PinError(ValueError):
    """A pinned item does not resolve, or is not readable as one."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _lf(data: bytes) -> bytes:
    """Text bytes with the checkout's line endings normalized away.

    The reason is `scripts/packs_support.py`'s, which normalizes for the
    same one before hashing a pack: the tree stores LF, so a working copy a
    Windows tool rewrote as CRLF is the same item, and hashing its raw bytes
    would pin a digest no other host reproduces -- green where it was
    written, red everywhere it is read.
    """

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
    """`sha256:<hex>` over one item directory: sorted paths, then bytes.

    Both the path and the byte length enter the hash before the bytes do,
    so no rename or concatenation of two files can produce another tree's
    digest.
    """

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
    """One frontmatter-safe line for a `{name: digest}` mapping.

    Canonical JSON on one line, the form `done` and `dispatch_v1` already
    take, because the frontmatter reader parses scalars and lists and
    nothing else.
    """

    return json.dumps(mapping, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def pin_fields(sheets: Sequence[str], skill, **overrides):
    """`(fields, refusal)` -- the four pin fields for one issuing ticket.

    A ticket stamping neither kind gets four `None`s, which the renderer
    drops: today's frontmatter, byte for byte.
    """

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
    if names:
        digests = {}
        for name in names:
            try:
                digests[name] = item_digest("sheet", name, **overrides)
            except PinError as error:
                return None, {"error": error.detail}
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
    """Every pin defect one ticket's frontmatter carries, as gradeable findings.

    Shape first, then drift: a `sheets` list with no digest beside it, or a
    digest with no item beside it, names nothing to compare, and reporting
    the comparison as the failure would send a reader to the wrong half.
    """

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
    "digests_of", "drift", "drift_refusal", "encode_digests", "item_digest",
    "names_of", "pin_fields", "pinned_findings", "resolved", "tree_digest",
)
