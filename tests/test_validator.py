"""Compatibility discovery seam for validator compiler regression cases."""
import sys
import unittest

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_validator_cases.support import _IsolatedTree
from tests.test_validator_cases.availability_and_packages import (
    TestASkippedCheckSaysSo,
    TestSheetAnatomy,
    TestSyntheticPackageBoundaryInputs,
    TestWorkflowLibraryHomes,
)
from tests.test_validator_cases.contracts_and_names import (
    TestEnvelopeCheck,
    TestNameResolution,
)
from tests.test_validator_cases.corpus_and_surfaces import (
    TestDuplicationCorpus,
    TestCraftSections,
    TestLicensedCopies,
    TestWordBudgetAndLinks,
)
from tests.test_validator_cases.repo_and_frontmatter import (
    TestFrontmatterBoundaryInputs,
    TestValidatorAgainstRepo,
)
import tools.validate as validate


class TestRecursiveNameResolution(_IsolatedTree):
    def test_nested_shipped_prose_resolves_skill_names(self):
        skill = self.tmp_path / "skills" / "kernel" / "orch-real"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: orch-real\ndescription: synthetic skill\nrole: worker\n---\n"
            "Require: input.\nNever: overreach.\nReturn: status; result.\n",
            encoding="utf-8",
        )
        (self.tmp_path / "ARCHITECTURE.md").write_text("# Tiers\n", encoding="utf-8")
        paths = (
            "rules/nested/call.md",
            "docs/nested/call.md",
            "contracts/nested/call.md",
            "templates/nested/call.md",
        )
        for relative in paths:
            path = self.tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Call `orch-missing`.\n", encoding="utf-8")

        result = self._run()

        for relative in paths:
            with self.subTest(relative=relative):
                self.assertIn(
                    f"ERROR {relative}: `orch-missing` names no package",
                    result.stdout.replace("\\", "/"),
                )


class TestDomainBlindnessAdmission(_IsolatedTree):
    """Machinery must not branch on pack or pack-owned skill names."""

    def _write_pack(self, name, executor):
        pack = self.tmp_path / "packs" / name
        pack.mkdir(parents=True)
        (pack / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: synthetic pack\n---\n"
            "| cell | binding |\n| --- | --- |\n"
            "| adapter | git |\n"
            "| craft | [references/craft.md](references/craft.md) |\n",
            encoding="utf-8",
        )

    def _write_machinery(self, directory, body):
        path = self.tmp_path / directory / "machinery.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def test_a_canonical_pack_name_in_scripts_is_refused(self):
        self._write_pack("orch-example-pack", "orch-example-executor")
        self._write_machinery("scripts", "PACK = 'orch-example-pack'\n")

        result = self._run()

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(
            "ERROR scripts/machinery.py: domain-specific name `orch-example-pack`",
            result.stdout.replace("\\", "/"),
        )

    def test_a_pack_owned_skill_name_in_tools_is_refused(self):
        self._write_pack("orch-example-pack", "orch-example-executor")
        self._write_machinery("tools", "PACK = 'orch-example-pack'\n")

        result = self._run()

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(
            "ERROR tools/machinery.py: domain-specific name `orch-example-pack`",
            result.stdout.replace("\\", "/"),
        )


class TestMarkdownAnchors(_IsolatedTree):
    def test_a_link_to_a_missing_heading_is_an_error(self):
        for root in validate.LINKED_MD_ROOTS:
            (self.tmp_path / root).mkdir(exist_ok=True)
        (self.tmp_path / "docs" / "target.md").write_text(
            "# Present heading\n", encoding="utf-8"
        )
        (self.tmp_path / "docs" / "source.md").write_text(
            "See [missing](target.md#absent-heading).\n", encoding="utf-8"
        )

        result = self._run()

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(
            "markdown anchor does not resolve: target.md#absent-heading",
            result.stdout,
        )


class TestPrivateReferenceAdmission(_IsolatedTree):
    def test_cross_package_private_reference_is_an_error(self):
        for name in ("pack-a", "pack-b"):
            package = self.tmp_path / "packs" / name
            package.mkdir(parents=True)
            (package / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: synthetic pack\n---\n",
                encoding="utf-8",
            )
        private = self.tmp_path / "packs" / "pack-b" / "references" / "private.md"
        private.parent.mkdir()
        private.write_text("# Private\n", encoding="utf-8")
        with (self.tmp_path / "packs" / "pack-a" / "SKILL.md").open(
            "a", encoding="utf-8"
        ) as stream:
            stream.write("\nSee [private](../pack-b/references/private.md).\n")

        result = self._run()

        finding = next(
            line for line in result.stdout.splitlines()
            if "cross-package link" in line and "private.md" in line
        )
        self.assertTrue(finding.startswith("ERROR "), finding)


