"""Regression checks for the preflight tool's executable documentation."""

import unittest

from tools import preflight


class PreflightDocumentationTest(unittest.TestCase):
    def test_module_docstring_names_the_active_ci_topology(self):
        self.assertIn("five active CI legs", preflight.__doc__)
        self.assertIn("three Ubuntu, one macOS, and one Windows", preflight.__doc__)
        self.assertNotIn("nine CI cells", preflight.__doc__)


if __name__ == "__main__":
    unittest.main()
