from tests.test_adapters_cases.youtube_attestation import *  # noqa: F401,F403

class TheUnheldVideoIsToldByItsAbsentDetailsTest(unittest.TestCase):
    """The measured discriminator: absent details refuse the read, present ones do not.

    The 2026-08-12 record left the ``videoDetails`` axis measured on one side
    only, and this class used to pin that nothing branched on it. The reopen
    condition it named — one bounded read of a video the origin certainly
    holds, capturing ``videoDetails`` presence beside
    ``playabilityStatus.status`` in the raw payload — was met 2026-08-31, on
    the web client, on both sides: ``dQw4w9WgXcQ`` answered 200 ``UNPLAYABLE``
    *with* its complete ``videoDetails`` and ``microformat``, and an
    eleven-character id the origin does not hold answered 200 ``ERROR`` with
    neither. The reason string was byte-identical on both sides — "Video
    unavailable" — so the reason still decides nothing, and the statuses still
    do not either: what tells a held video's degraded answer from an unheld
    id's refusal is the row the origin served or did not serve beside it.
    """

    # Both sides of the probe answered with this string, byte for byte —
    # measured 2026-08-12 and again 2026-08-31.
    MEASURED_REASON = "Video unavailable"

    def refusal(self, status, details=None):
        """One player answer at a refused playability, as the probe recorded it."""

        playability = {"status": status, "reason": self.MEASURED_REASON}
        payload = {youtube_innertube.PLAYABILITY_KEY: playability}
        if details is not None:
            payload[youtube_innertube.VIDEO_DETAILS_KEY] = details
        page, _ = adapter_page(
            youtube_innertube,
            200,
            json.dumps(payload),
            content_type="application/json",
            request=youtube_request("player:" + YOUTUBE_VIDEO_ID),
        )
        return page

    def test_the_two_measured_statuses_reach_a_caller_as_one_answer(self):
        # Without details, `ERROR` and `UNPLAYABLE` are still one answer:
        # neither carried anything to keep, and neither status alone is a
        # signature of "gone" — the 2026-08-10 probes recorded both on videos
        # that existed.
        unheld = self.refusal("ERROR")
        attested = self.refusal("UNPLAYABLE")

        self.assertEqual(unheld.outcome, attested.outcome)
        self.assertEqual(tuple(unheld.loss), tuple(attested.loss))
        self.assertEqual(unheld.records, ())
        self.assertEqual(attested.records, ())
        # And the operator is told, on both, that the status does not decide it.
        for page in (unheld, attested):
            self.assertIn("a video it no longer holds", " ".join(page.warnings))

    def test_a_refusal_carrying_the_row_is_a_served_answer_and_one_without_is_not(self):
        # The 2026-08-31 measurement, replayed on the shapes it recorded: the
        # held side keeps its record with the withholding named as loss, and
        # the unheld side is the refusal of the whole read.
        absent = self.refusal("ERROR")
        present = self.refusal(
            "UNPLAYABLE",
            details={
                youtube_innertube.VIDEO_ID_KEY: YOUTUBE_VIDEO_ID,
                youtube_innertube.TITLE_KEY: "held",
            },
        )

        self.assertEqual(absent.outcome, "failed")
        self.assertEqual(absent.records, ())
        self.assertEqual(present.outcome, "ok")
        self.assertEqual(len(present.records), 1)
        self.assertIn(youtube_innertube.ATTESTATION_REQUIRED, present.loss)


