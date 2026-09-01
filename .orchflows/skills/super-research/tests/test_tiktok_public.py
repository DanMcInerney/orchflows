"""`tiktok_public`: the video and profile pages, offline against captured fixtures.

`tests/fixtures/tiktok_public/video_page.html` and `profile_page.html` are the
real bytes TikTok answered on 2026-09-01 to a plain GET carrying this
package's own `User-Agent` — no cookie, no script run, no browser identity.
Everything else here (a malformed script, a missing script, a challenge
marker, a nonempty `itemList`) is constructed, because none of those four was
observed live and each is named as such where it is used.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from super_research import transport
from super_research.adapters import AdapterRequest, tiktok_public
from super_research.adapters._support import tiktok_public_records as records
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "tiktok_public"
VIDEO_ROUTE = transport.TIKTOK_VIDEO_PAGE_ROUTE
PROFILE_ROUTE = transport.TIKTOK_PROFILE_PAGE_ROUTE
HTML_CONTENT_TYPE = "text/html; charset=utf-8"

VIDEO_TARGET = "video:nba/7606907506589207838"
VIDEO_ID = "7606907506589207838"
VIDEO_HANDLE = "nba"
EXPECTED_PUBLISHED_AT = "2026-02-15T02:06:21Z"  # datetime.fromtimestamp(1771121181, utc)


def _fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def fetch(route, body, content_type, request):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(clock, {route: (200, body, content_type)})
    page = tiktok_public.fetch_native_page(carrier, request)
    return page, opener


def fetch_status(route, status, request):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route: (status, "", "text/html; charset=utf-8")}
    )
    page = tiktok_public.fetch_native_page(carrier, request)
    return page, opener


def video_request(target=VIDEO_TARGET, **kwargs):
    return AdapterRequest(step_id="s1", target_ids=(target,), **kwargs)


def profile_request(target="nba", **kwargs):
    return AdapterRequest(step_id="s1", target_ids=(target,), **kwargs)


WALL_BODY = (
    '<html><body><div id="captcha_container">'
    "Please verify to continue.</div></body></html>"
)
NO_SCRIPT_BODY = "<html><body><h1>Not Found</h1></body></html>"
MALFORMED_SCRIPT_BODY = (
    '<html><body><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"'
    ' type="application/json">{this is not json</script></body></html>'
)
NO_ITEM_STRUCT_BODY = (
    '<html><body><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"'
    ' type="application/json">{"__DEFAULT_SCOPE__": {"webapp.video-detail":'
    ' {"itemInfo": {}}}}</script></body></html>'
)
NO_USER_BODY = (
    '<html><body><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"'
    ' type="application/json">{"__DEFAULT_SCOPE__": {"webapp.user-detail":'
    ' {"userInfo": {}}}}</script></body></html>'
)


class OperationGrammarTest(unittest.TestCase):
    """`operation_for`: an explicit prefix, or an unprefixed target defaulting to profile."""

    def test_a_video_prefixed_target_names_the_video_operation(self):
        request = AdapterRequest(step_id="s1", target_ids=(VIDEO_TARGET,))
        self.assertEqual(
            tiktok_public.operation_for(request), ("video", "nba/7606907506589207838")
        )

    def test_a_profile_prefixed_target_names_the_profile_operation(self):
        request = AdapterRequest(step_id="s1", target_ids=("profile:nba",))
        self.assertEqual(tiktok_public.operation_for(request), ("profile", "nba"))

    def test_an_unprefixed_target_defaults_to_profile(self):
        request = AdapterRequest(step_id="s1", target_ids=("nba",))
        self.assertEqual(tiktok_public.operation_for(request), ("profile", "nba"))

    def test_a_query_is_read_the_same_way_target_ids_are(self):
        request = AdapterRequest(step_id="s1", query="nba")
        self.assertEqual(tiktok_public.operation_for(request), ("profile", "nba"))


class VideoTargetGrammarTest(unittest.TestCase):
    """`video_target`: the required `handle/id` pair, or a refusal naming why."""

    def test_the_pair_splits_cleanly(self):
        self.assertEqual(
            tiktok_public.video_target("nba/7606907506589207838"),
            ("nba", "7606907506589207838", ""),
        )

    def test_a_bare_handle_with_no_id_is_refused(self):
        handle, video_id, refusal = tiktok_public.video_target("nba")
        self.assertEqual((handle, video_id), ("", ""))
        self.assertTrue(refusal)

    def test_a_bare_id_with_no_handle_is_refused(self):
        handle, video_id, refusal = tiktok_public.video_target("/7606907506589207838")
        self.assertEqual((handle, video_id), ("", ""))
        self.assertTrue(refusal)

    def test_an_empty_argument_is_refused(self):
        handle, video_id, refusal = tiktok_public.video_target("")
        self.assertEqual((handle, video_id), ("", ""))
        self.assertTrue(refusal)


class VideoOperationRefusesWithoutThePairTest(unittest.TestCase):
    """A malformed `video:` target is refused before any call is made."""

    def _fetch_refused(self, target):
        clock = helpers.FakeClock()
        # No route is seeded at all: any attempted call raises, which is the
        # proof that none was made.
        carrier, opener = helpers.offline_transport(clock, {})
        page = tiktok_public.fetch_native_page(carrier, video_request(target=target))
        return page, opener

    def test_a_bare_video_prefix_is_refused_and_touches_no_carrier(self):
        page, opener = self._fetch_refused("video:")

        self.assertEqual(page.outcome, "refused")
        self.assertIn("unselected_target", page.loss)
        self.assertEqual(opener.opened, [])

    def test_a_handle_with_no_id_is_refused_and_touches_no_carrier(self):
        page, opener = self._fetch_refused("video:nba")

        self.assertEqual(page.outcome, "refused")
        self.assertIn("unselected_target", page.loss)
        self.assertEqual(opener.opened, [])

    def test_an_empty_profile_target_is_refused_and_touches_no_carrier(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {})
        page = tiktok_public.fetch_native_page(carrier, profile_request(target="profile:"))

        self.assertEqual(page.outcome, "refused")
        self.assertIn("unselected_target", page.loss)
        self.assertEqual(opener.opened, [])


class VideoPathParamsTest(unittest.TestCase):
    """The composed address: the pre-wired route shape needed no correction."""

    def test_the_handle_carries_the_leading_at_and_the_resource_and_id_follow(self):
        _, opener = fetch(VIDEO_ROUTE, _fixture("video_page.html"), HTML_CONTENT_TYPE, video_request())

        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(
            opener.opened[0].url,
            "https://www.tiktok.com/%40nba/video/7606907506589207838",
        )

    def test_a_caller_supplied_leading_at_is_not_doubled(self):
        _, opener = fetch(
            VIDEO_ROUTE,
            _fixture("video_page.html"),
            HTML_CONTENT_TYPE,
            video_request(target="video:@nba/7606907506589207838"),
        )

        self.assertEqual(
            opener.opened[0].url,
            "https://www.tiktok.com/%40nba/video/7606907506589207838",
        )


class VideoHappyPathTest(unittest.TestCase):
    """The real captured video page, parsed in full."""

    def setUp(self):
        self.page, self.opener = fetch(
            VIDEO_ROUTE, _fixture("video_page.html"), HTML_CONTENT_TYPE, video_request()
        )

    def test_exactly_one_call_is_made(self):
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_page_answers_ok_with_one_record(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 1)

    def test_identity_and_body_fields(self):
        record = self.page.records[0]
        self.assertEqual(record.native_item_id, VIDEO_ID)
        self.assertEqual(record.author, VIDEO_HANDLE)
        self.assertIn("Keshad Johnson", record.body)
        self.assertEqual(
            record.canonical_locator,
            "https://www.tiktok.com/@nba/video/7606907506589207838",
        )

    def test_created_time_the_epoch_second_string_became_the_artifacts_instant(self):
        record = self.page.records[0]
        self.assertEqual(record.published_at, EXPECTED_PUBLISHED_AT)

    def test_statsv2_digit_strings_became_exact_ints(self):
        engagement = dict(self.page.records[0].engagement)
        self.assertEqual(engagement["diggCount"], 72600)
        self.assertEqual(engagement["playCount"], 4900000)
        self.assertEqual(engagement["commentCount"], 443)
        self.assertEqual(engagement["shareCount"], 2311)
        self.assertEqual(engagement["collectCount"], 2480)
        self.assertEqual(engagement["repostCount"], 0)
        self.assertIsInstance(engagement["diggCount"], int)

    def test_hashtags_are_carried_as_repeated_attributes_and_the_mention_is_not(self):
        hashtags = [value for name, value in self.page.records[0].attributes if name == "hashtag"]
        self.assertEqual(hashtags, ["nba", "basketball", "nbaallstar", "keshadjohnson", "dunk"])

    def test_the_authors_nickname_is_carried_once(self):
        nicknames = [
            value for name, value in self.page.records[0].attributes if name == "nickname"
        ]
        self.assertEqual(nicknames, ["NBA"])

    def test_no_field_is_reported_missing_on_a_complete_row(self):
        self.assertEqual(self.page.records[0].loss, ())


class ProfileHappyPathTest(unittest.TestCase):
    """The real captured profile page: the account alone, with its warning."""

    def setUp(self):
        self.page, self.opener = fetch(
            PROFILE_ROUTE, _fixture("profile_page.html"), HTML_CONTENT_TYPE, profile_request()
        )

    def test_exactly_one_call_is_made(self):
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_page_answers_ok_with_one_record(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 1)

    def test_identity_and_engagement_fields(self):
        record = self.page.records[0]
        self.assertEqual(record.native_item_id, "134941634731003904")
        self.assertEqual(record.author, "nba")
        self.assertEqual(record.title, "NBA")
        self.assertEqual(record.canonical_locator, "https://www.tiktok.com/@nba")
        engagement = dict(record.engagement)
        self.assertEqual(engagement["followerCount"], 27200000)
        self.assertEqual(engagement["heartCount"], 1100000000)
        self.assertEqual(engagement["videoCount"], 23500)

    def test_the_empty_item_list_is_warned_about_by_name(self):
        self.assertTrue(self.page.warnings)
        self.assertIn("itemList", self.page.warnings[0])
        self.assertIn("signed client-side call", self.page.warnings[0])


class ProfilePathParamsTest(unittest.TestCase):
    def test_the_handle_alone_is_the_one_path_segment(self):
        _, opener = fetch(
            PROFILE_ROUTE, _fixture("profile_page.html"), HTML_CONTENT_TYPE, profile_request()
        )

        self.assertEqual(opener.opened[0].url, "https://www.tiktok.com/%40nba")


class ProfileNonemptyItemListTest(unittest.TestCase):
    """A constructed payload: the one shape the live read never carried."""

    BODY = (
        '<html><body><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"'
        ' type="application/json">'
        '{"__DEFAULT_SCOPE__": {"webapp.user-detail": {"userInfo": {'
        '"user": {"uniqueId": "handle", "nickname": "Nick", "signature": "Bio",'
        ' "id": "555"},'
        '"stats": {"followerCount": 10, "heartCount": 20, "videoCount": 1},'
        '"itemList": [{"id": "999", "createTime": "1700000000", "desc": "hi",'
        ' "statsV2": {"diggCount": "1", "shareCount": "2", "commentCount": "3",'
        ' "playCount": "4", "collectCount": "5", "repostCount": "6"},'
        ' "stats": {}, "author": {"uniqueId": "handle", "nickname": "Nick"},'
        ' "textExtra": [{"hashtagName": "tag", "type": 1}]}]'
        "}}}}"
        "</script></body></html>"
    )

    def test_a_nonempty_item_list_is_parsed_as_additional_video_records(self):
        page, _ = fetch(PROFILE_ROUTE, self.BODY, HTML_CONTENT_TYPE, profile_request(target="handle"))

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(page.records), 2)
        self.assertEqual(page.records[0].canonical_content_kind, "profile")
        self.assertEqual(page.records[1].canonical_content_kind, "video")
        self.assertEqual(page.records[1].native_item_id, "999")
        self.assertEqual(dict(page.records[1].engagement)["diggCount"], 1)

    def test_the_item_list_warning_does_not_appear_when_it_is_not_empty(self):
        page, _ = fetch(PROFILE_ROUTE, self.BODY, HTML_CONTENT_TYPE, profile_request(target="handle"))

        self.assertFalse(any("itemList" in warning for warning in page.warnings))


class NonTwoHundredTest(unittest.TestCase):
    def test_a_video_read_answering_other_than_200_is_http_status(self):
        page, opener = fetch_status(VIDEO_ROUTE, 404, video_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("http_status", page.loss)
        self.assertEqual(len(opener.opened), 1)

    def test_a_profile_read_answering_other_than_200_is_http_status(self):
        page, _ = fetch_status(PROFILE_ROUTE, 500, profile_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("http_status", page.loss)


class MissingScriptIsSchemaDriftTest(unittest.TestCase):
    """A 200 with no rehydration script and no challenge marker is a shape change."""

    def test_a_video_read_with_no_script_and_no_wall_marker_is_schema_drift(self):
        page, _ = fetch(VIDEO_ROUTE, NO_SCRIPT_BODY, HTML_CONTENT_TYPE, video_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("schema_drift", page.loss)

    def test_a_profile_read_with_no_script_and_no_wall_marker_is_schema_drift(self):
        page, _ = fetch(PROFILE_ROUTE, NO_SCRIPT_BODY, HTML_CONTENT_TYPE, profile_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("schema_drift", page.loss)


class ChallengeMarkerIsAuthRequiredTest(unittest.TestCase):
    """A 200 with no script and a genuine challenge marker: `auth_required`.

    `WALL_BODY` is constructed, not captured — see the module docstring on
    `tiktok_public` for why no live wall was available to capture, and the
    reopen condition in `references/_drafts/tiktok_public.md`.
    """

    def test_a_video_read_behind_a_challenge_marker_is_auth_required(self):
        page, _ = fetch(VIDEO_ROUTE, WALL_BODY, HTML_CONTENT_TYPE, video_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("auth_required", page.loss)

    def test_a_healthy_pages_own_i18n_text_never_trips_the_marker(self):
        # The exact false-positive this module's docstring warns about: every
        # ordinary page repeats the literal text "Log in" many times over in
        # its embedded translation dictionary. The real fixture is the proof.
        self.assertFalse(tiktok_public._looks_like_a_challenge(_fixture("video_page.html")))
        self.assertFalse(tiktok_public._looks_like_a_challenge(_fixture("profile_page.html")))


class MalformedJsonTest(unittest.TestCase):
    def test_a_script_tag_that_is_not_json_is_malformed_json(self):
        page, _ = fetch(VIDEO_ROUTE, MALFORMED_SCRIPT_BODY, HTML_CONTENT_TYPE, video_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("malformed_json", page.loss)

    def test_a_profile_script_tag_that_is_not_json_is_malformed_json(self):
        page, _ = fetch(PROFILE_ROUTE, MALFORMED_SCRIPT_BODY, HTML_CONTENT_TYPE, profile_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("malformed_json", page.loss)


class ValidJsonWrongShapeIsSchemaDriftTest(unittest.TestCase):
    def test_json_present_with_no_item_struct_is_schema_drift(self):
        page, _ = fetch(VIDEO_ROUTE, NO_ITEM_STRUCT_BODY, HTML_CONTENT_TYPE, video_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("schema_drift", page.loss)

    def test_json_present_with_no_user_is_schema_drift(self):
        page, _ = fetch(PROFILE_ROUTE, NO_USER_BODY, HTML_CONTENT_TYPE, profile_request())

        self.assertEqual(page.outcome, "failed")
        self.assertIn("schema_drift", page.loss)


class RecordsPureFunctionTest(unittest.TestCase):
    """`tiktok_public_records`, exercised directly: the two edges the fixture never carries."""

    def test_a_statsv2_digit_string_wins_over_stats(self):
        item = {"statsV2": {"diggCount": "5"}, "stats": {"diggCount": 9}}
        self.assertEqual(dict(records.video_engagement(item))["diggCount"], 5)

    def test_a_statsv2_key_with_a_non_digit_string_is_dropped_not_fallen_back(self):
        item = {"statsV2": {"diggCount": "N/A"}, "stats": {"diggCount": 9}}
        self.assertNotIn("diggCount", dict(records.video_engagement(item)))

    def test_a_statsv2_absent_key_falls_back_to_an_exact_stats_int(self):
        item = {"statsV2": {}, "stats": {"diggCount": 9}}
        self.assertEqual(dict(records.video_engagement(item))["diggCount"], 9)

    def test_a_stats_float_or_bool_is_never_read_as_a_count(self):
        item = {"statsV2": {}, "stats": {"diggCount": 9.5, "playCount": True}}
        engagement = dict(records.video_engagement(item))
        self.assertNotIn("diggCount", engagement)
        self.assertNotIn("playCount", engagement)

    def test_a_non_digit_create_time_carries_no_instant(self):
        self.assertEqual(records.route_instant_to_utc_iso("not-a-number"), "")

    def test_an_empty_create_time_carries_no_instant(self):
        self.assertEqual(records.route_instant_to_utc_iso(""), "")

    def test_a_digit_create_time_matches_the_stdlib_conversion(self):
        expected = datetime.fromtimestamp(1700000000, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self.assertEqual(records.route_instant_to_utc_iso("1700000000"), expected)

    def test_a_mention_entry_contributes_no_hashtag(self):
        item = {"textExtra": [{"hashtagName": "", "type": 0}, {"hashtagName": "real", "type": 1}]}
        self.assertEqual(records.hashtags_of(item), ("real",))

    def test_a_missing_id_marks_the_video_row_field_omitted(self):
        record = records.video_record(0, {}, "https://www.tiktok.com", "field_omitted")
        self.assertIn("field_omitted", record.loss)

    def test_a_complete_profile_row_carries_no_loss(self):
        user = {"uniqueId": "h", "nickname": "N", "signature": "S", "id": "1"}
        stats = {"followerCount": 1, "heartCount": 2, "videoCount": 3}
        record = records.profile_record(user, stats, "https://www.tiktok.com", "field_omitted")
        self.assertEqual(record.loss, ())

    def test_profile_native_item_id_falls_back_to_the_handle_with_no_numeric_id(self):
        user = {"uniqueId": "h", "nickname": "N", "signature": "S"}
        record = records.profile_record(user, {}, "https://www.tiktok.com", "field_omitted")
        self.assertEqual(record.native_item_id, "h")


if __name__ == "__main__":
    unittest.main()
