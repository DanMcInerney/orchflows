"""The required-check runner: order, exit mapping, payload, and its cache."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.test_run_required_cases.harness import REPO_ROOT, RunRequiredCase

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class TestRefusal(RunRequiredCase):
    """Exit 2 is reserved for what the runner cannot honestly attempt."""

    def test_a_directory_that_is_not_a_checkout_is_refused(self):
        outside = Path(self.repo).parent / "not-a-checkout"
        outside.mkdir()
        status, _, _, err = self.invoke("--repo", str(outside))
        self.assertEqual(2, status)
        self.assertIn("git", err)
        self.assertEqual([], self.stub.calls())

    def test_a_missing_interpreter_is_refused(self):
        missing = Path(self.repo).parent / "stub" / "absent-python"
        status, _, _, err = self.invoke("--python", str(missing))
        self.assertEqual(2, status)
        self.assertIn("interpreter", err)
        self.assertEqual([], self.stub.calls())

    def test_a_refusal_names_itself_in_the_json_stream(self):
        outside = Path(self.repo).parent / "also-not-a-checkout"
        outside.mkdir()
        _, payload, _, _ = self.invoke("--repo", str(outside))
        self.assertIsNotNone(payload)
        self.assertEqual("required-check-refusal/v1", payload["kind"])
        self.assertTrue(payload["reason"])


if __name__ == "__main__":
    unittest.main()
