"""Compatibility seam for the validation regression collection."""
import unittest

from tests.test_validate_cases.sink_contracts import (
    TestContractsNameTheSink,
    TestWorkItemLocationInvariant,
    TestWorklogStatesRunIdentity,
)
from tests.test_validate_cases.sink_law import (
    TestFrictionFallbackNamesTheSink,
    TestOnlyCanaryAndBinMentionsSurvive,
    TestOneProseOwnerForThePath,
    TestRepositoryKeepsTwoSubdirectories,
    TestSelfImproveSelectsByScopeAndProject,
    TestTheLawNamesTheSinkRoot,
    TestVocabularyResolvesToTheSink,
)
from tests.test_validate_cases.validator_ownership import (
    CrossTierDuplicationTest,
    FrictionLocationSyncTest,
    TestPackWorkspaceTableAgainstPacks,
    TestSyncCheckIsGone,
)

if __name__ == "__main__":
    unittest.main()
