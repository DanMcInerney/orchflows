"""Bounded subprocess keeps the real workspace fixture's sink local to its process."""
from pathlib import Path
import subprocess
import sys
import unittest


class RecordLandingTests(unittest.TestCase):
    def test_same_repository_attempt_lands_and_exports_after_candidate_retirement(self):
        result = subprocess.run([sys.executable, '-m', 'tests.benchmaker_landing_probe'],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
