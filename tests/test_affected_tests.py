"""Compatibility collector for the partitioned affected-test resolver suite."""
from __future__ import annotations

from tests.test_affected_tests_cases.fixture_tree import *  # noqa: F401,F403
from tests.test_affected_tests_cases.live_repo import *  # noqa: F401,F403

if __name__ == "__main__":
    unittest.main()
