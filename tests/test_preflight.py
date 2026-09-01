"""Regression checks for the preflight tool's executable documentation."""

import unittest

from tools import preflight, render_ci_topology


class PreflightDocumentationTest(unittest.TestCase):
    def test_module_docstring_names_the_active_ci_topology(self):
        # The leg breakdown is generated (tools/render_ci_topology.py), so
        # this asks the renderer what the truth is instead of hardcoding a
        # second copy that would only agree with checks.yml by accident.
        self.assertIn(render_ci_topology.leg_total_clause(), preflight.__doc__)
        self.assertNotIn("nine CI cells", preflight.__doc__)


if __name__ == "__main__":
    unittest.main()
