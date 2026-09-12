"""Historical Google News discovery and the exact publication-time filter."""

import unittest
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import parse_qs, urlsplit

from super_research import runner, schema, transport


def acquire(query, start="", end="", published=()):
    items = []
    for index, stamp in enumerate(published):
        moment = datetime.strptime(stamp, schema.INSTANT_FORMAT).replace(tzinfo=timezone.utc)
        items.append(
            '<item><title>Item {0}</title><link>https://example.net/{0}</link>'
            '<description>Candidate</description><pubDate>{1}</pubDate>'
            '<source url="https://example.net">Publisher</source></item>'.format(
                index, format_datetime(moment)
            )
        )
    body = "<rss><channel>" + "".join(items) + "</channel></rss>"
    manifest = schema.parse_manifest({
        "manifest_id": "web-window", "as_of": "2026-09-12T23:59:59Z",
        "steps": [{"step_id": "search", "kind": "discovery", "adapter_id": "web_search",
                   "query": query, "max_items": 10, "window_start": start, "window_end": end}],
    })
    carrier = transport.Transport(
        opener=lambda request: (200, body, "application/rss+xml", request.url, ()),
        now=lambda: "2026-09-12T12:00:00Z",
    )
    artifact = runner.run_acquisition(manifest, carrier=carrier)
    wire_query = parse_qs(urlsplit(carrier.calls[0].url).query)["q"][0]
    return artifact, wire_query


class GoogleNewsWindowTests(unittest.TestCase):
    def test_historical_window_does_not_become_a_relative_search_from_today(self):
        _, query = acquire("gnews:quantum computing", "2026-07-01T00:00:00Z", "2026-07-31T23:59:59Z")
        self.assertEqual(query, "quantum computing after:2026-06-30 before:2026-08-01")

    def test_exact_inclusive_endpoints_are_filtered_once_after_day_level_discovery(self):
        start, end = "2026-07-01T12:00:00Z", "2026-07-31T12:00:00Z"
        artifact, query = acquire("gnews:quantum", start, end, (
            "2026-07-01T11:59:59Z", start, end, "2026-07-31T12:00:01Z",
        ))
        self.assertEqual([record.published_at for record in artifact.records], [start, end])
        self.assertEqual(query, "quantum after:2026-06-30 before:2026-08-01")

    def test_midnight_end_still_retrieves_the_endpoint_day(self):
        end = "2026-08-01T00:00:00Z"
        artifact, query = acquire("gnews:quantum", end, end, (
            "2026-07-31T23:59:59Z", end, "2026-08-01T00:00:01Z",
        ))
        self.assertEqual([record.published_at for record in artifact.records], [end])
        self.assertEqual(query, "quantum after:2026-07-31 before:2026-08-02")

    def test_window_replaces_contradictory_query_operators_but_preserves_literals(self):
        _, query = acquire(
            'gnews:site:example.net "when:7d" quantum after:2020-01-01 BEFORE:2021-01-01 when:1d',
            "2026-07-01T00:00:00Z", "2026-07-31T00:00:00Z",
        )
        self.assertEqual(query, 'site:example.net "when:7d" quantum after:2026-06-30 before:2026-08-01')

    def test_all_time_removes_dates_instead_of_inventing_a_window(self):
        _, query = acquire("gnews:quantum after:2020-01-01 before:2021-01-01 when:30d")
        self.assertEqual(query, "quantum")

    def test_one_sided_windows_do_not_invent_the_other_endpoint(self):
        for start, end, expected in (
            ("2026-07-01T00:00:00Z", "", "quantum after:2026-06-30"),
            ("", "2026-07-31T23:59:59Z", "quantum before:2026-08-01"),
        ):
            with self.subTest(start=start, end=end):
                _, query = acquire("gnews:quantum", start, end)
                self.assertEqual(query, expected)

    def test_extreme_dates_do_not_overflow_or_exclude_valid_candidates(self):
        _, query = acquire("gnews:quantum", "0001-01-01T00:00:00Z", "9999-12-31T23:59:59Z")
        self.assertEqual(query, "quantum")


if __name__ == "__main__":
    unittest.main()
