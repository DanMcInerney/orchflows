"""Pack resolution and the content-addressed four-cell shape."""

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

from scripts import packs, rings, rings_trust


ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "packs"


@contextlib.contextmanager
def _home():
    """A temporary orchflows home, so no test writes the real trust ledger."""

    with tempfile.TemporaryDirectory(prefix="orchflows-home-") as tmp:
        home = Path(tmp).resolve()
        with patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": str(home / "state")}):
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

    def test_public_facade_does_not_reexport_private_support_names(self):
        private_support_names = {
            "_canonical_json",
            "_sha256",
            "_canonicalize_bytes",
            "_read_bytes",
            "_pack_name",
            "_PACK_NAME_RE",
            "_ADAPTER_RE",
            "_STAGE_RE",
            "_CELL_ROW_RE",
            "_LINK_RE",
            "_FRONTMATTER_NAME_RE",
            "_SHA_RE",
            "_CELL_SET",
            "_root_is_packs",
            "_canonical_default",
            "_project_default",
            "_scope_root",
            "_roots",
            "_candidate_path",
            "_frontmatter_name",
            "_parse_rows",
            "_atom",
            "_typed_cells",
            "_reference_paths",
            "_read_references",
            "_signature_digest",
            "_resolved",
            "_available_names",
        }
        self.assertTrue(private_support_names.isdisjoint(vars(packs)))

    def test_real_packs_resolve_to_typed_flat_cells_without_skill_bindings(self):
        result = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)

        self.assertEqual("orch-code-pack", result["pack"])
        self.assertEqual("lib", result["scope"])
        self.assertEqual(
            {"adapter", "assembly", "craft", "stages"},
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
                    f"{canonical / 'sample-pack' / 'SKILL.md'}"
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
                craft = project_pack / "references" / "craft.md"
                craft.write_bytes(craft.read_bytes() + b"\nchanged\n")
                with self.assertRaises(packs.PackError) as raised:
                    packs.resolve_pack(
                        "sample-pack", canonical_root=PACKS, project_root=project,
                    )
            self.assertEqual("pack-untrusted", raised.exception.code)

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

    def test_cells_returns_every_cell_of_the_resolved_digest(self):
        """One projection: every verb reads the same four cells and the
        whole craft document behind them — there is no lane to omit a
        section from."""

        resolved = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)

        projected = packs.cells_for(resolved["digest"], canonical_root=PACKS)

        self.assertEqual({"adapter", "assembly", "craft", "stages"}, set(projected["cells"]))
        self.assertEqual("orch-code-pack", projected["pack"])
        self.assertEqual(resolved["digest"], projected["digest"])
        self.assertNotIn("for", projected)
        self.assertIn("references/craft.md", projected["cells"]["craft"])

    def test_every_pack_resolves_a_distinct_outline_section(self):
        """Prose earns a section only when its content differs between packs
        (contracts/pack-signature.md, Admission)."""

        import re

        bodies = {}
        for name in sorted(path.parent.name for path in PACKS.glob("*/SKILL.md")):
            resolved = packs.resolve_pack(name, canonical_root=PACKS)
            self.assertIn("references/craft.md", resolved["cells"]["craft"])
            text = (PACKS / name / "references" / "craft.md").read_text(encoding="utf-8")
            match = re.search(r"(?ms)^## Outline\s*$(.*?)(?=^## |\Z)", text)
            self.assertIsNotNone(match, f"{name} craft carries no ## Outline section")
            bodies[name] = match.group(1).strip()
            self.assertTrue(bodies[name], f"{name} ## Outline section is empty")
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
        self.assertEqual(
            {"adapter", "assembly", "craft", "stages"},
            set(json.loads(projected.stdout)["cells"]),
        )
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
            packs.cells_for("sha256:" + "0" * 64, canonical_root=PACKS)
        resolved = packs.resolve_pack("orch-code-pack", canonical_root=PACKS)
        # The lane keyword is deleted, not aliased: a legacy caller refuses.
        with self.assertRaises(TypeError):
            packs.cells_for(resolved["digest"], canonical_root=PACKS, consumer="check")


if __name__ == "__main__":
    unittest.main()
