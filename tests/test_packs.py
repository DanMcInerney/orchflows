"""Pack resolution and the content-addressed collapsed-standard shape.

One manifest, `adapter` in frontmatter, identity over the directory tree.
The retired two-row cells table and the second file its `craft` cell named
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

from scripts import packs, rings, rings_trust, state_root


from tests._repo_root import ROOT
PACKS = ROOT / "packs"


@contextlib.contextmanager
def _home():
    """A temporary orchflows home, so no test writes the real trust ledger."""

    with tempfile.TemporaryDirectory(prefix="orchflows-home-") as tmp:
        home = Path(tmp).resolve()
        with patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
            yield home


def _trust(bundle: Path) -> None:
    rings_trust.grant(bundle)


def _named_pack(pack_dir: Path, name: str) -> None:
    """Rename a copied pack so it carries a name outside the reserved floor."""

    skill = pack_dir / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("name: orch-code-pack", f"name: {name}"),
        encoding="utf-8",
    )


def _copy_pack(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_file():
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


def _copy_pack_with_contract(source: Path, target: Path, root: Path) -> None:
    """Copy one pack and give its *ring* a copy of the standard contract.

    The copy lands beside the ring's item directories, never inside one, so
    it is exactly the self-supplied well-formedness document FM-2 refuses to
    let feed identity.
    """

    _copy_pack(source, target)
    del root
    destination = target.parent.parent / "contracts" / "standard.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "contracts" / "standard.md", destination)


class PackResolutionTests(unittest.TestCase):
    def test_public_facade_uses_same_family_resolver_owner(self):
        self.assertEqual("scripts.packs_support", packs._support.__name__)
        self.assertEqual("scripts.packs", packs.resolve_pack.__module__)
        self.assertEqual("packs_support", packs._support.resolve_pack.__module__.split(".")[-1])

    def test_public_facade_does_not_reexport_private_support_names(self):
        """Derived rather than listed: a private name added to the support
        module joins this ratchet without anyone remembering to add it."""

        private = {
            name for name in vars(packs._support)
            if name.startswith("_") and not name.startswith("__")
        }

        self.assertTrue(private, "the support module carries no private names")
        self.assertEqual(set(), private & set(vars(packs)))

    def test_a_real_standard_resolves_to_one_frontmatter_adapter(self):
        """The collapsed shape: no cells table, no second file, and the
        adapter is the one typed leaf the resolver reports."""

        result = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)

        self.assertEqual("orch-code-pack", result["pack"])
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
            pack_root = root / "packs"
            standard = pack_root / "sample-pack"
            _copy_pack_with_contract(PACKS / "orch-code-pack", standard, root)
            _named_pack(standard, "sample-pack")
            before = packs.resolve_pack("sample-pack", canonical_root=pack_root)["digest"]

            manifest = standard / "SKILL.md"
            original = manifest.read_bytes()
            manifest.write_bytes(original + b"\nchanged\n")
            changed = packs.resolve_pack("sample-pack", canonical_root=pack_root)["digest"]
            manifest.write_bytes(original)

            added = standard / "references" / "notes.md"
            added.parent.mkdir(parents=True, exist_ok=True)
            added.write_bytes(b"a file the standard did not carry\n")
            grown = packs.resolve_pack("sample-pack", canonical_root=pack_root)["digest"]
            added.unlink()
            added.parent.rmdir()
            restored = packs.resolve_pack("sample-pack", canonical_root=pack_root)["digest"]

            self.assertNotEqual(before, changed)
            self.assertNotEqual(before, grown)
            self.assertNotEqual(changed, grown)
            self.assertEqual(before, restored)

    def test_the_library_standard_contract_byte_changes_the_digest(self):
        """The library's own well-formedness contract is in the identity, so
        the digest moves when it does. `_signature_digest()` returning
        `None` -- what it did once `contracts/pack-signature.md` was deleted
        -- would make two `None`s compare equal and this check vacuous, so
        the live reading is asserted non-empty first."""

        self.assertIsNotNone(packs._support._signature_digest())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            pack_root = root / "packs"
            _copy_pack(PACKS / "orch-code-pack", pack_root / "sample-pack")
            _named_pack(pack_root / "sample-pack", "sample-pack")
            library = root / "lib"
            (library / "contracts").mkdir(parents=True)
            contract = library / "contracts" / "standard.md"
            shutil.copyfile(ROOT / "contracts" / "standard.md", contract)

            with patch.object(rings, "lib_root", return_value=library):
                self.assertIsNotNone(packs._support._signature_digest())
                before = packs.resolve_pack("sample-pack", canonical_root=pack_root)
                contract.write_bytes(contract.read_bytes() + b"\ncontract change\n")
                after = packs.resolve_pack("sample-pack", canonical_root=pack_root)

            self.assertNotEqual(before["digest"], after["digest"])

    def test_a_ring_relative_standard_contract_feeds_no_digest(self):
        """FM-2: the document that decides whether a standard is well formed
        is never readable from the standard's own ring. A ring shipping its
        own copy of that contract used to feed its own item's identity."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            pack_root = root / "packs"
            _copy_pack_with_contract(PACKS / "orch-code-pack", pack_root / "sample-pack", root)
            _named_pack(pack_root / "sample-pack", "sample-pack")
            before = packs.resolve_pack("sample-pack", canonical_root=pack_root)

            contract = root / "contracts" / "standard.md"
            contract.write_bytes(contract.read_bytes() + b"\nself-supplied\n")
            after = packs.resolve_pack("sample-pack", canonical_root=pack_root)

            self.assertEqual(before["digest"], after["digest"])

    def test_project_ring_with_identical_bytes_has_the_same_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / "canonical" / "packs"
            project = root / "project"
            _copy_pack_with_contract(PACKS / "orch-code-pack", canonical / "sample-pack", root)
            _named_pack(canonical / "sample-pack", "sample-pack")
            _copy_pack(PACKS / "orch-code-pack", project / ".orchflows" / "packs" / "sample-pack")
            _named_pack(project / ".orchflows" / "packs" / "sample-pack", "sample-pack")
            with _home():
                _trust(project / ".orchflows")
                resolved = packs.resolve_pack(
                    "sample-pack",
                    canonical_root=canonical,
                    project_root=project,
                )
            expected = packs.resolve_pack("sample-pack", canonical_root=canonical)

            self.assertEqual("project", resolved["scope"])
            self.assertEqual(expected["digest"], resolved["digest"])
            self.assertEqual(
                [
                    "shadow: pack 'sample-pack' resolves from the project ring "
                    f"at {resolved['path']} and shadows lib "
                    # The resolver canonicalizes roots (containment guards need
                    # real paths); /var vs /private/var and 8.3 short names on
                    # the CI runners diverge from the raw tempdir spelling.
                    f"{(canonical / 'sample-pack' / 'SKILL.md').resolve()}"
                ],
                resolved["notices"],
            )

    def test_project_ring_is_discovered_from_the_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_pack = project / ".orchflows" / "packs" / "sample-pack"
            _copy_pack(PACKS / "orch-code-pack", project_pack)
            _named_pack(project_pack, "sample-pack")

            with _home():
                _trust(project / ".orchflows")
                with patch.object(rings.Path, "cwd", return_value=project):
                    # The resolver's default ring is intentionally cwd-based
                    # so the CLI works without a project-root flag.
                    resolved = packs.resolve_pack("sample-pack", canonical_root=PACKS)

            self.assertEqual("project", resolved["scope"])

    def test_a_reserved_name_in_a_ring_is_refused_loudly(self):
        """`orch-*` is the mechanical floor: a ring copy neither shadows the
        library name nor silently never runs -- it refuses, naming itself."""

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            _copy_pack(PACKS / "orch-code-pack", project / ".orchflows" / "packs" / "orch-code-pack")

            with self.assertRaises(packs.PackError) as raised:
                packs.resolve_pack(
                    "orch-code-pack", canonical_root=PACKS, project_root=project,
                )

            self.assertEqual("pack-reserved", raised.exception.code)
            self.assertIn("reserved 'orch-' prefix", raised.exception.detail)

    def test_an_untrusted_project_bundle_refuses_with_the_two_step_remedy(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_pack = project / ".orchflows" / "packs" / "sample-pack"
            _copy_pack(PACKS / "orch-code-pack", project_pack)
            _named_pack(project_pack, "sample-pack")

            with _home(), self.assertRaises(packs.PackError) as raised:
                packs.resolve_pack(
                    "sample-pack", canonical_root=PACKS, project_root=project,
                )

            self.assertEqual("pack-untrusted", raised.exception.code)
            self.assertIn(f"orchflows trust --once {project / '.orchflows'}", raised.exception.detail)
            self.assertIn(f"orchflows trust {project / '.orchflows'}", raised.exception.detail)

    def test_a_use_once_grant_is_spent_by_the_resolution_it_allows(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_pack = project / ".orchflows" / "packs" / "sample-pack"
            _copy_pack(PACKS / "orch-code-pack", project_pack)
            _named_pack(project_pack, "sample-pack")
            with _home() as home:
                rings_trust.grant(project / ".orchflows", once=True, home=home)

                first = packs.resolve_pack(
                    "sample-pack", canonical_root=PACKS, project_root=project,
                )
                self.assertEqual("project", first["scope"])
                with self.assertRaises(packs.PackError):
                    packs.resolve_pack(
                        "sample-pack", canonical_root=PACKS, project_root=project,
                    )

    def test_a_bundle_edit_invalidates_the_remembered_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            project_pack = project / ".orchflows" / "packs" / "sample-pack"
            _copy_pack(PACKS / "orch-code-pack", project_pack)
            _named_pack(project_pack, "sample-pack")
            with _home():
                _trust(project / ".orchflows")
                packs.resolve_pack(
                    "sample-pack", canonical_root=PACKS, project_root=project,
                )
                manifest = project_pack / "SKILL.md"
                manifest.write_bytes(manifest.read_bytes() + b"\nchanged\n")
                with self.assertRaises(packs.PackError) as raised:
                    packs.resolve_pack(
                        "sample-pack", canonical_root=PACKS, project_root=project,
                    )
            self.assertEqual("pack-untrusted", raised.exception.code)

    def test_line_endings_across_the_tree_do_not_change_standard_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left"
            right = root / "right"
            for target in (left, right):
                _copy_pack_with_contract(PACKS / "orch-code-pack", target / "sample-pack", root)
                skill = target / "sample-pack" / "SKILL.md"
                skill.write_bytes(
                    skill.read_bytes()
                    .replace(b"\r\n", b"\n")
                    .replace(b"name: orch-code-pack", b"name: sample-pack")
                )
            for path in right.rglob("*"):
                if path.is_file():
                    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

            self.assertEqual(
                packs.resolve_pack("sample-pack", canonical_root=left)["digest"],
                packs.resolve_pack("sample-pack", canonical_root=right)["digest"],
            )

    def test_cells_projects_the_standard_the_resolved_digest_identifies(self):
        """One projection: every verb reads the same manifest, so what a
        digest projects to is the standard and its one adapter — there is no
        lane to omit a section from and no second file to point at."""

        resolved = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)

        projected = packs.cells_for(resolved["digest"], canonical_root=PACKS)

        self.assertEqual(
            {"pack", "scope", "digest", "adapter"}, set(projected),
        )
        self.assertEqual("orch-code-pack", projected["pack"])
        self.assertEqual(resolved["digest"], projected["digest"])
        self.assertEqual("git", projected["adapter"])

    def test_every_standard_resolves_a_distinct_root_lens_entry(self):
        """Prose earns a section only when its content differs between
        standards (contracts/standard.md, Admission). The `### root` entry is
        read off the manifest now: the collapse folded the craft document
        into it, so there is one document to read and one place to differ."""

        import re

        bodies = {}
        for name in sorted(path.parent.name for path in PACKS.glob("*/SKILL.md")):
            resolved = packs.resolve_pack(name, canonical_root=PACKS)
            self.assertTrue(resolved["adapter"], f"{name} declares no adapter")
            text = (PACKS / name / "SKILL.md").read_text(encoding="utf-8")
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
        command = [sys.executable, str(ROOT / "scripts" / "packs.py")]
        resolved = subprocess.run(
            command + ["resolve", "orch-code-pack", "--canonical-root", str(PACKS)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, resolved.returncode, resolved.stderr)
        payload = json.loads(resolved.stdout)
        projected = subprocess.run(
            command + ["cells", payload["digest"], "--canonical-root", str(PACKS)],
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
                "--canonical-root", str(PACKS),
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
        command = [sys.executable, str(ROOT / "scripts" / "packs.py")]
        result = subprocess.run(
            command + ["resolve", "orch-code-pack", "--canonical", str(PACKS)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_root_keyword_is_not_a_resolver_compatibility_alias(self):
        with self.assertRaises(TypeError):
            packs.resolve_pack("orch-code-pack", root=PACKS)


class PackShapeRefusalTests(unittest.TestCase):
    def test_a_manifest_still_carrying_the_retired_cells_table_is_refused(self):
        """The half-migrated shape: `adapter` moved to frontmatter and the
        table was deleted, so a manifest still carrying one is refused
        rather than resolved as if the rows were not there."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "packs"
            _copy_pack_with_contract(PACKS / "orch-code-pack", root / "bad-pack", Path(tmp))
            skill = root / "bad-pack" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "name: orch-code-pack", "name: bad-pack"
                ).replace(
                    "## Making",
                    "| Cell | Binding |\n| --- | --- |\n| adapter | git |\n"
                    "| craft | [craft](references/craft.md) |\n\n## Making",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(packs.PackError) as raised:
                packs.resolve_pack("bad-pack", canonical_root=root)

            self.assertEqual("pack-shape-invalid", raised.exception.code)
            self.assertIn("| Cell | Binding |", raised.exception.detail)

    def test_the_retired_cells_table_is_refused_on_the_chain_walk_too(self):
        """The chain walk is the live door -- `tickets_pins` pins through it
        -- so the refusal has to bite there and not only in `resolve_pack`."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "packs"
            _copy_pack(PACKS / "orch-code-pack", root / "bad-pack")
            skill = root / "bad-pack" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "name: orch-code-pack", "name: bad-pack"
                ) + "\n| Cell | Binding |\n| --- | --- |\n| adapter | git |\n",
                encoding="utf-8",
            )
            with self.assertRaises(packs.PackError) as raised:
                packs.resolve_chain(["bad-pack"], lib_dir=root)

            self.assertEqual("pack-shape-invalid", raised.exception.code)

    def test_a_frontmatter_adapter_naming_an_unregistered_key_is_refused(self):
        """Registration is `tickets_adapters.adapter_for_key`'s, called from
        the resolver rather than re-tested there."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "packs"
            _copy_pack(PACKS / "orch-code-pack", root / "bad-pack")
            skill = root / "bad-pack" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8")
                .replace("name: orch-code-pack", "name: bad-pack")
                .replace("adapter: git", "adapter: quantum-tree"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(packs.PackError, "unregistered adapter"):
                packs.resolve_pack("bad-pack", canonical_root=root)

    def test_unknown_digest_and_consumer_are_closed_refusals(self):
        with self.assertRaisesRegex(packs.PackError, "does not resolve"):
            packs.cells_for("sha256:" + "0" * 64, canonical_root=PACKS)
        resolved = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)
        # The lane keyword is deleted, not aliased: a legacy caller refuses.
        with self.assertRaises(TypeError):
            packs.cells_for(resolved["digest"], canonical_root=PACKS, consumer="check")


if __name__ == "__main__":
    unittest.main()
