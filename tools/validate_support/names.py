"""Validate canonical names and mandatory craft sections."""

from __future__ import annotations

from . import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source
dequote = __dep_packages.dequote
rel = __dep_packages.rel

from . import common as __dep_common
CRAFT_LIBRARY_LENS_KINDS = __dep_common.CRAFT_LIBRARY_LENS_KINDS
CRAFT_MANDATORY_SECTIONS = __dep_common.CRAFT_MANDATORY_SECTIONS
CRAFT_OPTIONAL_SECTIONS = __dep_common.CRAFT_OPTIONAL_SECTIONS
CRAFT_RETIRED_SECTIONS = __dep_common.CRAFT_RETIRED_SECTIONS
PACK_CELL_ROW_RE = __dep_common.PACK_CELL_ROW_RE
ROLE_PROFILES = __dep_common.ROLE_PROFILES
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

# The adapter registry is `scripts/tickets_adapters`', imported rather than
# respelled: a pack's artifact kind is the same fact the runtime branches on
# when it stamps a ticket, and a second table here would let a craft's Lens
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
    "rules", "docs", "contracts", "templates", "example-workflows", "packs", "skills"
)
NAME_CHECKED_FILES = ("README.md", "DESIGN.md", "ARCHITECTURE.md", "AGENTS.md", "TICKETS.md")
# Host routing owns this control directive; it is not a package in the
# repository's skill/pack namespace, but remains a valid backticked command
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
                f"and no packs/{name}/SKILL.md. A backticked name is a call "
                "edge (rules/composition.md rule 2); name it in plain text to "
                "mention it without calling it",
            )


CRAFT_SECTION_HEADING_RE = re.compile(r"(?m)^##\s+(.*\S)\s*$")
CRAFT_LENS_KEY_RE = re.compile(r"(?m)^###\s+(.*\S)\s*$")


def _lens_keys(text: str) -> list:
    """The `###` entry names under `## Lens`, in document order.

    Only the `###` level: the entries themselves may carry `####`
    subsections, and a craft's other `##` sections may carry `###` of
    their own, so the scan stops at the next `##`.
    """
    lens = None
    matches = list(CRAFT_SECTION_HEADING_RE.finditer(text))
    for i, match in enumerate(matches):
        if match.group(1) != "Lens":
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        lens = text[match.end():end]
        break
    if lens is None:
        return []
    return CRAFT_LENS_KEY_RE.findall(lens)


def _adapter_kind(pkg: dict):
    """The artifact kind this pack's declared adapter emits, or None when
    the adapter cell is missing or names no registered mechanism — both
    are validate_pack_signature's findings, reported in its words."""

    cells = dict(PACK_CELL_ROW_RE.findall(pkg.get("body", "")))
    adapter = ADAPTER_REGISTRY.get(dequote(cells.get("adapter", "")))
    return adapter.artifact_kind if adapter else None


def validate_craft_sections(packages, diag: Diagnostics) -> None:
    """Each pack's craft carries the mandatory `##` sections, none of the
    retired ones, nothing outside the table's roster, and a `## Lens`
    keyed by artifact kind.

    contracts/pack-signature.md's craft-section table names the sections
    each verb reads — the heading does what the lane projection did, so a
    missing one silently drops a domain's review criteria. Deleting a
    heading left the validator at exit 0.

    The Lens keys are the same check one level down. `root` and `cut` are
    library-owned and every domain judges both; the rest is whatever the
    pack's own adapter emits, read from the registry the runtime branches
    on. A missing key leaves a verb with no criteria for an artifact it
    will be handed; an extra one writes criteria for an artifact this
    domain never produces, and neither is visible from the prose alone.
    """

    for pkg in packages:
        if not pkg["is_pack"]:
            continue
        craft = pkg["path"] / "references" / "craft.md"
        if not craft.is_file():
            continue  # a missing craft is validate_pack_signature's finding
        text = _read_source(craft)
        found = set(CRAFT_SECTION_HEADING_RE.findall(text))
        for section in CRAFT_MANDATORY_SECTIONS:
            if section not in found:
                diag.error(
                    rel(craft),
                    f"craft carries no `## {section}` heading — "
                    "contracts/pack-signature.md's craft-section table makes "
                    "it mandatory, so that section has to be there",
                )
        for section in CRAFT_RETIRED_SECTIONS:
            if section in found:
                diag.error(
                    rel(craft),
                    f"craft carries a retired `## {section}` heading — "
                    "contracts/pack-signature.md retired it into a `## Lens` "
                    "entry keyed by artifact kind; move the content there "
                    "rather than owning the fact twice",
                )
        # The roster closes both ways, as the Lens keys below already do:
        # a retired heading is the loop above's finding, so this one names
        # only sections the signature table never listed at all.
        known = set(CRAFT_MANDATORY_SECTIONS) | set(CRAFT_OPTIONAL_SECTIONS)
        for section in sorted(found - known - set(CRAFT_RETIRED_SECTIONS)):
            diag.error(
                rel(craft),
                f"craft carries an unrecognized `## {section}` heading — "
                "contracts/pack-signature.md's craft-section table is the "
                f"whole roster ({', '.join(sorted(known))}), so this "
                "section is prose no verb is pointed at",
            )
        if "Lens" not in found:
            continue
        kind = _adapter_kind(pkg)
        if kind is None:
            continue
        expected = set(CRAFT_LIBRARY_LENS_KINDS) | {kind}
        keys = set(_lens_keys(text))
        for missing in sorted(expected - keys):
            diag.error(
                rel(craft),
                f"`## Lens` carries no `### {missing}` entry — the entries "
                f"are {', '.join(CRAFT_LIBRARY_LENS_KINDS)} and this pack's "
                f"adapter kind `{kind}`, so a verb handed a `{missing}` "
                "artifact would have no criteria to read",
            )
        for extra in sorted(keys - expected):
            diag.error(
                rel(craft),
                f"`## Lens` carries a `### {extra}` entry for an artifact "
                f"kind this pack never produces — its adapter emits "
                f"`{kind}`, beside the library's "
                f"{', '.join(CRAFT_LIBRARY_LENS_KINDS)}",
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
    'NAME_CHECK_MARKER', 'HEADING_RE', 'CRAFT_SECTION_HEADING_RE',
    'CRAFT_LENS_KEY_RE', '_lens_keys', '_adapter_kind',
    '_heading_slugs', 'validate_names', 'validate_craft_sections', 'validate_unique_names',
)
