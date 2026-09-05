"""Standard resolution and the content-addressed collapsed-standard shape.

One manifest, `adapter` in frontmatter, identity over the directory tree.
The retired two-row cells table and the second file its `standard` cell named
are gone, and a manifest still carrying that table refuses here.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import standards, rings, rings_trust, state_root, tickets_pins


from tests._repo_root import ROOT
STANDARDS = ROOT / "standards"


@contextlib.contextmanager
def _home():
    """A temporary orchflows home, so no test writes the real trust ledger."""

    with tempfile.TemporaryDirectory(prefix="orchflows-home-") as tmp:
        home = Path(tmp).resolve()
        with patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
            yield home


def _trust(bundle: Path) -> None:
    rings_trust.grant(bundle)


def _named_standard(standard_dir: Path, name: str) -> None:
    """Rename a copied standard so it carries a name outside the reserved floor."""

    skill = standard_dir / "STANDARD.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("name: orch-code", f"name: {name}"),
        encoding="utf-8",
    )


def _copy_standard(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_file():
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


def _copy_standard_with_contract(source: Path, target: Path, root: Path) -> None:
    """Copy one standard and give its *ring* a copy of the standard contract.

    The copy lands beside the ring's item directories, never inside one, so
    it is exactly the self-supplied well-formedness document FM-2 refuses to
    let feed identity.
    """

    _copy_standard(source, target)
    del root
    destination = target.parent.parent / "contracts" / "standard.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "contracts" / "standard.md", destination)


class StandardResolutionTests(unittest.TestCase):
    def test_public_facade_uses_same_family_resolver_owner(self):
        self.assertEqual("scripts.standards_support", standards._support.__name__)
        self.assertEqual("scripts.standards", standards.resolve_standard.__module__)
        self.assertEqual("standards_support", standards._support.resolve_standard.__module__.split(".")[-1])

    def test_public_facade_does_not_reexport_private_support_names(self):
        """Derived rather than listed: a private name added to the support
        module joins this ratchet without anyone remembering to add it."""

        private = {
            name for name in vars(standards._support)
            if name.startswith("_") and not name.startswith("__")
        }

        self.assertTrue(private, "the support module carries no private names")
        self.assertEqual(set(), private & set(vars(standards)))

    def test_a_real_standard_resolves_to_one_frontmatter_adapter(self):
        """The collapsed shape: no cells table, no second file, and the
        adapter is the one typed leaf the resolver reports."""

        result = standards.resolve_standard("orch-code", canonical_root=STANDARDS)

        self.assertEqual("orch-code", result["standard"])
        self.assertEqual("lib", result["scope"])
        self.assertEqual("git", result["adapter"])
        self.assertNotIn("cells", result)
        self.assertNotIn("references", result)
        self.assertRegex(result["digest"], r"^sha256:[0-9a-f]{64}$")

    def test_every_way_the_directory_tree_can_move_moves_the_digest(self):
        """The digest is SHA-256 over the standard's directory tree
        (contracts/standard.md rule 5), so a changed byte, a file added and
        a file deleted are each a different identity."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            standard_root = root / "standards"
            standard = standard_root / "sample-standard"
            _copy_standard_with_contract(STANDARDS / "orch-code", standard, root)
            _named_standard(standard, "sample-standard")
            before = standards.resolve_standard("sample-standard", canonical_root=standard_root)["digest"]

            manifest = standard / "STANDARD.md"
            original = manifest.read_bytes()
            manifest.write_bytes(original + b"\nchanged\n")
            changed = standards.resolve_standard("sample-standard", canonical_root=standard_root)["digest"]
            manifest.write_bytes(original)

            added = standard / "references" / "notes.md"
            added.parent.mkdir(parents=True, exist_ok=True)
            added.write_bytes(b"a file the standard did not carry\n")
            grown = standards.resolve_standard("sample-standard", canonical_root=standard_root)["digest"]
            added.unlink()
            added.parent.rmdir()
            restored = standards.resolve_standard("sample-standard", canonical_root=standard_root)["digest"]

            self.assertNotEqual(before, changed)
            self.assertNotEqual(before, grown)
            self.assertNotEqual(changed, grown)
            self.assertEqual(before, restored)

    def test_public_and_ticket_resolvers_share_one_standard_identity(self):
        """Both public inspection and ticket sealing name the same bytes."""

        public = standards.resolve_standard("orch-code")
        pinned = tickets_pins.resolved("standard", "orch-code")

        self.assertEqual(public["path"], pinned["path"])
        self.assertEqual(public["digest"], pinned["digest"])

    def test_a_ring_relative_standard_contract_feeds_no_digest(self):
        """FM-2: the document that decides whether a standard is well formed
        is never readable from the standard's own ring. A ring shipping its
        own copy of that contract used to feed its own item's identity."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            standard_root = root / "standards"
            _copy_standard_with_contract(STANDARDS / "orch-code", standard_root / "sample-standard", root)
            _named_standard(standard_root / "sample-standard", "sample-standard")
            before = standards.resolve_standard("sample-standard", canonical_root=standard_root)

            contract = root / "contracts" / "standard.md"
            contract.write_bytes(contract.read_bytes() + b"\nself-supplied\n")
            after = standards.resolve_standard("sample-standard", canonical_root=standard_root)

            self.assertEqual(before["digest"], after["digest"])

    def test_project_ring_with_identical_bytes_has_the_same_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / "canonical" / "standards"
            project = root / "project"
            _copy_standard_with_contract(STANDARDS / "orch-code", canonical / "sample-standard", root)
            _named_standard(canonical / "sample-standard", "sample-standard")
            _copy_standard(STANDARDS / "orch-code", project / ".orchflows" / "standards" / "sample-standard")
            _named_standard(project / ".orchflows" / "standards" / "sample-standard", "sample-standard")
            with _home():
                _trust(project / ".orchflows")
                resolved = standards.resolve_standard(
                    "sample-standard",
                    canonical_root=canonical,
                    project_root=project,
                )
            expected = standards.resolve_standard("sample-standard", canonical_root=canonical)

            self.assertEqual("project", resolved["scope"])
            self.assertEqual(expected["digest"], resolved["digest"])
            self.assertEqual(
                [
                    "shadow: standard 'sample-standard' resolves from the project ring "
                    f"at {resolved['path']} and shadows lib "
                    # The resolver canonicalizes roots (containment guards need
                    # real paths); /var vs /private/var and 8.3 short names on
                    # the CI runners diverge from the raw tempdir spelling.
                    f"{(canonical / 'sample-standard' / 'STANDARD.md').resolve()}"
                ],
                resolved["notices"],
            )

    def test_project_ring_is_discovered_from_the_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_standard = project / ".orchflows" / "standards" / "sample-standard"
            _copy_standard(STANDARDS / "orch-code", project_standard)
            _named_standard(project_standard, "sample-standard")

            with _home():
                _trust(project / ".orchflows")
                with patch.object(rings.Path, "cwd", return_value=project):
                    # The resolver's default ring is intentionally cwd-based
                    # so the CLI works without a project-root flag.
                    resolved = standards.resolve_standard("sample-standard", canonical_root=STANDARDS)

            self.assertEqual("project", resolved["scope"])

    def test_a_reserved_name_in_a_ring_is_refused_loudly(self):
        """`orch-*` is the mechanical floor: a ring copy neither shadows the
        library name nor silently never runs -- it refuses, naming itself."""

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            _copy_standard(STANDARDS / "orch-code", project / ".orchflows" / "standards" / "orch-code")

            with self.assertRaises(standards.StandardError) as raised:
                standards.resolve_standard(
                    "orch-code", canonical_root=STANDARDS, project_root=project,
                )

            self.assertEqual("standard-reserved", raised.exception.code)
            self.assertIn("reserved 'orch-' prefix", raised.exception.detail)

    def test_an_untrusted_project_bundle_refuses_with_the_two_step_remedy(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_standard = project / ".orchflows" / "standards" / "sample-standard"
            _copy_standard(STANDARDS / "orch-code", project_standard)
            _named_standard(project_standard, "sample-standard")

            with _home(), self.assertRaises(standards.StandardError) as raised:
                standards.resolve_standard(
                    "sample-standard", canonical_root=STANDARDS, project_root=project,
                )

            self.assertEqual("standard-untrusted", raised.exception.code)
            self.assertIn(f"orchflows trust --once {project / '.orchflows'}", raised.exception.detail)
            self.assertIn(f"orchflows trust {project / '.orchflows'}", raised.exception.detail)

    def test_a_use_once_grant_is_spent_by_the_resolution_it_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_standard = project / ".orchflows" / "standards" / "sample-standard"
            _copy_standard(STANDARDS / "orch-code", project_standard)
            _named_standard(project_standard, "sample-standard")
            with _home() as home:
                rings_trust.grant(project / ".orchflows", once=True, home=home)

                first = standards.resolve_standard(
                    "sample-standard", canonical_root=STANDARDS, project_root=project,
                )
                self.assertEqual("project", first["scope"])
                with self.assertRaises(standards.StandardError):
                    standards.resolve_standard(
                        "sample-standard", canonical_root=STANDARDS, project_root=project,
                    )

    def test_a_bundle_edit_invalidates_the_remembered_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_standard = project / ".orchflows" / "standards" / "sample-standard"
            _copy_standard(STANDARDS / "orch-code", project_standard)
            _named_standard(project_standard, "sample-standard")
            with _home():
                _trust(project / ".orchflows")
                standards.resolve_standard(
                    "sample-standard", canonical_root=STANDARDS, project_root=project,
                )
                manifest = project_standard / "STANDARD.md"
                manifest.write_bytes(manifest.read_bytes() + b"\nchanged\n")
                with self.assertRaises(standards.StandardError) as raised:
                    standards.resolve_standard(
                        "sample-standard", canonical_root=STANDARDS, project_root=project,
                    )
            self.assertEqual("standard-untrusted", raised.exception.code)

    def test_line_endings_across_the_tree_do_not_change_standard_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left"
            right = root / "right"
            for target in (left, right):
                _copy_standard_with_contract(STANDARDS / "orch-code", target / "sample-standard", root)
                skill = target / "sample-standard" / "STANDARD.md"
                skill.write_bytes(
                    skill.read_bytes()
                    .replace(b"\r\n", b"\n")
                    .replace(b"name: orch-code", b"name: sample-standard")
                )
            for path in right.rglob("*"):
                if path.is_file():
                    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

            self.assertEqual(
                standards.resolve_standard("sample-standard", canonical_root=left)["digest"],
                standards.resolve_standard("sample-standard", canonical_root=right)["digest"],
            )

    def test_cells_projects_the_standard_the_resolved_digest_identifies(self):
        """One projection: every verb reads the same manifest, so what a
        digest projects to is the standard and its one adapter — there is no
        lane to omit a section from and no second file to point at."""

        resolved = standards.resolve_standard("orch-code", canonical_root=STANDARDS)

        projected = standards.cells_for(resolved["digest"], canonical_root=STANDARDS)

        self.assertEqual(
            {"standard", "scope", "digest", "adapter"}, set(projected),
        )
        self.assertEqual("orch-code", projected["standard"])
        self.assertEqual(resolved["digest"], projected["digest"])
        self.assertEqual("git", projected["adapter"])

    def test_every_standard_resolves_a_distinct_root_lens_entry(self):
        """Prose earns a section only when its content differs between
        standards (contracts/standard.md, Admission). The `### root` entry is
        read off the manifest now: the collapse folded the standard document
        into it, so there is one document to read and one place to differ."""

        import re

        bodies = {}
        # Roots only: a narrowing is the same kind in the same directory and
        # carries neither an adapter nor a `### root` entry, so `narrows:` is
        # what selects the five this check is about.
        roots = sorted(
            path.parent.name
            for path in STANDARDS.glob("*/STANDARD.md")
            if not re.search(r"(?m)^narrows:", path.read_text(encoding="utf-8"))
        )
        for name in roots:
            resolved = standards.resolve_standard(name, canonical_root=STANDARDS)
            self.assertTrue(resolved["adapter"], f"{name} declares no adapter")
            text = (STANDARDS / name / "STANDARD.md").read_text(encoding="utf-8")
            self.assertNotIn("\n## Outline", text)
            lens = re.search(r"(?ms)^## Lens\s*$(.*?)(?=^## |\Z)", text)
            self.assertIsNotNone(lens, f"{name} carries no ## Lens section")
            match = re.search(r"(?ms)^### root\s*$(.*?)(?=^### |\Z)", lens.group(1))
            self.assertIsNotNone(match, f"{name} carries no `### root` entry")
            bodies[name] = match.group(1).strip()
            self.assertTrue(bodies[name], f"{name} `### root` entry is empty")
        self.assertEqual(5, len(bodies))
        self.assertEqual(len(bodies), len(set(bodies.values())))

    def test_cli_emits_json_for_resolve_and_cells(self):
        command = [sys.executable, str(ROOT / "scripts" / "standards.py")]
        resolved = subprocess.run(
            command + ["resolve", "orch-code", "--canonical-root", str(STANDARDS)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, resolved.returncode, resolved.stderr)
        payload = json.loads(resolved.stdout)
        projected = subprocess.run(
            command + ["cells", payload["digest"], "--canonical-root", str(STANDARDS)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, projected.returncode, projected.stderr)
        self.assertEqual("git", json.loads(projected.stdout)["adapter"])
        lane = subprocess.run(
            command + [
                "cells", payload["digest"], "--for", "check",
                "--canonical-root", str(STANDARDS),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        # The lane flag is deleted, not aliased: a legacy spelling refuses.
        self.assertNotEqual(0, lane.returncode)
        self.assertIn("unrecognized arguments", lane.stderr)

    def test_scope_aliases_are_not_accepted_by_the_resolver_facade(self):
        command = [sys.executable, str(ROOT / "scripts" / "standards.py")]
        result = subprocess.run(
            command + ["resolve", "orch-code", "--canonical", str(STANDARDS)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_root_keyword_is_not_a_resolver_compatibility_alias(self):
        with self.assertRaises(TypeError):
            standards.resolve_standard("orch-code", root=STANDARDS)


class StandardShapeRefusalTests(unittest.TestCase):
    def test_a_manifest_still_carrying_the_retired_cells_table_is_refused(self):
        """The half-migrated shape: `adapter` moved to frontmatter and the
        table was deleted, so a manifest still carrying one is refused
        rather than resolved as if the rows were not there."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "standards"
            _copy_standard_with_contract(STANDARDS / "orch-code", root / "bad-standard", Path(tmp))
            skill = root / "bad-standard" / "STANDARD.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "name: orch-code", "name: bad-standard"
                ).replace(
                    "## Making",
                    "| Cell | Binding |\n| --- | --- |\n| adapter | git |\n"
                    "| standard | [standard](references/standard.md) |\n\n## Making",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(standards.StandardError) as raised:
                standards.resolve_standard("bad-standard", canonical_root=root)

            self.assertEqual("standard-shape-invalid", raised.exception.code)
            self.assertIn("| Cell | Binding |", raised.exception.detail)

    def test_the_retired_cells_table_is_refused_on_the_chain_walk_too(self):
        """The chain walk is the live door -- `tickets_pins` pins through it
        -- so the refusal has to bite there and not only in `resolve_standard`."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "standards"
            _copy_standard(STANDARDS / "orch-code", root / "bad-standard")
            skill = root / "bad-standard" / "STANDARD.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "name: orch-code", "name: bad-standard"
                ) + "\n| Cell | Binding |\n| --- | --- |\n| adapter | git |\n",
                encoding="utf-8",
            )
            with self.assertRaises(standards.StandardError) as raised:
                standards.resolve_chain(["bad-standard"], lib_dir=root)

            self.assertEqual("standard-shape-invalid", raised.exception.code)

    def test_a_frontmatter_adapter_naming_an_unregistered_key_is_refused(self):
        """Registration is `tickets_adapters.adapter_for_key`'s, called from
        the resolver rather than re-tested there."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "standards"
            _copy_standard(STANDARDS / "orch-code", root / "bad-standard")
            skill = root / "bad-standard" / "STANDARD.md"
            skill.write_text(
                skill.read_text(encoding="utf-8")
                .replace("name: orch-code", "name: bad-standard")
                .replace("adapter: git", "adapter: quantum-tree"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(standards.StandardError, "unregistered adapter"):
                standards.resolve_standard("bad-standard", canonical_root=root)

    def test_unknown_digest_and_consumer_are_closed_refusals(self):
        with self.assertRaisesRegex(standards.StandardError, "does not resolve"):
            standards.cells_for("sha256:" + "0" * 64, canonical_root=STANDARDS)
        resolved = standards.resolve_standard("orch-code", canonical_root=STANDARDS)
        # The lane keyword is deleted, not aliased: a legacy caller refuses.
        with self.assertRaises(TypeError):
            standards.cells_for(resolved["digest"], canonical_root=STANDARDS, consumer="check")


if __name__ == "__main__":
    unittest.main()
