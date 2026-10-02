import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from benchkit.stopping import decide  # noqa: E402


class DecideTests(unittest.TestCase):
    def test_below(self):
        # 0 of 5 at level 0.8: upper bound 0.369 < 0.5
        self.assertEqual(decide(0, 5, low=0.5, high=0.9, level=0.8, max_attempts=20), "below")

    def test_above(self):
        # 5 of 5 at level 0.8: lower bound 0.631 > 0.5
        self.assertEqual(decide(5, 5, low=0.1, high=0.5, level=0.8, max_attempts=20), "above")

    def test_inside(self):
        # 50 of 100 at level 0.9: [0.414, 0.586] lies within [0.4, 0.6]
        self.assertEqual(decide(50, 100, low=0.4, high=0.6, max_attempts=200), "inside")

    def test_continue_while_undecided(self):
        self.assertEqual(decide(3, 5, low=0.2, high=0.8, max_attempts=20), "continue")
        self.assertEqual(decide(0, 0, low=0.2, high=0.8, max_attempts=20), "continue")

    def test_exhausted_at_the_cap(self):
        self.assertEqual(decide(3, 5, low=0.2, high=0.8, max_attempts=5), "exhausted")
        self.assertEqual(decide(30, 50, low=0.2, high=0.55, max_attempts=50), "exhausted")

    def test_decisive_result_wins_at_the_cap(self):
        self.assertEqual(decide(0, 5, low=0.5, high=0.9, level=0.8, max_attempts=5), "below")

    def test_interval_straddling_a_band_edge_is_undecided(self):
        # 2 of 5 at 0.9: [0.076, 0.811] overlaps the band edge at 0.5
        self.assertEqual(decide(2, 5, low=0.5, high=0.9, max_attempts=20), "continue")

    def test_level_changes_the_decision(self):
        # 0 of 5: upper bound 0.369 at level 0.8 but 0.522 at level 0.95
        self.assertEqual(decide(0, 5, low=0.4, high=0.9, level=0.8, max_attempts=20), "below")
        self.assertEqual(decide(0, 5, low=0.4, high=0.9, level=0.95, max_attempts=20), "continue")

    def test_rejects_bad_input(self):
        for kwargs in ({"successes": 6, "attempts": 5, "low": 0.1, "high": 0.9, "max_attempts": 9},
                       {"successes": 1, "attempts": 5, "low": 0.9, "high": 0.1, "max_attempts": 9},
                       {"successes": 1, "attempts": 5, "low": 0.1, "high": 0.9, "max_attempts": 0}):
            with self.assertRaises(ValueError):
                decide(**kwargs)


if __name__ == "__main__":
    unittest.main()
