from .common import *

def archive_seeds():
    """The two Reddit surfaces, each answering with the bytes it was measured on."""

    return {
        transport.ARCTIC_SHIFT_POSTS_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("arctic_shift_posts_ids.json").read_text(
                encoding="utf-8"
            ),
            "application/json",
        ),
        transport.REDDIT_FEED_ROUTE: (
            200,
            REDDIT_FEED_FIXTURE_DIR.joinpath("subreddit_new.xml").read_text(encoding="utf-8"),
            "application/atom+xml",
        ),
    }


def reddit_manifest():
    """One dispatch over one post, seen by the archive and by Reddit's own feed.

    Both steps, rather than the archive alone, because half of the `K3` law is
    that the label means something: a keyless route on the same platform,
    about the same post, in the same artifact, has to come back without it.
    """

    return schema.AcquisitionManifest(
        manifest_id="m-k3",
        mode="staged",
        as_of="2026-08-10T09:05:00Z",
        steps=(
            schema.AcquisitionStep(
                step_id="s1-archive",
                kind="hydration",
                adapter_id="reddit_archive",
                selected_hits=(
                    schema.SelectedHit(
                        discovery_locator="https://www.reddit.com/r/LocalLLaMA/comments/"
                        + ARCHIVED_POST_ID
                        + "/what_is_the_best_local_model_right_now/",
                        target_id=ARCHIVED_POST_ID,
                    ),
                ),
                max_items=5,
            ),
            schema.AcquisitionStep(
                step_id="s2-feed",
                kind="discovery",
                adapter_id="reddit_feed",
                query=REDDIT_SUBREDDIT,
                max_items=20,
            ),
        ),
    )


def records_from(fetch, step, request):
    """Run one adapter — shipped or written beside the tree — into artifact records."""

    clock = helpers.FakeClock()
    carrier, _ = helpers.offline_transport(clock, archive_seeds())
    page = fetch(carrier, request)
    return normalize.normalize_page(page, step, "artifact:m-k3", "m-k3")


ARCHIVE_STEP = reddit_manifest().steps[0]
FEED_STEP = reddit_manifest().steps[1]
ARCHIVE_REQUEST = adapters.AdapterRequest(
    step_id=ARCHIVE_STEP.step_id, target_ids=(ARCHIVED_POST_ID,)
)
FEED_REQUEST = adapters.AdapterRequest(step_id=FEED_STEP.step_id, query=REDDIT_SUBREDDIT)


class ThirdPartyArchiveTest(unittest.TestCase):
    """Criterion 5: a `K3` record says whose copy it is.

    Arctic Shift is volunteer-run and has no uptime guarantee and no
    obligation to be complete. A caller who reads its answer as Reddit's own
    reads a mirror's gap as a platform gap — the mirror image of the
    interception rule the captive-portal caveat turns on — so the label and
    the operator travel on
    every row, and the row is where a caller reads them.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(clock, archive_seeds())
        self.artifact = runner.run_acquisition(
            reddit_manifest(), carrier, clock=clock.monotonic
        )
        self.archived = [
            record for record in self.artifact.records if record.access_class == ARCHIVE_CLASS
        ]
        # The feed entry about the archived post: the one discovery record whose
        # locator the archive step froze, and so the source of the one edge.
        self.feed_entry = [
            record
            for record in self.artifact.records
            if record.access_class != ARCHIVE_CLASS
            and record.normalized_locator == self.archived[0].discovery_locator
        ][0]

    def test_the_run_read_both_reddit_surfaces_and_kept_rows_from_each(self):
        # The oracle below is only worth its verdict if it read something: one
        # archived post and the feed's three entries, from two routes.
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(len(self.archived), 1)
        self.assertEqual(len(self.artifact.records) - len(self.archived), 3)
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K0", "K3"]
        )

    def test_every_archive_record_carries_the_label_and_names_its_operator(self):
        assert_an_archive_never_speaks_as_the_platform(
            self, shipped_roster(), self.artifact.records
        )

    def test_the_operator_the_records_name_is_the_archive_and_not_reddit(self):
        for record in self.archived:
            with self.subTest(record=record.record_id):
                self.assertEqual(record.operator_identity, "arctic-shift")
                self.assertEqual(record.platform, "reddit")
                self.assertEqual(record.loss, (THIRD_PARTY_ARCHIVE,))
                self.assertEqual(record.time_confidence, "reported")

    def test_the_archive_row_is_linked_to_the_feed_entry_that_discovered_it(self):
        # One dispatch reads Reddit's feed and hydrates from the archive.
        # `link_discovery_hydration` sources an edge from any discovery record
        # whose locator the hydration froze — a feed entry since 2026-08-17,
        # not only an index hit — so the pair is a linked pair, and the archive
        # row carries no `discovery_not_recorded`: this run did discover it.
        self.assertEqual(
            [(edge.from_record_id, edge.to_record_id) for edge in self.artifact.edges],
            [(self.feed_entry.record_id, record.record_id) for record in self.archived],
        )
        self.assertEqual(
            sorted({record.representation_kind for record in self.artifact.records}),
            ["feed", "native"],
        )
        self.assertEqual(
            [
                record.record_id
                for record in self.artifact.records
                if DISCOVERY_NOT_RECORDED in record.loss
            ],
            [],
        )

    def test_reddits_own_feed_about_the_same_post_is_not_wearing_the_label(self):
        # Same platform, same post, one artifact. The feed's row states an
        # absence of its own — no engagement — and says nothing about archives.
        feed = [
            record for record in self.artifact.records if record.route_id == "reddit_feed"
        ]

        self.assertTrue(feed)
        for record in feed:
            with self.subTest(record=record.record_id):
                self.assertNotIn(THIRD_PARTY_ARCHIVE, record.loss)
                self.assertEqual(record.operator_identity, "reddit")
                self.assertEqual(record.time_confidence, "authoritative")

    def test_the_only_archive_surface_in_the_roster_is_the_one_that_declares_it(self):
        archives = [
            surface for surface in shipped_roster() if surface.access_class == ARCHIVE_CLASS
        ]

        # Two archives since 2026-08-17: the Reddit one, and FxTwitter, which
        # is an independent operator reading X on this package's behalf. Both
        # carry the label on every record, which is the half of the law that
        # matters; being the only one was never the claim.
        self.assertEqual(
            [surface.route_id for surface in archives],
            ["arctic_shift_posts_ids", "fxtwitter_api"],
        )
        self.assertEqual(archives[0].standing_loss, (THIRD_PARTY_ARCHIVE,))
        self.assertEqual(archives[0].operator_identity, "arctic-shift")
