from tests.test_adapters_cases.hacker_news_read import *  # noqa: F401,F403

def typed_hacker_news_pages(module):
    """Type every measured case through one adapter's own ``fetch_native_page``."""

    return {
        row["case_name"]: hn_page(
            row["body_fixture"],
            status=row["status"],
            query=row["query"],
            target_id=row["target_id"],
            cursor=row["cursor"],
            content_type=(
                "text/html" if row["body_fixture"].endswith(".txt") else "application/json"
            ),
            module=module,
        )[0]
        for row in hacker_news_cases()
    }


def assert_an_absence_is_never_a_moved_payload(case, adapter_id, pages):
    """The oracle: nothing here is both an answer of no rows and a shape change.

    ``pages`` maps a measured case name to the ``NativePage`` some adapter
    produced for it. Two confusions, one per direction. HN answers a request
    for an item it does not have with 200 and `null`, and Algolia answers a
    query nothing matched with 200 and an empty list; typing either as
    `schema_drift` sends a reader hunting a payload change over an ordinary
    answer. And a payload that really did move must never arrive as one of
    those, because then the platform looks quiet while this package reads the
    wrong keys.
    """

    for row in hacker_news_cases():
        name = row["case_name"]
        case.assertIn(name, pages, "{0} produced no page for case {1}".format(adapter_id, name))
        page = pages[name]
        loss = tuple(page.loss)
        detail = " {0} typed case {1} as outcome {2} loss {3}".format(
            adapter_id, name, page.outcome, loss
        )
        if row["answer_kind"] in ("absent", "no_matches"):
            if hacker_news.SCHEMA_DRIFT in loss:
                case.fail(
                    "an answer stating there is nothing there was recorded as a payload"
                    " that moved:" + detail
                )
            if page.records:
                case.fail("an answer stating there is nothing there carried rows:" + detail)
            if not page.warnings:
                case.fail("an empty answer was returned with nothing said about it:" + detail)
        elif row["answer_kind"] == "drifted":
            if page.outcome != "failed":
                case.fail("a payload that moved was recorded as an answer:" + detail)
            if page.records:
                case.fail("a payload that moved still produced rows:" + detail)
        elif row["answer_kind"] == "records" and not page.records:
            case.fail("an answer carrying rows produced none:" + detail)
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


class HackerNewsAbsenceIsNotDriftTest(unittest.TestCase):
    """Criterion 1's other half: an answer of nothing is an answer."""

    def test_every_measured_case_is_typed_as_its_evidence_says(self):
        assert_an_absence_is_never_a_moved_payload(
            self, "hacker_news", typed_hacker_news_pages(hacker_news)
        )

    def test_an_item_hn_does_not_have_is_an_answer_and_never_a_failure(self):
        page, _ = hn_page("firebase_absent_item.json", target_id=HN_ABSENT_ID)

        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())
        self.assertEqual(page.records, ())
        self.assertIn(HN_ABSENT_ID, " ".join(page.warnings))

    def test_a_query_that_matched_nothing_is_not_an_index_that_moved(self):
        matched, _ = hn_page("algolia_no_matches.json", query="a phrase")
        moved, _ = hn_page("algolia_reshaped.json", query="local models")

        self.assertEqual(matched.outcome, "empty")
        self.assertEqual(matched.loss, ())
        self.assertEqual(moved.outcome, "failed")
        self.assertEqual(moved.loss, (hacker_news.SCHEMA_DRIFT,))
        # The drift names the container it looked for, so a reader knows which
        # shape to go and check.
        self.assertIn(hacker_news.HITS_KEY, " ".join(moved.warnings))

    def test_neither_surface_calls_a_keyless_route_credentialed(self):
        # Criterion 1: with no credential store anywhere in this run, no answer
        # either surface can give is `auth_required`.
        typed = typed_hacker_news_pages(hacker_news)

        for name, page in sorted(typed.items()):
            with self.subTest(case=name):
                self.assertNotIn("auth_required", page.loss)


WRONG_HN_ADAPTERS = ("absent_item_as_drift_adapter", "drift_as_no_matches_adapter")


