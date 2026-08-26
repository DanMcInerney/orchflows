"""Compatibility discovery seam for validator compiler regression cases."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_validator_cases.support import _IsolatedTree
from tests.test_validator_cases.availability_and_packages import (
    TestASkippedCheckSaysSo,
    TestSyntheticPackageBoundaryInputs,
)
from tests.test_validator_cases.contracts_and_names import (
    TestEnvelopeCheck,
    TestNameResolution,
)
from tests.test_validator_cases.corpus_and_surfaces import (
    TestDuplicationCorpus,
    TestLensAnchor,
    TestLicensedCopies,
    TestWordBudgetAndLinks,
)
from tests.test_validator_cases.repo_and_frontmatter import (
    TestFrontmatterBoundaryInputs,
    TestPinFlagRoundTrip,
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
    def _write_skill(self, name, body, tier="instances", role="worker"):
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

    def test_a_utility_call_edge_is_primitive_impurity(self):
        self._write_skill(
            "orch-target", "Require: input.\nNever: skip.\nReturn: the completed ticket.\n"
        )
        self._write_skill(
            "orch-helper",
            "Require: input.\nCall `orch-target`.\nNever: skip.\nReturn: the completed ticket.\n",
            tier="utilities",
        )
        result = self._run()
        self.assertIn("utility skills are primitives", result.stdout)

    def test_pack_control_flow_is_rejected(self):
        self._write_pack(
            "orch-flow-pack",
            "If evidence is absent, then delegate and stop.\n",
        )
        result = self._run()
        self.assertIn("pack body carries control flow", result.stdout)

    def test_duplicate_pack_cell_rows_are_rejected(self):
        rows = "\n".join(
            f"| {cell} | binding |" for cell in validate.PACK_SIGNATURE_CELLS
        )
        self._write_pack(
            "orch-duplicate-pack",
            "| cell | binding |\n| --- | --- |\n" + rows + "\n| executor | other |\n",
        )
        result = self._run()
        self.assertIn("pack signature table repeats cell(s): executor", result.stdout)

    def test_a_new_executor_is_not_outside_envelope_admission(self):
        self._write_skill(
            "orch-new-executor", "Require: input.\nNever: skip.\nReturn: assumptions.\n"
        )
        result = self._run()
        self.assertIn("does not lead with the result envelope", result.stdout)

    def test_envelope_words_in_a_sentence_are_not_an_envelope(self):
        self._write_skill(
            "orch-prose-envelope",
            "Require: input.\nNever: skip.\n"
            "Return: the ticket has status, result identity, and verification.\n",
        )
        result = self._run()
        self.assertIn("does not lead with structured result-envelope fields", result.stdout)

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


if __name__ == "__main__":
    unittest.main()


# Keep this import after the direct-run seam to preserve its historical scope.
from tests.test_validator_cases.corpus_and_surfaces import TestSurfaceBudgets  # noqa: E402
