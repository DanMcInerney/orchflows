"""Compatibility seam for suite-check and preflight regression cases.

The cases live in concern modules whose names do not match unittest's
``test*.py`` discovery pattern. Re-exporting every ``TestCase`` here preserves
the historical ``tests.test_suite_check`` seam and keeps full-suite discovery
from collecting the same tests twice.
"""

from __future__ import annotations

import sys

from tests._repo_root import ROOT as REPO_ROOT
sys.path.insert(0, str(REPO_ROOT))

from tests.test_suite_check_cases.audit import (
    TestAuditSkips,
    TestBuildStrippedPath,
)
from tests.test_suite_check_cases.matrix import (
    TestPreflightMatrix,
    TestPreflightOsLine,
    TestPreflightWhich,
)
from tests.test_suite_check_cases.snapshot import (
    TestDiffSnapshots,
    TestHashAndSnapshot,
    TestSnapshotDirection,
)
from tests.test_suite_check_cases.subprocess import TestHarnessSubprocess

__all__ = [
    "TestAuditSkips",
    "TestBuildStrippedPath",
    "TestDiffSnapshots",
    "TestHarnessSubprocess",
    "TestHashAndSnapshot",
    "TestPreflightMatrix",
    "TestPreflightOsLine",
    "TestPreflightWhich",
    "TestSnapshotDirection",
]


if __name__ == "__main__":
    import unittest

    unittest.main()
