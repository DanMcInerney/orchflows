"""The coverage seam: hydration planning, and the two reviews.

Every case here is anchored to a failure measured on 2026-08-17, when a caller
that had read the contract shipped two valid manifests that under-acquired.
The point of each assertion is that the advisory names the thing that actually
went wrong, and stays quiet where the manifest was right.
"""

from __future__ import annotations

import unittest

from super_research import coverage, schema


def record(
    record_id,
    adapter_id,
    native_item_id="n1",
    locator="https://example.invalid/a",
    discovery_locator="",
    representation_kind="index",
):
    """One discovery record, with every field the schema requires supplied."""

    return schema.AcquisitionRecord(
        record_id=record_id,
        artifact_id="art",
        manifest_id="man",
        step_id="s1",
        adapter_id=adapter_id,
        adapter_version="1",
        route_id="r",
        access_class="K2",
        operator_identity="",
        platform="p",
        native_identity_namespace="ns",
        group_scope="g",
        representation_kind=representation_kind,
        canonical_content_kind="post",
        native_item_id=native_item_id,
        native_parent_id="",
        canonical_locator=locator,
        normalized_locator=locator,
        exact_content_hash="h",
        title="t",
        body="b",
        author="a",
        community="c",
        published_at="2026-08-17T00:00:00Z",
        observed_at="2026-08-17T00:00:00Z",
        time_confidence="authoritative",
        usable_basis_time="2026-08-17T00:00:00Z",
        engagement=(),
        page_index=0,
        list_index=0,
        native_position=0,
        discovery_locator=discovery_locator,
        outcome="ok",
        loss=(),
    )


def step(step_id, kind, adapter_id, **kw):
    return schema.AcquisitionStep(
        step_id=step_id, kind=kind, adapter_id=adapter_id, max_items=kw.pop("max_items", 500), **kw
    )


def manifest(*steps):
    return schema.AcquisitionManifest(
        manifest_id="m", mode="fused", as_of="2026-08-17T19:00:00Z", steps=tuple(steps)
    )


def codes(advisories):
    return sorted({found.code for found in advisories})


def subjects(advisories, code):
    return sorted(found.subject for found in advisories if found.code == code)


