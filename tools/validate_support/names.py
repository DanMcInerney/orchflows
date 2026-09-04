"""Validate canonical names and mandatory standard sections."""

from __future__ import annotations

from . import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source
dequote = __dep_packages.dequote
rel = __dep_packages.rel

from . import common as __dep_common
STANDARD_LIBRARY_LENS_KINDS = __dep_common.STANDARD_LIBRARY_LENS_KINDS
STANDARD_ADAPTER_KEY = __dep_common.STANDARD_ADAPTER_KEY
STANDARD_ROOT_REQUIRED_SECTIONS = __dep_common.STANDARD_ROOT_REQUIRED_SECTIONS
STANDARD_ROOT_OPTIONAL_SECTIONS = __dep_common.STANDARD_ROOT_OPTIONAL_SECTIONS
STANDARD_RETIRED_SECTIONS = __dep_common.STANDARD_RETIRED_SECTIONS
ROLE_PROFILES = __dep_common.ROLE_PROFILES
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

# The adapter registry is `scripts/tickets_adapters`', imported rather than
# respelled: a standard's artifact kind is the same fact the runtime branches on
# when it stamps a ticket, and a second table here would let a standard's Lens
# key a kind no adapter emits while both files read correct. Same direction
# as `packages.py`'s `dequote` import -- `tools` may import `scripts`.
#
# An install ships this package under `lib/` so `orchflows check` can run
# these checks over a ring, and the scripts it reads sit flat in `bin/`
# with no `scripts` package above them. The paired import is the tree's
# own idiom for that layout: one module, reached under either name.
try:
    from scripts.tickets_adapters import ADAPTER_REGISTRY
except ImportError:  # pragma: no cover - direct/installed flat script path
    from tickets_adapters import ADAPTER_REGISTRY

# Every shipped prose tree is recursive; depth does not change a call edge.
NAME_CHECKED_TREES = (
    "rules", "docs", "contracts", "templates", "example-workflows", "standards", "skills"
)
NAME_CHECKED_FILES = ("README.md", "DESIGN.md", "ARCHITECTURE.md", "AGENTS.md", "TICKETS.md")
# Host routing owns this control directive; it is not a package in the
# repository's skill/standard namespace, but remains a valid backticked command
# in the managed host block.
HOST_ROUTING_DIRECTIVES = {"orch-off"}
# `orch-` alone is the prefix, not a name; a name carries at least one
# segment after it. Plain text is how the library says "mentioned, not
# called" (rule 2 again), so DESIGN.md's supersession history needs no
# allowlist -- it just does not backtick the names it is burying.
BACKTICKED_NAME_RE = re.compile(r"`(orch-[a-z0-9]+(?:-[a-z0-9]+)*)`")
# The marker that says this tree is the library and not an isolated
# fixture. Same idiom as validate_friction_locations' owner check: a
# fixture copies the real contracts/ beside a synthetic skills/, and
# resolving one against the other would convict the contracts for the
# fixture's own emptiness. ARCHITECTURE.md is the tier map, so a tree
# without it has no tier map for a name to resolve against.
NAME_CHECK_MARKER = ROOT / "ARCHITECTURE.md"
HEADING_RE = re.compile(r"^#+\s+(.*\S)\s*$", re.MULTILINE)


def _heading_slugs(text: str) -> set:
    """Every heading in `text`, as the anchor a link would reach it by."""
    slugs = set()
    for title in HEADING_RE.findall(text):
        slug = re.sub(r"[^a-z0-9\s-]", "", title.lower())
        slugs.add(re.sub(r"\s+", "-", slug).strip("-"))
    return slugs


def validate_names(packages, diag: Diagnostics) -> None:
    """Every backticked `orch-*` outside the skill tree resolves inside it.

    Skipped where the tree is not the library -- no packages, or no
    ARCHITECTURE.md to mark it as the tree whose tiers a name resolves in.
    """

    if not NAME_CHECK_MARKER.is_file():
        diag.warn(rel(NAME_CHECK_MARKER), SKIPPED)
        return
    if not packages:
        diag.warn("skills", SKIPPED)
        return
    known = {pkg["path"].name for pkg in packages} | set(ROLE_PROFILES) | HOST_ROUTING_DIRECTIVES
    paths = []
    for directory in NAME_CHECKED_TREES:
        node = ROOT / directory
        if node.is_dir():
            paths.extend(sorted(node.rglob("*.md")))
    paths.extend(ROOT / name for name in NAME_CHECKED_FILES)
    # A package body is `build_call_graph`'s, which reports an unresolvable
    # name there in its own words; reading it here too would convict one
    # line twice in two vocabularies.
    bodies = {pkg["skill_md"].resolve() for pkg in packages}
    for path in paths:
        if not path.is_file() or path.resolve() in bodies:
            continue
        for name in sorted(set(BACKTICKED_NAME_RE.findall(_read_source(path)))):
            if name in known:
                continue
            diag.error(
                rel(path),
                f"`{name}` names no package: no skills/<tier>/{name}/SKILL.md "
                f"and no standards/{name}/SKILL.md. A backticked name is a call "
                "edge (rules/composition.md rule 2); name it in plain text to "
                "mention it without calling it",
            )


STANDARD_SECTION_HEADING_RE = re.compile(r"(?m)^##\s+(.*\S)\s*$")
STANDARD_LENS_KEY_RE = re.compile(r"(?m)^###\s+(.*\S)\s*$")


