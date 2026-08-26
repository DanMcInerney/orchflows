"""Discovery seam for the repository's current carriage checks.

The cases are partitioned by behavioral seam in ``test_carriage_cases``;
explicit imports keep ``tests.test_carriage`` as the complete collection used
by the sharded runner and existing callers.
"""

import unittest

from tests.test_carriage_cases.carriage_validation import (
    TestCarriageAgainstRepo,
    TestCarriagePackChecks,
    TestCarriageSeededViolation,
)
from tests.test_carriage_cases.copy_faithfulness import CopyFaithfulnessClauseTest
from tests.test_carriage_cases.friction_destination import FrictionDestinationTest
from tests.test_carriage_cases.script_ownership import ScriptOwnershipTest
from tests.test_carriage_cases.subcommand_reach import SubcommandReachTest
from tests.test_carriage_cases.verification_flow import (
    ReverificationSplitTest,
    TipCheckTest,
)

__all__ = [
    "CopyFaithfulnessClauseTest",
    "FrictionDestinationTest",
    "ReverificationSplitTest",
    "ScriptOwnershipTest",
    "SubcommandReachTest",
    "TestCarriageAgainstRepo",
    "TestCarriagePackChecks",
    "TestCarriageSeededViolation",
    "TipCheckTest",
]


if __name__ == "__main__":
    unittest.main()
