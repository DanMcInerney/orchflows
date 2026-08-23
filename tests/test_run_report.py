"""Compatibility collector for the partitioned speed-report suite."""

from __future__ import annotations

import unittest

from tests.test_run_report_cases.families import *  # noqa: F401,F403
from tests.test_run_report_cases.identity import *  # noqa: F401,F403
from tests.test_run_report_cases.runs import *  # noqa: F401,F403

if __name__ == "__main__":
    unittest.main()
