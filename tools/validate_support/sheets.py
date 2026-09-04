"""Grade every library standard against `contracts/standard.md`.

A root states a domain; a narrowing tightens one. They are one format
under one set of rules and differ only in the sections the contract's
section table allows them, so what a narrowing may say is bounded by what
its root already says. Every bound here is one that contract states: the
frontmatter keys, the two sections both kinds carry, the three a narrowing
is refused, the one word ceiling, and the refusal of anything executable
inside the directory.

Its own module rather than a fifth concern inside `packages.py`: that file
already owns discovery, frontmatter, role, anatomy and budget for skills at
four hundred lines, and a narrowing is a different manifest under a
different directory. The seam is the item kind, so the growth goes
sideways.

Two of the checks read a *root* to grade a *narrowing*. `narrows:` names
the one standard the narrowing tightens, so a name that resolves to no
root is a stamp that can never be taken; and a `## Lens` `###` entry is
keyed by the artifact kind that root's adapter emits, so an entry under
any other key is criteria no verb will ever read. Both are read out of the
root's own `adapter` frontmatter through `ADAPTER_REGISTRY`, never out of
a second table here.
"""

from __future__ import annotations

from . import common as __dep_common
PACK_ADAPTER_RE = __dep_common.PACK_ADAPTER_RE
Path = __dep_common.Path
ROOT = __dep_common.ROOT
SHEET_DIR_NAME = __dep_common.SHEET_DIR_NAME
SHEET_MANIFEST = __dep_common.SHEET_MANIFEST
SHEET_REFUSED_ENTRIES = __dep_common.SHEET_REFUSED_ENTRIES
STANDARD_ADAPTER_KEY = __dep_common.STANDARD_ADAPTER_KEY
STANDARD_NARROWS_KEY = __dep_common.STANDARD_NARROWS_KEY
STANDARD_NARROWING_OPTIONAL_SECTIONS = __dep_common.STANDARD_NARROWING_OPTIONAL_SECTIONS
STANDARD_NARROWING_REFUSED_SECTIONS = __dep_common.STANDARD_NARROWING_REFUSED_SECTIONS
STANDARD_NARROWING_REQUIRED_SECTIONS = __dep_common.STANDARD_NARROWING_REQUIRED_SECTIONS
STANDARD_OPTIONAL_FRONTMATTER = __dep_common.STANDARD_OPTIONAL_FRONTMATTER
STANDARD_REQUIRED_FRONTMATTER = __dep_common.STANDARD_REQUIRED_FRONTMATTER
STANDARD_RETIRED_SECTIONS = __dep_common.STANDARD_RETIRED_SECTIONS
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

from .packages import (
    DESCRIPTION_BUDGET, _read_source, dequote, parse_frontmatter, rel,
)
from .structure import validate_craft_budget

# The adapter-key-to-artifact-kind table is the runtime's, imported rather
# than respelled: a narrowing's Lens entries are keyed by exactly the kind
# the dispatch hands the child, and two spellings of that mapping is how a
# validator comes to pass a standard no child can read.
#
# An install ships this package under `lib/` so `orchflows check` can run
# these checks over a ring, and the scripts it reads sit flat in `bin/`
# with no `scripts` package above them. The paired import is the tree's
# own idiom for that layout: one module, reached under either name.
try:
    from scripts.tickets_adapters import ADAPTER_REGISTRY
except ImportError:  # pragma: no cover - direct/installed flat script path
    from tickets_adapters import ADAPTER_REGISTRY

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
LENS_ENTRY_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
ADAPTER_FIELD_RE = re.compile(r"(?m)^adapter:\s*([^\r\n]+?)\s*$")


def sheet_root() -> Path:
    return ROOT / SHEET_DIR_NAME


def discover_sheets():
    """Every library narrowing as ``{"path": dir, "manifest": manifest}``.

    A directory without the manifest is data rather than a standard,
    exactly as a tier directory holding only ``references/`` is no
    package: the ``is_file()`` guard reads it as nothing, not as a
    standard missing its manifest.
    """

    root = sheet_root()
    if not root.is_dir():
        return []
    found = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        manifest = directory / SHEET_MANIFEST
        if manifest.is_file():
            found.append({"path": directory, "manifest": manifest})
    return found


