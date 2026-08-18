"""Compatibility seam for the partitioned reader UI regression suite."""

import unittest

from tests.test_ui_cases.root_resolution import *  # noqa: F401,F403
from tests.test_ui_cases.rendering import *  # noqa: F401,F403
from tests.test_ui_cases.ticket_security import *  # noqa: F401,F403
from tests.test_ui_cases.graph import *  # noqa: F401,F403
from tests.test_ui_cases.active_polling import *  # noqa: F401,F403
from tests.test_ui_cases.feeds_validation import *  # noqa: F401,F403
from tests.test_ui_cases.http_server import *  # noqa: F401,F403
from tests.test_ui_cases.module_floor import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_index import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_rendering import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_cache import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_containment import *  # noqa: F401,F403
from tests.test_ui_cases.session_graph import *  # noqa: F401,F403
from tests.test_ui_cases.session_activity import *  # noqa: F401,F403
from tests.test_ui_cases.session_rendering import *  # noqa: F401,F403


if __name__ == "__main__":
    unittest.main()
