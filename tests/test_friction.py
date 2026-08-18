"""Compatibility collector for the partitioned friction regression suite."""
from __future__ import annotations

from tests.test_friction_cases.cli import *  # noqa: F401,F403
from tests.test_friction_cases.refusal import *  # noqa: F401,F403
from tests.test_friction_cases.storage import *  # noqa: F401,F403
from tests.test_friction_cases.storage_lock import *  # noqa: F401,F403

if __name__ == "__main__":
    unittest.main()