class HackerNewsOracleCanFailTest(unittest.TestCase):
    """The oracle above rejects each confusion, and accepts the shipped adapter.

    Each wrong adapter is the shipped one with a single conclusion changed,
    written beside the tree and loaded by path, so a rejection is attributable
    to that conclusion and nothing under test was mutated to produce it.
    """

    def _pages(self, name):
        return typed_hacker_news_pages(load_adapter_fixture(name, directory=HN_FIXTURE_DIR))

    def test_an_absent_item_read_as_a_moved_payload_fails_the_oracle(self):
        with self.assertRaisesRegex(AssertionError, "recorded as a payload that moved"):
            assert_an_absence_is_never_a_moved_payload(
                self, "absent_item_as_drift_adapter", self._pages(WRONG_HN_ADAPTERS[0])
            )

    def test_a_moved_payload_read_as_a_search_with_no_matches_fails_the_oracle(self):
        with self.assertRaisesRegex(AssertionError, "recorded as an answer"):
            assert_an_absence_is_never_a_moved_payload(
                self, "drift_as_no_matches_adapter", self._pages(WRONG_HN_ADAPTERS[1])
            )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_an_absence_is_never_a_moved_payload(
            self, "hacker_news", typed_hacker_news_pages(hacker_news)
        )

    def test_nothing_in_the_package_can_reach_either_wrong_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for wrong in WRONG_HN_ADAPTERS
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])


class HackerNewsDescriptorTest(unittest.TestCase):
    """One adapter, two surfaces, and a budget for each route it can reach."""

    def test_each_surface_declares_the_route_it_reads_under_one_adapter_id(self):
        self.assertEqual(
            [descriptor.route_id for descriptor in hacker_news.SURFACE_DESCRIPTORS],
            [
                transport.HN_FIREBASE_ITEM_ROUTE,
                transport.HN_ALGOLIA_SEARCH_ROUTE,
                transport.HN_ALGOLIA_ITEM_ROUTE,
            ],
        )
        for descriptor in hacker_news.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.adapter_id, "hacker_news")
                self.assertEqual(descriptor.access_class, "K0")
                self.assertEqual(descriptor.platform, "hackernews")
                self.assertEqual(descriptor.native_identity_namespace, "hackernews")
                self.assertEqual(descriptor.representation_kind, "native")
                # `K3` carries `third_party_archive`; this is HN's own index of
                # itself and HN's own item store, so neither surface does.
                self.assertEqual(descriptor.standing_loss, ())
                self.assertEqual(descriptor.volatile_identifiers, ())

    def test_nothing_was_measured_here_so_nothing_is_declared(self):
        # The 2026-08-10 probes record "no throttle observed" and no latency for
        # either surface. An unmeasured ceiling is not one to spend, so both
        # keep the protocol's conservative defaults rather than a number this
        # ticket would have had to invent.
        for descriptor in hacker_news.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(
                    runner.route_budgets()[descriptor.route_id],
                    runner.RouteBudget(
                        min_interval_ms=adapters.DEFAULT_MIN_INTERVAL_MS,
                        burst=adapters.DEFAULT_BURST,
                        cooldown_ms=adapters.DEFAULT_COOLDOWN_MS,
                    ),
                )

    def test_each_surface_declares_the_comment_count_its_own_route_reports(self):
        # The same quantity under two surfaces' own names: Firebase calls a
        # story's comment count `descendants` and Algolia calls it
        # `num_comments`. Declaring either under the other's name would be this
        # package inventing a vocabulary; declaring neither would leave
        # `most_commented` ranking on a number nobody reported.
        by_route = {
            descriptor.route_id: descriptor for descriptor in hacker_news.SURFACE_DESCRIPTORS
        }

        self.assertEqual(
            by_route[transport.HN_FIREBASE_ITEM_ROUTE].comment_count_metric,
            hacker_news.DESCENDANTS_METRIC,
        )
        self.assertEqual(
            by_route[transport.HN_ALGOLIA_SEARCH_ROUTE].comment_count_metric,
            hacker_news.NUM_COMMENTS_METRIC,
        )
        for descriptor in hacker_news.SURFACE_DESCRIPTORS:
            with self.subTest(route=descriptor.route_id):
                self.assertEqual(descriptor.reply_count_metric, "")

    def test_the_core_reaches_it_by_both_literal_branches_and_sees_both_surfaces(self):
        self.assertIn("hacker_news", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("hacker_news"), hacker_news.DESCRIPTOR)
        self.assertEqual(
            runner.surface_descriptors("hacker_news"), hacker_news.SURFACE_DESCRIPTORS
        )

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.HN_FIREBASE_ITEM_ROUTE: (
                    200,
                    read_hacker_news("firebase_story.json"),
                    "application/json",
                )
            },
        )
        page = runner.call_adapter("hacker_news", carrier, hn_request(target_id=HN_STORY_ID))

        self.assertEqual(len(page.records), 1)
        self.assertEqual(len(opener.opened), 1)
