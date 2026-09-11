from tests.test_adapters_cases.youtube_oracles_and_calls import *  # noqa: F401,F403

MEASURED_INSTAGRAM_BYTES = 455 * 1024


class YoutubeInstagramRouteTtlTest(unittest.TestCase):
    """How long each route's answer may stand in for a fresh read.

    One of these two declares a window and one cannot have one, and the
    difference is not a preference. A TTL belongs to a route's own volatility,
    and `cache.py`'s default is deliberately short — a route nobody has
    measured is not one to trust for long — so a declared window is proven from
    both sides here: a re-read inside it that the default would have sent back
    to the origin, and one outside it that comes back.
    """

    def _paced(self, clock, route_id, body):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "application/json")}
        )
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )
        return governor, opener

    def test_a_profile_reread_inside_the_window_is_answered_from_memory(self):
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.INSTAGRAM_WEB_PROFILE_ROUTE,
            read_instagram("web_profile_info.json"),
        )

        first = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)
        clock.advance(120)
        held = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)
        clock.advance(240)
        expired = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        # Two minutes, which the inherited default would have sent back to the
        # origin at a cost of 2.9 s — the slowest read in the roster.
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read.
        self.assertEqual(held.observed_at, first.observed_at)
        self.assertEqual(len(held.records), 13)

    def test_the_route_carrying_counts_holds_them_for_less_time_than_a_block_with_none(self):
        # A profile page's ld+json block carries no counter at all and changes
        # when a member edits it, so LinkedIn's window is the roster's longest.
        # This payload carries a follower count and twelve pairs of like and
        # comment counts, all of which move while nobody edits anything, so it
        # cannot hold them that long however expensive the read is.
        self.assertLess(
            cache.ttl_seconds(transport.INSTAGRAM_WEB_PROFILE_ROUTE),
            cache.ttl_seconds(transport.LINKEDIN_PUBLIC_PROFILE_ROUTE),
        )
        self.assertGreater(
            cache.ttl_seconds(transport.INSTAGRAM_WEB_PROFILE_ROUTE),
            cache.DEFAULT_TTL_SECONDS,
        )

    def test_a_body_the_size_the_evidence_measured_is_held_rather_than_served_through(self):
        # The mirror of the LinkedIn profile route, which makes the same claim
        # at 577 KB. At 455 KB this one fits with more room to spare, so the
        # window above is real at the size the evidence actually measured —
        # with 569 KB of headroom, and not a byte more.
        clock = helpers.FakeClock()
        payload = read_instagram("web_profile_info.json")
        measured = payload + " " * (MEASURED_INSTAGRAM_BYTES - len(payload.encode("utf-8")))
        governor, opener = self._paced(
            clock, transport.INSTAGRAM_WEB_PROFILE_ROUTE, measured
        )

        first = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)
        clock.advance(60)
        held = instagram_public.fetch_native_page(governor, INSTAGRAM_REQUEST)

        self.assertEqual(len(measured.encode("utf-8")), MEASURED_INSTAGRAM_BYTES)
        self.assertLess(MEASURED_INSTAGRAM_BYTES, cache.MAX_ENTRY_BYTES)
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(len(first.records), 13)
        self.assertEqual(len(held.records), 13)

    def test_an_innertube_answer_is_never_held_because_the_read_is_not_a_get(self):
        # The InnerTube route declares no window, and the reason is structural
        # rather than a judgment about volatility: `cache.cacheable` holds only
        # what came back from a read method, and this route asks its question
        # in a POST body. A second identical read one second later still
        # reaches the origin, so no window it could declare would ever bind.
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock, transport.YOUTUBE_INNERTUBE_ROUTE, read_youtube("player_metadata.json")
        )
        request = youtube_request("player:" + YOUTUBE_VIDEO_ID)

        first = youtube_innertube.fetch_native_page(governor, request)
        clock.advance(1)
        second = youtube_innertube.fetch_native_page(governor, request)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertNotIn(cache.CACHE_HIT, second.loss)
        self.assertEqual(len(opener.opened), 2)
        self.assertNotIn(
            transport.route_constant(transport.YOUTUBE_INNERTUBE_ROUTE).method,
            transport.READ_METHODS,
        )
        self.assertNotIn(transport.YOUTUBE_INNERTUBE_ROUTE, cache.ROUTE_TTL_SECONDS)

    def test_two_of_the_three_innertube_answers_are_too_large_to_hold_anyway(self):
        # And the window would not bind even if the verb changed: the
        # 2026-08-10 probes recorded search at 2.27 MB and next at 1.12 MB, both past
        # `MAX_ENTRY_BYTES`, so only the 21 KB player answer could ever be
        # held. The smaller of the two is what fixes the ceiling on that
        # constant — a cap above 1.12 MB would start holding it.
        for measured_bytes in (2270 * 1024, 1120 * 1024):
            with self.subTest(body_bytes=measured_bytes):
                self.assertGreater(measured_bytes, cache.MAX_ENTRY_BYTES)
        self.assertLess(21 * 1024, cache.MAX_ENTRY_BYTES)