class AttestationOracleCanFailTest(unittest.TestCase):
    """Criterion 6: the oracle above rejects a wrong result, in every direction.

    All three adapters here are written beside the tree and loaded by path.
    Each runs the shipped adapter and then draws exactly one wrong conclusion
    from what it returned, which is what makes a rejection attributable to that
    conclusion and to nothing else. Nothing in the package produces them and
    nothing under test is mutated to obtain them.
    """

    def _assert_oracle_rejects(self, name, reason):
        wrong = load_adapter_fixture(name, directory=YOUTUBE_FIXTURE_DIR)

        with self.assertRaises(AssertionError) as caught:
            assert_captions_are_never_reported_absent(
                self, name, typed_youtube_pages(wrong)
            )

        self.assertIn(reason, str(caught.exception))

    def test_an_adapter_that_calls_a_withheld_caption_list_an_absence_fails_the_oracle(self):
        # Row 6's named case: the empty list becomes a successful answer
        # asserting that the video has no captions, which is a claim about the
        # video that this package is in no position to make.
        self._assert_oracle_rejects(
            "empty_captions_as_absence_adapter",
            "a player answer listing no caption track was recorded as a video with"
            " no captions",
        )

    def test_an_adapter_that_calls_every_player_answer_attested_fails_the_oracle(self):
        # The opposite error. Without this side the oracle could be satisfied
        # by typing every player answer as withheld, and the package would
        # report attestation on a video it could have read.
        self._assert_oracle_rejects(
            "every_player_as_attested_adapter",
            "a player answer that did list caption tracks was recorded as withheld",
        )

    def test_an_adapter_that_answers_a_refused_request_with_nothing_fails_the_oracle(self):
        self._assert_oracle_rejects(
            "stale_version_as_empty_adapter",
            "a refused request was recorded as an empty success",
        )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_captions_are_never_reported_absent(
            self, "youtube_innertube", typed_youtube_pages(youtube_innertube)
        )

    def test_the_caption_scan_can_fail(self):
        # Which is what makes the shipped adapter's count of zero worth
        # anything: a module beside the tree that does read the constant is
        # named by the same scan.
        self.assertGreater(
            names_read(
                YOUTUBE_FIXTURE_DIR / "empty_captions_as_absence_adapter.py",
                "CAPTION_FETCH_FIELD",
            ),
            0,
        )

    def test_nothing_in_the_package_can_reach_a_wrong_youtube_adapter(self):
        named = [
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for name in WRONG_YOUTUBE_ADAPTERS
            if name in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(named, [])


class YoutubeInstagramOneCallOnePageTest(unittest.TestCase):
    """Criterion 5: one bounded call in, exactly one page out, whatever comes back."""

    def _every_case(self):
        for row in youtube_cases():
            yield (
                "youtube_innertube/" + row["case_name"],
                youtube_innertube,
                row["status"],
                read_youtube(row["body_fixture"]),
                youtube_request(row["target_id"], cursor=row["cursor"]),
            )
        for row in instagram_cases():
            yield (
                "instagram_public/" + row["case_name"],
                instagram_public,
                row["status"],
                read_instagram(row["body_fixture"]),
                adapters.AdapterRequest(step_id="s1-ig", target_ids=(row["username"],)),
            )
        for status in (404, 429, 500, 503):
            yield (
                "youtube_innertube/http_{0}".format(status),
                youtube_innertube,
                status,
                '{"error": "no"}',
                youtube_request("player:" + YOUTUBE_VIDEO_ID),
            )
            yield (
                "instagram_public/http_{0}".format(status),
                instagram_public,
                status,
                '{"error": "no"}',
                INSTAGRAM_REQUEST,
            )

    def test_every_answer_costs_one_call_on_the_adapters_own_route(self):
        for name, module, status, body, request in self._every_case():
            with self.subTest(case=name):
                page, opener = adapter_page(
                    module, status, body, content_type="application/json", request=request
                )

                self.assertEqual(len(opener.opened), 1)
                self.assertEqual(
                    [call.route_id for call in opener.opened], [module.DESCRIPTOR.route_id]
                )
                self.assertEqual(page.route_id, module.DESCRIPTOR.route_id)
                self.assertIsInstance(page, adapters.NativePage)

    def test_a_continuation_the_core_hands_back_is_spent_on_the_next_single_call(self):
        page, opener = youtube_page(
            "next_comment_threads.json",
            target_id="next:" + YOUTUBE_VIDEO_ID,
            cursor=YOUTUBE_COMMENT_CURSOR,
        )

        self.assertEqual(len(opener.opened), 1)
        self.assertTrue(page.cursor_out)

    def test_neither_adapter_names_another_adapter_or_the_cores_dispatch(self):
        for module_name, own_id in (
            ("youtube_innertube.py", "youtube_innertube"),
            ("instagram_public.py", "instagram_public"),
        ):
            with self.subTest(module=module_name):
                self.assertEqual(adapters_named(ADAPTER_DIR / module_name, own_id), [])
                self.assertNotIn(
                    "call_adapter", adapter_owner_source(ADAPTER_DIR / module_name)
                )

    def test_neither_adapter_reads_a_file_opens_a_socket_or_waits(self):
        cases = (
            (youtube_innertube, "player_metadata.json", read_youtube,
             youtube_request("player:" + YOUTUBE_VIDEO_ID)),
            (instagram_public, "web_profile_info.json", read_instagram, INSTAGRAM_REQUEST),
        )

        for module, fixture, reader, request in cases:
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                clock = helpers.FakeClock()
                carrier, _ = helpers.offline_transport(
                    clock,
                    {module.DESCRIPTOR.route_id: (200, reader(fixture), "application/json")},
                )

                with helpers.forbid_io():
                    with helpers.forbid_sleep():
                        page = module.fetch_native_page(carrier, request)

                self.assertEqual(page.outcome, "ok")

    def test_a_local_block_is_never_recorded_as_a_platform_gap(self):
        # Inherited from the protocol by writing nothing: `fetch_one_page`
        # reads the channel verdict ahead of any status test either adapter
        # runs, so a captive portal's 503 is `network_intercepted` and never a
        # YouTube attestation or an Instagram refusal.
        portal = TRANSPORT_FIXTURE_DIR.joinpath("captive_portal.html").read_text(
            encoding="utf-8"
        )

        for module, request in (
            (youtube_innertube, youtube_request("player:" + YOUTUBE_VIDEO_ID)),
            (instagram_public, INSTAGRAM_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, _ = adapter_page(
                    module, 503, portal, content_type="text/html", request=request
                )

                self.assertEqual(page.loss, (transport.NETWORK_INTERCEPTED,))
                self.assertEqual(page.outcome, "failed")

    def test_a_refusal_to_slow_down_is_typed_and_never_substituted(self):
        for module, request in (
            (youtube_innertube, youtube_request("player:" + YOUTUBE_VIDEO_ID)),
            (instagram_public, INSTAGRAM_REQUEST),
        ):
            with self.subTest(adapter=module.DESCRIPTOR.adapter_id):
                page, opener = adapter_page(
                    module,
                    transport.RATE_LIMITED_STATUS,
                    "slow down",
                    content_type="text/plain",
                    request=request,
                )

                self.assertEqual(page.loss, (transport.RATE_LIMITED,))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(len(opener.opened), 1)


# The 2026-08-10 probes (Instagram): 455 KB per answer. Held against `MAX_ENTRY_BYTES`
# below, because whether a route's declared window can ever bind depends on it.
