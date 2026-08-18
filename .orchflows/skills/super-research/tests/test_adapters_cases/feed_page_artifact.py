from tests.test_adapters_cases.feed_page_calls_and_ttl import *  # noqa: F401,F403

TRACER_FIXTURE_DIR = TEST_DIR / "fixtures" / "tracer"
ARCHIVED_POST_ID = "1abc234"

# The whole roster, at the revision that completes it: nineteen live adapters
# plus the offline fixture, each with the class the measured ladder gives it.
# T10 binds its access-class law to this set, so it is spelled here in full
# rather than derived — a list compared only against itself would admit a
# eighteenth member silently.
ROSTER = {
    "bluesky": "K0",
    "fake": "offline",
    "github_rest": "K0",
    "hacker_news": "K0",
    "instagram_public": "K1",
    "linkedin_jobs": "K0",
    "linkedin_public": "K2",
    "prediction_markets": "K0",
    "public_page": "K0",
    "reddit_archive": "K3",
    "reddit_feed": "K0",
    "reddit_shreddit": "K2",
    "rss_atom": "K0",
    "stocktwits": "K0",
    "open_page": "K0",
    "web_search": "K4",
    "x_fxtwitter": "K3",
    "x_guest": "K1",
    "x_syndication": "K2",
    "youtube_innertube": "K1",
}


def feed_page_manifest():
    """One dispatch across the roster's last three, and one post seen twice."""

    return schema.AcquisitionManifest(
        manifest_id="m-feed-page",
        mode="staged",
        # After the reads this dispatch makes, because a frozen horizon that
        # fell before its own observations would replay to nothing.
        as_of="2026-08-10T09:05:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-feed",
                kind="discovery",
                adapter_id="reddit_feed",
                query=REDDIT_SUBREDDIT,
                max_items=20,
            ),
            schema.AcquisitionStep(
                step_id="s2-archive",
                kind="hydration",
                adapter_id="reddit_archive",
                prior_step_id="s1-feed",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator=REDDIT_PERMALINK, target_id=ARCHIVED_POST_ID
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s3-channel",
                kind="discovery",
                adapter_id="rss_atom",
                query=FEED_CHANNEL_ID,
                max_items=20,
            ),
            schema.AcquisitionStep(
                step_id="s4-article",
                kind="hydration",
                adapter_id="public_page",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator=ARTICLE_LOCATOR, target_id=ARTICLE_TARGET
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s5-control",
                kind="discovery",
                adapter_id="public_page",
                query="control",
                max_items=5,
            ),
        ),
    )


