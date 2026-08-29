"""Pack resolution and content-addressed cell projections."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import packs


ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"


def _copy_pack(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_file():
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


def _copy_pack_with_contract(source: Path, target: Path, root: Path) -> None:
    _copy_pack(source, target)
    del root
    destination = target.parent.parent / "contracts" / "pack-signature.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "contracts" / "pack-signature.md", destination)


class PackResolutionTests(unittest.TestCase):
    def test_public_facade_uses_same_family_resolver_owner(self):
        self.assertEqual("scripts.packs_support", packs._support.__name__)
        self.assertEqual("scripts.packs", packs.resolve_pack.__module__)
        self.assertEqual("packs_support", packs._support.resolve_pack.__module__.split(".")[-1])

    def test_real_packs_resolve_to_typed_flat_cells_without_skill_bindings(self):
        result = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)

        self.assertEqual("orch-code-pack", result["pack"])
        self.assertEqual("canonical", result["scope"])
        self.assertEqual(
            {
                "adapter",
                "assembly",
                "craft",
                "evidence",
                "lens",
                "required_spec_fields",
                "slicing",
                "stages",
                "workspace",
            },
            set(result["cells"]),
        )
        self.assertNotIn("executor", result["cells"])
        self.assertRegex(result["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual("git", result["cells"]["adapter"])
        self.assertIsInstance(result["cells"]["stages"], list)

    def test_a_referenced_byte_changes_the_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_root = root / "packs"
            _copy_pack_with_contract(PACKS / "orch-code-pack", pack_root / "sample-pack", root)
            skill = pack_root / "sample-pack" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace("name: orch-code-pack", "name: sample-pack"),
                encoding="utf-8",
            )
            before = packs.resolve_pack("sample-pack", canonical_root=pack_root)

            craft = pack_root / "sample-pack" / "references" / "craft.md"
            craft.write_bytes(craft.read_bytes() + b"\nchanged\n")
            after = packs.resolve_pack("sample-pack", canonical_root=pack_root)

            self.assertNotEqual(before["digest"], after["digest"])

    def test_signature_contract_byte_changes_the_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_root = root / "packs"
            _copy_pack_with_contract(PACKS / "orch-code-pack", pack_root / "sample-pack", root)
            skill = pack_root / "sample-pack" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace("name: orch-code-pack", "name: sample-pack"),
                encoding="utf-8",
            )
            before = packs.resolve_pack("sample-pack", canonical_root=pack_root)
            contract = root / "contracts" / "pack-signature.md"
            contract.write_bytes(contract.read_bytes() + b"\ncontract change\n")
            after = packs.resolve_pack("sample-pack", canonical_root=pack_root)

            self.assertNotEqual(before["digest"], after["digest"])

    def test_project_scope_with_identical_bytes_has_the_same_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / "canonical" / "packs"
            project = root / "project"
            _copy_pack_with_contract(PACKS / "orch-code-pack", canonical / "orch-code-pack", root)
            _copy_pack(PACKS / "orch-code-pack", project / ".orchflows" / "packs" / "orch-code-pack")
            (project / ".orchflows" / "contracts").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                ROOT / "contracts" / "pack-signature.md",
                project / ".orchflows" / "contracts" / "pack-signature.md",
            )

            resolved = packs.resolve_pack(
                "orch-code-pack",
                canonical_root=canonical,
                project_root=project,
            )
            expected = packs.resolve_pack("orch-code-pack", canonical_root=canonical)

            self.assertEqual("project", resolved["scope"])
            self.assertEqual(expected["digest"], resolved["digest"])

    def test_project_scope_is_discovered_from_the_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            project_pack = project / ".orchflows" / "packs" / "orch-code-pack"
            _copy_pack(PACKS / "orch-code-pack", project_pack)
            contracts = project / ".orchflows" / "contracts"
            contracts.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "contracts" / "pack-signature.md", contracts / "pack-signature.md")

            with patch.object(packs.Path, "cwd", return_value=project):
                # The resolver's default scope is intentionally cwd-based so
                # the CLI works without a project-root flag.
                resolved = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)

            self.assertEqual("project", resolved["scope"])

    def test_text_reference_line_endings_do_not_change_pack_identity(self):
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

    def test_cells_projects_exact_consumer_leaves(self):
        resolved = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)

        execute = packs.cells_for(resolved["digest"], canonical_root=PACKS, consumer="execute")
        check = packs.cells_for(resolved["digest"], canonical_root=PACKS, consumer="check")

        self.assertEqual(
            {"adapter", "assembly", "craft", "required_spec_fields", "slicing", "stages", "workspace"},
            set(execute["cells"]),
        )
        self.assertEqual({"craft", "evidence", "lens"}, set(check["cells"]))
        self.assertNotIn("evidence", execute["cells"])
        self.assertNotIn("workspace", check["cells"])

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
            command + [
                "cells", payload["digest"], "--for", "check",
                "--canonical-root", str(PACKS),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, projected.returncode, projected.stderr)
        self.assertEqual({"craft", "evidence", "lens"}, set(json.loads(projected.stdout)["cells"]))


class PackShapeRefusalTests(unittest.TestCase):
    def test_old_skill_binding_cell_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "packs"
            _copy_pack_with_contract(PACKS / "orch-code-pack", root / "bad-pack", Path(tmp))
            skill = root / "bad-pack" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "name: orch-code-pack", "name: bad-pack"
                ).replace(
                    "| adapter | git |", "| executor | `orch-tdd` |\n| adapter | git |"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(packs.PackError, "unknown pack cell"):
                packs.resolve_pack("bad-pack", canonical_root=root)

    def test_unknown_digest_and_consumer_are_closed_refusals(self):
        with self.assertRaisesRegex(packs.PackError, "does not resolve"):
            packs.cells_for("sha256:" + "0" * 64, canonical_root=PACKS, consumer="check")
        resolved = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)
        with self.assertRaisesRegex(packs.PackError, "consumer"):
            packs.cells_for(resolved["digest"], canonical_root=PACKS, consumer="other")


if __name__ == "__main__":
    unittest.main()
