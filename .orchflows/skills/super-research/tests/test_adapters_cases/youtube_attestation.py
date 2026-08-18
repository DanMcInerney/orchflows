from tests.test_adapters_cases.youtube_viewmodels_and_player import *  # noqa: F401,F403

WRONG_YOUTUBE_ADAPTERS = (
    "empty_captions_as_absence_adapter",
    "stale_version_as_empty_adapter",
    "every_player_as_attested_adapter",
    "old_shape_dropped_adapter",
)


def typed_youtube_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: adapter_page(
            module,
            row["status"],
            read_youtube(row["body_fixture"]),
            content_type="application/json",
            request=youtube_request(row["target_id"], cursor=row["cursor"]),
        )[0]
        for row in youtube_cases()
    }


def assert_captions_are_never_reported_absent(case, adapter_id, pages):
    """Row 3's oracle: a withheld caption list is named, and named as itself.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. Four confusions are called out by name, because each is a
    different wrong thing to believe.

    A player answer listing no caption track, read as a video with no captions,
    asserts something false about the video rather than about the read — and it
    is the one the 2026-08-10 probes recorded on every client and every video, so it
    is the answer this adapter will meet every single time.

    A player answer that did list tracks, read as withheld, is the mirror: it
    would make the claim above satisfiable by typing every player answer the
    same way, and this package would report attestation on a video it could
    have read.

    A request the origin refused, read as an empty result, turns a scheduled
    client-version rotation into silence nobody can attribute; read as an
    authorization failure, it calls a keyless route credentialed.
    """

    for row in youtube_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if row["captions_withheld"] is True:
            if youtube_innertube.ATTESTATION_REQUIRED not in loss:
                case.fail(
                    "a player answer listing no caption track was recorded as a"
                    " video with no captions:" + detail
                )
        elif row["captions_withheld"] is False:
            if youtube_innertube.ATTESTATION_REQUIRED in loss:
                case.fail(
                    "a player answer that did list caption tracks was recorded as"
                    " withheld:" + detail
                )
        if row["expected_loss"] == youtube_innertube.STALE_IDENTIFIER:
            if not page.records and page.outcome != "failed":
                case.fail("a refused request was recorded as an empty success:" + detail)
            if youtube_innertube.AUTH_REQUIRED in loss:
                case.fail(
                    "a refused request was recorded as an authorization failure:" + detail
                )
        case.assertEqual(
            page.outcome,
            row["expected_outcome"],
            "case {0} came back {1}, its evidence says {2}".format(
                name, page.outcome, row["expected_outcome"]
            ),
        )
        case.assertEqual(
            loss, (row["expected_loss"],) if row["expected_loss"] else (), detail
        )


# One caption track as the player names it: a signed address this package
# neither makes nor reads, and the two facts the record needs alongside it.
TRANSCRIPT_TRACK = {
    "baseUrl": (
        "https://www.youtube.com/api/timedtext?v=" + YOUTUBE_VIDEO_ID
        + "&lang=en&expire=1786000000&signature=0f1e2d"
    ),
    "languageCode": "en",
    "kind": "asr",
}


def transcript_page_two(status, body):
    """Read the timed-text route's answer as the transcript's second page.

    Page two is the one the core reaches by spending page one's continuation,
    so it is reached here the same way: the cursor the first page publishes,
    and the timed-text route seeded rather than InnerTube's.
    """

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {transport.YOUTUBE_TIMEDTEXT_ROUTE: (status, body, "application/json")}
    )
    page = youtube_innertube.fetch_native_page(
        carrier,
        youtube_request(
            youtube_innertube.TRANSCRIPT_OPERATION + ":" + YOUTUBE_VIDEO_ID,
            cursor=youtube_innertube.transcript_cursor(YOUTUBE_VIDEO_ID, TRANSCRIPT_TRACK),
        ),
    )
    return (page, opener)


class YoutubeTranscriptFailureTest(unittest.TestCase):
    """The three ways page two can fail, each reported rather than raised.

    A caption address is signed and expires, and the timed-text payload is a
    shape this package reads rather than one it is promised. So all three of
    these are ordinary weather on this route, and the loss table in
    ``protocol.md`` already names this adapter for all three. What a caller
    must never get is a raise: an adapter that raises costs the core the whole
    page and reports nothing, which is precisely the report the typed
    vocabulary exists to make. Each test names the code the branch types, so
    a branch retyped to a neighbouring code fails here too.
    """

    def test_a_non_200_returns_a_typed_page(self):
        page, opener = transcript_page_two(404, "")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertEqual(page.records, ())
        # The read happened: this is the origin's answer, not a short circuit
        # ahead of it.
        self.assertEqual(len(opener.opened), 1)
        self.assertIn("404", page.warnings[0])

    def test_an_unparseable_body_returns_a_typed_page(self):
        # What an expired signature answers with: 200, and no json in it.
        page, _ = transcript_page_two(200, "<!DOCTYPE html><html><body>Sign in</body></html>")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("malformed_json",))
        self.assertEqual(page.records, ())

    def test_an_answer_with_no_events_returns_a_typed_page(self):
        # Json, and not the json3 the route declares: the events list is gone.
        page, _ = transcript_page_two(200, '{"wireMagic": "pb3"}')

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_the_three_codes_are_the_ones_the_loss_table_names(self):
        # Spelled as every sibling adapter spells them, because a code the
        # core cannot recognise reports as little as a raise does.
        self.assertEqual(youtube_innertube.HTTP_STATUS, "http_status")
        self.assertEqual(youtube_innertube.MALFORMED_JSON, "malformed_json")
        self.assertEqual(youtube_innertube.SCHEMA_DRIFT, "schema_drift")


