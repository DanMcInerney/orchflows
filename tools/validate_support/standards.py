"""Grade every library standard against `contracts/standard.md`.

A root states a domain; a narrowing tightens one. They are one kind in one
`standards/` directory, told apart by `narrows:` alone: this module grades
the narrowings and `packages.py` the roots, because the section table gives
each a different set. What a narrowing may say is bounded by what its root
already says. Every bound here is one that contract states: the
frontmatter keys, the two sections both kinds carry, the three a narrowing
is refused, the one word ceiling, and the refusal of anything executable
inside the directory.

Its own module rather than a fifth concern inside `packages.py`: that file
already owns discovery, frontmatter, role, anatomy and budget for skills at
four hundred lines. The seam is the section table a manifest is graded
against, so the growth goes sideways.

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
STANDARD_ADAPTER_RE = __dep_common.STANDARD_ADAPTER_RE
Path = __dep_common.Path
ROOT = __dep_common.ROOT
STANDARD_DIR_NAME = __dep_common.STANDARD_DIR_NAME
STANDARD_MANIFEST = __dep_common.STANDARD_MANIFEST
STANDARD_REFUSED_ENTRIES = __dep_common.STANDARD_REFUSED_ENTRIES
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
    narrowings, because `packages.discover_packages` takes the roots and
    grades them against the sections a root is *required*.

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


def standard_lens_kinds(standard_roots, standards):
    """``(kind_by_standard, unresolved)`` for the standard a narrowing names.

    ``kind_by_standard`` maps each resolved name to the one artifact kind its
    adapter emits. Their values are the closed set of `###` keys the
    narrowing's `## Lens` may key, and each key is separately owed: a root
    whose kind no entry carries is a stamp that would hand a verb a
    standard with nothing in it to read. A name that does not resolve, or
    whose adapter is unregistered, lands in ``unresolved`` instead of
    silently widening that set.

    ``standard_roots`` is the directories to look in, nearest first. The
    library has one; a ring's narrowing almost always names a *library*
    root, so a caller grading a ring passes every directory that resolves
    from there and a stamp that can be taken is not reported as one that
    cannot.
    """

    kind_by_standard, unresolved = {}, []
    for name in standards:
        manifest = _standard_manifest(standard_roots, name)
        if manifest is None:
            unresolved.append(name)
            continue
        adapter = ADAPTER_REGISTRY.get(declared_adapter(_read_source(manifest)))
        if adapter is None:
            unresolved.append(name)
            continue
        kind_by_standard[name] = adapter.artifact_kind
    return kind_by_standard, unresolved


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


def validate_standard_sections(body: str, standard: dict, diag) -> None:
    file_label = rel(standard["manifest"])
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


def validate_standard_lens(body: str, fm: dict, standard: dict, diag, standard_roots=None) -> None:
    """`## Lens` keys and the named root's kind are the same set.

    Both directions, because each fails its own way: an entry under a key
    the named root never emits is criteria no verb reads, and a named root
    whose kind no entry carries is a stamp that hands its verb a standard
    with nothing in it for the artifact it makes (contracts/standard.md
    `## Lens`).
    """

    file_label = rel(standard["manifest"])
    standards = declared_standards(fm.get(STANDARD_NARROWS_KEY))
    kind_by_standard, unresolved = standard_lens_kinds(
        default_standard_roots() if standard_roots is None else standard_roots, standards,
    )
    for name in unresolved:
        diag.error(
            file_label,
            f"narrows names '{name}', which resolves to no standard with a "
            "registered adapter in this library",
        )
    kinds = set(kind_by_standard.values())
    entries = LENS_ENTRY_RE.findall(body)
    if standards and not unresolved and not entries:
        diag.error(file_label, "standard '## Lens' carries no '###' artifact-kind entry")
    for entry in entries:
        if unresolved or not kinds:
            break
        if entry not in kinds:
            diag.error(
                file_label,
                f"'## Lens' entry '### {entry}' is not an artifact kind the "
                f"standard {sorted(standards)} emits ({sorted(kinds)})",
            )
    if unresolved:
        return
    for name in sorted(kind_by_standard):
        if kind_by_standard[name] not in entries:
            diag.error(
                file_label,
                f"narrows names '{name}', whose artifact kind "
                f"'{kind_by_standard[name]}' has no '## Lens' entry "
                f"'### {kind_by_standard[name]}'",
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
    kind, and the section table does not partition it.
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
        validate_standard_budget(standard["manifest"], diag)


__all__ = (
    "declared_adapter", "declared_standards", "default_standard_roots",
    "discover_standards", "standard_lens_kinds", "standard_root",
    "validate_standard_contents",
    "validate_standard_frontmatter", "validate_standard_lens",
    "validate_standard_sections", "validate_standards",
    "validate_standard_adapter",
)
