#!/usr/bin/env python3
"""`orchflows check`: the library compiler's item checks, asked about a ring.

`tools/validate.py` answers one question about the library -- is every item
here well formed? -- and a ring holds the same kinds of item under a user's
own directory. So this asks that question by calling those functions: the
refusal a ring author reads is the same sentence, from the same line, a
contributor reads. No bound and no wording lives here.

Two things differ. A ring keeps one flat directory per kind
(`scripts/rings.py`'s `RING_DIRS`) where the library keeps skill tiers and
two workflow homes, so discovery is this module's. And a ring item's
`orch-` call edges point into the library, so the names an edge may
resolve to are every name that resolves from here, not the ring's own.

A ring skill is an applied skill, so the library's Require/Never/Return
anatomy and its tier word budget are not its law. Its frontmatter is
graded, because a name that does not match its folder resolves nothing;
and its `role` is graded against the two an applied skill may declare,
because `--skill` reads that field and a ring skill without one would pass
here and be refused at dispatch. A ring pack, workflow and sheet take the
library's checks whole.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from scripts import orchflows_envs, orchflows_tools, rings, rings_trust
except ImportError:  # pragma: no cover - direct/installed flat script path
    import orchflows_envs
    import orchflows_tools
    import rings
    import rings_trust


def support():
    """`(bundle, names, packages, sheets, structure, tooling)`, checkout or install."""

    library = str(rings.lib_root())
    if library not in sys.path:
        sys.path.insert(0, library)
    try:
        from tools.validate_support import (
            bundle, names, packages, sheets, structure, tooling,
        )
    except ImportError:  # pragma: no cover - direct/installed flat script path
        from validate_support import (
            bundle, names, packages, sheets, structure, tooling,
        )
    return bundle, names, packages, sheets, structure, tooling


def ring_at(argument=None) -> Path:
    """The ring to grade: the directory named, else this project's, else home."""

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
    """Every `(directory, manifest)` of one kind in this ring, by name."""

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
    """Every item name a call edge in this ring may resolve to."""

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


def _folded(path) -> str:
    """One spelling of a path, for comparing two a caller spelled differently."""

    try:
        return str(Path(path).resolve()).casefold()
    except OSError:  # pragma: no cover - an unreadable path
        return str(path).casefold()


def _imported(ring: Path) -> bool:
    """Whether `imports.lock` pins this bundle."""

    home = rings.home_ring()
    folded = _folded(ring)
    return any(
        _folded(home / rings.IMPORTS_DIR / record["name"] / rings.BUNDLE_DIR) == folded
        for record in rings.read_imports(home)
    )


def _untrusted(ring: Path):
    """The ring, unless this is content its user has already accepted."""

    if _folded(ring) == _folded(rings.home_ring()):
        return None
    if _imported(ring):
        return None
    return None if rings_trust.state(ring)["trusted"] else ring


def _tooling(ring: Path, diag, declaring, packages) -> None:
    """Every declared tool or variable this machine is missing, with its line."""

    untrusted = _untrusted(ring)
    for kind, directory in declaring:
        if kind == "sheet":
            continue  # `validate_sheets` has already refused this file's existence
        tools = orchflows_tools.tools_of(directory)
        if tools is None:
            continue
        file_label = packages.rel(tools)
        if untrusted is not None:
            diag.warn(file_label, orchflows_envs.UNTRUSTED_REMEDY.format(
                kind=kind, name=directory.name, bundle=untrusted,
            ))
            continue
        try:
            parsed, _problems = orchflows_tools.declarations(tools)
        except (OSError, UnicodeDecodeError):
            continue  # the grammar pass above already named the unreadable file
        for entry in parsed:
            missing = orchflows_tools.resolve(entry)
            if missing is not None:
                diag.error(file_label, f"line {entry['line']}: {missing}")


def _grade(ring: Path, diag, bundle, names, packages, sheets, structure, tooling) -> dict:
    """Run every check over the ring, and return what each kind counted."""

    counted = {}
    graded = []
    declaring = []
    for kind in rings.KINDS:
        found = items(ring, kind)
        counted[kind] = len(found)
        declaring.extend((kind, directory) for directory, _manifest in found)
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
            if kind == "skill":
                packages.validate_role(
                    fm, pkg, diag, allowed=packages.APPLIED_ROLE_VALUES,
                )
                continue
            if kind != "pack":
                continue
            packages.validate_role(fm, pkg, diag)
            packages.validate_anatomy(body, pkg, diag)
            sheets.validate_standard_adapter(fm, pkg, diag)
            structure.validate_craft_budget(manifest, diag)
    names.validate_craft_sections(graded, diag)
    structure.validate_templates(diag, roots=[ring / rings.RING_DIRS["workflow"]])
    sheets.validate_sheets(diag, pack_roots=_roots(ring, "pack"))
    structure.validate_call_graph(graded, diag, known=resolvable_names(ring))
    # A `tools.txt` is a declaration `orchflows sync` reads before a run; a
    # line its parser cannot read is a tool nobody is told is missing. The
    # ring keeps no tiers, so the directories walked above are handed over.
    tooling.validate_tools_declarations(
        diag, item_dirs=[directory for _kind, directory in declaring],
    )
    _tooling(ring, diag, declaring, packages)
    # A ring is a bundle directory, so its manifest sits at the ring root.
    bundle.validate_bundle_manifest(diag, bundle=ring)
    return counted


def check(ring: Path):
    """`(diagnostics, counts)` for one ring, graded by the library's checks."""

    bundle, names, packages, sheets, structure, tooling = support()
    modules = (bundle, names, packages, sheets, structure, tooling)
    diag = packages.Diagnostics()
    saved = [module.ROOT for module in modules]
    for module in modules:
        module.ROOT = ring
    try:
        counted = _grade(
            ring, diag, bundle, names, packages, sheets, structure, tooling,
        )
    finally:
        for module, root in zip(modules, saved):
            module.ROOT = root
    return diag, counted


__all__ = (
    "check", "items", "resolvable_names", "ring_at", "support",
)
