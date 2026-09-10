from tests.test_adapters_cases.hacker_news_github_ttl import *  # noqa: F401,F403

class HackerNewsGithubArtifactSeamTest(unittest.TestCase):
    """The widest seam: the records a caller keeps, after normalize has run.

    Every check above reads a ``NativePage``, which is an intermediate value.
    "These two reach their measured capability" is a claim about the artifact,
    and the two-surface question only becomes real here: one story read on two
    origins has to arrive as two records that group, ranked on the name each
    surface itself reported.
    """

    def setUp(self):
        clock = helpers.FakeClock()
        carrier, self.opener = helpers.offline_transport(
            clock,
            {
                transport.HN_ALGOLIA_SEARCH_ROUTE: (
                    200,
                    as_a_last_page(read_hacker_news("algolia_search_by_date.json")),
                    "application/json",
                ),
                # One route, two items, in the order the steps read them.
                transport.HN_FIREBASE_ITEM_ROUTE: [
                    (200, read_hacker_news("firebase_story.json"), "application/json"),
                    (200, read_hacker_news("firebase_comment.json"), "application/json"),
                ],
                transport.GITHUB_REST_ROUTE: [
                    (200, read_github("repo.json"), "application/json"),
                    (200, read_github("issues.json"), "application/json"),
                ],
                transport.GITHUB_SEARCH_ROUTE: (
                    200,
                    read_github("search_repositories.json"),
                    "application/json",
                ),
            },
        )
        self.artifact = runner.run_acquisition(
            hacker_news_github_manifest(), carrier, clock=clock.monotonic
        )
        self.by_step = {}
        for record in self.artifact.records:
            self.by_step.setdefault(record.step_id, []).append(record)

    def test_the_artifact_holds_every_row_all_six_steps_returned(self):
        self.assertEqual(len(self.artifact.records), 12)
        self.assertEqual(
            [step.records_kept for step in self.artifact.steps], [4, 1, 1, 1, 3, 2]
        )
        self.assertEqual(len(self.opener.opened), 6)
        self.assertEqual(self.artifact.outcome, "ok")
        self.assertEqual(self.artifact.loss, ())

    def test_neither_platform_reports_needing_a_credential_anywhere_in_the_run(self):
        # Criterion 1 at the artifact, with no credential store in the process:
        # both of these are documented keyless, and nothing in the run says
        # otherwise.
        self.assertNotIn(github_rest.AUTH_REQUIRED, self.artifact.loss)
        for record in self.artifact.records:
            with self.subTest(record=record.record_id):
                self.assertNotIn(github_rest.AUTH_REQUIRED, record.loss)
        self.assertEqual(
            sorted({record.access_class for record in self.artifact.records}), ["K0"]
        )

    def test_one_story_read_on_two_origins_is_two_records_held_together(self):
        # wrong_merge_law rule 1: Algolia's `objectID` is HN's own item id, so
        # the hit and the item share a namespace, an id and a kind. One group
        # of two, never one record — and they disagree about nothing here,
        # which is not why they are kept apart.
        seen = [
            record
            for record in self.artifact.records
            if record.native_item_id == HN_STORY_ID
        ]
        grouped = [
            group for group in self.artifact.groups if len(group.member_record_ids) > 1
        ]

        self.assertEqual([record.step_id for record in seen], ["s1-search", "s2-story"])
        self.assertEqual(
            [record.route_id for record in seen],
            [transport.HN_ALGOLIA_SEARCH_ROUTE, transport.HN_FIREBASE_ITEM_ROUTE],
        )
        # Two origins answered, and each record says which one did.
        self.assertEqual(
            [record.operator_identity for record in seen], ["algolia", "hacker-news"]
        )
        # Two folds in this run, both the same shape: one story read on HN's
        # two origins, and one repository both found by GitHub's search and
        # read from GitHub's core. Each is one group of two.
        folded = [sorted(group.member_record_ids) for group in grouped]
        repository = [
            record for record in self.artifact.records if record.native_item_id == "704212099"
        ]

        self.assertEqual(len(grouped), 2)
        self.assertEqual(sorted({group.key_kind for group in grouped}), ["strong"])
        self.assertIn(sorted(record.record_id for record in seen), folded)
        self.assertEqual(
            [record.step_id for record in repository], ["s4-repository", "s6-search"]
        )
        self.assertIn(sorted(record.record_id for record in repository), folded)

    def test_the_tree_is_walked_by_the_core_one_call_per_item(self):
        # The story hands back the ids of what hangs off it; the caller chose
        # one and the core spent one call on it. The adapter walked nothing:
        # six steps, six calls, and the kid names the story it came from.
        story = self.by_step["s2-story"][0]
        kid = self.by_step["s3-kid"][0]

        self.assertEqual(
            [value for name, value in story.attributes if name == hacker_news.KIDS_KEY],
            ["44831402", "44831377", "44831301"],
        )
        self.assertEqual(kid.native_item_id, HN_KID_ID)
        self.assertEqual(kid.native_parent_id, HN_STORY_ID)
        self.assertEqual(kid.canonical_content_kind, "comment")
        self.assertEqual(len(self.opener.opened), 6)

    def test_each_step_names_the_route_it_actually_read(self):
        # A two-surface adapter is the first thing here that could record a
        # step against a route it never touched: the descriptor the core routes
        # by names one surface, and the step may have read the other.
        self.assertEqual(
            [step.route_id for step in self.artifact.steps],
            [
                transport.HN_ALGOLIA_SEARCH_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_SEARCH_ROUTE,
            ],
        )

    def test_the_work_ledger_charges_each_read_to_the_route_it_left_on(self):
        # The same fact one seam lower: a run's accounting of what it consumed
        # is per route, and two surfaces are two budgets.
        run = runner.run_scheduled(
            hacker_news_github_manifest(),
            helpers.offline_transport(
                helpers.FakeClock(),
                {
                    transport.HN_ALGOLIA_SEARCH_ROUTE: (
                        200,
                        as_a_last_page(read_hacker_news("algolia_search_by_date.json")),
                        "application/json",
                    ),
                    transport.HN_FIREBASE_ITEM_ROUTE: (
                        200,
                        read_hacker_news("firebase_story.json"),
                        "application/json",
                    ),
                    transport.GITHUB_REST_ROUTE: (
                        200,
                        read_github("repo.json"),
                        "application/json",
                    ),
                    transport.GITHUB_SEARCH_ROUTE: (
                        200,
                        read_github("search_repositories.json"),
                        "application/json",
                    ),
                },
            )[0],
        )

        self.assertEqual(
            [event.route_id for event in runner.planned_operations(run.ledger)],
            [
                transport.HN_ALGOLIA_SEARCH_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_REST_ROUTE,
                transport.GITHUB_SEARCH_ROUTE,
            ],
        )

    def test_two_surfaces_rank_together_on_the_name_each_one_reported(self):
        # The payoff of one descriptor per surface. Algolia calls a story's
        # comment count `num_comments` and Firebase calls the same quantity
        # `descendants`; each record is ranked by the name its own surface
        # published, so a view over both is one ranking rather than a list with
        # half of it unranked at the bottom.
        stories = [
            record
            for record in self.artifact.records
            if record.canonical_content_kind == "story"
        ]
        ranked = runner.order_records(stories, "most_commented", self.artifact.as_of)
        counts = []
        for record in ranked:
            named = {snapshot.metric_name: snapshot.value for snapshot in record.engagement}
            counts.append(named.get("num_comments", named.get("descendants")))

        self.assertEqual(len(stories), 4)
        self.assertEqual(counts, [311, 233, 233, 12])
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_an_issue_list_ranks_on_the_count_github_reported(self):
        issues = self.by_step["s5-issues"]
        ranked = runner.order_records(issues, "most_commented", self.artifact.as_of)
        counts = [
            runner.eligible_snapshot(record, "comments", self.artifact.as_of).value
            for record in ranked
        ]

        self.assertEqual(counts, [31, 23, 0])
        # And that is a different view from the newest one, so the ranking is
        # the count's doing rather than the order they arrived in.
        self.assertNotEqual(
            [record.native_item_id for record in ranked],
            [
                record.native_item_id
                for record in runner.order_records(issues, "newest", self.artifact.as_of)
            ],
        )

    def test_every_row_is_the_platform_speaking_for_itself(self):
        # Neither of these is an archive: HN's own search of HN and GitHub's
        # own search of GitHub are both the platform reporting its own items,
        # so nothing carries `third_party_archive`. Each search hit is still a
        # discovery, and the item it led to is linked to it and never merged
        # into it — one edge per selected hit, and no false alarm about the
        # run's own lineage.
        self.assertEqual(
            sorted({record.representation_kind for record in self.artifact.records}),
            ["native"],
        )
        self.assertEqual(
            sorted((edge.from_record_id, edge.to_record_id) for edge in self.artifact.edges),
            [("s1-search#0.0", "s2-story#0.0"), ("s6-search#0.0", "s4-repository#0.0")],
        )
        # The two hydrations no search here led to — a kid the search did
        # not list, and an issues collection nothing indexes — are the two
        # that say so, and only those two.
        self.assertEqual(
            sorted(
                {
                    record.step_id
                    for record in self.artifact.records
                    if "discovery_not_recorded" in record.loss
                }
            ),
            ["s3-kid", "s5-issues"],
        )
        for record in self.artifact.records:
            with self.subTest(record=record.record_id):
                self.assertNotIn("third_party_archive", record.loss)
                self.assertEqual(record.time_confidence, "authoritative")

    def test_a_named_fact_each_route_reported_survives_normalization(self):
        story = self.by_step["s2-story"][0]
        repository = self.by_step["s4-repository"][0]

        self.assertIn(("url", "https://harbourlight.example/70b-two-gpus"), story.attributes)
        self.assertIn(("language", "Python"), repository.attributes)
        self.assertEqual(
            [value for name, value in repository.attributes if name == "topics"],
            ["benchmarks", "inference", "gpu"],
        )

    def test_both_platforms_keep_their_own_moments_and_their_own_addresses(self):
        story = self.by_step["s2-story"][0]
        release_free = self.by_step["s6-search"][0]

        self.assertEqual(story.usable_basis_time, "2026-08-09T16:41:52Z")
        self.assertEqual(story.canonical_locator, HN_PERMALINK + HN_STORY_ID)
        self.assertEqual(
            story.normalized_locator, normalize.normalized_locator(story.canonical_locator)
        )
        self.assertEqual(release_free.canonical_locator, "https://github.com/" + GITHUB_TARGET)
        self.assertEqual(release_free.usable_basis_time, "2024-11-03T09:14:22Z")


# The last three adapters, and the four routes they read. Named here as the
# evidence names them, so a route check reads against the roster row rather
# than against an adapter's own constants.
#
# The 2026-08-10 probes, Reddit: `www.reddit.com/r/<sub>.rss` answered 200 with 32 KB
# in 1.4 s carrying title, link, author and updated, at a ceiling of 1–2
# requests per ~30 s per IP. Every `.json` form answered 403 to three unrelated
# User-Agents.
