from tests.test_adapters_cases.x_stale_and_artifact import *  # noqa: F401,F403

class LinkedInRouteConstantTest(unittest.TestCase):
    """Both LinkedIn routes name a surface the evidence measured, owned by transport."""

    def test_the_jobs_guest_route_is_the_search_endpoint_the_evidence_measured(self):
        request = transport.build_transport_request(
            transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
            {"keywords": "reliability engineer", "location": "Seattle", "start": "10"},
        )

        # The 2026-08-10 probes (LinkedIn): linkedin.com/jobs-guest/jobs/api/
        # seeMoreJobPostings/search returned 200 with 10 jobs, start= paginating.
        self.assertEqual(
            request.url,
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            "?keywords=reliability+engineer&location=Seattle&start=10",
        )
        self.assertEqual(request.method, "GET")

    def test_the_public_profile_route_spends_the_slug_as_a_path_segment(self):
        request = transport.build_transport_request(
            transport.LINKEDIN_PUBLIC_PROFILE_ROUTE, {"slug": "avery-lindqvist-8a41b207"}
        )

        # The 2026-08-10 probes (LinkedIn): linkedin.com/in/<slug> returned 200 with a
        # complete ld+json Person block. The slug is a path segment, so the
        # endpoint's shape stays transport's and only the value is the caller's.
        self.assertEqual(
            request.url, "https://www.linkedin.com/in/avery-lindqvist-8a41b207"
        )
        self.assertEqual(request.method, "GET")

    def test_both_linkedin_routes_are_keyless_and_read_only(self):
        for route_id in (
            transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
            transport.LINKEDIN_PUBLIC_PROFILE_ROUTE,
        ):
            with self.subTest(route=route_id):
                route = transport.route_constant(route_id)

                self.assertTrue(transport.route_admissions()[route_id])
                self.assertEqual(transport.admitted_methods(route_id), transport.READ_METHODS)
                self.assertEqual(route.operator_identity, "linkedin")
                # Neither route carries a credential of any kind. The whole
                # claim this pair defends is that LinkedIn is readable without
                # one, so a credential here would contradict the finding.
                self.assertIsNone(transport.route_credential(route_id))


JOBS_REQUEST = adapters.AdapterRequest(step_id="s1-li", query="reliability engineer")

# The 2026-08-10 probes (LinkedIn): every field the jobs row records this route
# returning per card, named as the evidence names them rather than as the
# record spells them, so the check reads against the roster row.
LINKEDIN_JOBS_ROSTER_FIELDS = ("urn_id", "title", "company", "posted_date")


def read_linkedin(name):
    """Read one offline LinkedIn fixture."""

    return LINKEDIN_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def jobs_roster_row(record):
    """One job card's roster row, keyed by the names the evidence uses."""

    return {
        "urn_id": record.native_item_id,
        "title": record.title,
        "company": record.author,
        "posted_date": record.published_at,
    }


def jobs_page(fixture, status=200, request=None):
    """Run ``linkedin_jobs`` over one canned answer."""

    return adapter_page(
        linkedin_jobs,
        status,
        read_linkedin(fixture),
        content_type="text/html",
        request=JOBS_REQUEST if request is None else request,
    )


