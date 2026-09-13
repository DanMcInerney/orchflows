"""Window capability distinguishes measured support, measured refusal and unknown."""
import unittest
from super_research import runner as window_reach


class TheLossCodeMappingIsThreeWayTest(unittest.TestCase):
    """`window_loss_code`: the one place the three readings become two codes."""

    def test_unmeasured_gets_its_own_code(self):
        self.assertEqual(
            window_reach.window_loss_code(None), window_reach.WINDOW_CAPABILITY_UNMEASURED
        )

    def test_measured_unable_gets_the_pre_existing_code(self):
        self.assertEqual(
            window_reach.window_loss_code(False), window_reach.WINDOW_NOT_HONORED
        )

    def test_measured_able_gets_no_code_at_all(self):
        self.assertIsNone(window_reach.window_loss_code(True))

    def test_the_two_codes_are_distinct(self):
        self.assertNotEqual(
            window_reach.WINDOW_CAPABILITY_UNMEASURED, window_reach.WINDOW_NOT_HONORED
        )


if __name__ == "__main__":
    unittest.main()