class KeylessCredentialTest(unittest.TestCase):
    """Criterion 4: the two K1 credentials live in one module and reach no record.

    Both are vendor-published client credentials rather than user secrets —
    the key youtube.com embeds in its own page source, and the app id
    Instagram's own web client sends — so the question is not whether they are
    kept safe but whether they stay route constants. A credential that reached
    a manifest or an artifact would make a keyless route look credentialed to
    everything downstream, which is the same false capability this pair's
    other checks defend from the opposite direction.
    """

    def _values(self):
        return (
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.YOUTUBE_INNERTUBE_WEB_KEY].value,
            transport.PUBLIC_CLIENT_CREDENTIALS[transport.INSTAGRAM_WEB_APP_ID].value,
        )

    def test_neither_credential_is_spelled_in_any_module_but_a_declared_owner(self):
        owners = {
            owner
            for name in ROUTE_OWNING_MODULES
            for owner in adapter_owner_paths(PACKAGE_DIR / (name + ".py"))
        }
        named = sorted(
            (path.name, value)
            for path in PACKAGE_DIR.rglob("*.py")
            if path not in owners
            for value in self._values()
            if value in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])

    def test_neither_credential_reaches_an_artifact_either_route_produced(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_INNERTUBE_ROUTE: [
                    (200, read_youtube("search_results.json"), "application/json"),
                    (200, read_youtube("player_metadata.json"), "application/json"),
                ],
                transport.INSTAGRAM_WEB_PROFILE_ROUTE: (
                    200,
                    read_instagram("web_profile_info.json"),
                    "application/json",
                ),
            },
        )

        artifact = runner.run_acquisition(
            youtube_instagram_manifest(), carrier, clock=clock.monotonic
        )

        self.assertTrue(artifact.records)
        for value in self._values():
            with self.subTest(credential=value[:8]):
                self.assertNotIn(value, repr(artifact))
                self.assertNotIn(value, repr(carrier.calls))
                self.assertNotIn(value, repr(youtube_instagram_manifest()))


def youtube_instagram_manifest():
    """One dispatch reading both platforms, and YouTube twice about one video."""

    return schema.AcquisitionManifest(
        manifest_id="m-yt-ig",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-search",
                kind="discovery",
                adapter_id="youtube_innertube",
                query="local models",
                max_items=25,
            ),
            schema.AcquisitionStep(
                step_id="s2-video",
                kind="hydration",
                adapter_id="youtube_innertube",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.youtube.com/watch?v=" + YOUTUBE_VIDEO_ID,
                        target_id="player:" + YOUTUBE_VIDEO_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s3-profile",
                kind="hydration",
                adapter_id="instagram_public",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.instagram.com/" + INSTAGRAM_USERNAME + "/",
                        target_id=INSTAGRAM_USERNAME,
                    ),
                ),
                max_items=25,
            ),
        ),
    )


