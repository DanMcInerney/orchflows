"""Compatibility seams for scripts being split behind thin facades."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts import cutcheck
from scripts import migrate_state
from scripts import search_plan
from scripts import tickets
from scripts import trace
from scripts import ui
from scripts import workspace


ROOT = Path(__file__).resolve().parents[1]


def _call(main, argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = main(argv)
        except SystemExit as exit_:
            code = exit_.code
    return code, stdout.getvalue(), stderr.getvalue()


class TicketsFacadeCompatibilityTest(unittest.TestCase):
    """The command surface and sibling imports survive implementation moves."""

    COMMANDS = {
        "amend",
        "check",
        "claim",
        "gate",
        "grant",
        "improvement",
        "instantiate",
        "list",
        "new",
        "packet",
        "ready",
        "recut",
        "result",
        "result-grade",
        "run-state",
        "set-status",
        "worklog",
    }
    SIBLING_IMPORTS = {
        "CHECKED_BY_KEY",
        "COVERAGE_RECORD_NAME",
        "DURATION_RE",
        "GATE_EXECUTORS",
        "GATE_ID_MARKER",
        "INSTRUCTION_BUDGET",
        "ORACLE_CLASS_RE",
        "PLACEHOLDER_RE",
        "PROPOSALS_DIR",
        "PROVENANCE_RE",
        "REQUIRED_ISOLATION",
        "ROOT_EXECUTOR",
        "RUN_IDENTITY_NAME",
        "SCRIPT_EXECUTOR_PREFIX",
        "SINK_CONVENTION",
        "TEMPLATE_FILE",
        "_criteria",
        "_load_ticket",
        "_origin_url",
        "_parse_frontmatter",
        "_parse_iso",
        "_project_key",
        "_read_identity",
        "_same_project",
        "_scope_entries",
        "_sections",
        "_set_frontmatter_field",
        "_writer_identity",
        "instruction_words",
        "normalized_isolation",
        "template_defects",
    }

    def test_help_keeps_the_command_set_and_json_exit_contract(self):
        code, stdout, stderr = _call(tickets.main, ["--help"])
        payload = json.loads(stdout)
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        self.assertEqual(self.COMMANDS, set(payload["help"]["subcommands"]))

    def test_every_symbol_consumed_by_sibling_modules_remains_exported(self):
        missing = sorted(name for name in self.SIBLING_IMPORTS if not hasattr(tickets, name))
        self.assertEqual([], missing)


class UiFacadeCompatibilityTest(unittest.TestCase):
    def test_help_keeps_the_public_flags_and_argparse_exit_contract(self):
        code, stdout, stderr = _call(ui.main, ["--help"])
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        for flag in ("--root", "--port", "--transcripts"):
            self.assertIn(flag, stdout)


class CutcheckFacadeCompatibilityTest(unittest.TestCase):
    def test_help_keeps_the_positional_and_public_flags(self):
        code, stdout, stderr = _call(cutcheck.main, ["--help"])
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        self.assertIn("run", stdout)
        for flag in ("--baseline", "--lib"):
            self.assertIn(flag, stdout)


class SearchPlanFacadeCompatibilityTest(unittest.TestCase):
    def test_unknown_command_keeps_the_refusal_contract(self):
        code, stdout, stderr = _call(search_plan.main, [])
        self.assertEqual(2, code)
        self.assertEqual("", stdout)
        self.assertEqual("search-plan: expected advance\n", stderr)


class TraceFacadeCompatibilityTest(unittest.TestCase):
    def test_missing_source_keeps_the_usage_exit_contract(self):
        code, stdout, stderr = _call(trace.main, [])
        self.assertEqual(2, code)
        self.assertEqual("", stdout)
        for flag in ("--claude", "--codex", "--mermaid"):
            self.assertIn(flag, stderr)


class WorkspaceFacadeCompatibilityTest(unittest.TestCase):
    def test_help_keeps_commands_verdicts_and_direct_return_contract(self):
        code, stdout, stderr = _call(workspace.main, ["--help"])
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        for command in ("start", "check"):
            self.assertIn(command, stdout)
        for verdict in workspace.VERDICTS.values():
            self.assertIn(verdict, stdout)


class MigrateStateFacadeCompatibilityTest(unittest.TestCase):
    def test_missing_source_keeps_the_json_refusal_and_zero_exit_contract(self):
        code, stdout, stderr = _call(migrate_state.main, [])
        payload = json.loads(stdout)
        self.assertEqual(0, code)
        self.assertEqual("", stderr)
        self.assertEqual(
            f"at least one --from ROOT is required. {migrate_state.USAGE}",
            payload["error"],
        )


class V2ProducerMigrationTest(unittest.TestCase):
    """New cut producers opt in while dispatch and legacy paths stay exact."""

    def test_v2_cut_producers_and_consumers_share_one_sealed_generation_contract(self):
        documents = {
            "spec": (ROOT / "skills/workflows/orch-spec/SKILL.md").read_text(),
            "decompose": (
                ROOT / "skills/kernel/orch-decompose/SKILL.md"
            ).read_text(),
            "frontier": (
                ROOT / "skills/engines/orch-frontier/SKILL.md"
            ).read_text(),
            "integrate": (
                ROOT / "skills/kernel/orch-integrate/SKILL.md"
            ).read_text(),
            "lens": (
                ROOT / "skills/kernel/orch-decompose/references/cut-lens.md"
            ).read_text(),
        }

        required = {
            "spec": ("v2", "draft", "root_generation", "validated", "sealed"),
            "decompose": (
                "v2",
                "cut_generation",
                "ownership_regions",
                "assignment_seal",
                "validation receipt",
            ),
            "frontier": (
                "assignment_seal",
                "root_generation",
                "cut_generation",
                "exact sealed generation",
                "v1",
            ),
            "integrate": (
                "amendment-request:",
                "continue",
                "amend-and-reseal",
                "recut-remaining",
                "successor-or-new-root",
                "once per dispatch",
            ),
            "lens": (
                "draft",
                "validation receipt",
                "assignment_seal",
                "generation",
                "ownership region",
                "merge oracle",
            ),
        }
        for name, tokens in required.items():
            text = documents[name]
            for token in tokens:
                with self.subTest(document=name, token=token):
                    self.assertIn(token, text)

        for name, text in documents.items():
            with self.subTest(document=name, compatibility="v1"):
                self.assertIn("absence of v2 fields means v1", text)

        manifest = json.loads(
            (ROOT / "tests/serial_compat_manifest.json").read_text()
        )
        self.assertIn(
            "test_refactor_compat.V2ProducerMigrationTest."
            "test_v2_cut_producers_and_consumers_share_one_sealed_generation_contract",
            manifest["discovery"]["identities"],
        )


if __name__ == "__main__":
    unittest.main()
