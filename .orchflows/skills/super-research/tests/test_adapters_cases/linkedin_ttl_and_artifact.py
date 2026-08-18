from tests.test_adapters_cases.linkedin_claims import *  # noqa: F401,F403

MEASURED_LINKEDIN_BYTES = 577 * 1024


class LinkedInRouteTtlTest(unittest.TestCase):
    """How long each LinkedIn route's answer may stand in for a fresh read.

    A TTL belongs to a route's own volatility, and `cache.py`'s default is
    deliberately short — a route nobody has measured is not one to trust for
    long. Both of these were measured, so both declare their own, and the proof
    is behavioral from both sides: a re-read inside the window that the default
    would have sent back to the origin, and one outside it that comes back.
    """

    def _paced(self, clock, route_id, body):
        carrier, opener = helpers.offline_transport(
            clock, {route_id: (200, body, "text/html")}
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
            transport.LINKEDIN_PUBLIC_PROFILE_ROUTE,
            read_linkedin("profile_person.html"),
        )

        first = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)
        clock.advance(600)
        held = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)
        clock.advance(400)
        expired = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)

        self.assertNotIn(cache.CACHE_HIT, first.loss)
        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        # The mark moves, the moment does not: a served page still states when
        # the origin was really read.
        self.assertEqual(held.observed_at, first.observed_at)
        self.assertEqual(len(held.records), 1)

    def test_the_route_serving_the_more_volatile_thing_holds_it_for_the_least_time(self):
        # A profile changes when a member edits it and its block carries no
        # counter, and it is the most expensive read in the roster per item —
        # 577 KB and 1.3 s. A jobs search changes as postings arrive and costs
        # 27 KB and 0.7 s, so holding it longer buys less and risks more.
        clock = helpers.FakeClock()
        governor, opener = self._paced(
            clock,
            transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
            read_linkedin("jobs_search_page.html"),
        )

        linkedin_jobs.fetch_native_page(governor, JOBS_REQUEST)
        clock.advance(120)
        held = linkedin_jobs.fetch_native_page(governor, JOBS_REQUEST)
        clock.advance(240)
        expired = linkedin_jobs.fetch_native_page(governor, JOBS_REQUEST)

        self.assertIn(cache.CACHE_HIT, held.loss)
        self.assertNotIn(cache.CACHE_HIT, expired.loss)
        self.assertEqual(len(opener.opened), 2)
        self.assertLess(
            cache.ttl_seconds(transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE),
            cache.ttl_seconds(transport.LINKEDIN_PUBLIC_PROFILE_ROUTE),
        )

    def test_a_body_the_size_the_evidence_measured_is_held_rather_than_served_through(self):
        # The 2026-08-10 probes recorded this route at 577 KB — the largest answer in
        # the roster, and the one its 900 s window exists for. The window is
        # real at the size the evidence actually measured, not only at some
        # smaller page. Stated here rather than in prose so it cannot rot.
        clock = helpers.FakeClock()
        payload = read_linkedin("profile_person.html")
        measured = payload + "<!--{0}-->".format(
            "x" * (MEASURED_LINKEDIN_BYTES - len(payload.encode("utf-8")) - 7)
        )
        governor, opener = self._paced(
            clock, transport.LINKEDIN_PUBLIC_PROFILE_ROUTE, measured
        )

        first = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)
        clock.advance(1)
        second = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)

        self.assertEqual(len(measured.encode("utf-8")), MEASURED_LINKEDIN_BYTES)
        self.assertLess(MEASURED_LINKEDIN_BYTES, cache.MAX_ENTRY_BYTES)
        self.assertIn(cache.CACHE_HIT, second.loss)
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(len(first.records), 1)
        self.assertEqual(len(second.records), 1)

    def test_a_body_past_the_cap_is_still_served_through(self):
        # The guard still guards; it guards at a higher number. A page this
        # far past the cap has never been measured on this route — the point
        # is that the cap binds when something does reach it.
        clock = helpers.FakeClock()
        oversized = read_linkedin("profile_person.html") + "<!--{0}-->".format(
            "x" * cache.MAX_ENTRY_BYTES
        )
        governor, opener = self._paced(
            clock, transport.LINKEDIN_PUBLIC_PROFILE_ROUTE, oversized
        )

        first = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)
        clock.advance(1)
        second = linkedin_public.fetch_native_page(governor, LINKEDIN_PROFILE_REQUEST)

        self.assertGreater(len(oversized.encode("utf-8")), cache.MAX_ENTRY_BYTES)
        self.assertNotIn(cache.CACHE_HIT, second.loss)
        self.assertEqual(len(opener.opened), 2)
        # Served through, and still correct: the page is parsed both times.
        self.assertEqual(len(first.records), 1)
        self.assertEqual(len(second.records), 1)


def linkedin_manifest():
    """One dispatch reading LinkedIn through both of its routes."""

    return schema.AcquisitionManifest(
        manifest_id="m-li-pair",
        mode="staged",
        as_of="2026-08-10T09:00:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-jobs",
                kind="discovery",
                adapter_id="linkedin_jobs",
                query="reliability engineer",
                max_items=25,
            ),
            schema.AcquisitionStep(
                step_id="s2-profile",
                kind="hydration",
                adapter_id="linkedin_public",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.linkedin.com/in/" + PROFILE_SLUG,
                        target_id=PROFILE_SLUG,
                    ),
                ),
                max_items=5,
            ),
        ),
    )


