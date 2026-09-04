#!/usr/bin/env python3
"""Digest pins for the ring items a ticket stamps.

Two kinds pin here: the standards a ticket stamps as its standard
(`contracts/standard.md`) and the applied skill its executor enters as its
method. Both are ordinary ring items resolving through `scripts/rings.py`'s
one order, so both carry one hazard: a *name* resolves to whatever bytes
happen to be nearest.

The answer to it: take the digest at issue, the last moment the assignment
is still a draft, and re-derive it at every later door. Identity is a hash
over the item's directory tree, which is one rule for a root standard, a
narrowing, and an applied skill alike.

A stamped standard is not one item but a chain. `scripts/standards.py` walks
`narrows:` to the root and checks the resolved set; this module turns that
chain into the one ordered `(name, digest)` list the ticket carries.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from scripts import standards_support, rings
    from scripts.tickets_markdown import (
        STANDARDS_FIELD, STANDARD_SEPARATOR, dequote,
    )
except ImportError:  # pragma: no cover - direct/installed flat script path
    import standards_support
    import rings
    from tickets_markdown import STANDARDS_FIELD, STANDARD_SEPARATOR, dequote


# The kinds this module pins, and the directories inside one that its tree
# hash skips. A standard carries prose and nothing else, so nothing is
# skipped for either directory one still lives in. A skill may carry its own
# tests and installed dependencies, and neither is what the ticket stamped.
PINNED_KINDS = ("standard", "standard", "skill")
SKIPPED_DIRS = {
    "standard": frozenset(),
    "standard": frozenset(),
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


def resolved_standards(names: Sequence[str], **overrides) -> List[Dict[str, object]]:
    """One stamped set's whole chain, broad to narrow, each level digested.

    Resolution -- the `narrows:` walk, the cycle, depth and parent refusals,
    and the one-adapter check -- belongs to `standards_support` and raises
    `StandardError`. What is added here is the pin: the tree digest of every
    level, taken once, at the last moment the assignment is still a draft.
    """

    chain = standards_support.resolve_chain(list(names), **overrides)
    for link in chain:
        link["digest"] = tree_digest(str(link["kind"]), Path(str(link["dir"])))
    return chain


def encode_standards(chain: Sequence[Dict[str, object]]) -> List[str]:
    """The chain as the frontmatter list the ticket carries, in walk order."""

    return [f"{link['name']}{STANDARD_SEPARATOR}{link['digest']}" for link in chain]


def standards_of(value) -> List[Tuple[str, str]]:
    """The `(name, digest)` levels one `standards:` value carries, in order."""

    levels = []
    for entry in names_of(value if isinstance(value, (list, tuple)) else [value]):
        name, separator, digest = entry.partition(STANDARD_SEPARATOR)
        if separator:
            levels.append((name.strip(), digest.strip()))
    return levels


def adapter_standard(data: dict, **overrides) -> str:
    """The stamped standard declaring this ticket's adapter, or `''`.

    Empty covers both a ticket stamping nothing and a set whose adapter no
    longer resolves; the second is reported as its own finding by the
    admission door, which is the one place a resolution failure is graded.
    """

    names = [name for name, _digest in standards_of(data.get(STANDARDS_FIELD))]
    if not names:
        return ""
    try:
        return standards_support.adapter_standard(names, **overrides)
    except standards_support.StandardError:
        return ""


def declared_domain(link: Dict[str, object]) -> List[str]:
    """The domains one narrowing declares it may be stamped under.

    `standards:` is the pre-`narrows:` spelling of one rule -- a narrowing
    tightens the domain it was written against and says nothing about one it
    was not -- and it survives only while an item can still carry it. Once a
    narrowing names its parent, the parent *is* the declaration and the two
    lists cannot disagree, so this reads one field and returns `[]` for an
    item that has moved on.
    """

    try:
        text = Path(str(link["path"])).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise PinError("item-unreadable", f"unreadable standard {link['path']}: {error}")
    data = standards_support._parse_frontmatter(text)
    if dequote(data.get("narrows")):
        return []
    return names_of(data.get("standards"))


def domain_refusal(name: str, domain: str, declared: Sequence[str]) -> str:
    """The one sentence a narrowing says when it is stamped off its domain."""

    return (
        f"standard '{name}' declares standards {list(declared)} and this callable "
        f"stamps '{domain}': a narrowing tightens a standard it was written "
        f"against and says nothing about one it was not. Stamp '{name}' "
        f"beside a domain it names, or add '{domain}' to its `standards:` if it "
        "really governs that domain."
    )


def _domain_refusals(chain: Sequence[Dict[str, object]]):
    """Why one resolved chain does not compose, under the legacy spelling."""

    domain = next(str(link["name"]) for link in chain if link["adapter"])
    for link in chain:
        if link["adapter"]:
            continue
        declared = declared_domain(link)
        if declared and domain not in declared:
            return domain_refusal(str(link["name"]), domain, declared)
    return None


def pin_fields(standards: Sequence[str], skill, **overrides):
    """`(fields, refusal)` -- the pin fields for one issuing ticket."""

    fields = {STANDARDS_FIELD: None, "skill": None, "skill_digest": None}
    names = names_of(list(standards or ()))
    if names:
        try:
            chain = resolved_standards(names, **overrides)
            refusal = _domain_refusals(chain)
            if refusal is not None:
                return None, {"error": refusal}
            fields[STANDARDS_FIELD] = encode_standards(chain)
        except (standards_support.StandardError, PinError) as error:
            return None, {"error": error.detail}
    applied = names_of(skill)
    if applied:
        try:
            fields["skill_digest"] = item_digest("skill", applied[0], **overrides)
        except PinError as error:
            return None, {"error": error.detail}
        fields["skill"] = applied[0]
    return fields, None


def _chain_drift(levels, chain, finding) -> List[dict]:
    """Every level whose bytes -- or whose place in the chain -- moved."""

    current = {str(link["name"]): link for link in chain}
    findings = []
    for name, pinned in levels:
        link = current.get(name)
        if link is not None and str(link["digest"]) == pinned:
            continue
        findings.append(finding(
            "standard-digest-mismatch", STANDARDS_FIELD,
            drift_refusal(
                "standard", name,
                "no" if link is None else str(link["ring"]),
                pinned,
                "nothing" if link is None else str(link["digest"]),
            ),
        ))
    for name in current:
        if name not in {level for level, _digest in levels}:
            findings.append(finding(
                "standard-digest-mismatch", STANDARDS_FIELD,
                f"standard '{name}' is in the chain the stamped names resolve "
                f"to now, and this sealed assignment pinned no level for it: a "
                f"`narrows:` edge changed under the seal. Restore the pinned "
                f"chain, or open a fresh callable (tickets.py do | judge).",
            ))
    return findings


def pinned_findings(data: dict, finding, **overrides) -> List[dict]:
    """Every pin defect one ticket's frontmatter carries, as gradeable findings."""

    findings = []
    raw = data.get(STANDARDS_FIELD)
    levels = standards_of(raw)
    stamped = names_of(raw if isinstance(raw, (list, tuple)) else [raw])
    if len(levels) != len(stamped):
        findings.append(finding(
            "standard-pin-invalid", STANDARDS_FIELD,
            f"every {STANDARDS_FIELD} entry is "
            f"'<name>{STANDARD_SEPARATOR}sha256:<hex>'; got {stamped}",
        ))
    elif levels:
        try:
            chain = resolved_standards([name for name, _digest in levels], **overrides)
        except (standards_support.StandardError, PinError) as error:
            chain = None
            findings.append(finding(error.code, STANDARDS_FIELD, error.detail))
        if chain is not None:
            findings.extend(_chain_drift(levels, chain, finding))
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
    "DIGEST_PREFIX", "PINNED_KINDS", "STANDARDS_FIELD", "STANDARD_SEPARATOR",
    "PinError", "SKIPPED_DIRS", "TREE_VERSION",
    "adapter_standard", "declared_domain", "domain_refusal", "drift",
    "drift_refusal", "encode_standards", "item_digest", "names_of",
    "pin_fields", "pinned_findings", "resolved", "resolved_standards",
    "standards_of", "tree_digest",
)