def declared_packs(value: str):
    """The one standard a ``narrows:`` value names, as a list.

    A list, because the caller resolves a set of names and the rule that
    the field carries exactly one is contracts/standard.md rule 3 rather
    than this parser's.
    """

    name = dequote(str(value or "").strip())
    return [name] if name else []


def _pack_manifest(pack_roots, name: str):
    """The first packs directory carrying ``name``'s manifest, or ``None``."""

    for root in pack_roots:
        manifest = Path(root) / name / "SKILL.md"
        if manifest.is_file():
            return manifest
    return None


def default_pack_roots():
    """Where a library narrowing's `narrows:` name resolves: this library's."""

    return [ROOT / "packs"]


def declared_adapter(text: str) -> str:
    """The ``adapter:`` frontmatter value in one manifest's source, or ``""``."""

    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    match = ADAPTER_FIELD_RE.search(parts[1])
    return dequote(match.group(1)) if match else ""


def pack_lens_kinds(pack_roots, packs):
    """``(kind_by_pack, unresolved)`` for the standard a narrowing names.

    ``kind_by_pack`` maps each resolved name to the one artifact kind its
    adapter emits. Their values are the closed set of `###` keys the
    narrowing's `## Lens` may key, and each key is separately owed: a root
    whose kind no entry carries is a stamp that would hand a verb a
    standard with nothing in it to read. A name that does not resolve, or
    whose adapter is unregistered, lands in ``unresolved`` instead of
    silently widening that set.

    ``pack_roots`` is the directories to look in, nearest first. The
    library has one; a ring's narrowing almost always names a *library*
    root, so a caller grading a ring passes every directory that resolves
    from there and a stamp that can be taken is not reported as one that
    cannot.
    """

    kind_by_pack, unresolved = {}, []
    for name in packs:
        manifest = _pack_manifest(pack_roots, name)
        if manifest is None:
            unresolved.append(name)
            continue
        adapter = ADAPTER_REGISTRY.get(declared_adapter(_read_source(manifest)))
        if adapter is None:
            unresolved.append(name)
            continue
        kind_by_pack[name] = adapter.artifact_kind
    return kind_by_pack, unresolved


def validate_standard_adapter(fm: dict, pkg: dict, diag) -> None:
    """A root's `adapter:` names one registered workspace mechanism key.

    The typed leaf downstream machinery branches on, so an unregistered
    value is a standard whose `## Lens` keys an artifact kind no verb is
    ever handed.
    """

    file_label = rel(pkg["skill_md"])
    value = dequote(fm.get(STANDARD_ADAPTER_KEY, ""))
    if not value:
        diag.error(
            file_label,
            "standard frontmatter declares no 'adapter'; a root introduces "
            "its domain, so it names the one workspace mechanism key",
        )
        return
    if not PACK_ADAPTER_RE.match(value):
        diag.error(
            file_label,
            f"adapter must be one registered mechanism key, got: {value!r}",
        )
        return
    if value not in ADAPTER_REGISTRY:
        diag.error(
            file_label, f"adapter names an unregistered mechanism key: {value!r}"
        )


def validate_sheet_frontmatter(fm: dict, sheet: dict, diag) -> None:
    file_label = rel(sheet["manifest"])
    allowed = set(STANDARD_REQUIRED_FRONTMATTER) | set(STANDARD_OPTIONAL_FRONTMATTER)
    for key in sorted(set(fm) - allowed):
        diag.error(file_label, f"standard frontmatter key '{key}' is not allowed")
    for key in STANDARD_REQUIRED_FRONTMATTER:
        if not fm.get(key):
            diag.error(file_label, f"standard frontmatter missing required key '{key}'")
    if not fm.get(STANDARD_NARROWS_KEY):
        diag.error(
            file_label,
            "standard frontmatter missing required key 'narrows'; every item "
            "under this directory is a narrowing, and a standard with no "
            "'narrows' is a root",
        )
    name = fm.get("name")
    if name and name != sheet["path"].name:
        diag.error(
            file_label,
            f"standard frontmatter name '{name}' does not match folder name "
            f"'{sheet['path'].name}'",
        )
    description = fm.get("description") or ""
    if len(description) > DESCRIPTION_BUDGET:
        diag.error(
            file_label,
            f"description is {len(description)} chars, exceeds "
            f"{DESCRIPTION_BUDGET}-char budget",
        )


