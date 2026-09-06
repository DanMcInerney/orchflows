"""Grade every library standard against `contracts/standard.md`.

A root states a domain; a narrowing tightens one. They are one kind in one
`standards/` directory, told apart by optional `narrows:` alone. Both carry
ordinary domain guidance in any clear Markdown layout. This module checks
the shared frontmatter, nonempty guidance, optional legacy Lens structure,
the word ceiling, and the refusal of executable content.

Its own module rather than a fifth concern inside `packages.py`: that file
already owns discovery, frontmatter, role, anatomy and budget for skills at
four hundred lines. Standard-specific checks stay here so the growth goes
sideways.

One check reads a *root* to grade a *narrowing*: `narrows:` names the one
standard it tightens, so a name that resolves to no manifest is a stamp that
can never be taken. Adapter hints and Lens labels do not decide composition.
"""

from __future__ import annotations

from . import common as __dep_common
STANDARD_ADAPTER_RE = __dep_common.STANDARD_ADAPTER_RE
Path = __dep_common.Path
ROOT = __dep_common.ROOT
STANDARD_DIR_NAME = __dep_common.STANDARD_DIR_NAME
STANDARD_MANIFEST = __dep_common.STANDARD_MANIFEST
STANDARD_REFUSED_ENTRIES = __dep_common.STANDARD_REFUSED_ENTRIES
STANDARD_ADAPTER_KEY = __dep_common.STANDARD_ADAPTER_KEY
STANDARD_NARROWS_KEY = __dep_common.STANDARD_NARROWS_KEY
STANDARD_OPTIONAL_FRONTMATTER = __dep_common.STANDARD_OPTIONAL_FRONTMATTER
STANDARD_REQUIRED_FRONTMATTER = __dep_common.STANDARD_REQUIRED_FRONTMATTER
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

from .packages import (
    DESCRIPTION_BUDGET, _read_source, declares_narrows, dequote,
    parse_frontmatter, rel,
)
from .structure import validate_standard_budget

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


def standard_root() -> Path:
    return ROOT / STANDARD_DIR_NAME


def discover_standards():
    """Every library standard as ``{"path", "manifest", "narrows"}``.

    Root and narrowing alike, with `narrows` saying which: they are one
    kind in one directory, so the field is the partition and the path is
    not. The section, frontmatter and Lens checks below take the
    narrowings, because `packages.discover_packages` takes the roots.

    A directory without the manifest is data rather than a standard,
    exactly as a tier directory holding only ``references/`` is no
    package: the ``is_file()`` guard reads it as nothing, not as a
    standard missing its manifest.
    """

    root = standard_root()
    if not root.is_dir():
        return []
    found = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        manifest = directory / STANDARD_MANIFEST
        if manifest.is_file():
            found.append({
                "path": directory,
                "manifest": manifest,
                "narrows": declares_narrows(_read_source(manifest)),
            })
    return found


def declared_standards(value: str):
    """The one standard a ``narrows:`` value names, as a list.

    A list, because the caller resolves a set of names and the rule that
    the field carries exactly one is contracts/standard.md rule 3 rather
    than this parser's.
    """

    name = dequote(str(value or "").strip())
    return [name] if name else []


def _standard_manifest(standard_roots, name: str):
    """The first standards directory carrying ``name``'s manifest, or ``None``."""

    for root in standard_roots:
        manifest = Path(root) / name / STANDARD_MANIFEST
        if manifest.is_file():
            return manifest
    return None


def default_standard_roots():
    """Where a library narrowing's `narrows:` name resolves: this library's."""

    return [standard_root()]


def declared_adapter(text: str) -> str:
    """The ``adapter:`` frontmatter value in one manifest's source, or ``""``."""

    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    match = ADAPTER_FIELD_RE.search(parts[1])
    return dequote(match.group(1)) if match else ""


def validate_standard_adapter(fm: dict, pkg: dict, diag) -> None:
    """When present, ``adapter:`` is one registered legacy workspace hint."""

    file_label = rel(pkg["skill_md"])
    value = dequote(fm.get(STANDARD_ADAPTER_KEY, ""))
    if not value:
        return
    if not STANDARD_ADAPTER_RE.match(value):
        diag.error(
            file_label,
            f"adapter must be one registered mechanism key, got: {value!r}",
        )
        return
    if value not in ADAPTER_REGISTRY:
        diag.error(
            file_label, f"adapter names an unregistered mechanism key: {value!r}"
        )