class TestStructuralAdmissionMutants(_IsolatedTree):
    def _write_skill(self, name, body, tier="kernel", role="worker"):
        path = self.tmp_path / "skills" / tier / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: synthetic skill\nrole: {role}\n---\n{body}",
            encoding="utf-8",
        )

    def _write_pack(self, name, body):
        path = self.tmp_path / "packs" / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: synthetic pack\n---\n{body}",
            encoding="utf-8",
        )

    def test_labels_in_a_fence_do_not_satisfy_skill_anatomy(self):
        self._write_skill(
            "orch-fenced",
            "```text\nRequire: example.\nNever: example.\nReturn: example.\n```\nDo work.\n",
        )
        result = self._run()
        self.assertIn("skill body missing ordered Require/procedure/Never/Return anatomy", result.stdout)

    def test_a_return_must_be_the_terminal_paragraph(self):
        self._write_skill(
            "orch-after-return",
            "Require: input.\n\nDo work.\n\nNever: skip.\n\nReturn: the completed ticket.\n\nDo more work.\n",
        )
        result = self._run()
        self.assertIn("Return must be the terminal paragraph", result.stdout)

    def test_a_kernel_call_edge_is_primitive_impurity(self):
        self._write_skill(
            "orch-target", "Require: input.\nNever: skip.\nReturn: the completed ticket.\n"
        )
        self._write_skill(
            "orch-helper",
            "Require: input.\nCall `orch-target`.\nNever: skip.\nReturn: the completed ticket.\n",
            tier="kernel",
        )
        result = self._run()
        self.assertIn("kernel skills are primitives", result.stdout)

    def test_pack_control_flow_is_rejected(self):
        self._write_pack(
            "orch-flow-pack",
            "If evidence is absent, then delegate and stop.\n",
        )
        result = self._run()
        self.assertIn("pack body carries control flow", result.stdout)

    def test_duplicate_pack_cell_rows_are_rejected(self):
        rows = (
            "| slicing | inline |\n| workspace | inline |\n"
            "| required_spec_fields | inline |\n| craft | inline |\n"
            "| adapter | git |\n| adapter | git |\n"
            "| evidence | inline |"
        )
        self._write_pack(
            "orch-duplicate-pack",
            "| cell | binding |\n| --- | --- |\n" + rows + "\n",
        )
        result = self._run()
        self.assertIn("pack signature table repeats cell(s): adapter", result.stdout)

    def test_a_new_executor_is_not_outside_envelope_admission(self):
        self._write_skill(
            "orch-new-executor", "Require: input.\nNever: skip.\nReturn: assumptions.\n"
        )
        self._write_pack("orch-binding-pack", "| executor | `orch-new-executor` |\n")
        result = self._run()
        self.assertIn("unknown cell", result.stdout)

    def test_envelope_words_in_a_sentence_are_not_an_envelope(self):
        self._write_skill(
            "orch-prose-envelope",
            "Require: input.\nNever: skip.\n"
            "Return: the ticket has status, result identity, and verification.\n",
        )
        self._write_pack("orch-binding-pack", "| executor | `orch-prose-envelope` |\n")
        result = self._run()
        self.assertIn("unknown cell", result.stdout)

    def test_one_unrelated_shared_stem_does_not_carry_an_input(self):
        self._write_skill(
            "orch-callee",
            "Require: a distinctive telemetry beacon.\n\nNever: skip.\n\n"
            "Return: the completed ticket.\n",
        )
        self._write_skill(
            "orch-caller",
            "Require: a work order.\n\nInspect telemetry, then call `orch-callee`.\n\n"
            "Never: skip.\n\nReturn: the completed ticket.\n",
        )
        result = self._run()
        self.assertIn("Require item 'a distinctive telemetry beacon.", result.stdout)
        self.assertIn("not carried", result.stdout)


