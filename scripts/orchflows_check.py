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
skill. The library's Require/Never/Return anatomy and its tier word budget
are therefore not its law -- `orchflows new skill` writes neither, and the
home ring's own `super-research` body is 672 words against a 450-word tier
budget. Its frontmatter is graded, because a name that does not match its
folder is an item the host reads under a name nothing resolves; and its
`role` is graded against the two an applied skill may declare, because
`--skill` reads that field to establish the child and a ring skill without
one would pass here and be refused at dispatch. A ring pack, workflow and
sheet are the same kinds of thing the library ships and take the library's
checks whole.
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
    """`(bundle, names, packages, sheets, structure, tooling)`, checkout or install.

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
        from tools.validate_support import (
            bundle, names, packages, sheets, structure, tooling,
        )
    except ImportError:  # pragma: no cover - direct/installed flat script path
        from validate_support import (
            bundle, names, packages, sheets, structure, tooling,
        )
    return bundle, names, packages, sheets, structure, tooling


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


def _untrusted(ring: Path):
    """The ring, when it is a project bundle the trust ledger does not trust.

    Reading a declaration is inert and resolving a name on `PATH` runs
    nothing, but a `::` probe is the item's own command. `scripts/rings.py`
    holds a *project* ring alone to the ledger -- home, imports and library
    content is inherent -- so that is the one ring whose probes wait for a
    grant, and it waits with `orchflows sync`'s own remedy rather than a
    second sentence.
    """

    project = rings.project_ring()
    if project is None or str(project).casefold() != str(ring).casefold():
        return None
    return None if rings_trust.state(ring)["trusted"] else ring


def _tooling(ring: Path, diag, declaring, packages) -> None:
    """Every declared tool or variable this machine is missing, with its line.

    The grammar half is the library's, already reported by
    `tooling.validate_tools_declarations`. This is the other half, and it is
    the half a ring author came for: `orchflows sync` resolves each
    declaration before a run, and a `check` that stayed silent about a tool
    that is not here would pass a ring no run can use. The resolver is
    `sync`'s, so the sentence and the line a reader gets are the same at
    both doors; only the surrounding format is each door's own.
    """

    untrusted = _untrusted(ring)
    for kind, directory in declaring:
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
            packages.validate_budget(body, pkg, diag)
            packages.validate_pack_signature(body, pkg, diag)
            structure.validate_craft_budget(pkg, diag)
    names.validate_craft_sections(graded, diag)
    structure.validate_templates(diag, roots=[ring / rings.RING_DIRS["workflow"]])
    sheets.validate_sheets(diag, pack_roots=_roots(ring, "pack"))
    structure.validate_call_graph(graded, diag, known=resolvable_names(ring))
    # A `tools.txt` is a declaration `orchflows sync` reads before a run; a
    # line its parser cannot read is a tool nobody is told is missing. The
    # ring keeps no tiers, so the directories walked above are handed over
    # rather than rediscovered.
    tooling.validate_tools_declarations(
        diag, item_dirs=[directory for _kind, directory in declaring],
    )
    _tooling(ring, diag, declaring, packages)
    # A ring is a bundle directory, so its manifest sits at the ring root.
    bundle.validate_bundle_manifest(diag, bundle=ring)
    return counted


def check(ring: Path):
    """`(diagnostics, counts)` for one ring, graded by the library's checks.

    The check functions read a module-level root, which is the seam
    `tools/validate.py` uses to point them at a tree; it is bound to the
    ring for the duration and restored, so every file label a finding
    carries is relative to the ring the reader asked about.
    """

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
