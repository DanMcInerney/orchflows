from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from installer.doctor import inspect_installation
from installer.models import BlockPlan, ConfigPlan, ImportPlan, Plan


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DoctorFixture:
    def __init__(self, root: Path):
        self.root = root
        source = root / "source"
        installed = root / "installed"
        hosts = root / "hosts"
        source.mkdir()

        library_source = source / "catalog" / "orch-tdd" / "SKILL.md"
        library_source.parent.mkdir(parents=True)
        library_source.write_text("canonical skill\n", encoding="utf-8")

        self.library = installed / "lib" / "catalog" / "orch-tdd" / "SKILL.md"
        self.by_name = installed / "lib" / "by-name" / "orch-tdd" / "SKILL.md"
        self.redirect = hosts / "codex" / "skills" / "orch-tdd" / "SKILL.md"
        self.role = hosts / "codex" / "agents" / "orch-worker.toml"
        self.config = hosts / "codex" / "config.toml"
        self.host_surface = hosts / "codex" / "AGENTS.md"
        self.claude_surface = hosts / "claude" / "CLAUDE.md"
        self.host_block = installed / "host-block.md"
        desired = {
            self.library: library_source.read_text(encoding="utf-8"),
            self.by_name: "Read installed/lib/catalog/orch-tdd/SKILL.md\n",
            self.redirect: "Read installed/lib/by-name/orch-tdd/SKILL.md\n",
            self.role: 'name = "orch-worker"\n',
            self.config: "[agents]\nmax_depth = 4\n",
            self.host_block: "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
        }
        for path, content in desired.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.host_surface.parent.mkdir(parents=True, exist_ok=True)
        self.host_surface.write_text(
            "local\n<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
            encoding="utf-8",
        )
        self.claude_surface.parent.mkdir(parents=True, exist_ok=True)
        self.claude_surface.write_text(f"local\n@{self.host_block.resolve()}\n", encoding="utf-8")

        receipt_path = installed / "receipt.json"
        self.plan = Plan(
            scope="user",
            project_root=None,
            lib_home=installed / "lib",
            scope_home=installed,
            bin_dir=installed / "bin",
            receipt_path=receipt_path,
            lib_copies=[(library_source, self.library)],
            by_name=[(self.by_name, desired[self.by_name])],
            codex_skills=[(self.redirect, desired[self.redirect])],
            codex_agents=[(self.role, desired[self.role])],
            configs=[ConfigPlan(self.config, desired[self.config], "codex-config", "Codex config")],
            blocks=[
                BlockPlan(
                    self.host_surface,
                    "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
                    "<!-- BEGIN ORCHFLOWS -->",
                    "<!-- END ORCHFLOWS -->",
                    "Codex instructions",
                )
            ],
            host_block=ConfigPlan(
                self.host_block,
                desired[self.host_block],
                "host-block",
                "Host instructions",
            ),
            claude_import=ImportPlan(
                self.claude_surface,
                self.host_block.resolve(),
                "<!-- BEGIN ORCHFLOWS -->",
                "<!-- END ORCHFLOWS -->",
                "Claude instructions",
            ),
        )
        kinds = {
            self.library: "lib",
            self.by_name: "by-name",
            self.redirect: "codex-skill",
            self.role: "codex-agent",
            self.config: "codex-config",
            self.host_block: "host-block",
        }
        receipt = {
            "version": 4,
            "scope": "user",
            "project_root": None,
            "source_commit": "abc123",
            "lib_home": str(self.plan.lib_home),
            "bin_dir": str(self.plan.bin_dir),
            "files": [
                {"path": str(path), "kind": kind, "sha256": _sha256(path)}
                for path, kind in kinds.items()
            ],
            "blocks": [
                {
                    "path": str(self.host_surface),
                    "start_marker": "<!-- BEGIN ORCHFLOWS -->",
                    "end_marker": "<!-- END ORCHFLOWS -->",
                }
            ],
            "imports": [
                {
                    "path": str(self.claude_surface),
                    "import_line": f"@{self.host_block.resolve()}",
                }
            ],
            "dirs": [],
        }
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")


class TestInstallDoctor(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="orchflows-doctor-")
        self.fixture = DoctorFixture(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def _tree_identity(self):
        return {
            path.relative_to(self.fixture.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.fixture.root.rglob("*"))
            if path.is_file()
        }

    def test_coherent_installation_is_deterministic_and_read_only(self):
        before = self._tree_identity()

        first = inspect_installation(self.fixture.plan, current_source_commit="abc123")
        second = inspect_installation(self.fixture.plan, current_source_commit="abc123")

        self.assertEqual({"status": "coherent", "findings": []}, first)
        self.assertEqual(first, second)
        self.assertEqual(before, self._tree_identity())

    def test_each_bootstrap_surface_reports_drift_by_stable_identity(self):
        mutations = (
            ("receipt.source-commit", None, "different"),
            ("catalog.content", self.fixture.library, "drifted catalog\n"),
            ("by-name.content", self.fixture.by_name, "drifted pointer\n"),
            ("redirect.content", self.fixture.redirect, "drifted redirect\n"),
            ("role-profile.content", self.fixture.role, "drifted role\n"),
        )
        for expected_id, path, content in mutations:
            with self.subTest(expected_id=expected_id):
                if path is None:
                    report = inspect_installation(
                        self.fixture.plan, current_source_commit=content
                    )
                else:
                    original = path.read_text(encoding="utf-8")
                    path.write_text(content, encoding="utf-8")
                    try:
                        report = inspect_installation(
                            self.fixture.plan, current_source_commit="abc123"
                        )
                    finally:
                        path.write_text(original, encoding="utf-8")
                identities = {finding["id"] for finding in report["findings"]}
                self.assertIn(expected_id, identities)
                self.assertEqual(report, inspect_installation(
                    self.fixture.plan,
                    current_source_commit=(content if path is None else "abc123"),
                ) if path is None else report)

    def test_desired_plan_and_receipt_drift_have_stable_findings(self):
        duplicate = self.fixture.plan.codex_skills[0]
        self.fixture.plan.by_name.append(duplicate)
        receipt = json.loads(self.fixture.plan.receipt_path.read_text(encoding="utf-8"))
        receipt["files"] = receipt["files"][:-1]
        self.fixture.plan.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

        report = inspect_installation(self.fixture.plan, current_source_commit="abc123")

        identities = {finding["id"] for finding in report["findings"]}
        self.assertIn("desired-plan.duplicate-destination", identities)
        self.assertIn("receipt.missing-entry", identities)
        self.assertEqual(identities, {
            finding["id"]
            for finding in inspect_installation(
                self.fixture.plan, current_source_commit="abc123"
            )["findings"]
        })


if __name__ == "__main__":
    unittest.main()