class TestCompositionProtocolAdmission(_IsolatedTree):
    """A composition is ticket control flow, never a private protocol tier."""

    def _write(self, relative: str, body: str = "fixture\n") -> None:
        path = self.tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def _findings(self, allowlist=None):
        saved = validate.ROOT
        try:
            validate._bind_root(self.tmp_path)
            diag = validate.Diagnostics()
            if allowlist is None:
                validate.validate_composition_admission(diag)
            else:
                validate.validate_composition_admission(diag, allowlist=allowlist)
            return diag.lines()
        finally:
            validate._bind_root(saved)

    def test_schema_fixture_format_and_script_are_refused(self):
        self._write("example-workflows/probe/SKILL.md")
        self._write("example-workflows/probe/state.schema.json", "{}\n")
        self._write("example-workflows/probe/replay-fixtures.json", "{}\n")
        self._write("example-workflows/probe/validate.py", "# executable machinery\n")

        findings = self._findings()

        for relative, kind in (
            ("example-workflows/probe/state.schema.json", "schema"),
            ("example-workflows/probe/replay-fixtures.json", "fixture format"),
            ("example-workflows/probe/validate.py", "script"),
        ):
            with self.subTest(relative=relative):
                self.assertTrue(
                    any(
                        line.startswith("ERROR " + relative)
                        and "workflow 'probe'" in line
                        and kind in line
                        for line in findings
                    ),
                    findings,
                )

    def test_browser_game_is_the_one_dated_visible_exception(self):
        self._write("example-workflows/browser-game/SKILL.md")
        self._write(
            "example-workflows/references/browser-game-checkpoint.schema.json", "{}\n"
        )
        self._write(
            "example-workflows/references/browser-game-instance-fixtures.json", "{}\n"
        )
        self._write("scripts/browser_game_validate.py", "# legacy validator\n")

        findings = self._findings()

        self.assertEqual(
            {"browser-game": "2026-08-28"},
            validate.COMPOSITION_PROTOCOL_ALLOWLIST,
        )
        self.assertFalse(any(line.startswith("ERROR ") for line in findings), findings)
        exception = [
            line
            for line in findings
            if line.startswith("WARN ") and "browser-game" in line
        ]
        self.assertEqual(1, len(exception), findings)
        self.assertIn("2026-08-28", exception[0])
        self.assertIn("script", exception[0])

    def test_removing_the_browser_game_entry_exposes_its_protocol_artifacts(self):
        self._write("example-workflows/browser-game/SKILL.md")
        self._write(
            "example-workflows/references/browser-game-checkpoint.schema.json", "{}\n"
        )
        self._write(
            "example-workflows/references/browser-game-instance-fixtures.json", "{}\n"
        )
        self._write("scripts/browser_game_validate.py", "# legacy validator\n")

        findings = self._findings(allowlist={})

        errors = [line for line in findings if line.startswith("ERROR ")]
        self.assertEqual(3, len(errors), findings)
        self.assertTrue(all("workflow 'browser-game'" in line for line in errors))

    def test_a_script_module_named_for_a_composition_is_refused_by_boundary(self):
        self._write("example-workflows/probe/SKILL.md")
        self._write("scripts/probe_validate.py", "# composition machinery\n")
        self._write("scripts/probeish.py", "# unrelated bounded stem\n")

        findings = self._findings()

        errors = [line for line in findings if line.startswith("ERROR ")]
        self.assertEqual(1, len(errors), findings)
        self.assertTrue(errors[0].startswith("ERROR scripts/probe_validate.py"), errors)
        self.assertIn("workflow 'probe'", errors[0])
        self.assertIn("workflow-named script machinery", errors[0])

    def test_authoring_standard_states_the_protocol_boundary_and_exception(self):
        text = (ROOT / "docs" / "custom-workflow-authoring.md").read_text(
            encoding="utf-8"
        )
        admission = text.split("## Workflow admission", 1)

        self.assertEqual(2, len(admission), "missing Workflow admission section")
        for term in (
            "schema",
            "fixture format",
            "script",
            "workflow-named",
            "browser-game",
            "2026-08-28",
            "warning",
        ):
            with self.subTest(term=term):
                self.assertIn(term, admission[1])


if __name__ == "__main__":
    unittest.main()


# Keep this import after the direct-run seam to preserve its historical scope.
from tests.test_validator_cases.corpus_and_surfaces import TestSurfaceBudgets  # noqa: E402
from tests.test_validator_cases.corpus_and_surfaces import TestRoutingBlockBudget  # noqa: E402