class PlanHydrationTest(unittest.TestCase):
    def test_a_reddit_permalink_is_the_target_and_is_not_taken_apart(self):
        """Reddit's comments grammar takes the permalink a row carried.

        Re-deriving `<subreddit>/<post id>` here would be this module parsing
        an address the adapter already parses, and a second parser is a second
        thing to get wrong.
        """

        permalink = "https://www.reddit.com/r/Bitcoin/comments/1vos2t2/just_sold_it_all"
        plan = coverage.plan_hydration(
            [record("r1", "reddit_shreddit", locator=permalink)],
            "reddit_shreddit",
            "comments",
            "cm",
            max_items=40,
        )

        self.assertEqual(plan.step.kind, "hydration")
        self.assertEqual(plan.step.adapter_id, "reddit_shreddit")
        self.assertEqual(len(plan.step.selected_hits), 1)
        self.assertEqual(plan.step.selected_hits[0].target_id, "comments:" + permalink)
        # The locator is what ties the hydration back to its discovery, so it
        # rides verbatim and is never recomposed.
        self.assertEqual(plan.step.selected_hits[0].discovery_locator, permalink)
        self.assertEqual(plan.skipped, ())

    def test_youtube_targets_the_native_id_under_the_named_operation(self):
        plan = coverage.plan_hydration(
            [record("y1", "youtube_innertube", native_item_id="4jZjM0Zs_LY")],
            "youtube_innertube",
            "transcript",
            "tx",
            max_items=400,
        )

        self.assertEqual(plan.step.selected_hits[0].target_id, "transcript:4jZjM0Zs_LY")

    def test_records_off_the_adapter_are_listed_and_never_silently_dropped(self):
        """The leftovers are returned, for `relevance.partition`'s reason.

        A selection whose leftovers were never listed is a silent drop wearing
        a plan's clothes.
        """

        plan = coverage.plan_hydration(
            [record("a", "reddit_shreddit"), record("b", "hacker_news")],
            "reddit_shreddit",
            "comments",
            "cm",
            max_items=40,
        )

        self.assertEqual(len(plan.step.selected_hits), 1)
        self.assertEqual([held.record_id for held in plan.skipped], ["b"])
        self.assertIn("off adapter hacker_news", plan.skipped[0].reason)

    def test_the_callers_own_limit_is_reported_as_the_reason_it_stopped(self):
        rows = [record("r%d" % index, "reddit_shreddit", locator="u%d" % index) for index in range(5)]

        plan = coverage.plan_hydration(rows, "reddit_shreddit", "comments", "cm", 40, limit=2)

        self.assertEqual(len(plan.step.selected_hits), 2)
        self.assertEqual(len(plan.skipped), 3)
        self.assertTrue(all("limit" in held.reason for held in plan.skipped))

    def test_a_record_already_hydrated_is_not_hydrated_again(self):
        plan = coverage.plan_hydration(
            [
                record(
                    "h1",
                    "reddit_shreddit",
                    discovery_locator="https://example.invalid/parent",
                    representation_kind="native",
                )
            ],
            "reddit_shreddit",
            "comments",
            "cm",
            max_items=40,
        )

        self.assertEqual(plan.step.selected_hits, ())
        self.assertEqual(plan.skipped[0].reason, "already hydrated")

    def test_an_unaddressable_record_is_skipped_rather_than_addressed_by_the_other_id(self):
        """A missing native id is never quietly replaced by the locator.

        Guessing which id a route meant is how a hydration lands on the wrong
        item and still looks authorized.
        """

        plan = coverage.plan_hydration(
            [record("y1", "youtube_innertube", native_item_id="")],
            "youtube_innertube",
            "player",
            "pl",
            max_items=5,
        )

        self.assertEqual(plan.step.selected_hits, ())
        self.assertIn("native item id", plan.skipped[0].reason)

    def test_an_undeclared_adapter_or_operation_is_refused(self):
        with self.assertRaises(coverage.CoverageError):
            coverage.plan_hydration([], "stocktwits", "comments", "s", 10)
        with self.assertRaises(coverage.CoverageError):
            coverage.plan_hydration([], "youtube_innertube", "captions", "s", 10)

    def test_a_cap_that_is_not_a_positive_integer_is_refused(self):
        with self.assertRaises(coverage.CoverageError):
            coverage.plan_hydration([], "youtube_innertube", "player", "s", 0)


class ReviewManifestTest(unittest.TestCase):
    def test_discovery_with_no_hydration_names_what_the_run_will_not_carry(self):
        """The 2026-08-17 YouTube case, caught before the run.

        `search:` was called and the report said "no transcripts, no view
        counts". The manifest was valid; the depth was never asked for.
        """

        found = coverage.review_manifest(
            manifest(step("yt", "discovery", "youtube_innertube", query="search:btc"))
        )

        self.assertEqual(subjects(found, coverage.DEPTH_NOT_PLANNED), ["youtube_innertube"])
        self.assertIn("transcripts", found[0].message)

    def test_planning_the_hydration_silences_it(self):
        found = coverage.review_manifest(
            manifest(
                step("yt", "discovery", "youtube_innertube", query="search:btc"),
                step(
                    "tx",
                    "hydration",
                    "youtube_innertube",
                    query="transcript",
                    selected_hits=(schema.SelectedHit("https://example.invalid/a", "transcript:a"),),
                ),
            )
        )

        self.assertNotIn(coverage.DEPTH_NOT_PLANNED, codes(found))

    def test_an_unwindowed_step_is_named_only_where_the_origin_would_have_bounded_it(self):
        """The 2026-08-17 news case, and the false positive it used to carry.

        `web_search` pushes Google News `when:` server-side, so omitting the
        window there is strictly wasteful. `prediction_markets` does not, and
        an unwindowed markets step is ordinarily deliberate — open markets
        closing next year are the point. Warning about both trained a reader
        to skip the line that mattered.
        """

        found = coverage.review_manifest(
            manifest(
                step("rd", "discovery", "reddit_shreddit", query="search:btc",
                     window_start="2026-07-18T00:00:00Z"),
                step("web", "discovery", "web_search", query="gnews:btc"),
                step("pm", "discovery", "prediction_markets", query="polymarket:btc"),
            )
        )

        self.assertEqual(subjects(found, coverage.WINDOW_ABSENT), ["web"])

    def test_no_window_anywhere_is_a_choice_and_draws_nothing(self):
        """An all-evergreen manifest is a legitimate shape, not an oversight.

        Windowing is per step and optional; a run that bounds nothing has
        decided that, and this check only fires on the inconsistency.
        """

        found = coverage.review_manifest(
            manifest(step("web", "discovery", "web_search", query="gnews:btc"))
        )

        self.assertNotIn(coverage.WINDOW_ABSENT, codes(found))

    def test_a_cap_under_the_page_size_is_named_before_the_read_not_during_it(self):
        found = coverage.review_manifest(
            manifest(step("bs", "discovery", "bluesky", query="search:btc", max_items=50))
        )

        self.assertIn(coverage.CAP_BELOW_PAGE_SIZE, codes(found))

    def test_a_clean_manifest_draws_nothing(self):
        """The check that keeps the others honest: silence is reachable."""

        found = coverage.review_manifest(
            manifest(
                step("hn", "discovery", "hacker_news", query="search:btc", max_items=1000,
                     window_start="2026-07-18T00:00:00Z"),
                step(
                    "tree",
                    "hydration",
                    "hacker_news",
                    query="tree",
                    selected_hits=(schema.SelectedHit("https://example.invalid/a", "tree:1"),),
                ),
            )
        )

        self.assertEqual(found, ())