class YoutubeInstagramArtifactSeamTest(unittest.TestCase):
    """The widest seam: the record a caller keeps, after normalize has run.

    Every test above reads a ``NativePage``, which is an intermediate value.
    "These two reach their measured capability" is a claim about the artifact,
    so it is closed here — including the part where the one thing this half
    must never say quietly stays said, on the record and on the artifact.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                # One route, two operations, in the order the steps run them.
                transport.YOUTUBE_INNERTUBE_ROUTE: [
                    (200, as_a_last_page(read_youtube("search_results.json")),
                     "application/json"),
                    (200, read_youtube("player_metadata.json"), "application/json"),
                ],
                transport.INSTAGRAM_WEB_PROFILE_ROUTE: (
                    200,
                    read_instagram("web_profile_info.json"),
                    "application/json",
                ),
            },
        )
        self.artifact = runner.run_acquisition(
            youtube_instagram_manifest(), carrier, clock=clock.monotonic
        )
        self.posts = [
            record
            for record in self.artifact.records
            if record.adapter_id == "instagram_public"
            and record.canonical_content_kind == "post"
        ]

    def test_the_artifact_holds_every_row_all_three_steps_returned(self):
        self.assertEqual(len(self.artifact.records), 19)
        self.assertEqual([step.records_kept for step in self.artifact.steps], [5, 1, 13])
        self.assertEqual(len(self.opener.opened), 3)
        self.assertEqual(self.artifact.outcome, "ok")

    def test_the_one_thing_this_half_must_never_say_reaches_the_artifact_unsaid(self):
        # The whole ticket, at the value a caller keeps: nothing anywhere in
        # this artifact states that the video has no captions, and the reason
        # the captions are missing is on the record and on the run.
        video = [
            record
            for record in self.artifact.records
            if record.step_id == "s2-video"
        ][0]

        self.assertEqual(self.artifact.loss, (youtube_innertube.ATTESTATION_REQUIRED,))
        self.assertIn(youtube_innertube.ATTESTATION_REQUIRED, video.loss)
        self.assertEqual(video.title, "Running a 70B locally on two consumer GPUs")
        self.assertEqual(video.usable_basis_time, "2026-07-26T00:00:00Z")
        self.assertEqual(video.time_confidence, "authoritative")
        self.assertIn("date_precision_only", video.loss)

    def test_one_video_seen_twice_is_two_records_held_together(self):
        # wrong_merge_law rule 1: a search hit and a player read of one video
        # share a namespace, an item id and a content kind, so they are one
        # group of two and never one record. They disagree about nothing here,
        # and they would still not be folded if they did.
        seen = [
            record
            for record in self.artifact.records
            if record.native_item_id == YOUTUBE_VIDEO_ID
        ]
        grouped = [
            group for group in self.artifact.groups if len(group.member_record_ids) > 1
        ]

        self.assertEqual([record.step_id for record in seen], ["s1-search", "s2-video"])
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0].key_kind, "strong")
        self.assertEqual(
            sorted(grouped[0].member_record_ids), sorted(record.record_id for record in seen)
        )

    def test_a_search_hit_is_the_platform_speaking_and_not_an_index_entry(self):
        # Every operation on this route is YouTube reporting its own items, so
        # nothing here is an index representation. The search hit is still the
        # discovery the player read was selected from, so the two are linked —
        # linked, and grouped apart, because a link is not a merge.
        self.assertEqual(
            sorted({record.representation_kind for record in self.artifact.records}),
            ["native"],
        )
        self.assertEqual(
            [(edge.from_record_id, edge.to_record_id) for edge in self.artifact.edges],
            [("s1-search#0.0", "s2-video#0.0")],
        )

    def test_a_named_fact_the_route_wrote_for_a_reader_survives_normalization(self):
        first = [
            record for record in self.artifact.records if record.step_id == "s1-search"
        ][0]

        self.assertEqual(
            first.attributes,
            (
                (youtube_innertube.VIEW_COUNT_TEXT_KEY, "1,284,553 views"),
                (youtube_innertube.PUBLISHED_TIME_TEXT_KEY, "2 weeks ago"),
            ),
        )
        # And the record states no time at all, rather than one derived from
        # the words beside it.
        self.assertEqual(first.usable_basis_time, "")
        self.assertEqual(first.time_confidence, "unknown")

    def test_a_post_keeps_the_platforms_own_counts_at_the_moment_they_were_read(self):
        first = self.posts[0]
        snapshots = {snapshot.metric_name: snapshot for snapshot in first.engagement}

        self.assertEqual(
            sorted(snapshots),
            sorted((instagram_public.LIKE_METRIC, instagram_public.COMMENT_METRIC)),
        )
        self.assertEqual(snapshots[instagram_public.LIKE_METRIC].value, 412873)
        self.assertEqual(
            snapshots[instagram_public.LIKE_METRIC].observed_at, first.observed_at
        )
        # The platform's own payload, so its times are authoritative rather
        # than reported: nothing here is an archive speaking for Instagram.
        self.assertEqual(first.time_confidence, "authoritative")
        self.assertEqual(first.access_class, "K1")

    def test_a_route_that_declares_a_comment_metric_ranks_on_the_one_it_reported(self):
        # The counterpart to LinkedIn's fall-through: there, no metric was
        # declared and `most_commented` ranked on time. Here the descriptor
        # names the exact key path the payload publishes the count at, so the
        # view ranks on the count itself — and on nothing this package named.
        ranked = runner.order_records(self.posts, "most_commented", self.artifact.as_of)
        counts = [
            runner.eligible_snapshot(
                record, instagram_public.COMMENT_METRIC, self.artifact.as_of
            ).value
            for record in ranked
        ]

        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(ranked[0].native_item_id, "C9xR2mQLpQz")
        self.assertNotEqual(
            [record.native_item_id for record in ranked],
            [
                record.native_item_id
                for record in runner.order_records(
                    self.posts, "newest", self.artifact.as_of
                )
            ],
        )

    def test_two_platforms_at_one_access_class_stay_nineteen_records(self):
        # Both of these are `K1`, and nothing about sharing a class makes two
        # platforms' rows comparable. Nineteen records, nineteen strong
        # identities, and exactly one fold — the video read twice, above.
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K1"]
        )
        self.assertEqual(
            sorted({record.platform for record in self.artifact.records}),
            ["instagram", "youtube"],
        )
        self.assertEqual(len(self.artifact.groups), 18)
        self.assertEqual(
            sorted({group.key_kind for group in self.artifact.groups}), ["strong"]
        )


# The 2026-08-10 probes, carry-over routes: the four surfaces this ticket reads, named
# here as the evidence names them so the route checks read against the roster
# row rather than against an adapter's own constants.
