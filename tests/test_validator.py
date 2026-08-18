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


if __name__ == "__main__":
    unittest.main()


# Keep this import after the direct-run seam to preserve its historical scope.
from tests.test_validator_cases.corpus_and_surfaces import TestSurfaceBudgets  # noqa: E402
