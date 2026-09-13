"""Selected FxTwitter reads retain identity, third-party provenance and typed failures."""
from tests.test_social_adapters_cases._support import *


class SelectedConversationTests(unittest.TestCase):
    def test_conversation_retains_root_replies_counts_and_provenance_once(self):
        page, opener = fxtwitter_page("conversation.json", hydration(X_ROOT_ID))
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].url, "https://api.fxtwitter.com/2/conversation/" + X_ROOT_ID)
        ids = [record.native_item_id for record in page.records]
        self.assertEqual(ids.count(X_ROOT_ID), 1)
        self.assertGreater(len(ids), 1)
        self.assertTrue(any(record.native_parent_id for record in page.records))
        self.assertTrue(all("third_party_archive" in record.loss for record in page.records))
        self.assertTrue(any(record.engagement for record in page.records))
        self.assertEqual(page.cursor_out, "")

    def test_unproved_continuation_is_never_sent(self):
        page, opener = fxtwitter_page("conversation.json", hydration(X_ROOT_ID, cursor="next-page"))
        self.assertNotIn("cursor=", opener.opened[0].url)
        self.assertEqual(page.cursor_out, "")

    def test_unsupported_operations_refuse_before_a_read(self):
        for query in ("spacex", "search:spacex", "search_top:spacex", "timeline:SpaceX", "user:SpaceX", "conversation:abc"):
            with self.subTest(query=query), self.assertRaises(adapters.AdapterError):
                fxtwitter_page("conversation.json", discovery(query))

    def test_refusals_are_operator_failures_and_never_platform_silence(self):
        for status, fixture, outcome, loss in (
            (404, "conversation_not_found_404.json", "failed", "http_status"),
            (429, "conversation_not_found_404.json", "failed", "rate_limited"),
            (200, "conversation_reshaped.json", "failed", "schema_drift"),
            (200, "code_500_in_200.json", "failed", "http_status"),
            (200, "code_404_in_200.json", "empty", None),
        ):
            with self.subTest(status=status, fixture=fixture):
                page, opener = fxtwitter_page(fixture, hydration(X_ROOT_ID), status=status)
                self.assertEqual(page.outcome, outcome)
                self.assertEqual(len(opener.opened), 1)
                if loss:
                    self.assertIn(loss, page.loss)
                self.assertNotIn("auth_required", page.loss)

    def test_non_json_and_unreported_counts_are_not_invented(self):
        page, _ = answered(x_fxtwitter, FXTWITTER_ROUTE, "broken", hydration(X_ROOT_ID))
        self.assertEqual(page.loss, ("malformed_json",))
        for value in (True, False, None, 1.5, "1.2K", "21,068"):
            self.assertIsNone(x_fxtwitter.exact_count(value))
        self.assertEqual(x_fxtwitter.exact_count(0), 0)