def _lens_keys(text: str) -> list:
    """The `###` entry names under `## Lens`, in document order.

    Only the `###` level: the entries themselves may carry `####`
    subsections, and a standard's other `##` sections may carry `###` of
    their own, so the scan stops at the next `##`.
    """
    lens = None
    matches = list(STANDARD_SECTION_HEADING_RE.finditer(text))
    for i, match in enumerate(matches):
        if match.group(1) != "Lens":
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        lens = text[match.end():end]
        break
    if lens is None:
        return []
    return STANDARD_LENS_KEY_RE.findall(lens)


def _adapter_kind(pkg: dict):
    """The artifact kind this standard's declared adapter emits, or None.

    The adapter is one frontmatter key now, not a table cell: a missing or
    unregistered value is `standards.validate_standard_adapter`'s finding,
    reported in its words rather than a second time here.
    """

    adapter = ADAPTER_REGISTRY.get(
        dequote(pkg.get("frontmatter", {}).get(STANDARD_ADAPTER_KEY, ""))
    )
    return adapter.artifact_kind if adapter else None


def validate_standard_sections(packages, diag: Diagnostics) -> None:
    """Each root carries the required `##` sections, none of the retired
    ones, nothing outside the table's roster, and a `## Lens` keyed by
    artifact kind.

    contracts/standard.md's section table names the sections each verb
    reads — the heading does what the lane projection did, so a missing one
    silently drops a domain's review criteria. Deleting a heading left the
    validator at exit 0.

    The Lens keys are the same check one level down. `root` and `cut` are
    library-owned and every domain judges both; the rest is whatever the
    standard's own adapter emits, read from the registry the runtime
    branches on. A missing key leaves a verb with no criteria for an
    artifact it will be handed; an extra one writes criteria for an
    artifact this domain never produces, and neither is visible from the
    prose alone.

    Narrowings are graded against the other row of the same table, by
    `standards.validate_standards`: they arrive under a different directory
    and a different manifest name until the rename lands.
    """

    for pkg in packages:
        if not pkg["is_standard"]:
            continue
        manifest = pkg["skill_md"]
        text = pkg.get("body", "")
        found = set(STANDARD_SECTION_HEADING_RE.findall(text))
        for section in STANDARD_ROOT_REQUIRED_SECTIONS:
            if section not in found:
                diag.error(
                    rel(manifest),
                    f"standard carries no `## {section}` heading — "
                    "contracts/standard.md's section table requires it of a "
                    "root, so that section has to be there",
                )
        for section in STANDARD_RETIRED_SECTIONS:
            if section in found:
                diag.error(
                    rel(manifest),
                    f"standard carries a retired `## {section}` heading — "
                    "contracts/standard.md's section table does not list it; "
                    "move the content to the section that owns it rather "
                    "than owning the fact twice",
                )
        # The roster closes both ways, as the Lens keys below already do:
        # a retired heading is the loop above's finding, so this one names
        # only sections the table never listed at all.
        known = set(STANDARD_ROOT_REQUIRED_SECTIONS) | set(
            STANDARD_ROOT_OPTIONAL_SECTIONS
        )
        for section in sorted(found - known - set(STANDARD_RETIRED_SECTIONS)):
            diag.error(
                rel(manifest),
                f"standard carries an unrecognized `## {section}` heading — "
                "contracts/standard.md's section table is the whole roster "
                f"({', '.join(sorted(known))}), so this section is prose no "
                "verb is pointed at",
            )
        if "Lens" not in found:
            continue
        kind = _adapter_kind(pkg)
        if kind is None:
            continue
        expected = set(STANDARD_LIBRARY_LENS_KINDS) | {kind}
        keys = set(_lens_keys(text))
        for missing in sorted(expected - keys):
            diag.error(
                rel(manifest),
                f"`## Lens` carries no `### {missing}` entry — the entries "
                f"are {', '.join(STANDARD_LIBRARY_LENS_KINDS)} and this "
                f"standard's adapter kind `{kind}`, so a verb handed a "
                f"`{missing}` artifact would have no criteria to read",
            )
        for extra in sorted(keys - expected):
            diag.error(
                rel(manifest),
                f"`## Lens` carries a `### {extra}` entry for an artifact "
                f"kind this standard never produces — its adapter emits "
                f"`{kind}`, beside the library's "
                f"{', '.join(STANDARD_LIBRARY_LENS_KINDS)}",
            )


def validate_unique_names(packages, diag: Diagnostics) -> None:
    seen = {}
    for pkg in packages:
        name = pkg["path"].name
        if name in seen:
            diag.error(rel(pkg["skill_md"]), f"duplicate package name '{name}', also at {rel(seen[name])}")
        else:
            seen[name] = pkg["skill_md"]

__all__ = (
    'NAME_CHECKED_TREES', 'NAME_CHECKED_FILES', 'BACKTICKED_NAME_RE',
    'HOST_ROUTING_DIRECTIVES',
    'NAME_CHECK_MARKER', 'HEADING_RE', 'STANDARD_SECTION_HEADING_RE',
    'STANDARD_LENS_KEY_RE', '_lens_keys', '_adapter_kind',
    '_heading_slugs', 'validate_names', 'validate_standard_sections', 'validate_unique_names',
)
