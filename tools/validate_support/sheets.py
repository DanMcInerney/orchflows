"""Grade every library sheet against `contracts/sheet.md`.

A sheet is not a small pack. It is extra craft one ticket stamps beside its
pack, read by that ticket's maker and by its judge at a pinned digest -- so
what it may say is bounded by what the pack already says, and every bound
here is one that contract states: the three frontmatter fields, the two
mandatory sections, the three pack-only sections it may not carry, the
hundred-line ceiling, and the refusal of anything executable inside the
directory.

Its own module rather than a fifth concern inside `packages.py`: that file
already owns discovery, frontmatter, role, anatomy and budget for skills and
packs at 424 lines, and a sheet is a different manifest under a different
directory with a different shape. The seam is the item kind, so the growth
goes sideways.

Two of the checks read a *pack* to grade a *sheet*. `packs:` names the packs
a sheet may be stamped beside, so a name that resolves to no pack is a stamp
that can never be taken; and a `## Lens` `###` entry is keyed by the artifact
kind the named packs' adapters emit, so an entry under any other key is
criteria no verb will ever read. Both are read out of the pack's own typed
`adapter` cell through `ADAPTER_REGISTRY`, never out of a second table here.
"""

from __future__ import annotations

from . import common as __dep_common
PACK_CELL_ROW_RE = __dep_common.PACK_CELL_ROW_RE
Path = __dep_common.Path
ROOT = __dep_common.ROOT
SHEET_BUDGET = __dep_common.SHEET_BUDGET
SHEET_DIR_NAME = __dep_common.SHEET_DIR_NAME
SHEET_MANIFEST = __dep_common.SHEET_MANIFEST
SHEET_OPTIONAL_SECTIONS = __dep_common.SHEET_OPTIONAL_SECTIONS
SHEET_PACK_ONLY_SECTIONS = __dep_common.SHEET_PACK_ONLY_SECTIONS
SHEET_REFUSED_ENTRIES = __dep_common.SHEET_REFUSED_ENTRIES
SHEET_REQUIRED_FRONTMATTER = __dep_common.SHEET_REQUIRED_FRONTMATTER
SHEET_REQUIRED_SECTIONS = __dep_common.SHEET_REQUIRED_SECTIONS
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

from .packages import (
    DESCRIPTION_BUDGET, _read_source, parse_frontmatter, rel,
)

# The adapter-key-to-artifact-kind table is the runtime's, imported rather
# than respelled: a sheet's Lens entries are keyed by exactly the kind the
# dispatch hands the child, and two spellings of that mapping is how a
# validator comes to pass a sheet no child can read.
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
# `packs: [a, b]` -- the one inline-list form a sheet's frontmatter takes.
# `scripts/tickets_markdown.py` parses the same shape when the runtime reads
# it; this is the validator's half of that one form.
INLINE_LIST_RE = re.compile(r"^\[(.*)\]$")


def sheet_root() -> Path:
    return ROOT / SHEET_DIR_NAME


def discover_sheets():
    """Every library sheet as ``{"path": dir, "manifest": SHEET.md}``.

    A directory without the manifest is data rather than a sheet, exactly as
    a tier directory holding only ``references/`` is no package: the
    ``is_file()`` guard reads it as nothing, not as a sheet missing its
    manifest.
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
    """The pack names one `packs:` frontmatter value carries, in file order."""

    raw = str(value or "").strip()
    if not raw:
        return []
    match = INLINE_LIST_RE.match(raw)
    if match:
        raw = match.group(1)
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]


def _pack_manifest(pack_roots, name: str):
    """The first packs directory carrying ``name``'s manifest, or ``None``."""

    for root in pack_roots:
        manifest = Path(root) / name / "SKILL.md"
        if manifest.is_file():
            return manifest
    return None


def default_pack_roots():
    """Where a library sheet's `packs:` names resolve: this library's own."""

    return [ROOT / "packs"]


