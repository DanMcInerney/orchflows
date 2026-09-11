from tests.test_adapters_cases.youtube_instagram_routes import *  # noqa: F401,F403

class InstagramAnswersWithNoProfileTest(unittest.TestCase):
    """The four ways this route answers with no profile, told apart.

    The one that matters is the login page. It arrives at HTTP 200 saying "Log
    in" in plain words, and reading that as a refusal is exactly the false
    negative the LinkedIn measurement overturned. Only a status line may make
    this route `auth_required`; a body may not, whatever it says.
    """

    def _typed(self, case_name):
        row = next(case for case in instagram_cases() if case["case_name"] == case_name)
        page, _ = instagram_page(
            row["body_fixture"],
            status=row["status"],
            request=adapters.AdapterRequest(step_id="s1-ig", target_ids=(row["username"],)),
        )
        return page, row

    def test_a_username_nobody_holds_is_empty_and_says_so(self):
        page, _ = self._typed("no_such_username_200")

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn("nobody.holds.this.name", " ".join(page.warnings))

    def test_a_payload_whose_container_moved_is_drift_and_not_an_absent_profile(self):
        page, _ = self._typed("payload_container_moved_200")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())
        # Names what was looked for, so an operator learns the shape changed
        # rather than only that nothing came back.
        self.assertIn(
            ".".join(instagram_public.PROFILE_PATH), " ".join(page.warnings)
        )

    def test_a_login_page_at_two_hundred_is_not_read_as_a_refusal(self):
        page, _ = self._typed("login_page_at_200")

        self.assertEqual(page.loss, ("malformed_json",))
        self.assertNotIn(instagram_public.AUTH_REQUIRED, page.loss)

    def test_the_same_bytes_at_two_statuses_are_two_different_answers(self):
        # The sharpest form of the rule. One body, twice: at 200 it is a route
        # that stopped answering in JSON, at 401 it is the origin refusing.
        # Nothing in the body moved, so nothing in the body decided.
        at_two_hundred, _ = self._typed("login_page_at_200")
        refused, _ = self._typed("origin_refused_401")

        self.assertEqual(at_two_hundred.loss, ("malformed_json",))
        self.assertEqual(refused.loss, (instagram_public.AUTH_REQUIRED,))
        self.assertIn("401", " ".join(refused.warnings))

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        for row in instagram_cases():
            with self.subTest(case=row["case_name"]):
                page, _ = self._typed(row["case_name"])

                self.assertEqual(page.outcome, row["expected_outcome"])
                self.assertEqual(
                    tuple(page.loss),
                    (row["expected_loss"],) if row["expected_loss"] else (),
                )

    def test_the_route_returns_no_auth_required_with_an_empty_credential_store(self):
        # Criterion 1's other half. The route carries a vendor-published app
        # id, which is not a user credential and is never asked of anyone: the
        # only way `auth_required` appears is the origin's own status line.
        page, _ = instagram_page("web_profile_info.json")

        self.assertNotIn(instagram_public.AUTH_REQUIRED, page.loss)
        self.assertEqual(page.outcome, "ok")
        self.assertTrue(
            transport.route_admissions()[transport.INSTAGRAM_WEB_PROFILE_ROUTE]
        )


