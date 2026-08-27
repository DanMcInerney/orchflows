#!/usr/bin/env python3

"""Compatibility discovery seam for the five live probe harnesses.

Behavioral cases are partitioned by harness seam below this module. Importing
them here preserves the complete tests.test_live_harnesses collection.
"""

import unittest

from tests.test_live_harnesses_cases.grok_profile_cases import TestGrokRoleProfiles
from tests.test_live_harnesses_cases.loop_cases import (
    TestBuiltCommand,
    TestLoopAnalyzeRun,
    TestRunScenario,
)
from tests.test_live_harnesses_cases.profile_cases import (
    TestClaudeLiveProfiles,
    TestCodexLiveProfiles,
)
from tests.test_live_harnesses_cases.routing_grading_cases import (
    TestRoutingCaseLoader,
    TestRoutingCases,
    TestRoutingGrading,
)
from tests.test_live_harnesses_cases.routing_run_cases import TestRoutingBenchRun
from tests.test_live_harnesses_cases.routing_summary_cases import (
    TestRoutingBenchMain,
    TestRoutingSummary,
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
