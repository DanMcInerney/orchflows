"""Normalization boundary cases."""

from .support import *  # noqa: F403

class NormalizeTest(unittest.TestCase):
    """Normalization derives artifact fields without inventing any."""

    def test_engagement_refuses_a_boolean_value(self):
        with self.assertRaises(normalize.NormalizeError):
            normalize.engagement_snapshots((("score", True),), FROZEN_OBSERVED_AT)

    def test_engagement_refuses_a_negative_value(self):
        with self.assertRaises(normalize.NormalizeError):
            normalize.engagement_snapshots((("score", -1),), FROZEN_OBSERVED_AT)

    def test_locator_normalization_is_stable_across_case_and_trailing_slash(self):
        self.assertEqual(
            normalize.normalized_locator("HTTPS://Www.Reddit.com/r/LocalLLaMA/comments/1abc234/"),
            normalize.normalized_locator("https://www.reddit.com/r/LocalLLaMA/comments/1abc234"),
        )

    def test_content_hash_is_empty_when_there_is_no_content(self):
        self.assertEqual(normalize.content_hash(""), "")
        self.assertNotEqual(normalize.content_hash("a snippet"), "")
