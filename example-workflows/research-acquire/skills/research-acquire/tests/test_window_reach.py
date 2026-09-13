"""Origin window capability stays distinct from the core's row filter."""
import unittest
from super_research import runner, schema
from tests import helpers
from tests.test_keyless_cases.support import roster_seeds


def run_hn(query, start="", end=""):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, roster_seeds())
    step = schema.AcquisitionStep(step_id="hn", kind="discovery", adapter_id="hacker_news",
        query=query, max_items=5, window_start=start, window_end=end)
    result, records, _ = runner.run_step(step, carrier, "a", "m", clock=clock.monotonic)
    return result, records, opener


class WindowReachTests(unittest.TestCase):
    def test_every_retained_adapter_has_a_declared_capability(self):
        self.assertEqual(set(runner.ADAPTER_IDS), set(runner.WINDOW_REACH))
        for adapter, operation in (("missing", ""), ("hacker_news", "missing")):
            with self.assertRaises(runner.WindowReachError):
                runner.can_bound_at_origin(adapter, operation)

    def test_empty_old_window_does_not_disguise_an_origin_without_date_filter(self):
        start, end = "2016-01-01T00:00:00Z", "2016-02-01T00:00:00Z"
        searched, search_records, _ = run_hn("python", start, end)
        hydrated, item_records, _ = run_hn("item:44831234", start, end)
        self.assertFalse(search_records)
        self.assertFalse(item_records)
        self.assertNotIn(runner.WINDOW_NOT_HONORED, searched.loss)
        self.assertIn(runner.WINDOW_NOT_HONORED, hydrated.loss)

    def test_a_window_does_not_change_an_item_request_and_no_window_adds_no_loss(self):
        first, records, a = run_hn("item:44831234")
        second, _, b = run_hn("item:44831234", "2016-01-01T00:00:00Z")
        self.assertTrue(records)
        self.assertNotIn(runner.WINDOW_NOT_HONORED, first.loss)
        self.assertIn(runner.WINDOW_NOT_HONORED, second.loss)
        self.assertEqual(a.opened[0].url, b.opened[0].url)
