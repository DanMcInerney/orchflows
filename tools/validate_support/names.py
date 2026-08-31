"""Validate canonical names and mandatory craft sections."""

from __future__ import annotations

from tools.validate_support import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source
rel = __dep_packages.rel

from tools.validate_support import common as __dep_common
CRAFT_MANDATORY_SECTIONS = __dep_common.CRAFT_MANDATORY_SECTIONS
ROLE_PROFILES = __dep_common.ROLE_PROFILES
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

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


def validate_craft_sections(packages, diag: Diagnostics) -> None:
    """Each pack's craft carries every mandatory `##` section.

    contracts/pack-signature.md's craft-section table names the sections
    each verb reads — the heading does what the lane projection did, so a
    missing one silently drops a domain's slicing, evidence, or review
    criteria. Deleting a heading left the validator at exit 0.
    """

    for pkg in packages:
        if not pkg["is_pack"]:
            continue
        craft = pkg["path"] / "references" / "craft.md"
        if not craft.is_file():
            continue  # a missing craft is validate_pack_signature's finding
        found = set(CRAFT_SECTION_HEADING_RE.findall(_read_source(craft)))
        for section in CRAFT_MANDATORY_SECTIONS:
            if section not in found:
                diag.error(
                    rel(craft),
                    f"craft carries no `## {section}` heading — "
                    "contracts/pack-signature.md's craft-section table makes "
                    "it mandatory, so that section has to be there",
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
    '_heading_slugs', 'validate_names', 'validate_craft_sections', 'validate_unique_names',
)