def validate_standard_frontmatter(fm: dict, standard: dict, diag) -> None:
    file_label = rel(standard["manifest"])
    allowed = set(STANDARD_REQUIRED_FRONTMATTER) | set(STANDARD_OPTIONAL_FRONTMATTER)
    for key in sorted(set(fm) - allowed):
        diag.error(file_label, f"standard frontmatter key '{key}' is not allowed")
    for key in STANDARD_REQUIRED_FRONTMATTER:
        if not fm.get(key):
            diag.error(file_label, f"standard frontmatter missing required key '{key}'")
    if not fm.get(STANDARD_NARROWS_KEY):
        diag.error(
            file_label,
            "standard frontmatter missing required key 'narrows'; this "
            "check grades narrowings, and a standard with no 'narrows' is a "
            "root graded against a root's sections instead",
        )
    name = fm.get("name")
    if name and name != standard["path"].name:
        diag.error(
            file_label,
            f"standard frontmatter name '{name}' does not match folder name "
            f"'{standard['path'].name}'",
        )
    description = fm.get("description") or ""
    if len(description) > DESCRIPTION_BUDGET:
        diag.error(
            file_label,
            f"description is {len(description)} chars, exceeds "
            f"{DESCRIPTION_BUDGET}-char budget",
        )


def _substantive(text: str) -> bool:
    """Whether Markdown contains guidance beyond headings and fences."""

    without_headings = re.sub(r"(?m)^\s{0,3}#{1,6}\s+.*$", "", text)
    without_fences = re.sub(r"(?m)^\s*(?:---|```|~~~)\s*$", "", without_headings)
    return bool(without_fences.strip())


def _lens_entries(body: str):
    """The optional Lens regions and their ``###`` entries, mechanically."""

    sections = list(SECTION_RE.finditer(body))
    lenses = []
    for index, section in enumerate(sections):
        if section.group(1) != "Lens":
            continue
        end = sections[index + 1].start() if index + 1 < len(sections) else len(body)
        region = body[section.end():end]
        lenses.append((region, list(LENS_ENTRY_RE.finditer(region))))
    return lenses


def validate_standard_sections(body: str, standard: dict, diag) -> None:
    """Require guidance; if a legacy Lens exists, require sound structure.

    Headings are author choices. The validator does not infer semantic
    coverage from their names or from an adapter hint.
    """

    file_label = rel(standard["manifest"])
    if not _substantive(body):
        diag.error(file_label, "standard body carries no domain guidance")
        return
    lenses = _lens_entries(body)
    if len(lenses) > 1:
        diag.error(file_label, "standard carries more than one `## Lens` heading")
        return
    if not lenses:
        return
    region, entries = lenses[0]
    if not entries:
        diag.error(file_label, "standard `## Lens` carries no `###` entry")
        return
    names = [entry.group(1) for entry in entries]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    for name in duplicates:
        diag.error(file_label, f"standard `## Lens` repeats `### {name}`")
    for index, entry in enumerate(entries):
        end = entries[index + 1].start() if index + 1 < len(entries) else len(region)
        if not _substantive(region[entry.end():end]):
            diag.error(
                file_label,
                f"standard `## Lens` entry `### {entry.group(1)}` carries no guidance",
            )


def validate_standard_lens(body: str, fm: dict, standard: dict, diag, standard_roots=None) -> None:
    """Check only that optional ``narrows:`` resolves to one manifest.

    Lens labels are reader guidance, not a machine claim that the standard
    covers an adapter's artifact kinds.
    """

    file_label = rel(standard["manifest"])
    standards = declared_standards(fm.get(STANDARD_NARROWS_KEY))
    roots = default_standard_roots() if standard_roots is None else standard_roots
    for name in standards:
        if _standard_manifest(roots, name) is not None:
            continue
        diag.error(
            file_label,
            f"narrows names '{name}', which resolves to no standard in this library",
        )


def validate_standard_contents(standard: dict, diag) -> None:
    """A standard's directory carries prose and nothing executable."""

    file_label = rel(standard["manifest"])
    for entry in STANDARD_REFUSED_ENTRIES:
        if (standard["path"] / entry).exists():
            diag.error(
                file_label,
                f"standard directory carries '{entry}'; a standard has no "
                "code of its own, so it declares no dependencies and owns no "
                "environment",
            )


def validate_standards(diag, standard_roots=None) -> None:
    """Grade every narrowing under this root, or say the check found none.

    `validate_standard_contents` is the one check here that reaches a root
    as well: what a standard's *directory* may hold is a fact about the
    kind.
    """

    root = standard_root()
    if not root.is_dir():
        diag.warn(rel(root), SKIPPED)
        return
    for standard in discover_standards():
        validate_standard_contents(standard, diag)
        if not standard["narrows"]:
            continue
        file_label = rel(standard["manifest"])
        fm, body = parse_frontmatter(_read_source(standard["manifest"]), file_label, diag)
        if fm is None or body is None:
            continue
        validate_standard_frontmatter(fm, standard, diag)
        validate_standard_sections(body, standard, diag)
        validate_standard_lens(body, fm, standard, diag, standard_roots)
        validate_standard_adapter(fm, {"skill_md": standard["manifest"]}, diag)
        validate_standard_budget(standard["manifest"], diag)


__all__ = (
    "declared_adapter", "declared_standards", "default_standard_roots",
    "discover_standards", "standard_root",
    "validate_standard_contents",
    "validate_standard_frontmatter", "validate_standard_lens",
    "validate_standard_sections", "validate_standards",
    "validate_standard_adapter",
)
