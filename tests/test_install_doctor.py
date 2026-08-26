from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import install
from installer.doctor import inspect_installation
from installer.models import BlockPlan, ConfigPlan, ImportPlan, Plan


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DoctorFixture:
    """One installed tree, one plan, one receipt that agree with each other.

    ``grok`` selects whether a Grok surface was installed at all: a host with
    no CLI on PATH plans nothing, records nothing, and must draw no finding.
    ``grok_root`` relocates that surface the way ``GROK_HOME`` does.
    """

    def __init__(self, root: Path, *, grok: bool = True, grok_root: Path | None = None):
        self.root = root
        source = root / "source"
        installed = root / "installed"
        hosts = root / "hosts"
        source.mkdir()
        grok_home = (hosts / "grok") if grok_root is None else grok_root

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
        self.grok_skill = grok_home / "skills" / "orch-tdd" / "SKILL.md"
        self.grok_agent = grok_home / "agents" / "orch-worker.md"
        self.grok_config = grok_home / "config.toml"
        self.grok_rules = grok_home / "rules" / "orchflows.md"
        desired = {
            self.library: library_source.read_text(encoding="utf-8"),
            self.by_name: "Read installed/lib/catalog/orch-tdd/SKILL.md\n",
            self.redirect: "Read installed/lib/by-name/orch-tdd/SKILL.md\n",
            self.role: 'name = "orch-worker"\n',
            self.config: "[agents]\nmax_depth = 4\n",
            self.host_block: "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
        }
        if grok:
            desired.update(
                {
                    self.grok_skill: "---\nname: orch-tdd\n---\n\nRead it exactly.\n",
                    self.grok_agent: "---\nname: orch-worker\n---\n\nrole\n",
                    self.grok_config: "[subagents]\nmax_depth = 1\n",
                    self.grok_rules: "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
                }
            )
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
            grok_skills=(
                [(self.grok_skill, desired[self.grok_skill])] if grok else []
            ),
            grok_agents=(
                [(self.grok_agent, desired[self.grok_agent])] if grok else []
            ),
            grok_rules=(
                ConfigPlan(
                    self.grok_rules,
                    desired[self.grok_rules],
                    "grok-rules",
                    "Grok instruction file",
                )
                if grok
                else None
            ),
            configs=[ConfigPlan(self.config, desired[self.config], "codex-config", "Codex config")]
            + (
                [
                    ConfigPlan(
                        self.grok_config,
                        desired[self.grok_config],
                        "grok-config",
                        "Grok subagent limits",
                    )
                ]
                if grok
                else []
            ),
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
        if grok:
            kinds.update(
                {
                    self.grok_skill: "grok-skill",
                    self.grok_agent: "grok-agent",
                    self.grok_config: "grok-config",
                    self.grok_rules: "grok-rules",
                }
            )
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

    def _grok_census(self):
        """Every Grok artifact, paired with the receipt kind that files it."""

        return (
            ("redirect", "grok-skill", self.fixture.grok_skill),
            ("role-profile", "grok-agent", self.fixture.grok_agent),
            ("configuration", "grok-config", self.fixture.grok_config),
            ("configuration", "grok-rules", self.fixture.grok_rules),
        )

    def test_each_grok_artifact_reports_presence_and_staleness_by_receipt(self):
        """Absent from the desired plan, a Grok artifact is neither checked for
        drift nor expected in the receipt -- so a whole installed Grok surface
        reads back as unexpected junk, and a corrupted one reads as coherent.
        """

        for surface, kind, path in self._grok_census():
            with self.subTest(kind=kind, state="stale"):
                original = path.read_text(encoding="utf-8")
                path.write_text("drifted\n", encoding="utf-8")
                try:
                    report = inspect_installation(
                        self.fixture.plan, current_source_commit="abc123"
                    )
                finally:
                    path.write_text(original, encoding="utf-8")
                self.assertIn(
                    {"id": f"{surface}.content", "path": str(path), "kind": kind},
                    report["findings"],
                )
                self.assertIn(
                    {"id": "receipt.hash", "path": str(path), "kind": kind},
                    report["findings"],
                )
            with self.subTest(kind=kind, state="missing"):
                original = path.read_text(encoding="utf-8")
                path.unlink()
                try:
                    report = inspect_installation(
                        self.fixture.plan, current_source_commit="abc123"
                    )
                finally:
                    path.write_text(original, encoding="utf-8")
                self.assertIn(
                    {"id": f"{surface}.missing", "path": str(path), "kind": kind},
                    report["findings"],
                )

    def test_an_uninstalled_grok_leaves_the_report_exactly_as_it_was(self):
        """No grok CLI plans no Grok surface, records none in the receipt, and
        must draw no finding -- and the Claude and Codex findings must read
        exactly as they did before the Grok column existed. Both halves at
        once: the same Claude-side drift, reported against a Grok-bearing
        install and a Grok-free one, has to relativise to the same findings."""

        def relative(report, root):
            return sorted(
                (
                    finding["id"],
                    Path(finding["path"]).relative_to(root).as_posix(),
                    finding.get("kind"),
                )
                for finding in report["findings"]
                if "path" in finding
            )

        with tempfile.TemporaryDirectory(prefix="orchflows-doctor-bare-") as name:
            bare = DoctorFixture(Path(name), grok=False)
            self.assertEqual(
                {"status": "coherent", "findings": []},
                inspect_installation(bare.plan, current_source_commit="abc123"),
            )
            for fixture in (bare, self.fixture):
                fixture.by_name.write_text("drifted pointer\n", encoding="utf-8")
            bare_report = inspect_installation(bare.plan, current_source_commit="abc123")
            self.assertEqual(
                relative(bare_report, bare.root),
                relative(
                    inspect_installation(
                        self.fixture.plan, current_source_commit="abc123"
                    ),
                    self.fixture.root,
                ),
            )
        self.assertEqual(
            [], [entry for entry in relative(bare_report, bare.root) if "grok" in str(entry)]
        )

    def test_the_doctor_inspects_whatever_grok_home_the_override_names(self):
        """The doctor holds no host path of its own: it reads the desired plan
        it is handed. So the whole chain -- override, plan, report -- has to be
        run to state that ``GROK_HOME`` is the surface a doctor run examines,
        and that the default ``~/.grok`` is not examined beside it."""

        with tempfile.TemporaryDirectory(prefix="orchflows-doctor-home-") as name:
            root = Path(name)
            home = root / "home"
            home.mkdir()
            override = root / "relocated-grok"
            output = io.StringIO()
            with patch.dict(os.environ, {"GROK_HOME": str(override)}), patch.object(
                install.Path, "home", return_value=home
            ), patch.object(
                install.shutil,
                "which",
                side_effect=lambda candidate: (
                    "mock-grok" if candidate.split(".", 1)[0] == "grok" else None
                ),
            ), redirect_stdout(output):
                exit_code = install.main(["doctor"])

            report = json.loads(output.getvalue())
            self.assertEqual(1, exit_code)
            grok = [
                finding
                for finding in report["findings"]
                if str(finding.get("kind", "")).startswith("grok-")
            ]
            self.assertEqual(
                {"grok-skill", "grok-agent", "grok-rules", "grok-config"},
                {finding["kind"] for finding in grok},
            )
            for finding in grok:
                with self.subTest(kind=finding["kind"]):
                    self.assertIn(override, Path(finding["path"]).parents)
            self.assertEqual(
                [],
                [
                    finding
                    for finding in report["findings"]
                    if "path" in finding
                    and home / ".grok" in Path(finding["path"]).parents
                ],
            )

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

    def test_both_cli_forms_print_the_same_report_and_exit_by_status(self):
        for argv in (["doctor"], ["--doctor"]):
            with self.subTest(argv=argv), patch.object(
                install, "build_plan", return_value=self.fixture.plan
            ), patch.object(
                install, "resolve_source_commit", return_value="abc123"
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = install.main(argv)

                self.assertEqual(0, exit_code)
                self.assertEqual(
                    {"findings": [], "status": "coherent"},
                    json.loads(output.getvalue()),
                )

        self.fixture.by_name.write_text("drifted pointer\n", encoding="utf-8")
        with patch.object(
            install, "build_plan", return_value=self.fixture.plan
        ), patch.object(install, "resolve_source_commit", return_value="abc123"):
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = install.main(["doctor"])

        self.assertEqual(1, exit_code)
        self.assertEqual("drift", json.loads(output.getvalue())["status"])


if __name__ == "__main__":
    unittest.main()
