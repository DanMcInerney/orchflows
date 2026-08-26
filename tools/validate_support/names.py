"""Validate canonical names and lens anchors."""

from __future__ import annotations

from tools.validate_support import packages as __dep_packages
Diagnostics = __dep_packages.Diagnostics
_read_source = __dep_packages._read_source
rel = __dep_packages.rel

from tools.validate_support import common as __dep_common
ROLE_PROFILES = __dep_common.ROLE_PROFILES
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
re = __dep_common.re

# Every shipped prose tree is recursive; depth does not change a call edge.
NAME_CHECKED_TREES = (
    "rules", "docs", "contracts", "templates", "compositions", "packs", "skills"
)
NAME_CHECKED_FILES = ("README.md", "DESIGN.md", "ARCHITECTURE.md", "AGENTS.md", "TICKETS.md")
# `orch-` alone is the prefix, not a name; a name carries at least one
# segment after it. Plain text is how the library says "mentioned, not
# called" (rule 2 again), so DESIGN.md's supersession history needs no
# allowlist -- it just does not backtick the names it is burying.
BACKTICKED_NAME_RE = re.compile(r"`(orch-[a-z0-9]+(?:-[a-z0-9]+)*)`")
# The lens cell is a pointer into a section, and the row is compared as
# three words of text (see CELL_CLAUSE_MIN_WORDS above) rather than
# resolved -- so nothing looked at whether the section is there.
# The marker that says this tree is the library and not an isolated
# fixture. Same idiom as validate_friction_locations' owner check: a
# fixture copies the real contracts/ beside a synthetic skills/, and
# resolving one against the other would convict the contracts for the
# fixture's own emptiness. ARCHITECTURE.md is the tier map, so a tree
# without it has no tier map for a name to resolve against.
NAME_CHECK_MARKER = ROOT / "ARCHITECTURE.md"
LENS_ROW_RE = re.compile(r"^\|\s*lens\s*\|(.*)\|\s*$", re.MULTILINE)
LENS_ANCHOR_RE = re.compile(r"\(([^)]*#[^)]*)\)")
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
    known = {pkg["path"].name for pkg in packages} | set(ROLE_PROFILES)
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


def validate_lens_anchor(packages, diag: Diagnostics) -> None:
    """Each pack's lens cell anchor lands on a heading that exists.

    contracts/pack-signature.md binds the lens to `orch-critique` plus the
    pack's craft `## Lens`, and every gate lane the pack stamps reads its
    criteria there. Deleting the heading left the validator at exit 0.
    """

    for pkg in packages:
        if not pkg["is_pack"]:
            continue
        row = LENS_ROW_RE.search(pkg.get("body") or "")
        if row is None:
            continue  # a missing cell is validate_pack_signature's finding
        file_label = rel(pkg["skill_md"])
        for target in LENS_ANCHOR_RE.findall(row.group(1)):
            relative, _, anchor = target.partition("#")
            craft = (pkg["skill_md"].parent / relative).resolve()
            if not craft.is_file():
                diag.error(
                    file_label,
                    f"lens cell anchor `{target}` names no file at "
                    f"{relative} beside this pack",
                )
                continue
            if anchor.lower() not in _heading_slugs(_read_source(craft)):
                diag.error(
                    file_label,
                    f"lens cell anchor `{target}` lands nowhere: "
                    f"{rel(craft)} carries no heading reached by "
                    f"`#{anchor}` — the cell binds a `## Lens` section, so "
                    "that section has to be there",
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
    'NAME_CHECK_MARKER', 'LENS_ROW_RE', 'LENS_ANCHOR_RE', 'HEADING_RE',
    '_heading_slugs', 'validate_names', 'validate_lens_anchor', 'validate_unique_names',
)