class LinkedInArtifactSeamTest(unittest.TestCase):
    """The widest seam: the record a caller keeps, after normalize has run.

    Every test above reads a ``NativePage``, which is an intermediate value.
    "LinkedIn reaches its measured capability" is a claim about the artifact,
    so it is closed here — including the part where the whole Person block
    survives normalization under the block's own names.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE: (
                    200,
                    read_linkedin("jobs_search_page.html"),
                    "text/html",
                ),
                transport.LINKEDIN_PUBLIC_PROFILE_ROUTE: (
                    200,
                    read_linkedin("profile_person.html"),
                    "text/html",
                ),
            },
        )
        self.artifact = runner.run_acquisition(
            linkedin_manifest(), carrier, clock=clock.monotonic
        )
        self.jobs = [
            record
            for record in self.artifact.records
            if record.canonical_content_kind == "job_posting"
        ]

    def test_the_artifact_holds_every_row_both_routes_returned(self):
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())
        self.assertEqual(len(self.artifact.records), 11)
        self.assertEqual([step.records_kept for step in self.artifact.steps], [10, 1])
        self.assertEqual(len(self.opener.opened), 2)

    def test_a_profile_record_keeps_its_whole_roster_row_where_a_caller_reads_it(self):
        profile = self.artifact.records[-1]
        carried = profile_roster_row(profile)

        for name in LINKEDIN_PROFILE_ROSTER_FIELDS:
            self.assertTrue(carried[name], name)
        self.assertEqual(profile.access_class, "K2")
        self.assertEqual(profile.platform, "linkedin")
        # The page states no publication time, so the record claims none and
        # says so rather than borrowing the moment it was read.
        self.assertEqual(profile.time_confidence, "unknown")
        self.assertEqual(profile.usable_basis_time, "")

    def test_a_job_record_says_both_what_it_knows_and_how_precisely(self):
        first = self.jobs[0]

        self.assertEqual(first.access_class, "K0")
        self.assertEqual(first.published_at, "2026-08-05T00:00:00Z")
        self.assertEqual(first.usable_basis_time, "2026-08-05T00:00:00Z")
        # LinkedIn's own date, so the day is authoritative — and the midnight
        # is this package's form for a day, which the record says out loud
        # rather than leaving a reader to assume a posting appeared at 00:00.
        self.assertEqual(first.time_confidence, "authoritative")
        self.assertEqual(first.loss, ("date_precision_only",))

    def test_one_platform_read_at_two_access_classes_stays_eleven_records(self):
        # wrong_merge_law rule 1: a strong identity is namespace, item id and
        # content kind together. Ten postings and one profile share a platform
        # and a namespace and nothing else, so nothing here may fold.
        multiples = [
            group for group in self.artifact.groups if len(group.member_record_ids) > 1
        ]

        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K0", "K2"]
        )
        self.assertEqual(len(self.artifact.groups), 11)
        self.assertEqual(multiples, [])
        self.assertEqual(
            sorted({group.key_kind for group in self.artifact.groups}), ["strong"]
        )

    def test_two_postings_from_one_company_are_two_records_and_never_one(self):
        # Three of these ten are Northwind Analytics. A grouping that keyed on
        # anything the cards share rather than on the posting's own id would
        # collapse them, and a caller would lose two open roles.
        northwind = [
            record for record in self.jobs if record.author == "Northwind Analytics"
        ]

        self.assertEqual(len(northwind), 3)
        self.assertEqual(len({record.record_id for record in northwind}), 3)
        self.assertEqual(len({record.canonical_locator for record in northwind}), 3)

    def test_a_route_reporting_no_count_refuses_the_counted_view_out_loud(self):
        # Neither descriptor declares a comment or reply metric, so the two
        # metric orders have no eligible snapshot to rank on. Until 2026-08-17
        # they fell through to time while still answering to the counted
        # name — the silent degradation the bakeoff review measured; a counted
        # view over a set in which nothing counts is refused, and the refusal
        # says why. `newest` is the view that answers here.
        for record in self.jobs:
            self.assertIsNone(
                runner.eligible_snapshot(record, "comment_count", self.artifact.as_of)
            )
        with self.assertRaisesRegex(runner.OrderingError, "no eligible metric"):
            runner.order_records(self.jobs, "most_commented", self.artifact.as_of)
        self.assertEqual(
            len(runner.order_records(self.jobs, "newest", self.artifact.as_of)),
            len(self.jobs),
        )

    def test_newest_orders_day_precision_postings_by_the_day_the_origin_reported(self):
        ranked = runner.order_records(self.jobs, "newest", self.artifact.as_of)

        self.assertEqual(
            [record.native_item_id for record in ranked],
            [
                "3971120007",
                "3971120001",
                "3971120002",
                "3971120003",
                "3971120004",
                "3971120005",
                "3971120006",
                "3971120008",
                "3971120009",
                "3971120010",
            ],
        )


