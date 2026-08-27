"""Compatibility seam for the partitioned reader UI regression suite."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import ui_frontend

from tests.test_ui_cases.root_resolution import *  # noqa: F401,F403
from tests.test_ui_cases.rendering import *  # noqa: F401,F403
from tests.test_ui_cases.ticket_security import *  # noqa: F401,F403
from tests.test_ui_cases.graph import *  # noqa: F401,F403
from tests.test_ui_cases.active_polling import *  # noqa: F401,F403
from tests.test_ui_cases.feeds_validation import *  # noqa: F401,F403
from tests.test_ui_cases.domain_projections import *  # noqa: F401,F403
from tests.test_ui_cases.artifacts_projection import *  # noqa: F401,F403
from tests.test_ui_cases.experience_foundation_gap import *  # noqa: F401,F403
from tests.test_ui_cases.experience_projection import *  # noqa: F401,F403
from tests.test_ui_cases.http_server import *  # noqa: F401,F403
from tests.test_ui_cases.module_floor import *  # noqa: F401,F403
from tests.test_ui_cases.projection_modules import *  # noqa: F401,F403
from tests.test_ui_cases.projection_security import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_projection import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_http import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_catalog import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_compositions import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_identity import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_skills import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_sources import *  # noqa: F401,F403
from tests.test_ui_cases.workflows_summary import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_index import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_rendering import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_cache import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_containment import *  # noqa: F401,F403
from tests.test_ui_cases.session_graph import *  # noqa: F401,F403
from tests.test_ui_cases.session_activity import *  # noqa: F401,F403
from tests.test_ui_cases.session_rendering import *  # noqa: F401,F403
from tests.test_ui_cases.platform_admission import *  # noqa: F401,F403
from tests.test_ui_cases.run_folder_projection import *  # noqa: F401,F403


class VisualDiffExitTest(unittest.TestCase):
    def test_changed_capture_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            actual, goldens = root / "actual", root / "goldens"
            actual.mkdir()
            goldens.mkdir()
            (actual / "home.png").write_bytes(b"new")
            (goldens / "home.png").write_bytes(b"old")
            output, errors = io.StringIO(), io.StringIO()
            with mock.patch.object(
                ui_frontend, "_view_manifest",
                return_value={"views": [{"identity": "home"}]},
            ), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = ui_frontend.main([
                    "diff", "--actual", str(actual), "--goldens", str(goldens),
                    "--manifest", "ignored.json",
                ])
        self.assertEqual(1, status)
        self.assertIn('"different"', output.getvalue())
        self.assertIn("ui-frontend diff: FAIL", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
