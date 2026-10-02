import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from benchkit import stats  # noqa: E402


class SignFlipTests(unittest.TestCase):
    def test_four_positive_clusters(self):
        self.assertEqual(stats.sign_flip_p([1, 2, 3, 4]), 0.125)
        self.assertEqual(stats.sign_flip_p([1, 2, 3, 4], alternative="greater"), 0.0625)
        self.assertEqual(stats.sign_flip_p([1, 2, 3, 4], alternative="one-sided"), 0.0625)
        self.assertEqual(stats.sign_flip_p([1, 2, 3, 4], alternative="less"), 1.0)

    def test_zero_cluster_doubles_assignments_not_the_sum(self):
        # sums reach +-4 under 4 of the 16 assignments (the zero's sign is free)
        self.assertEqual(stats.sign_flip_p([1, 2, 0, 1]), 0.25)

    def test_symmetric_and_null_cases(self):
        self.assertEqual(stats.sign_flip_p([1, -1]), 1.0)
        self.assertEqual(stats.sign_flip_p([0, 0, 0]), 1.0)
        self.assertEqual(stats.sign_flip_p([-1, -2, -3, -4], alternative="less"), 0.0625)

    def test_single_cluster_cannot_reject(self):
        self.assertEqual(stats.sign_flip_p([5.0]), 1.0)

    def test_monte_carlo_is_deterministic_and_close_to_exact(self):
        first = stats.sign_flip_p([1, 2, 3, 4], exact_max=0, draws=20000, seed=7)
        self.assertEqual(first, stats.sign_flip_p([1, 2, 3, 4], exact_max=0, draws=20000, seed=7))
        self.assertAlmostEqual(first, 0.125, delta=0.015)

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            stats.sign_flip_p([])
        with self.assertRaises(ValueError):
            stats.sign_flip_p([1.0, math.nan])
        with self.assertRaises(ValueError):
            stats.sign_flip_p([1.0], alternative="sideways")


class WildClusterTests(unittest.TestCase):
    def test_two_clusters_hand_computed(self):
        # residuals -1, +1: reweighted mean residuals {-1, 0, 0, +1} around 2
        self.assertEqual(stats.wild_cluster_ci([1.0, 3.0]), (1.0, 3.0))

    def test_four_clusters_hand_computed(self):
        # residuals .375 -.125 -.625 .375: the largest reweighted mean is their mean absolute value, .375
        low, high = stats.wild_cluster_ci([1.0, 0.5, 0.0, 1.0])
        self.assertAlmostEqual(low, 0.25)
        self.assertAlmostEqual(high, 1.0)

    def test_interval_brackets_the_mean_and_widens_with_level(self):
        values = [0.1, 0.4, 0.2, 0.9, 0.5, 0.3]
        mean = sum(values) / len(values)
        low90, high90 = stats.wild_cluster_ci(values, level=0.9)
        low99, high99 = stats.wild_cluster_ci(values, level=0.99)
        self.assertLess(low90, mean)
        self.assertGreater(high90, mean)
        self.assertLessEqual(low99, low90)
        self.assertGreaterEqual(high99, high90)

    def test_sampled_branch_is_deterministic(self):
        values = [float(i % 5) for i in range(14)]
        first = stats.wild_cluster_ci(values, exact_max=0, draws=2000, seed=3)
        self.assertEqual(first, stats.wild_cluster_ci(values, exact_max=0, draws=2000, seed=3))
        exact = stats.wild_cluster_ci(values, exact_max=14)
        self.assertAlmostEqual(first[0], exact[0], delta=0.15)
        self.assertAlmostEqual(first[1], exact[1], delta=0.15)

    def test_needs_two_clusters(self):
        with self.assertRaises(ValueError):
            stats.wild_cluster_ci([1.0])


