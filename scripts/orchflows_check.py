#!/usr/bin/env python3
"""`orchflows check`: the library compiler's item checks, asked about a ring.

`tools/validate.py` answers one question about the library -- is every item
here well formed? -- and a ring holds the same kinds of item under a user's
own directory. So this asks that question by calling those functions: the
refusal a ring author reads is the same sentence, from the same line, a
contributor reads from the compiler. No bound and no wording lives here.

Two things differ between a ring and the library, and only two.

A ring keeps one flat directory per kind (`scripts/rings.py`'s `RING_DIRS`)
where the library keeps skill tiers and two workflow homes, so discovery is
this module's and the checks are told where to look.

A ring item's `orch-` call edges point out of the ring and into the library,
so the names an edge may resolve to are every name that resolves from here,
not the ring's own -- grading a ring against itself alone would refuse
`orch-do`.

What is *not* asked is as deliberate. A ring skill is an applied skill: a
host's own artifact a kernel verb wraps as its method, not a kernel-tier
skill. The library's `role` key, its Require/Never/Return anatomy and its
tier word budget are therefore not its law -- `orchflows new skill` writes
none of the three, and the home ring's own `super-research` body is 672
words against a 450-word tier budget. Its frontmatter is still graded,
because a name that does not match its folder is an item the host reads
under a name nothing resolves. A ring pack, workflow and sheet are the same
kinds of thing the library ships and take the library's checks whole.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts import rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings


def support():
    """`(names, packages, sheets, structure)`, from this checkout or the install.

    One package under two parents. `scripts/rings.py` already owns which
    library this process reads -- a checkout, else the installed `lib/` --
    and the package sits inside it either way: under `tools/` in a
    checkout, directly under `lib/` in an install
    (`installer/planning_support.py` puts it there). Every import inside it
    is relative, so the two names are the same modules and neither is a
    copy of the other.
    """

    library = str(rings.lib_root())
    if library not in sys.path:
        sys.path.insert(0, library)
    try:
        from tools.validate_support import names, packages, sheets, structure
    except ImportError:  # pragma: no cover - direct/installed flat script path
        from validate_support import names, packages, sheets, structure
    return names, packages, sheets, structure


def ring_at(argument=None) -> Path:
    """The ring to grade: the directory named, else this project's, else home.

    A named directory that is not itself a ring but holds one resolves to
    the bundle inside it. That is what a person standing in their own
    repository types, and `<repo>` and `<repo>/.orchflows` name one ring.
    """

    if not argument:
        bundle = rings.project_ring()
        return bundle if bundle is not None else rings.home_ring()
    named = Path(argument).expanduser().resolve()
    inside = named / rings.BUNDLE_DIR
    if inside.is_dir() and not any(
        (named / directory).is_dir() for directory in rings.RING_DIRS.values()
    ):
        return inside
    return named


def items(ring: Path, kind: str):
    """Every `(directory, manifest)` of one kind in this ring, by name.

    A directory without the kind's manifest is data rather than an item,
    the same reading `tools/validate_support/packages.py` gives a tier
    directory that holds only references.
    """

    directory = ring / rings.RING_DIRS[kind]
    if not directory.is_dir():
        return []
    found = []
    for entry in sorted(directory.iterdir()):
        manifest = entry / rings.MANIFESTS[kind]
        if entry.is_dir() and rings.NAME_RE.fullmatch(entry.name) and manifest.is_file():
            found.append((entry, manifest))
    return found


def _ordered(paths):
    """The paths in order, each once: two rings can name one directory."""

    seen, ordered = set(), []
    for path in paths:
        marker = str(path).casefold()
        if marker not in seen:
            seen.add(marker)
            ordered.append(path)
    return ordered


def _roots(ring: Path, kind: str):
    """This ring's directory for a kind, then every other that resolves."""

    return _ordered(
        [ring / rings.RING_DIRS[kind]]
        + [root for _ring, root in rings.item_roots(kind)]
    )


def resolvable_names(ring: Path) -> set:
    """Every item name a call edge in this ring may resolve to.

    The ring's own items and everything else `scripts/rings.py` resolves
    from here, which is the set a dispatch will resolve against: a ring
    item calls the library by name, and the library never calls back.
    """

    found = set()
    for kind in rings.KINDS:
        for root in _roots(ring, kind):
            try:
                entries = sorted(path for path in root.iterdir() if path.is_dir())
            except OSError:
                continue
            found.update(
                path.name for path in entries
                if (path / rings.MANIFESTS[kind]).is_file()
            )
    return found


def _package(directory: Path, manifest: Path, kind: str) -> dict:
    """One ring item in the shape the compiler's checks take a package in."""

    return {
        "path": directory,
        "skill_md": manifest,
        "kind": kind,
        "is_pack": kind == "pack",
    }


def _grade(ring: Path, diag, names, packages, sheets, structure) -> dict:
    """Run every check over the ring, and return what each kind counted."""

    counted = {}
    graded = []
    for kind in rings.KINDS:
        found = items(ring, kind)
        counted[kind] = len(found)
        if kind == "sheet":
            continue  # a sheet has no body and its own checks below
        for directory, manifest in found:
            pkg = _package(directory, manifest, kind)
            fm, body = packages.parse_frontmatter(
                packages._read_source(manifest), packages.rel(manifest), diag,
            )
            if fm is None or body is None:
                continue
            pkg["frontmatter"], pkg["body"] = fm, body
            graded.append(pkg)
            if kind == "workflow":
                continue  # validate_templates grades a workflow's frontmatter
            packages.validate_frontmatter(fm, pkg, diag)
            if kind != "pack":
                continue
            packages.validate_role(fm, pkg, diag)
            packages.validate_anatomy(body, pkg, diag)
            packages.validate_budget(body, pkg, diag)
            packages.validate_pack_signature(body, pkg, diag)
            structure.validate_craft_budget(pkg, diag)
    names.validate_craft_sections(graded, diag)
    structure.validate_templates(diag, roots=[ring / rings.RING_DIRS["workflow"]])
    sheets.validate_sheets(diag, pack_roots=_roots(ring, "pack"))
    structure.validate_call_graph(graded, diag, known=resolvable_names(ring))
    return counted


def check(ring: Path):
    """`(diagnostics, counts)` for one ring, graded by the library's checks.

    The check functions read a module-level root, which is the seam
    `tools/validate.py` uses to point them at a tree; it is bound to the
    ring for the duration and restored, so every file label a finding
    carries is relative to the ring the reader asked about.
    """

    names, packages, sheets, structure = support()
    modules = (names, packages, sheets, structure)
    diag = packages.Diagnostics()
    saved = [module.ROOT for module in modules]
    for module in modules:
        module.ROOT = ring
    try:
        counted = _grade(ring, diag, names, packages, sheets, structure)
    finally:
        for module, root in zip(modules, saved):
            module.ROOT = root
    return diag, counted


__all__ = (
    "check", "items", "resolvable_names", "ring_at", "support",
)