class AttestationIsNotAnAbsenceTest(unittest.TestCase):
    """Criteria 2 and 3: this half's spine, and the false capability it prevents.

    Across five clients and three videos, ``captionTracks`` came back empty
    every time and playability degraded to ``UNPLAYABLE`` after the first
    metadata call. That is attestation, not a property of the videos. An
    adapter that reported it as "no captions" would assert something false
    about every video it ever read, and it would do so quietly, on a 200, with
    the rest of the metadata looking perfectly healthy beside it.
    """

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_captions_are_never_reported_absent(
            self, "youtube_innertube", typed_youtube_pages(youtube_innertube)
        )

    def test_a_withheld_caption_list_names_where_it_looked_and_why_it_is_empty(self):
        page, _ = youtube_page("player_metadata.json")
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, (youtube_innertube.ATTESTATION_REQUIRED,))
        self.assertEqual(page.outcome, "ok")
        self.assertIn(".".join(youtube_innertube.CAPTION_TRACKS_PATH), warning)
        self.assertIn("attestation", warning)
        # The record a caller keeps carries it too: a caller reading one record
        # would otherwise have to correlate back to a step to learn that the
        # captions were withheld rather than absent.
        self.assertIn(
            youtube_innertube.ATTESTATION_REQUIRED, page.records[0].loss
        )

    def test_a_video_that_does_list_tracks_is_not_reported_as_withheld(self):
        # Without this the claim above is satisfiable by typing every player
        # answer the same way, and the oracle would be checking nothing.
        page, _ = youtube_page(
            "player_with_caption_tracks.json", target_id="player:7pQm3nXkT2a"
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertNotIn(youtube_innertube.ATTESTATION_REQUIRED, page.records[0].loss)

    def test_an_unplayable_answer_is_attestation_and_never_a_credential_problem(self):
        page, _ = youtube_page("player_unplayable.json")
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, (youtube_innertube.ATTESTATION_REQUIRED,))
        self.assertEqual(page.outcome, "failed")
        self.assertNotIn(youtube_innertube.AUTH_REQUIRED, page.loss)
        self.assertIn("UNPLAYABLE", warning)
        self.assertIn("bot", warning)

    def test_each_refusal_is_typed_as_the_one_it_is_and_not_as_the_measured_one(self):
        # `attestation_required` is reserved for a payload withheld behind an
        # attestation this package does not perform. Every non-`OK` playability
        # used to take it, so a private video and a deleted one were both filed
        # as a deferred capability — and the warning quoted five clients and
        # three videos as the evidence for a status the probe run never saw.
        expected = {
            "UNPLAYABLE": youtube_innertube.ATTESTATION_REQUIRED,
            "ERROR": youtube_innertube.ATTESTATION_REQUIRED,
            "LOGIN_REQUIRED": youtube_innertube.AUTH_REQUIRED,
            "AGE_VERIFICATION_REQUIRED": youtube_innertube.AUTH_REQUIRED,
            "CONTENT_CHECK_REQUIRED": youtube_innertube.WITHHELD,
        }
        for status, code in sorted(expected.items()):
            with self.subTest(playability=status):
                page, _ = adapter_page(
                    youtube_innertube,
                    200,
                    json.dumps(
                        {"playabilityStatus": {"status": status, "reason": "a reason"}}
                    ),
                    content_type="application/json",
                    request=youtube_request("player:" + YOUTUBE_VIDEO_ID),
                )
                warning = " ".join(page.warnings)

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.records, ())
                self.assertEqual(tuple(page.loss), (code,))
                self.assertIn(status, warning)
                self.assertIn("a reason", warning)
                # The measured citation appears only on the statuses it was
                # measured on: a module that quotes evidence for its own typing
                # under a status nobody probed is its own witness.
                self.assertEqual(
                    "The 2026-08-10 probes recorded this status" in warning,
                    status in youtube_innertube.ATTESTED_PLAYABILITY,
                )

    def test_a_degraded_answer_is_not_mined_for_the_metadata_it_still_carries(self):
        # That fixture carries a complete videoDetails. The origin said it was
        # not serving this client, so reporting its contents as a successful
        # read would make a degraded response indistinguishable from a healthy
        # one at exactly the moment a caller needs to tell them apart.
        page, _ = youtube_page("player_unplayable.json")

        self.assertEqual(page.records, ())
        self.assertIn(
            "Running a 70B locally", read_youtube("player_unplayable.json")
        )

    def test_a_refused_request_names_the_rotating_part_and_the_way_back(self):
        page, opener = youtube_page("innertube_invalid_argument.json", status=400)
        warning = " ".join(page.warnings)

        self.assertEqual(page.loss, (youtube_innertube.STALE_IDENTIFIER,))
        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.records, ())
        self.assertIn(youtube_innertube.CLIENT_VERSION, warning)
        self.assertIn("ytcfg", warning)
        # And it cost one call: a refused request is an answer, not a reason to
        # look somewhere else.
        self.assertEqual(len(opener.opened), 1)

    def test_the_same_bytes_at_two_statuses_are_two_different_answers(self):
        refused_request, _ = youtube_page("innertube_invalid_argument.json", status=400)
        refused_read, _ = youtube_page("innertube_invalid_argument.json", status=403)

        self.assertEqual(refused_request.loss, (youtube_innertube.STALE_IDENTIFIER,))
        self.assertEqual(refused_read.loss, (youtube_innertube.AUTH_REQUIRED,))

    def test_a_results_section_that_moved_is_drift_and_not_a_search_with_no_matches(self):
        page, _ = youtube_page("search_reshaped.json", target_id=YOUTUBE_SEARCH_TARGET)
        warning = " ".join(page.warnings)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertIn(".".join(youtube_innertube.SEARCH_RESULTS_PATH), warning)

    def test_a_search_continuation_page_is_read_and_not_typed_as_drift(self):
        """Page two of a search carries no first-page container, and is not drift.

        Measured 2026-08-17: `search:bitcoin price prediction` answered page one
        with 19 rows and a cursor, and every page after it was typed
        `schema_drift` because the adapter read only
        `SEARCH_RESULTS_PATH` — a container a continuation answer never sends.
        A search could therefore never return more than one page. With the
        continuation shape declared, the same query read 92 rows over five
        pages, all `ok`.
        """

        page, _ = youtube_page(
            "search_continuation.json", target_id=YOUTUBE_SEARCH_TARGET, cursor="PAGE_TWO_TOKEN"
        )

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.loss, ())
        self.assertEqual(
            tuple(record.native_item_id for record in page.records),
            ("J-uXheGywLA", "K8vQrTmXp2A"),
        )
        # The rows carry the route's own view text, exactly as page one does:
        # a continuation is the same shape arriving under a different key, so
        # nothing about the record may differ because of where it was read.
        self.assertEqual(
            list(attributes_of(page.records[0])["viewCountText"]), ["12,345 views"]
        )
        # And the next token is spent from the same place, so paging continues
        # past page two rather than stopping one short of the cap.
        self.assertEqual(page.cursor_out, "PAGE_THREE_TOKEN")

    def test_neither_search_shape_present_is_still_drift(self):
        """The fix widens what counts as an answer; it must not swallow drift.

        `search_reshaped.json` carries neither container, and stays `failed`.
        Read beside the continuation test above: one asserts the new shape is
        accepted, this one asserts the old refusal survived it.
        """

        page, _ = youtube_page("search_reshaped.json", target_id=YOUTUBE_SEARCH_TARGET)

        self.assertIsNone(youtube_innertube.search_sections(json.loads(
            read_youtube("search_reshaped.json")
        )))
        self.assertEqual(page.loss, ("schema_drift",))

    def test_the_field_a_caption_fetcher_needs_is_read_once_where_it_is_spent(self):
        # Caption retrieval was deferred by the spec, and the deferral's whole
        # enforcement was that this field was read nowhere. The reopen
        # condition it named has been met: the `ANDROID` client answered `OK`
        # with a populated track list on 2026-08-17 where every client measured
        # on 2026-08-10 answered with an empty one. So the count is one rather
        # than zero, and one is the statement now — the field is spent building
        # the continuation and nowhere else, so no second site can reach a
        # caption address.
        source = ADAPTER_DIR / "youtube_innertube.py"

        self.assertEqual(names_read(source, "CAPTION_FETCH_FIELD"), 1)
        self.assertIn("baseUrl", adapter_owner_source(source))

    def test_no_youtube_route_returns_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. The web key is a vendor-published constant,
        # not a user credential: the only way `auth_required` appears is the
        # origin's own 401 or 403.
        for fixture, target in (
            ("search_results.json", YOUTUBE_SEARCH_TARGET),
            ("player_metadata.json", "player:" + YOUTUBE_VIDEO_ID),
        ):
            with self.subTest(fixture=fixture):
                page, _ = youtube_page(fixture, target_id=target)

                self.assertNotIn(youtube_innertube.AUTH_REQUIRED, page.loss)
                self.assertEqual(page.outcome, "ok")
                self.assertTrue(
                    transport.route_admissions()[transport.YOUTUBE_INNERTUBE_ROUTE]
                )
