#!/usr/bin/env python3

"""Compatibility discovery seam for the live probe harnesses.

Behavioral cases are partitioned by harness seam below this module. Importing
them here preserves the complete tests.test_live_harnesses collection.
"""

import unittest

from tests.test_live_harnesses_cases.grok_profile_cases import TestGrokRoleProfiles
from tests.test_live_harnesses_cases.profile_cases import (
    TestClaudeLiveProfiles,
    TestCodexLiveProfiles,
)
from tests.test_live_harnesses_cases.sweep_cases import (
    TestCleanup,
    TestCleanupFriction,
    TestLogDirIsInTheSink,
    TestMainGuard,
    TestRunId,
    TestRunLiveSweepCleanupPaths,
    TestSnapshotPath,
    TestSweepAnalyzeRun,
)


if __name__ == "__main__":
    unittest.main()