def pack_lens_kinds(pack_roots, packs):
    """``(kinds, unresolved)`` for the packs a sheet names.

    ``kinds`` is every artifact kind the named packs' adapters emit, which
    is the closed set of `###` keys the sheet's `## Lens` may use; a pack
    that does not resolve, or whose adapter is unregistered, lands in
    ``unresolved`` instead of silently widening that set.

    ``pack_roots`` is the packs directories to look in, nearest first. The
    library has one; a ring's sheet almost always names a *library* pack,
    so a caller grading a ring passes every packs directory that resolves
    from there and a stamp that can be taken is not reported as one that
    cannot.
    """

    kinds, unresolved = set(), []
    for name in packs:
        manifest = _pack_manifest(pack_roots, name)
        if manifest is None:
            unresolved.append(name)
            continue
        cells = dict(PACK_CELL_ROW_RE.findall(_read_source(manifest)))
        adapter = ADAPTER_REGISTRY.get(str(cells.get("adapter", "")).strip().strip("`"))
        if adapter is None:
            unresolved.append(name)
            continue
        kinds.add(adapter.artifact_kind)
    return kinds, unresolved


def validate_sheet_frontmatter(fm: dict, sheet: dict, diag) -> None:
    file_label = rel(sheet["manifest"])
    extra = set(fm) - set(SHEET_REQUIRED_FRONTMATTER)
    for key in sorted(extra):
        diag.error(file_label, f"sheet frontmatter key '{key}' is not allowed")
    for key in SHEET_REQUIRED_FRONTMATTER:
        if not fm.get(key):
            diag.error(file_label, f"sheet frontmatter missing required key '{key}'")
    name = fm.get("name")
    if name and name != sheet["path"].name:
        diag.error(
            file_label,
            f"sheet frontmatter name '{name}' does not match folder name "
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
    for heading in SHEET_REQUIRED_SECTIONS:
        if heading not in present:
            diag.error(file_label, f"sheet missing required section '## {heading}'")
    allowed = set(SHEET_REQUIRED_SECTIONS) | set(SHEET_OPTIONAL_SECTIONS)
    for heading in present:
        if heading in SHEET_PACK_ONLY_SECTIONS:
            diag.error(
                file_label,
                f"section '## {heading}' is the pack's; a sheet carrying it "
                "would be a second owner of a fact about the domain",
            )
        elif heading not in allowed:
            diag.error(file_label, f"section '## {heading}' is not a sheet section")


def validate_sheet_lens(body: str, fm: dict, sheet: dict, diag, pack_roots=None) -> None:
    """Every `###` entry is keyed by a kind one named pack actually emits."""

    file_label = rel(sheet["manifest"])
    packs = declared_packs(fm.get("packs"))
    kinds, unresolved = pack_lens_kinds(
        default_pack_roots() if pack_roots is None else pack_roots, packs,
    )
    for name in unresolved:
        diag.error(
            file_label,
            f"packs names '{name}', which resolves to no pack with a "
            "registered adapter in this library",
        )
    entries = LENS_ENTRY_RE.findall(body)
    if packs and not unresolved and not entries:
        diag.error(file_label, "sheet '## Lens' carries no '###' artifact-kind entry")
    for entry in entries:
        if unresolved or not kinds:
            break
        if entry not in kinds:
            diag.error(
                file_label,
                f"'## Lens' entry '### {entry}' is not an artifact kind the "
                f"packs {sorted(packs)} emit ({sorted(kinds)})",
            )


def validate_sheet_budget(body: str, sheet: dict, diag) -> None:
    lines = sum(1 for line in body.split("\n") if line.strip())
    if lines > SHEET_BUDGET:
        diag.error(
            rel(sheet["manifest"]),
            f"sheet has {lines} non-empty lines, exceeds the sheet budget of "
            f"{SHEET_BUDGET}",
        )


def validate_sheet_contents(sheet: dict, diag) -> None:
    """A sheet directory carries prose and nothing executable."""

    file_label = rel(sheet["manifest"])
    for entry in SHEET_REFUSED_ENTRIES:
        if (sheet["path"] / entry).exists():
            diag.error(
                file_label,
                f"sheet directory carries '{entry}'; a sheet has no code of "
                "its own, so it declares no dependencies and owns no "
                "environment",
            )


def validate_sheets(diag, pack_roots=None) -> None:
    """Grade every sheet under this root, or say the check found none."""

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
        validate_sheet_budget(body, sheet, diag)
        validate_sheet_contents(sheet, diag)


__all__ = (
    "SHEET_BUDGET", "declared_packs", "default_pack_roots", "discover_sheets",
    "pack_lens_kinds",
    "sheet_root", "validate_sheet_budget", "validate_sheet_contents",
    "validate_sheet_frontmatter", "validate_sheet_lens",
    "validate_sheet_sections", "validate_sheets",
)