class InstagramDescriptorTest(unittest.TestCase):
    """The descriptor T04's seam reads: measured ceiling, class, declared metric."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        # The 2026-08-10 probes (Instagram): 2.9 s per request, the slowest read in
        # the roster. Nothing here was measured refusing, so burst and cooldown
        # keep the conservative defaults rather than a ceiling nobody observed.
        descriptor = instagram_public.DESCRIPTOR

        self.assertEqual(descriptor.min_interval_ms, 2900)
        self.assertEqual(descriptor.burst, adapters.DEFAULT_BURST)
        self.assertEqual(descriptor.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)
        self.assertEqual(
            runner.route_budgets()[transport.INSTAGRAM_WEB_PROFILE_ROUTE],
            runner.RouteBudget(min_interval_ms=2900, burst=1, cooldown_ms=60000),
        )

    def test_it_declares_the_comment_metric_it_reports_and_no_reply_metric(self):
        # Instagram reports a count of comments on a post and nothing named for
        # replies. Declaring the one under both names would make two of the
        # five views silently identical on a number reported once.
        self.assertEqual(
            instagram_public.DESCRIPTOR.comment_count_metric,
            instagram_public.COMMENT_METRIC,
        )
        self.assertEqual(instagram_public.DESCRIPTOR.reply_count_metric, "")

    def test_it_declares_no_rotating_identifier_because_it_depends_on_none(self):
        # The app id is a vendor-published constant, not a rotating one: it is
        # the same value every client sends and the evidence records it in
        # full. Declaring it volatile would attach a recovery procedure to
        # something that has not been observed to move.
        self.assertEqual(instagram_public.DESCRIPTOR.volatile_identifiers, ())

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        self.assertIn("instagram_public", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("instagram_public"), instagram_public.DESCRIPTOR)

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.INSTAGRAM_WEB_PROFILE_ROUTE: (
                    200,
                    read_instagram("web_profile_info.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter("instagram_public", carrier, INSTAGRAM_REQUEST)

        self.assertEqual(len(page.records), 13)
        self.assertEqual(len(opener.opened), 1)


YOUTUBE_VIDEO_ID = "dQw4w9WgXcQ"
YOUTUBE_SEARCH_TARGET = "search:local models"
YOUTUBE_COMMENT_CURSOR = "Eg0SC2RRdzR3OVdnWGNRGAYyJSIRIgtkUXc0dzlXZ1hjUTAA"

# The 2026-08-10 probes (YouTube): the roster row records a field set for `player` and
# names only the capability for the other two. These are the three the evidence
# enumerates, named as it names them.
YOUTUBE_PLAYER_ROSTER_FIELDS = ("title", "viewCount", "publishDate")


def read_youtube(name):
    """Read one offline YouTube fixture."""

    return YOUTUBE_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


# The two claims a capture in this file makes about a page after the one it
# carries: InnerTube's continuation token and Algolia's `page`/`nbPages` pair.
# Both are the origin's, and a dispatch below that seeds one canned answer per
# route cannot stand behind either — a core that spends the cursor asks for a
# page this opener would answer with the same one. No page two of either route
# has ever been measured, so a whole-dispatch seed states what it can honestly
# stand for, and the page-level rows above keep reading the capture as it came.
NEXT_PAGE_CLAIMS = (
    ('"continuationCommand": {"token": "EpcDEgxsb2NhbCBtb2RlbHMaggNTQlNDQVE"}',
     '"continuationCommand": {}'),
    ('"nbPages": 50', '"nbPages": 1'),
)


def as_a_last_page(body):
    """One capture with the next-page claim it makes dropped."""

    for claim, replacement in NEXT_PAGE_CLAIMS:
        if claim in body:
            return body.replace(claim, replacement)
    raise AssertionError("this capture states no next page to drop")


def youtube_cases():
    """The measured case table: a status, a body, and the loss its evidence names."""

    return tuple(json.loads(read_youtube("attestation_cases.json"))["cases"])


def youtube_request(target_id, cursor=""):
    return adapters.AdapterRequest(step_id="s1-yt", target_ids=(target_id,), cursor=cursor)


def youtube_page(fixture, status=200, target_id=None, cursor=""):
    """Run ``youtube_innertube`` over one canned answer for one named operation."""

    return adapter_page(
        youtube_innertube,
        status,
        read_youtube(fixture),
        content_type="application/json",
        request=youtube_request(
            "player:" + YOUTUBE_VIDEO_ID if target_id is None else target_id, cursor=cursor
        ),
    )


def youtube_comments_page(payload):
    """Run the `next` operation over one payload built here rather than read whole.

    The comment route's own request, because a page assembled in a test is only
    evidence about this adapter if it arrives the way the origin's does: the
    same operation, the same cursor, the same content type.
    """

    return adapter_page(
        youtube_innertube,
        200,
        json.dumps(payload),
        content_type="application/json",
        request=youtube_request(
            "next:" + YOUTUBE_VIDEO_ID, cursor=YOUTUBE_COMMENT_CURSOR
        ),
    )


def attributes_of(record):
    """One record's named string facts, grouped under the names the route used."""

    named = {}
    for name, value in record.attributes:
        named.setdefault(name, []).append(value)
    return named