class ReviewArtifactTest(unittest.TestCase):
    def artifact(self, steps=(), records=()):
        return schema.AcquisitionArtifact(
            artifact_id="a",
            manifest_id="m",
            mode="fused",
            as_of="2026-08-17T19:00:00Z",
            records=tuple(records),
            steps=tuple(steps),
            edges=(),
            groups=(),
            outcome="ok",
            loss=(),
        )

    def result(self, step_id, outcome="ok", loss=()):
        return schema.StepResult(
            step_id=step_id,
            adapter_id="bluesky",
            route_id="r",
            pages=1,
            records_received=0,
            records_kept=0,
            outcome=outcome,
            loss=tuple(loss),
            warnings=(),
        )

    def test_a_typed_loss_is_named_as_something_the_report_must_state(self):
        found = coverage.review_artifact(
            self.artifact(steps=[self.result("bs", "failed", ("auth_required",))])
        )

        self.assertEqual(codes(found), [coverage.STEP_CARRIED_LOSS])
        self.assertIn("not an absence", found[0].message)

    def test_a_truncated_recall_gets_one_advisory_and_not_two(self):
        """Two advisories for one loss is how a reader learns to skim them."""

        found = coverage.review_artifact(
            self.artifact(steps=[self.result("x", "partial", ("recall_window_partial",))])
        )

        self.assertEqual(codes(found), [coverage.RECALL_WAS_A_WINDOW])

    def test_a_run_that_discovered_and_never_deepened_says_so(self):
        found = coverage.review_artifact(
            self.artifact(records=[record("r1", "reddit_shreddit")])
        )

        self.assertEqual(subjects(found, coverage.NOTHING_HYDRATED), ["reddit_shreddit"])

    def test_a_run_that_hydrated_what_it_discovered_draws_nothing(self):
        found = coverage.review_artifact(
            self.artifact(
                records=[
                    record("r1", "reddit_shreddit"),
                    record(
                        "r2",
                        "reddit_shreddit",
                        discovery_locator="https://example.invalid/a",
                        representation_kind="native",
                    ),
                ]
            )
        )

        self.assertEqual(found, ())


class NoIOTest(unittest.TestCase):
    def test_the_module_calls_nothing_that_opens_a_file_or_a_socket(self):
        """The seam's reliability bar, read off the syntax and not the prose.

        Asserted against the AST rather than the source text: the module's own
        docstring says it "reaches no socket", and a substring scan fails on
        the sentence that states the guarantee.
        """

        import ast
        import inspect

        called = set()
        for node in ast.walk(ast.parse(inspect.getsource(coverage))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)

        for forbidden in ("open", "urlopen", "socket", "Path", "read_text", "write_text"):
            self.assertNotIn(forbidden, called, forbidden)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