class RankingTests(unittest.TestCase):
    def test_kendall_tau_b_with_ties(self):
        # pairs: 3 concordant, 1 discordant, 1 tied in x, 1 tied in y -> 2 / sqrt(5 * 5)
        self.assertAlmostEqual(stats.kendall_tau_b([1, 2, 2, 3], [1, 3, 2, 2]), 0.4)

    def test_kendall_tau_b_extremes(self):
        self.assertEqual(stats.kendall_tau_b([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertEqual(stats.kendall_tau_b([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertTrue(math.isnan(stats.kendall_tau_b([1, 1, 1], [1, 2, 3])))

    def test_pair_accuracy_counts_ties_as_half(self):
        scores = {"a": 3, "b": 2, "c": 2, "d": 1}
        known = [("a", "b"), ("b", "c"), ("c", "d"), ("a", "d")]
        self.assertEqual(stats.pair_accuracy(scores, known), 0.875)
        self.assertEqual(stats.pair_accuracy({"a": 1, "b": 2}, [("a", "b")]), 0.0)

    def test_pair_accuracy_skips_unscored_members(self):
        self.assertEqual(stats.pair_accuracy({"a": 2, "b": 1, "c": None}, [("a", "b"), ("c", "a"), ("a", "z")]), 1.0)
        self.assertTrue(math.isnan(stats.pair_accuracy({}, [("a", "b")])))

    def test_order_null_p_total_order_of_six(self):
        members = list("abcdef")
        known = [(members[i], members[j]) for i in range(6) for j in range(i + 1, 6)]
        # permutations of six with at most 2 inversions: 1 + 5 + 14 = 20 of 720
        p = stats.order_null_p(members, known, 13 / 15)
        self.assertEqual(round(p, 4), 0.0278)
        self.assertAlmostEqual(p, 20 / 720)
        self.assertAlmostEqual(stats.order_null_p(members, known, 1.0), 1 / 720)
        self.assertEqual(stats.order_null_p(members, known, 0.0), 1.0)

    def test_order_null_p_sampled_matches_exact(self):
        members = list("abcdef")
        known = [(members[i], members[j]) for i in range(6) for j in range(i + 1, 6)]
        sampled = stats.order_null_p(members, known, 13 / 15, exact_max=3, draws=40000, seed=1)
        self.assertAlmostEqual(sampled, 20 / 720, delta=0.006)

    def test_order_null_p_partial_known_pairs(self):
        # two disjoint pairs: P(both ordered right) = 1/4; members outside the pairs do not matter
        p = stats.order_null_p(list("abcdefgh"), [("a", "b"), ("c", "d")], 1.0)
        self.assertAlmostEqual(p, 0.25)

    def test_order_null_p_rejects_foreign_members(self):
        with self.assertRaises(ValueError):
            stats.order_null_p(["a"], [("a", "b")], 1.0)


class ClopperPearsonTests(unittest.TestCase):
    def test_zero_of_five(self):
        low, high = stats.clopper_pearson(0, 5, 0.8)
        self.assertEqual(low, 0.0)
        self.assertAlmostEqual(high, 1 - 0.1 ** 0.2, places=9)
        self.assertAlmostEqual(high, 0.369, places=3)

    def test_five_of_five_mirrors(self):
        low, high = stats.clopper_pearson(5, 5, 0.8)
        self.assertEqual(high, 1.0)
        self.assertAlmostEqual(low, 0.1 ** 0.2, places=9)

    def test_one_of_two_closed_form(self):
        low, high = stats.clopper_pearson(1, 2, 0.9)
        self.assertAlmostEqual(low, 1 - math.sqrt(0.95), places=9)
        self.assertAlmostEqual(high, math.sqrt(0.95), places=9)

    def test_fifty_of_hundred_reference_value(self):
        low, high = stats.clopper_pearson(50, 100, 0.95)
        self.assertAlmostEqual(low, 0.3983, places=3)
        self.assertAlmostEqual(high, 0.6017, places=3)

    def test_large_n_and_empty(self):
        low, high = stats.clopper_pearson(3000, 10000, 0.95)
        self.assertLess(low, 0.3)
        self.assertGreater(high, 0.3)
        self.assertEqual(stats.clopper_pearson(0, 0, 0.9), (0.0, 1.0))

    def test_rejects_bad_input(self):
        for k, n, level in ((6, 5, 0.9), (-1, 5, 0.9), (1, 5, 1.0), (1, 5, 0.0)):
            with self.assertRaises(ValueError):
                stats.clopper_pearson(k, n, level)


if __name__ == "__main__":
    unittest.main()
