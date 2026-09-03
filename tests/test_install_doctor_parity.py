"""The doctor's inspected surface and the installer's written surface are one.

``installer/doctor.py::_planned_files`` is a hand-written second reading of the
same ``Plan`` that ``installer/application.py::apply_plan`` writes from. Nothing
in either file holds them equal, and the disagreement is not quiet: a file the
installer writes and records but the doctor never enumerates reads back as
``receipt.unexpected-entry`` -- a healthy install reported as junk to delete.
That already happened once, for the whole Grok column.

So the two are held equal here, by running the real write loop rather than by
restating either list: every ``(path, kind)`` pair ``apply_plan`` records is a
pair ``_planned_files`` inspects, and the reverse. The guard is only as wide as
the plan it is run against, so the plan is held maximal against ``Plan``'s own
fields -- a new field is exercised here or named unexercised, and either way it
cannot be added silently.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from installer.application import apply_plan
from installer.doctor import _planned_files
from installer.models import BlockPlan, ConfigPlan, ImportPlan, Plan, _frontend_manifest_identity

# ``Plan`` fields the maximal plan below deliberately leaves at their default,
# each with the reason it cannot be exercised by a parity fixture. Everything
# else must be passed explicitly, so a new file-bearing field either shows up
# in the receipt this test compares or fails the coverage test outright.
UNEXERCISED_FIELDS = {
    "runtime_action": "the only non-None value builds a real private venv; it records no file",
    "home_ring": "the user's own ring; the receipt deliberately records none of it",
}


def _maximal_plan(root: Path) -> tuple[Plan, dict]:
    """One plan carrying at least one entry in every file-bearing field."""

    source = root / "source"
    installed = root / "installed"
    hosts = root / "hosts"
    library_source = source / "catalog" / "orch-tdd" / "SKILL.md"
    library_source.parent.mkdir(parents=True)
    library_source.write_text("canonical skill\n", encoding="utf-8")
    script_source = source / "tickets.py"
    script_source.write_text("print('tickets')\n", encoding="utf-8")

    # ``frontend_action="reuse"`` verifies the distribution already on disk and
    # copies nothing, which is the one frontend path a fixture can take without
    # standing up a build. The assets are still planned, so they are still
    # recorded -- which is all this test reads.
    frontend_home = installed / "ui"
    frontend_asset = frontend_home / "index.html"
    frontend_asset.parent.mkdir(parents=True)
    frontend_asset.write_text("<!doctype html>\n", encoding="utf-8")

    fields = {
        "lib_home": installed / "lib",
        "scope_home": installed,
        "bin_dir": installed / "bin",
        "receipt_path": installed / "receipt.json",
        "runtime_dirs": [installed / "state"],
        "lib_copies": [(library_source, installed / "lib" / "catalog" / "orch-tdd" / "SKILL.md")],
        "scripts": [(script_source, installed / "bin" / "tickets.py")],
        "frontend_home": frontend_home,
        "frontend_assets": [(frontend_asset, frontend_asset)],
        "frontend_manifest_sha256": _frontend_manifest_identity(frontend_home),
        "frontend_action": "reuse",
        "claude_adapters": [(hosts / "claude" / "skills" / "orch-tdd" / "SKILL.md", "adapter\n")],
        "codex_prompts": [(hosts / "codex" / "prompts" / "orch-tdd.md", "prompt\n")],
        "codex_skills": [(hosts / "codex" / "skills" / "orch-tdd" / "SKILL.md", "codex skill\n")],
        "grok_skills": [(hosts / "grok" / "skills" / "orch-tdd" / "SKILL.md", "grok skill\n")],
        "by_name": [(installed / "lib" / "by-name" / "orch-tdd" / "SKILL.md", "pointer\n")],
        "claude_agents": [(hosts / "claude" / "agents" / "orch-worker.md", "claude role\n")],
        "codex_agents": [(hosts / "codex" / "agents" / "orch-worker.toml", "codex role\n")],
        "grok_agents": [(hosts / "grok" / "agents" / "orch-worker.md", "grok role\n")],
        "configs": [
            ConfigPlan(hosts / "codex" / "config.toml", "[agents]\n", "codex-config", "Codex config"),
            ConfigPlan(hosts / "grok" / "config.toml", "[subagents]\n", "grok-config", "Grok limits"),
        ],
        "blocks": [
            BlockPlan(
                hosts / "codex" / "AGENTS.md",
                "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
                "<!-- BEGIN ORCHFLOWS -->",
                "<!-- END ORCHFLOWS -->",
                "Codex instructions",
            )
        ],
        "host_block": ConfigPlan(
            installed / "host-block.md",
            "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
            "host-block",
            "Host instructions",
        ),
        "grok_rules": ConfigPlan(
            hosts / "grok" / "rules" / "orchflows.md",
            "<!-- BEGIN ORCHFLOWS -->\nbody\n<!-- END ORCHFLOWS -->\n",
            "grok-rules",
            "Grok instruction file",
        ),
        "claude_import": ImportPlan(
            hosts / "claude" / "CLAUDE.md",
            installed / "host-block.md",
            "Claude instructions",
        ),
        "warnings": ["informational preflight note"],
        "manage_host_surfaces": True,
        "claude_enabled": True,
        "codex_enabled": True,
        "grok_enabled": True,
    }
    return Plan(**fields), fields


class TestDoctorInspectsWhatTheInstallerWrites(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="orchflows-parity-")
        self.root = Path(self.temporary.name)
        self.plan, self.fields = _maximal_plan(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def _apply(self) -> dict:
        """Run the real write loop with every host path inside the fixture."""

        home = self.root / "home"
        home.mkdir(exist_ok=True)
        with patch.dict(os.environ), patch.object(install.Path, "home", return_value=home):
            for variable in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "GROK_HOME"):
                os.environ.pop(variable, None)
            return apply_plan(self.plan, "abc123")

    def test_the_maximal_plan_exercises_every_field_a_plan_can_carry(self):
        """A field left out here is a field the parity test below cannot see,
        so leaving one out has to fail rather than narrow the guard."""

        declared = {field.name for field in dataclasses.fields(Plan)}
        self.assertEqual(set(), set(UNEXERCISED_FIELDS) - declared)
        self.assertEqual(
            declared - set(UNEXERCISED_FIELDS),
            set(self.fields),
            "add the new Plan field to _maximal_plan, or name it in UNEXERCISED_FIELDS",
        )

    def test_every_receipt_entry_the_installer_writes_is_one_the_doctor_inspects(self):
        receipt = self._apply()

        recorded = {(entry["path"], entry["kind"]) for entry in receipt["files"]}
        inspected = {(str(destination), kind) for _, kind, destination, _, _ in _planned_files(self.plan)}

        self.assertNotEqual(set(), recorded)
        self.assertEqual(
            set(),
            recorded - inspected,
            "apply_plan records these, so the doctor reports them receipt.unexpected-entry",
        )
        self.assertEqual(
            set(),
            inspected - recorded,
            "the doctor inspects these, so it reports them missing on a healthy install",
        )

    def test_the_written_install_reads_back_coherent_to_the_doctor(self):
        """The pair comparison above is a claim about two enumerations. This is
        the claim about the surface itself: what the installer just wrote, the
        doctor reads with nothing to report."""

        from installer.doctor import inspect_installation

        self._apply()
        report = inspect_installation(self.plan, current_source_commit="abc123")

        self.assertEqual({"status": "coherent", "findings": []}, report)

    def test_every_kind_the_receipt_carries_is_a_kind_the_doctor_knows(self):
        """The ticket's own wording, asserted directly: no receipt kind
        ``apply_plan`` can emit is absent from ``_planned_files``."""

        receipt = self._apply()
        written = {entry["kind"] for entry in receipt["files"]}

        self.assertEqual(set(), written - {kind for _, kind, _, _, _ in _planned_files(self.plan)})
        self.assertLessEqual(
            {"lib", "script", "frontend-asset", "by-name", "adapter", "prompt",
             "codex-skill", "grok-skill", "claude-agent", "codex-agent", "grok-agent",
             "codex-config", "grok-config", "host-block", "grok-rules"},
            written,
            "the maximal plan stopped exercising a kind the installer still writes",
        )

    def test_the_receipt_on_disk_is_the_receipt_returned(self):
        """``_planned_files`` is compared against the returned value above; the
        doctor reads the file. They are the same document or the guard is
        checking something no doctor run ever sees."""

        returned = self._apply()

        self.assertEqual(
            returned, json.loads(self.plan.receipt_path.read_text(encoding="utf-8"))
        )


if __name__ == "__main__":
    unittest.main()
