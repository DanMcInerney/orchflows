"""Complete reader regression suite.

The reader's migrated Python partitions are intentionally assembled here so
that their cases run under the reader's own dependency contract.  The library
runner does not discover this module: the reader gate invokes it explicitly.
"""

import contextlib
import importlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reader.tools import ui_frontend

ACTIVE_MODULES = (
    "reader.tests.test_reader_api",
    "reader.tests.test_reader_extraction",
    "reader.tests.test_ui_cases.artifacts_projection",
    "reader.tests.test_ui_cases.domain_projections",
    "reader.tests.test_ui_cases.experience_foundation_gap",
    "reader.tests.test_ui_cases.experience_projection",
    "reader.tests.test_ui_cases.graph",
    "reader.tests.test_ui_cases.module_floor",
    "reader.tests.test_ui_cases.platform_admission",
    "reader.tests.test_ui_cases.projection_security",
    "reader.tests.test_ui_cases.root_resolution",
    "reader.tests.test_ui_cases.run_folder_projection",
    "reader.tests.test_ui_cases.session_activity",
    "reader.tests.test_ui_cases.ticket_security",
    "reader.tests.test_ui_cases.transcript_containment",
    "reader.tests.test_ui_cases.workflows_catalog",
    "reader.tests.test_ui_cases.workflows_compositions",
    "reader.tests.test_ui_cases.workflows_http",
    "reader.tests.test_ui_cases.workflows_identity",
    "reader.tests.test_ui_cases.workflows_projection",
    "reader.tests.test_ui_cases.workflows_skills",
    "reader.tests.test_ui_cases.workflows_sources",
    "reader.tests.test_ui_cases.workflows_summary",
)


def load_tests(loader, tests, pattern):
    """Load each active reader partition once under its declared package."""

    del tests, pattern
    suite = unittest.TestSuite()
    for name in ACTIVE_MODULES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(name)))
    suite.addTest(VisualDiffExitTest("test_changed_capture_exits_nonzero"))
    return suite


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