def validate_sheet_sections(body: str, sheet: dict, diag) -> None:
    file_label = rel(sheet["manifest"])
    present = SECTION_RE.findall(body)
    for heading in STANDARD_NARROWING_REQUIRED_SECTIONS:
        if heading not in present:
            diag.error(file_label, f"standard missing required section '## {heading}'")
    allowed = set(STANDARD_NARROWING_REQUIRED_SECTIONS) | set(
        STANDARD_NARROWING_OPTIONAL_SECTIONS
    )
    for heading in present:
        if heading in STANDARD_NARROWING_REFUSED_SECTIONS:
            diag.error(
                file_label,
                f"section '## {heading}' is a root's; a narrowing carrying it "
                "would be a second owner of a fact about the domain",
            )
        elif heading in STANDARD_RETIRED_SECTIONS:
            diag.error(
                file_label,
                f"standard carries a retired `## {heading}` heading; "
                "contracts/standard.md's section table does not list it",
            )
        elif heading not in allowed:
            diag.error(file_label, f"section '## {heading}' is not a standard section")


def validate_sheet_lens(body: str, fm: dict, sheet: dict, diag, pack_roots=None) -> None:
    """`## Lens` keys and the named root's kind are the same set.

    Both directions, because each fails its own way: an entry under a key
    the named root never emits is criteria no verb reads, and a named root
    whose kind no entry carries is a stamp that hands its verb a standard
    with nothing in it for the artifact it makes (contracts/standard.md
    `## Lens`).
    """

    file_label = rel(sheet["manifest"])
    packs = declared_packs(fm.get(STANDARD_NARROWS_KEY))
    kind_by_pack, unresolved = pack_lens_kinds(
        default_pack_roots() if pack_roots is None else pack_roots, packs,
    )
    for name in unresolved:
        diag.error(
            file_label,
            f"narrows names '{name}', which resolves to no standard with a "
            "registered adapter in this library",
        )
    kinds = set(kind_by_pack.values())
    entries = LENS_ENTRY_RE.findall(body)
    if packs and not unresolved and not entries:
        diag.error(file_label, "standard '## Lens' carries no '###' artifact-kind entry")
    for entry in entries:
        if unresolved or not kinds:
            break
        if entry not in kinds:
            diag.error(
                file_label,
                f"'## Lens' entry '### {entry}' is not an artifact kind the "
                f"standard {sorted(packs)} emits ({sorted(kinds)})",
            )
    if unresolved:
        return
    for name in sorted(kind_by_pack):
        if kind_by_pack[name] not in entries:
            diag.error(
                file_label,
                f"narrows names '{name}', whose artifact kind "
                f"'{kind_by_pack[name]}' has no '## Lens' entry "
                f"'### {kind_by_pack[name]}'",
            )


def validate_sheet_budget(sheet: dict, diag) -> None:
    """The one ceiling, applied to a narrowing's manifest."""

    validate_craft_budget(sheet["manifest"], diag)


def validate_sheet_contents(sheet: dict, diag) -> None:
    """A standard's directory carries prose and nothing executable."""

    file_label = rel(sheet["manifest"])
    for entry in SHEET_REFUSED_ENTRIES:
        if (sheet["path"] / entry).exists():
            diag.error(
                file_label,
                f"standard directory carries '{entry}'; a standard has no "
                "code of its own, so it declares no dependencies and owns no "
                "environment",
            )


def validate_sheets(diag, pack_roots=None) -> None:
    """Grade every narrowing under this root, or say the check found none."""

    root = sheet_root()
    if not root.is_dir():
        diag.warn(rel(root), SKIPPED)
        return
    for sheet in discover_sheets():
        file_label = rel(sheet["manifest"])
        fm, body = parse_frontmatter(_read_source(sheet["manifest"]), file_label, diag)
        if fm is None or body is None:
            continue
        validate_sheet_frontmatter(fm, sheet, diag)
        validate_sheet_sections(body, sheet, diag)
        validate_sheet_lens(body, fm, sheet, diag, pack_roots)
        validate_sheet_budget(sheet, diag)
        validate_sheet_contents(sheet, diag)


__all__ = (
    "declared_adapter", "declared_packs", "default_pack_roots",
    "discover_sheets", "pack_lens_kinds", "sheet_root",
    "validate_sheet_budget", "validate_sheet_contents",
    "validate_sheet_frontmatter", "validate_sheet_lens",
    "validate_sheet_sections", "validate_sheets",
    "validate_standard_adapter",
)
