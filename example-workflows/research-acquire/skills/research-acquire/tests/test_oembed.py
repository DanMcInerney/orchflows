"""`oembed`: one platform url in, one record out, over six declared surfaces.

Standalone and offline throughout: every carrier here is
`helpers.offline_transport` over either a real captured payload
(`tests/fixtures/oembed/*.json`, X's status and one more provider) or a
small synthetic answer shaped exactly like this module's own docstring
describes the remaining four. No test in this file names a declared route's
origin literally — an item url on a host `_support/route_catalog_k0.py`
declares is composed from `transport.route_constant(...).origin` at run
time, the way the item under test is required to; X's `x.com` is not a
declared route origin (the declared one is `publish.x.com`), so its status
url is spelled directly, the same as the probe in `probes.py` does.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from super_research import transport
from super_research.adapters import AdapterRequest, oembed
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "oembed"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def item_url_on(route_id: str, path: str) -> str:
    """One example item url on a declared route's own origin, composed at run

    time rather than spelled here: the route-ownership law reserves a
    declared route's host literal for the module that owns it, and this
    test module is not one.
    """

    return transport.route_constant(route_id).origin + path


X_STATUS_URL = "https://x.com/jack/status/20"
VIMEO_ITEM_URL = item_url_on(transport.VIMEO_OEMBED_ROUTE, "/76979871")
SPOTIFY_ITEM_URL = item_url_on(transport.SPOTIFY_OEMBED_ROUTE, "/track/7GhIk7Il098yCjg4BQjzvb")
SOUNDCLOUD_ITEM_URL = item_url_on(transport.SOUNDCLOUD_OEMBED_ROUTE, "/forss/flickermood")
YOUTUBE_ITEM_URL = item_url_on(transport.YOUTUBE_OEMBED_ROUTE, "/watch?v=dQw4w9WgXcQ")
TIKTOK_ITEM_URL = item_url_on(transport.TIKTOK_OEMBED_ROUTE, "/@scout2015/video/6718335390845095173")

# Minimal synthetic answers, shaped exactly like the module's own docstring
# measures the four providers not captured as a fixture. Every string in
# them is either this module's own vocabulary or a neutral placeholder on no
# declared route's host.
VIMEO_PAYLOAD = json.dumps(
    {
        "type": "video",
        "title": "Rock Climbing on Cliffs of Insanity",
        "author_name": "Vimeo Staff",
        "author_url": "https://example.com/vimeo-staff",
    }
)
SPOTIFY_PAYLOAD = json.dumps(
    {
        "type": "rich",
        "title": "Never Gonna Give You Up",
        "thumbnail_url": "https://example.com/spotify-thumb.jpg",
    }
)
SOUNDCLOUD_PAYLOAD = json.dumps(
    {
        "type": "rich",
        "title": "Flickermood by Forss",
        "author_name": "Forss",
        "author_url": "https://example.com/soundcloud-forss",
        "thumbnail_url": "https://example.com/soundcloud-thumb.jpg",
        "description": "From the Soulhack album",
    }
)


def fetch(route_id, body, target, content_type="application/json", status=200):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (status, body, content_type)}
    )
    page = oembed.fetch_native_page(carrier, AdapterRequest(step_id="s1", target_ids=(target,)))
    return page, opener


class OperationGrammarTest(unittest.TestCase):
    """`operation_for`: the six prefixes, and nothing inferred from an argument."""

    def test_each_of_the_six_prefixes_names_its_own_provider(self):
        for provider in oembed.OEMBED_OPERATIONS:
            with self.subTest(provider=provider):
                request = AdapterRequest(step_id="s", query=provider + ":https://example.com/i")
                self.assertEqual(
                    oembed.operation_for(request), (provider, "https://example.com/i")
                )

    def test_an_unprefixed_query_names_no_provider(self):
        request = AdapterRequest(step_id="s", query="just a plain query")
        self.assertEqual(oembed.operation_for(request), ("", "just a plain query"))

    def test_an_unknown_prefix_names_no_provider(self):
        request = AdapterRequest(step_id="s", query="dailymotion:https://example.com/i")
        self.assertEqual(
            oembed.operation_for(request), ("", "dailymotion:https://example.com/i")
        )

    def test_a_hydration_target_reads_the_same_grammar_as_a_query(self):
        request = AdapterRequest(step_id="s", target_ids=("x:" + X_STATUS_URL,))
        self.assertEqual(oembed.operation_for(request), ("x", X_STATUS_URL))

    def test_the_item_url_rides_exactly_as_given_even_carrying_a_colon(self):
        # The grammar's whole rule is "everything after the first colon", so
        # an item url that itself contains one (a scheme) is not re-split.
        request = AdapterRequest(step_id="s", query="youtube:" + YOUTUBE_ITEM_URL)
        self.assertEqual(oembed.operation_for(request), ("youtube", YOUTUBE_ITEM_URL))


class RefusalTest(unittest.TestCase):
    """A target naming no provider is refused before any call is made."""

    def _refused_with_no_call(self, query):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {})
        page = oembed.fetch_native_page(carrier, AdapterRequest(step_id="s1", query=query))
        return page, opener

    def test_an_unprefixed_target_is_refused(self):
        page, opener = self._refused_with_no_call("rate limiting")

        self.assertEqual(page.outcome, "refused")
        self.assertEqual(page.loss, (oembed.UNSELECTED_TARGET,))
        self.assertEqual(opener.opened, [])

    def test_the_refusal_warning_names_all_six_prefixes(self):
        page, _ = self._refused_with_no_call("rate limiting")

        for provider in oembed.OEMBED_OPERATIONS:
            with self.subTest(provider=provider):
                self.assertIn(provider, page.warnings[0])

    def test_an_unknown_prefix_is_refused(self):
        page, opener = self._refused_with_no_call("dailymotion:https://example.com/i")

        self.assertEqual(page.outcome, "refused")
        self.assertEqual(page.loss, (oembed.UNSELECTED_TARGET,))
        self.assertEqual(opener.opened, [])

    def test_a_named_provider_with_no_item_url_is_refused(self):
        page, opener = self._refused_with_no_call("youtube:")

        self.assertEqual(page.outcome, "refused")
        self.assertEqual(page.loss, (oembed.UNSELECTED_TARGET,))
        self.assertIn("youtube", page.warnings[0])
        self.assertEqual(opener.opened, [])


class ProviderRoutingTest(unittest.TestCase):
    """Each of the six prefixes spends exactly one call on its own declared route."""

    def test_every_prefix_reaches_its_own_route_and_only_that_route(self):
        cases = (
            ("youtube", transport.YOUTUBE_OEMBED_ROUTE, YOUTUBE_PAYLOAD_MIN, YOUTUBE_ITEM_URL),
            ("vimeo", transport.VIMEO_OEMBED_ROUTE, VIMEO_PAYLOAD, VIMEO_ITEM_URL),
            ("spotify", transport.SPOTIFY_OEMBED_ROUTE, SPOTIFY_PAYLOAD, SPOTIFY_ITEM_URL),
            (
                "soundcloud",
                transport.SOUNDCLOUD_OEMBED_ROUTE,
                SOUNDCLOUD_PAYLOAD,
                SOUNDCLOUD_ITEM_URL,
            ),
            ("tiktok", transport.TIKTOK_OEMBED_ROUTE, read_fixture("tiktok_video.json"), TIKTOK_ITEM_URL),
            ("x", transport.X_PUBLISH_OEMBED_ROUTE, read_fixture("x_status.json"), X_STATUS_URL),
        )
        for provider, route_id, body, item_url in cases:
            with self.subTest(provider=provider):
                page, opener = fetch(route_id, body, provider + ":" + item_url)

                self.assertEqual(page.outcome, "ok")
                self.assertEqual(page.route_id, route_id)
                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(opener.opened[0].route_id, route_id)

    def test_youtube_and_soundcloud_send_format_json_and_the_others_do_not(self):
        for provider, route_id, body, item_url, sends_format in (
            ("youtube", transport.YOUTUBE_OEMBED_ROUTE, YOUTUBE_PAYLOAD_MIN, YOUTUBE_ITEM_URL, True),
            (
                "soundcloud",
                transport.SOUNDCLOUD_OEMBED_ROUTE,
                SOUNDCLOUD_PAYLOAD,
                SOUNDCLOUD_ITEM_URL,
                True,
            ),
            ("vimeo", transport.VIMEO_OEMBED_ROUTE, VIMEO_PAYLOAD, VIMEO_ITEM_URL, False),
            ("spotify", transport.SPOTIFY_OEMBED_ROUTE, SPOTIFY_PAYLOAD, SPOTIFY_ITEM_URL, False),
            ("x", transport.X_PUBLISH_OEMBED_ROUTE, read_fixture("x_status.json"), X_STATUS_URL, False),
        ):
            with self.subTest(provider=provider):
                _, opener = fetch(route_id, body, provider + ":" + item_url)

                self.assertEqual("format=json" in opener.opened[0].url, sends_format)


YOUTUBE_PAYLOAD_MIN = json.dumps(
    {"type": "video", "title": "placeholder", "author_name": "placeholder"}
)


class RealFixtureParseTest(unittest.TestCase):
    """The three captured payloads: X, TikTok and YouTube, parsed field by field."""

    def test_x_publish_answers_rich_with_author_and_no_title(self):
        page, _ = fetch(transport.X_PUBLISH_OEMBED_ROUTE, read_fixture("x_status.json"), "x:" + X_STATUS_URL)

        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "rich")
        self.assertEqual(record.author, "jack")
        self.assertEqual(record.title, "")
        self.assertEqual(record.canonical_locator, X_STATUS_URL)
        self.assertEqual(record.native_item_id, "")
        self.assertIn(("author_url", "https://x.com/jack"), record.attributes)
        self.assertIn(("provider_name", "X"), record.attributes)
        # `html` is deliberately not carried.
        self.assertNotIn("html", dict(record.attributes))

    def test_tiktok_answers_video_with_the_embed_product_id_as_native_item_id(self):
        page, _ = fetch(
            transport.TIKTOK_OEMBED_ROUTE, read_fixture("tiktok_video.json"), "tiktok:" + TIKTOK_ITEM_URL
        )

        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "video")
        self.assertEqual(record.native_item_id, "6718335390845095173")
        self.assertEqual(record.author, "Scout, Suki & Stella")
        self.assertTrue(record.title)
        self.assertIn(("author_unique_id", "scout2015"), record.attributes)
        self.assertIn(("provider_name", "TikTok"), record.attributes)
        self.assertTrue(dict(record.attributes)["thumbnail_url"])

    def test_youtube_answers_video_with_no_native_item_id(self):
        page, _ = fetch(
            transport.YOUTUBE_OEMBED_ROUTE, read_fixture("youtube_video.json"), "youtube:" + YOUTUBE_ITEM_URL
        )

        record = page.records[0]
        self.assertEqual(record.canonical_content_kind, "video")
        self.assertEqual(record.author, "Rick Astley")
        self.assertTrue(record.title)
        # YouTube's answer carries no `embed_product_id`; only TikTok's does.
        self.assertEqual(record.native_item_id, "")
        self.assertIn(("provider_name", "YouTube"), record.attributes)


class DocumentedAbsenceTest(unittest.TestCase):
    """An absent title or author is documented, not an extra loss code."""

    def test_xs_absent_title_carries_only_the_two_standing_losses(self):
        page, _ = fetch(transport.X_PUBLISH_OEMBED_ROUTE, read_fixture("x_status.json"), "x:" + X_STATUS_URL)

        record = page.records[0]
        self.assertEqual(record.title, "")
        self.assertEqual(
            set(record.loss),
            {oembed.UNKNOWN_PUBLICATION_TIME, oembed.ENGAGEMENT_UNAVAILABLE},
        )

    def test_spotifys_absent_author_carries_only_the_two_standing_losses(self):
        page, _ = fetch(
            transport.SPOTIFY_OEMBED_ROUTE, SPOTIFY_PAYLOAD, "spotify:" + SPOTIFY_ITEM_URL
        )

        record = page.records[0]
        self.assertEqual(record.author, "")
        self.assertEqual(
            set(record.loss),
            {oembed.UNKNOWN_PUBLICATION_TIME, oembed.ENGAGEMENT_UNAVAILABLE},
        )


class StandingLossTest(unittest.TestCase):
    """No provider states a date or a count: every record carries both codes."""

    def test_every_provider_carries_no_date_and_no_count_on_a_clean_answer(self):
        cases = (
            (transport.YOUTUBE_OEMBED_ROUTE, YOUTUBE_PAYLOAD_MIN, "youtube:" + YOUTUBE_ITEM_URL),
            (transport.VIMEO_OEMBED_ROUTE, VIMEO_PAYLOAD, "vimeo:" + VIMEO_ITEM_URL),
            (transport.SPOTIFY_OEMBED_ROUTE, SPOTIFY_PAYLOAD, "spotify:" + SPOTIFY_ITEM_URL),
            (
                transport.SOUNDCLOUD_OEMBED_ROUTE,
                SOUNDCLOUD_PAYLOAD,
                "soundcloud:" + SOUNDCLOUD_ITEM_URL,
            ),
            (
                transport.TIKTOK_OEMBED_ROUTE,
                read_fixture("tiktok_video.json"),
                "tiktok:" + TIKTOK_ITEM_URL,
            ),
            (transport.X_PUBLISH_OEMBED_ROUTE, read_fixture("x_status.json"), "x:" + X_STATUS_URL),
        )
        for route_id, body, target in cases:
            with self.subTest(target=target.split(":", 1)[0]):
                page, _ = fetch(route_id, body, target)

                record = page.records[0]
                self.assertEqual(record.published_at, "")
                self.assertEqual(record.engagement, ())
                self.assertIn(oembed.UNKNOWN_PUBLICATION_TIME, record.loss)
                self.assertIn(oembed.ENGAGEMENT_UNAVAILABLE, record.loss)


class FailureTypingTest(unittest.TestCase):
    """Non-200, non-JSON and drifted-shape answers, each typed apart."""

    def test_a_404_is_http_status_and_names_deletion_or_privacy(self):
        page, _ = fetch(
            transport.VIMEO_OEMBED_ROUTE,
            "404 Not Found",
            "vimeo:" + VIMEO_ITEM_URL,
            content_type="text/plain",
            status=404,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, (oembed.HTTP_STATUS,))
        self.assertIn("deleted", page.warnings[0])

    def test_a_200_that_is_not_json_is_malformed_json(self):
        page, _ = fetch(
            transport.SPOTIFY_OEMBED_ROUTE,
            "not json at all {{{",
            "spotify:" + SPOTIFY_ITEM_URL,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, (oembed.MALFORMED_JSON,))

    def test_json_with_no_type_is_schema_drift(self):
        page, _ = fetch(
            transport.SOUNDCLOUD_OEMBED_ROUTE,
            json.dumps({"title": "no type on this row"}),
            "soundcloud:" + SOUNDCLOUD_ITEM_URL,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, (oembed.SCHEMA_DRIFT,))

    def test_a_json_list_instead_of_an_object_is_schema_drift(self):
        page, _ = fetch(
            transport.TIKTOK_OEMBED_ROUTE,
            json.dumps(["not", "an", "object"]),
            "tiktok:" + TIKTOK_ITEM_URL,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, (oembed.SCHEMA_DRIFT,))


class OneCallTest(unittest.TestCase):
    """One hydration, one call: never a retry, never a second surface."""

    def test_a_successful_read_opens_exactly_one_request(self):
        _, opener = fetch(transport.X_PUBLISH_OEMBED_ROUTE, read_fixture("x_status.json"), "x:" + X_STATUS_URL)

        self.assertEqual(len(opener.opened), 1)

    def test_a_failed_read_still_opens_exactly_one_request(self):
        _, opener = fetch(
            transport.VIMEO_OEMBED_ROUTE,
            "404 Not Found",
            "vimeo:" + VIMEO_ITEM_URL,
            content_type="text/plain",
            status=404,
        )

        self.assertEqual(len(opener.opened), 1)


if __name__ == "__main__":
    unittest.main()
