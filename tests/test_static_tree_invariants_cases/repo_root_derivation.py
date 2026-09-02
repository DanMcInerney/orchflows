"""Every ``Path(__file__)`` walk that lands at the repository root is owned
or explained (A3, B1.8's repair of the B1.7 seam review).

S1's own acceptance was stated as a grep spelling
(``resolve().parents[`` and its variants), which grades the pattern and not
the fact: a walk one ``.parent`` deep (``install.py``, which sits AT the
root) or chained off an already-resolved name
(``reader/tools/ui_frontend.py``'s ``REPOSITORY_ROOT = ROOT.parent``) never
matched any spelling no matter how many were added. This check states the
acceptance semantically instead: evaluate what each site's expression
actually resolves to, from that file's own real path, and require every site
landing on the repository root to be the production owner
(``scripts/_bootstrap.py``), one of the two test-tree owners
(``tests/_repo_root.py``, ``reader/tests/_repo_root.py``), or a site whose
surrounding lines explain itself in a comment -- the same bar the 22 already
commented production sites already clear.
"""

from __future__ import annotations

import ast
import subprocess
import tempfile
import unittest
from pathlib import Path

from ._support import ROOT

OWNERS = frozenset({
    "scripts/_bootstrap.py",
    "tests/_repo_root.py",
    "reader/tests/_repo_root.py",
})
COMMENT_WINDOW = 8


def _is_path_dunder_file_call(node) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "Path"
        and len(node.args) == 1 and not node.keywords
        and isinstance(node.args[0], ast.Name) and node.args[0].id == "__file__"
    )


def _up_count(node, names: dict):
    """Directory levels an expression climbs from ``__file__``, or ``None``
    if it is not a walk this classifier recognizes -- following a bare name
    back to the module-level assignment that defined it, so a fact chained
    off an already-resolved name (``ROOT.parent``) is still evaluated."""

    if isinstance(node, ast.Call):
        if _is_path_dunder_file_call(node):
            return 0
        if (isinstance(node.func, ast.Attribute) and node.func.attr == "resolve"
                and not node.args and not node.keywords):
            return _up_count(node.func.value, names)
        return None
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        base = _up_count(node.value, names)
        return None if base is None else base + 1
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
            and node.value.attr == "parents"):
        base = _up_count(node.value.value, names)
        index = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
        if base is None or not isinstance(index, ast.Constant) or not isinstance(index.value, int):
            return None
        return base + index.value + 1
    if isinstance(node, ast.Name):
        return names.get(node.id)
    return None


def module_root_sites(source: str):
    """``(lineno, up_count)`` for each site that walks at least one
    directory level up from ``__file__``, module-level name chains
    followed. A bare-name alias (``ROOT = _FACADE_ROOT``) re-exports a
    fact whose own site is already a candidate, so it is not one itself.
    """

    tree = ast.parse(source)
    names, sites = {}, []
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
        elif isinstance(stmt, ast.AnnAssign):
            target = stmt.target
        else:
            continue
        value = getattr(stmt, "value", None)
        if not isinstance(target, ast.Name) or value is None:
            continue
        up = _up_count(value, names)
        if up is None:
            continue
        names[target.id] = up
        if up >= 1 and not isinstance(value, ast.Name):
            sites.append((stmt.lineno, up))
    return sites


def _resolved_directory(file_path: Path, up_count: int):
    parents = file_path.resolve().parents
    return parents[up_count - 1] if up_count - 1 < len(parents) else None


def _carries_exception_comment(source_lines, lineno: int) -> bool:
    window = source_lines[max(0, lineno - 1 - COMMENT_WINDOW):lineno - 1]
    return any(line.strip().startswith("#") for line in window)


def offenders(root: Path, relative_paths):
    """Sites under ``root`` resolving to it that are neither an owner nor
    carry an explanatory comment, as ``"<relative path>:<lineno>"``.

    ``root`` is resolved before anything is compared against it, because the
    site side of that comparison is resolved and a half-resolved comparison
    silently finds nothing. A caller handing a path that is not already
    canonical is the normal case, not the exotic one: a macOS temporary
    directory is ``/var/...`` whose real path is ``/private/var/...``, and a
    Windows CI runner's is an 8.3 short name (``RUNNER~1``) that expands.
    Both made this module's own can-fail test pass vacuously on a developer
    box and fail on two CI platforms.
    """

    root = root.resolve()
    found = []
    for relative in relative_paths:
        source = (root / relative).read_text(encoding="utf-8")
        for lineno, up in module_root_sites(source):
            if _resolved_directory(root / relative, up) != root:
                continue
            if relative in OWNERS:
                continue
            if _carries_exception_comment(source.splitlines(), lineno):
                continue
            found.append(f"{relative}:{lineno}")
    return found


class TestRepoRootDerivationSitesAreOwnedOrExplained(unittest.TestCase):
    """Semantic classifier for S1's acceptance, in place of a grep spelling."""

    def test_every_site_resolving_to_the_repository_root_is_owned_or_commented(self):
        listing = subprocess.run(
            ["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True,
            text=True, check=True,
        ).stdout.splitlines()
        found = offenders(ROOT, listing)
        self.assertEqual(
            [], found,
            "Path(__file__) walk lands at the repository root without an "
            "owner or an explanatory comment:\n" + "\n".join(found),
        )
        # Without this the test passes when the walk finds nothing to walk.
        self.assertGreater(len(listing), 100, "found suspiciously few tracked *.py files")

    def test_the_classifier_fails_on_a_synthetic_uncommented_site(self):
        with tempfile.TemporaryDirectory() as raw:
            fixture_root = Path(raw)
            site = fixture_root / "pkg" / "site.py"
            site.parent.mkdir()
            site.write_text(
                "from pathlib import Path\n"
                "ROOT = Path(__file__).resolve().parent.parent\n",
                encoding="utf-8",
            )
            found = offenders(fixture_root, ["pkg/site.py"])
        self.assertEqual(["pkg/site.py:2"], found)
