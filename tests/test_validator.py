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


if __name__ == "__main__":
    unittest.main()


# Keep this import after the direct-run seam to preserve its historical scope.
from tests.test_validator_cases.corpus_and_surfaces import TestSurfaceBudgets  # noqa: E402
