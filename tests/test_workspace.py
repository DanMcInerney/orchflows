"""Compatibility discovery seam for every workspace behavioral case."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_workspace_cases.cli_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.contract_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.grade_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.operation_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.prepare import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.sharing_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.start_cases import *  # noqa: E402,F401,F403


if __name__ == "__main__":
    unittest.main()