class LinkedInJobsPageTest(unittest.TestCase):
    """Criterion 1, K0 half: ten jobs a page, each carrying its whole roster row."""

    def setUp(self):
        self.page, self.opener = jobs_page("jobs_search_page.html")

    def test_one_page_carries_the_ten_jobs_the_evidence_measured(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(len(self.page.records), 10)
        self.assertEqual(len(self.opener.opened), 1)

    def test_every_card_carries_every_field_its_roster_row_names(self):
        for record in self.page.records:
            with self.subTest(item=record.native_item_id):
                carried = jobs_roster_row(record)

                self.assertEqual(sorted(carried), sorted(LINKEDIN_JOBS_ROSTER_FIELDS))
                for name in LINKEDIN_JOBS_ROSTER_FIELDS:
                    self.assertTrue(carried[name], name)
                # The route reports a day and no time of day, so every record
                # from it says so and none of them says anything else.
                self.assertEqual(record.loss, linkedin_jobs.DESCRIPTOR.standing_loss)

    def test_a_record_names_the_posting_its_company_and_the_day_it_appeared(self):
        first = self.page.records[0]

        self.assertEqual(first.canonical_content_kind, "job_posting")
        self.assertEqual(first.native_item_id, "3971120001")
        # The address the card itself published, with its per-response tracking
        # parameters dropped and nothing else touched. Two reads of one posting
        # therefore normalize to one locator and group; and no adapter spells a
        # route's host, which is transport.py's alone.
        self.assertEqual(
            first.canonical_locator,
            "https://www.linkedin.com/jobs/view/"
            "staff-data-engineer-at-northwind-analytics-3971120001",
        )
        self.assertNotIn("refId", first.canonical_locator)
        self.assertEqual(first.title, "Staff Data Engineer")
        self.assertEqual(first.author, "Northwind Analytics")
        self.assertEqual(first.published_at, "2026-08-05T00:00:00Z")
        self.assertEqual(first.native_position, 0)
        self.assertEqual(first.engagement, ())

    def test_a_company_the_origin_pretty_printed_is_the_name_and_not_the_whitespace(self):
        self.assertEqual(self.page.records[2].author, "Harborline Freight")

    def test_the_posted_day_is_read_from_the_time_element_and_not_from_a_class(self):
        # Card 7 carries LinkedIn's listdate--new variant, which it puts on a
        # recent posting. A parser keyed to the class name would lose the date
        # the day a posting became new.
        self.assertEqual(self.page.records[6].published_at, "2026-08-09T00:00:00Z")

    def test_a_card_without_a_posted_date_is_marked_and_never_dated_from_the_read(self):
        page, _ = jobs_page("jobs_partial_card.html")
        complete, partial = page.records

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(complete.loss, linkedin_jobs.DESCRIPTOR.standing_loss)
        self.assertEqual(
            partial.loss, linkedin_jobs.DESCRIPTOR.standing_loss + ("field_omitted",)
        )
        # Absent, not derived: a posting dated from the moment it was found
        # would look exactly as fresh as the search that found it.
        self.assertEqual(partial.published_at, "")
        self.assertEqual(partial.native_item_id, "3971120012")

    def test_a_search_that_matched_nothing_is_empty_and_not_a_page_that_moved(self):
        # The container is there and holds no card, which is the origin saying
        # "no jobs" — a search past the last result, or a keyword nobody posted
        # against. Typing it as drift would send an operator hunting a markup
        # change every time a query came up short.
        page, _ = jobs_page("jobs_empty_list.html")

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn(linkedin_jobs.RESULTS_LIST_CLASS, " ".join(page.warnings))

    def test_markup_carrying_no_card_at_all_is_drift_and_not_an_empty_search(self):
        page, _ = jobs_page("jobs_reshaped_markup.html")
        warning = " ".join(page.warnings)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())
        # Names both declared markers, so an operator learns what was looked
        # for rather than only that nothing was found.
        self.assertIn(linkedin_jobs.RESULTS_LIST_CLASS, warning)
        self.assertIn(linkedin_jobs.JOB_URN_PREFIX, warning)

    def test_an_answer_with_no_markup_at_all_is_empty_and_not_a_page_that_moved(self):
        # Nothing arrived, so nothing changed shape. A body with no markup in
        # it is the route declining to send a list, which is the same fact as
        # an empty list and a different fact from markup that moved.
        page, _ = adapter_page(linkedin_jobs, 200, "   \n", content_type="text/html",
                               request=JOBS_REQUEST)

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())

    def test_the_origins_own_failure_stays_the_origins(self):
        page, _ = adapter_page(
            linkedin_jobs, 503, "<html><body>no</body></html>",
            content_type="text/html", request=JOBS_REQUEST,
        )

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertIn("503", " ".join(page.warnings))

    def test_the_page_speaks_for_linkedin_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "linkedin_jobs")
        self.assertEqual(self.page.platform, "linkedin")
        self.assertEqual(self.page.native_identity_namespace, "linkedin")
        self.assertEqual(self.page.access_class, "K0")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE)

    def test_the_start_offset_is_the_callers_and_the_adapter_derives_none(self):
        # Row 4: `start=` pagination is the core's. The caller's cursor is
        # spent on the wire, and the page hands back no next offset — this
        # fragment states none, and inventing one from the count returned would
        # make the adapter the thing that decides there is another page.
        page, opener = jobs_page(
            "jobs_search_page.html",
            request=adapters.AdapterRequest(
                step_id="s1-li", query="reliability engineer", cursor="10"
            ),
        )

        self.assertIn("start=10", opener.opened[0].url)
        self.assertEqual(page.cursor_out, "")
        self.assertEqual(len(opener.opened), 1)

    def test_a_first_page_asks_for_no_offset_at_all(self):
        self.assertNotIn("start=", self.opener.opened[0].url)
        self.assertIn("keywords=reliability+engineer", self.opener.opened[0].url)


class LinkedInJobsDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metrics."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # The 2026-08-10 probes (LinkedIn): 0.7 s per request. Nothing on this route
        # was measured refusing, so burst and cooldown keep the conservative
        # defaults rather than a ceiling nobody observed.
        descriptor = linkedin_jobs.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 700)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE],
            runner.RouteBudget(min_interval_ms=700, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_neither_engagement_metric_because_the_route_reports_none(self):
        # A metric name is never inferred. With `comment_count_metric` unset a
        # snapshot named `comment_count` would be a missing comment count, and
        # this route reports no count of any kind.
        self.assertEqual(linkedin_jobs.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(linkedin_jobs.DESCRIPTOR.reply_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("linkedin_jobs", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("linkedin_jobs"), linkedin_jobs.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE: (
                    200,
                    read_linkedin("jobs_search_page.html"),
                    "text/html",
                )
            },
        )
        page = runner.call_adapter("linkedin_jobs", carrier, JOBS_REQUEST)

        self.assertEqual(len(page.records), 10)
        self.assertEqual(len(opener.opened), 1)


PROFILE_SLUG = "avery-lindqvist-8a41b207"
LINKEDIN_PROFILE_REQUEST = adapters.AdapterRequest(
    step_id="s1-li", target_ids=(PROFILE_SLUG,)
)

# The 2026-08-10 probes (LinkedIn): every field the profile row records the ld+json
# Person block carrying, named as the evidence names them.
LINKEDIN_PROFILE_ROSTER_FIELDS = (
    "name",
    "jobTitle",
    "addressLocality",
    "description",
    "worksFor",
    "alumniOf",
)


def profile_page(fixture, status=200, request=None):
    """Run ``linkedin_public`` over one canned answer."""

    return adapter_page(
        linkedin_public,
        status,
        read_linkedin(fixture),
        content_type="text/html",
        request=LINKEDIN_PROFILE_REQUEST if request is None else request,
    )


def profile_roster_row(record):
    """One profile's roster row exactly as a caller reads it off the record.

    Deliberately assembled from the record and never from the adapter's own
    parse: the claim is that the fields reach the value a caller keeps, and a
    helper that read the block again would be checking the parser twice.
    """

    repeated = {}
    for name, value in record.attributes:
        repeated.setdefault(name, []).append(value)
    return {
        "name": record.title,
        "jobTitle": repeated.get("jobTitle", []),
        "addressLocality": "".join(repeated.get("addressLocality", [])),
        "description": record.body,
        "worksFor": repeated.get("worksFor", []),
        "alumniOf": repeated.get("alumniOf", []),
    }


class LinkedInPublicProfileTest(unittest.TestCase):
    """Criterion 1, K2 half: the whole Person block out of a page anyone can read."""

    def setUp(self):
        self.page, self.opener = profile_page("profile_person.html")

    def test_one_page_carries_the_one_profile_this_route_serves(self):
        self.assertEqual(self.page.outcome, "ok")
        self.assertEqual(self.page.loss, ())
        self.assertEqual(len(self.page.records), 1)
        self.assertEqual(len(self.opener.opened), 1)

    def test_the_record_carries_every_field_its_roster_row_names(self):
        carried = profile_roster_row(self.page.records[0])

        self.assertEqual(sorted(carried), sorted(LINKEDIN_PROFILE_ROSTER_FIELDS))
        for name in LINKEDIN_PROFILE_ROSTER_FIELDS:
            self.assertTrue(carried[name], name)
        self.assertEqual(carried["name"], "Avery Lindqvist")
        # Repeated facts arrive repeated, in the order the block listed them.
        # Joining them into one string would invent a separator the origin
        # never sent and make two positions unreadable as two.
        self.assertEqual(
            carried["jobTitle"], ["Principal Reliability Engineer", "Board Advisor"]
        )
        self.assertEqual(
            carried["addressLocality"], "Gothenburg, Vastra Gotaland County, Sweden"
        )
        self.assertIn("distributed storage", carried["description"])
        self.assertEqual(carried["worksFor"], ["Northwind Analytics", "Kestrel Systems"])
        self.assertEqual(
            carried["alumniOf"],
            ["Chalmers University of Technology", "Lund University"],
        )
        self.assertEqual(self.page.records[0].loss, ())

    def test_the_record_names_the_profile_and_the_address_the_origin_published(self):
        record = self.page.records[0]

        self.assertEqual(record.canonical_content_kind, "profile")
        # Identity is the slug this run read, which is the route's own path
        # segment and LinkedIn's own public name for a member. The address is
        # the one the block published, so no adapter spells a route host.
        self.assertEqual(record.native_item_id, PROFILE_SLUG)
        self.assertEqual(record.author, PROFILE_SLUG)
        self.assertEqual(
            record.canonical_locator,
            "https://www.linkedin.com/in/avery-lindqvist-8a41b207",
        )
        # A profile page states no publication time, so the record states none
        # rather than borrowing the moment it was read.
        self.assertEqual(record.published_at, "")
        self.assertEqual(record.engagement, ())
        self.assertEqual(record.native_position, 0)

    def test_the_person_is_found_by_its_declared_type_and_never_by_position(self):
        # The page carries two ld+json scripts and the Person is in neither
        # first position: not the first script, and not the first node of the
        # graph inside it. A parser keyed to position would read a
        # BreadcrumbList and report a profile named "LinkedIn".
        self.assertEqual(self.page.records[0].title, "Avery Lindqvist")

    def test_a_profile_the_origin_populated_in_part_is_marked_and_never_filled(self):
        page, _ = profile_page(
            "profile_partial_person.html",
            request=adapters.AdapterRequest(
                step_id="s1-li", target_ids=("mira-okonkwo-4d90c113",)
            ),
        )
        carried = profile_roster_row(page.records[0])

        self.assertEqual(page.outcome, "ok")
        self.assertEqual(page.records[0].loss, ("field_omitted",))
        # Marked, and absent rather than invented: no locality and no summary
        # at all, instead of an empty string that reads as "wrote nothing".
        self.assertEqual(carried["addressLocality"], "")
        self.assertEqual(carried["description"], "")
        self.assertEqual(carried["jobTitle"], [])
        self.assertEqual(carried["alumniOf"], [])
        self.assertEqual(carried["name"], "Mira Okonkwo")
        self.assertEqual(carried["worksFor"], ["Kestrel Systems"])

    def test_the_slug_is_read_from_the_target_or_from_the_query(self):
        for request in (
            adapters.AdapterRequest(step_id="s1-li", target_ids=(PROFILE_SLUG,)),
            adapters.AdapterRequest(step_id="s1-li", query=PROFILE_SLUG),
        ):
            with self.subTest(request=request):
                _, opener = profile_page("profile_person.html", request=request)

                self.assertTrue(
                    opener.opened[0].url.endswith("/" + PROFILE_SLUG), opener.opened[0].url
                )

    def test_the_page_speaks_for_linkedin_at_the_class_the_ladder_gives_it(self):
        self.assertEqual(self.page.adapter_id, "linkedin_public")
        self.assertEqual(self.page.platform, "linkedin")
        self.assertEqual(self.page.native_identity_namespace, "linkedin")
        self.assertEqual(self.page.access_class, "K2")
        self.assertEqual(self.page.representation_kind, "native")
        self.assertEqual(self.page.route_id, transport.LINKEDIN_PUBLIC_PROFILE_ROUTE)


class LinkedInPublicDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metrics."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # The 2026-08-10 probes (LinkedIn): 1.3 s per request. Nothing on this route
        # was measured refusing, so burst and cooldown keep the conservative
        # defaults rather than a ceiling nobody observed.
        descriptor = linkedin_public.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 1300)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.LINKEDIN_PUBLIC_PROFILE_ROUTE],
            runner.RouteBudget(min_interval_ms=1300, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_neither_engagement_metric_because_the_block_reports_none(self):
        self.assertEqual(linkedin_public.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(linkedin_public.DESCRIPTOR.reply_count_metric, "")

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("linkedin_public", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("linkedin_public"), linkedin_public.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.LINKEDIN_PUBLIC_PROFILE_ROUTE: (
                    200,
                    read_linkedin("profile_person.html"),
                    "text/html",
                )
            },
        )
        page = runner.call_adapter("linkedin_public", carrier, LINKEDIN_PROFILE_REQUEST)

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)