class FeedPageArtifactSeamTest(unittest.TestCase):
    """The widest seam: the records a caller keeps, after normalize has run.

    Every check above reads a ``NativePage``, which is an intermediate value.
    "These three reach their measured capability" is a claim about the
    artifact, and one thing only becomes visible here: Reddit's freshness probe
    and Reddit's archive describe the same post, name it with the same
    identity string, and arrive as two records that are never folded into one.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                transport.REDDIT_FEED_ROUTE: (
                    200,
                    read_reddit_feed("subreddit_new.xml"),
                    "application/atom+xml",
                ),
                transport.ARCTIC_SHIFT_POSTS_ROUTE: (
                    200,
                    TRACER_FIXTURE_DIR.joinpath("arctic_shift_posts_ids.json").read_text(
                        encoding="utf-8"
                    ),
                    "application/json",
                ),
                transport.YOUTUBE_CHANNEL_FEED_ROUTE: (
                    200,
                    read_rss_atom("youtube_channel_feed.xml"),
                    "application/atom+xml",
                ),
                transport.PUBLIC_PAGE_ARTICLE_ROUTE: (
                    200,
                    read_public_page("article.html"),
                    "text/html",
                ),
                transport.PUBLIC_PAGE_CONTROL_ROUTE: (
                    200,
                    read_public_page("control.html"),
                    "text/html",
                ),
            },
        )
        self.artifact = runner.run_acquisition(
            feed_page_manifest(), carrier, clock=clock.monotonic
        )
        self.by_step = {}
        for record in self.artifact.records:
            self.by_step.setdefault(record.step_id, []).append(record)

    def test_the_artifact_holds_every_row_all_five_steps_returned(self):
        self.assertEqual(len(self.artifact.records), 8)
        self.assertEqual(
            [step.records_kept for step in self.artifact.steps], [3, 1, 2, 1, 1]
        )
        self.assertEqual(len(self.opener.opened), 5)
        self.assertEqual(self.artifact.outcome, "ok")

    def test_no_step_reports_needing_a_credential_anywhere_in_the_run(self):
        # Criterion 1 at the artifact, with no credential store in the process.
        # Three documented-keyless adapters and one third-party archive, and
        # nothing in the run says a credential was wanted.
        self.assertNotIn(public_page.AUTH_REQUIRED, self.artifact.loss)
        for record in self.artifact.records:
            with self.subTest(record=record.record_id):
                self.assertNotIn(public_page.AUTH_REQUIRED, record.loss)
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}),
            ["K0", "K3"],
        )

    def test_one_post_seen_by_the_probe_and_by_the_archive_is_two_records(self):
        # The probe says a post exists and when; the archive says what is in it
        # and how it has been received. They name the same post with the same
        # identity string — `t3_` is Reddit's own fullname on both — and they
        # are never folded, because `representation_kind` partitions every
        # grouping key before identity is consulted. A caller gets four fields
        # observed at one moment beside a full record observed at another,
        # rather than one record that quietly claims to be both.
        seen = [
            record
            for record in self.artifact.records
            if record.native_item_id == REDDIT_POST_ID
        ]

        self.assertEqual([record.step_id for record in seen], ["s1-feed", "s2-archive"])
        self.assertEqual(
            [record.representation_kind for record in seen], ["feed", "native"]
        )
        self.assertEqual(
            [record.normalized_locator for record in seen],
            [normalize.normalized_locator(REDDIT_PERMALINK)] * 2,
        )
        folded = [
            sorted(group.member_record_ids)
            for group in self.artifact.groups
            if len(group.member_record_ids) > 1
        ]

        self.assertEqual(folded, [])
        self.assertNotEqual(seen[0].record_id, seen[1].record_id)

    def test_the_probe_carries_no_count_and_the_archive_beside_it_carries_three(self):
        # The distinction the freshness row exists to keep. One of these routes
        # publishes engagement and one does not, and the one that does not says
        # so rather than reporting a zero that would be indistinguishable from
        # a post nobody has voted on.
        probe = self.by_step["s1-feed"][0]
        archived = self.by_step["s2-archive"][0]

        self.assertEqual(probe.engagement, ())
        self.assertIn("engagement_unavailable", probe.loss)
        self.assertEqual(
            sorted(snapshot.metric_name for snapshot in archived.engagement),
            ["num_comments", "score"],
        )
        self.assertIn("third_party_archive", archived.loss)

    def test_each_route_states_its_own_confidence_in_the_time_it_reported(self):
        # The platform's own feed is authoritative about when it published;
        # an independent archive reports the platform's time rather than
        # stating it.
        self.assertEqual(self.by_step["s1-feed"][0].time_confidence, "authoritative")
        self.assertEqual(self.by_step["s2-archive"][0].time_confidence, "reported")

    def test_the_document_read_reaches_the_artifact_with_its_fingerprint(self):
        article = self.by_step["s4-article"][0]

        self.assertEqual(article.body, read_public_page("article.html"))
        self.assertEqual(
            article.exact_content_hash,
            normalize.content_hash(read_public_page("article.html")),
        )
        self.assertEqual(article.canonical_locator, ARTICLE_LOCATOR)
        self.assertEqual(
            [value for name, value in article.attributes
             if name == public_page.CONTENT_TYPE_ATTRIBUTE],
            ["text/html"],
        )
        self.assertIn(
            (public_page.LINK_ATTRIBUTE, "/wiki/Token_bucket"), article.attributes
        )

    def test_two_documents_from_two_selections_are_scoped_by_the_route_that_served(self):
        article = self.by_step["s4-article"][0]
        control = self.by_step["s5-control"][0]

        self.assertEqual(article.group_scope, transport.PUBLIC_PAGE_ARTICLE_ROUTE)
        self.assertEqual(control.group_scope, transport.PUBLIC_PAGE_CONTROL_ROUTE)
        self.assertEqual(article.adapter_id, control.adapter_id)
        self.assertEqual(article.operator_identity, "wikimedia")
        self.assertEqual(control.operator_identity, "iana")

    def test_each_step_names_the_route_it_actually_read(self):
        self.assertEqual(
            [step.route_id for step in self.artifact.steps],
            [
                transport.REDDIT_FEED_ROUTE,
                transport.ARCTIC_SHIFT_POSTS_ROUTE,
                transport.YOUTUBE_CHANNEL_FEED_ROUTE,
                transport.PUBLIC_PAGE_ARTICLE_ROUTE,
                transport.PUBLIC_PAGE_CONTROL_ROUTE,
            ],
        )

    def test_the_feed_probe_and_the_archive_read_are_linked_and_never_merged(self):
        # `link_discovery_hydration` sources an edge from any discovery record
        # whose locator a hydration froze — since 2026-08-17 a feed entry as
        # much as an index hit, which closed the gap this test used to record.
        # The pair is still two records: linked, and never merged, which the
        # representation partition guarantees.
        self.assertEqual(
            [(edge.edge_kind, edge.from_record_id, edge.to_record_id) for edge in self.artifact.edges],
            [("discovery_hydration", "s1-feed#0.0", "s2-archive#0.0")],
        )
        self.assertEqual(
            sorted({record.representation_kind for record in self.artifact.records}),
            ["feed", "native", "page"],
        )
        # The article read is the one hydration nothing here discovered — its
        # locator was frozen from outside this artifact — and it is the one
        # record that says so.
        self.assertEqual(
            sorted(
                record.step_id
                for record in self.artifact.records
                if "discovery_not_recorded" in record.loss
            ),
            ["s4-article"],
        )

    def test_the_syndication_entries_keep_their_own_addresses_and_moments(self):
        entries = self.by_step["s3-channel"]

        self.assertEqual(
            [record.canonical_locator for record in entries],
            [FEED_VIDEO_LOCATOR, "https://www.youtube.com/watch?v=aBcDeFgHiJk"],
        )
        self.assertEqual(entries[0].usable_basis_time, "2026-08-09T15:30:12Z")
        self.assertEqual(entries[0].native_item_id, FEED_VIDEO_ID)
